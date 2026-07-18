local M = {}
local adapters = {}
local adapter_runtime = {}

local slow_call_nanoseconds = 5 * 1000 * 1000
local issue_limit = 3
local cooldown_nanoseconds = 5 * 1000 * 1000 * 1000

local type_names = {
  file = "file", dir = "directory", directory = "directory",
  link = "symbolicLink", symbolicLink = "symbolicLink", socket = "socket",
  fifo = "fifo", char = "characterDevice", characterDevice = "characterDevice",
  block = "blockDevice", blockDevice = "blockDevice",
}
local selection_states = { marked = true, unmarked = true }
local clipboard_states = { copied = true, cut = true, none = true }
local action_names = {
  add = true, change = true, copy = true, create = true, delete = true,
  move = true, multiple = true, rename = true, restore = true,
}
local action_results = { success = true, cancelled = true, failed = true }

local function utf8_sequence_length(value, offset)
  local first = value:byte(offset)
  if not first then return nil end
  if first <= 0x7f then return 1 end

  local second = value:byte(offset + 1)
  if first >= 0xc2 and first <= 0xdf then
    return second and second >= 0x80 and second <= 0xbf and 2 or nil
  end

  local third = value:byte(offset + 2)
  if first == 0xe0 then
    return second and second >= 0xa0 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf and 3 or nil
  end
  if (first >= 0xe1 and first <= 0xec) or (first >= 0xee and first <= 0xef) then
    return second and second >= 0x80 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf and 3 or nil
  end
  if first == 0xed then
    return second and second >= 0x80 and second <= 0x9f
      and third and third >= 0x80 and third <= 0xbf and 3 or nil
  end

  local fourth = value:byte(offset + 3)
  if first == 0xf0 then
    return second and second >= 0x90 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf
      and fourth and fourth >= 0x80 and fourth <= 0xbf and 4 or nil
  end
  if first >= 0xf1 and first <= 0xf3 then
    return second and second >= 0x80 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf
      and fourth and fourth >= 0x80 and fourth <= 0xbf and 4 or nil
  end
  if first == 0xf4 then
    return second and second >= 0x80 and second <= 0x8f
      and third and third >= 0x80 and third <= 0xbf
      and fourth and fourth >= 0x80 and fourth <= 0xbf and 4 or nil
  end
  return nil
end

local function bounded(value, maximum)
  if type(value) ~= "string" then return "" end
  local offset, boundary = 1, 0
  while offset <= #value do
    local sequence_length = utf8_sequence_length(value, offset)
    if not sequence_length then return "" end
    local sequence_end = offset + sequence_length - 1
    if sequence_end > maximum then break end
    boundary = sequence_end
    offset = sequence_end + 1
  end
  return boundary == #value and value or value:sub(1, boundary)
end

local function normalize_entry(entry)
  if type(entry) ~= "table" then return nil end
  local name = bounded(entry.name, 512)
  if name == "" then return nil end
  local selection_state = selection_states[entry.selectionState] and entry.selectionState or nil
  local clipboard_state = clipboard_states[entry.clipboardState] and entry.clipboardState or nil
  return {
    name = name,
    path = bounded(entry.path, 2048),
    type = type_names[entry.type] or bounded(entry.type, 64),
    marked = entry.marked == true or selection_state == "marked"
      or clipboard_state == "copied" or clipboard_state == "cut",
    selectionState = selection_state,
    clipboardState = clipboard_state,
    expanded = type(entry.expanded) == "boolean" and entry.expanded or nil,
    size = type(entry.size) == "number" and entry.size or nil,
  }
end

local function normalize_manager(manager, fallback_name)
  if type(manager) ~= "table" then return nil end
  local name = bounded(manager.name, 64)
  if name == "" then name = bounded(fallback_name, 64) end
  if name == "" then return nil end
  return {
    name = name,
    root = bounded(manager.root, 2048),
    currentDirectory = bounded(manager.currentDirectory, 2048),
    entry = normalize_entry(manager.entry),
  }
end

local function runtime_for(name)
  local runtime = adapter_runtime[name]
  if runtime then return runtime end
  runtime = {
    failureCount = 0,
    slowCallCount = 0,
    cooldownCount = 0,
    buffers = {},
  }
  adapter_runtime[name] = runtime
  return runtime
end

local function buffer_runtime(name)
  local runtime = runtime_for(name)
  local buffer = vim.api.nvim_get_current_buf()
  local value = runtime.buffers[buffer]
  if not value then
    value = { issues = {}, active = false, disabledUntil = 0 }
    runtime.buffers[buffer] = value
  end
  return runtime, value
end

local function adapter_disabled(name)
  local runtime, value = buffer_runtime(name)
  local disabled = value.disabledUntil > vim.uv.hrtime()
  if not disabled then value.disabledUntil = 0 end
  return disabled, value, runtime
end

local function record_issue(runtime, value, phase, slow)
  if slow then
    runtime.slowCallCount = runtime.slowCallCount + 1
    runtime.lastIssue = phase .. "Slow"
  else
    runtime.failureCount = runtime.failureCount + 1
    runtime.lastIssue = phase .. "Error"
  end
  local key = phase .. (slow and "Slow" or "Error")
  value.issues[key] = (value.issues[key] or 0) + 1
  if value.issues[key] >= issue_limit then
    value.issues[key] = 0
    value.disabledUntil = vim.uv.hrtime() + cooldown_nanoseconds
    runtime.cooldownCount = runtime.cooldownCount + 1
  end
end

local function protected_call(name, phase, callback)
  local disabled, value, runtime = adapter_disabled(name)
  if disabled then return false, nil, "disabled" end
  local started = vim.uv.hrtime()
  local ok, result = pcall(callback)
  local slow = vim.uv.hrtime() - started > slow_call_nanoseconds
  if not ok then
    record_issue(runtime, value, phase, false)
    return false, nil, "error"
  end
  value.issues[phase .. "Error"] = 0
  if slow then
    record_issue(runtime, value, phase, true)
  else
    value.issues[phase .. "Slow"] = 0
  end
  return true, result, nil
end

local function netrw_wide_column(line)
  local width = tonumber(vim.b.netrw_cpf)
  if not width or width < 1 then return nil end
  local virtual_column = vim.fn.virtcol(".")
  local start_virtual = math.floor((math.max(1, virtual_column) - 1) / width) * width + 1
  local line_number = vim.api.nvim_win_get_cursor(0)[1]
  local start_byte = vim.fn.virtcol2col(0, line_number, start_virtual)
  if not start_byte or start_byte < 1 then return nil end
  local next_virtual = start_virtual + width
  local end_byte = #line
  if next_virtual <= vim.fn.strdisplaywidth(line) then
    local next_byte = vim.fn.virtcol2col(0, line_number, next_virtual)
    if type(next_byte) == "number" and next_byte > start_byte then end_byte = next_byte - 1 end
  end
  return line:sub(start_byte, end_byte):gsub("%s+$", "")
end

local function netrw_strip_tree_depth(line)
  local stripped = line
  local indented = false
  while stripped:sub(1, 2) == "| " do
    stripped = stripped:sub(3)
    indented = true
  end
  while stripped:sub(1, 4) == "│ " do
    stripped = stripped:sub(5)
    indented = true
  end
  return stripped, indented
end

local function netrw_displayed_name(line)
  local banner_end = tonumber(vim.w.netrw_bannercnt)
  if banner_end and vim.api.nvim_win_get_cursor(0)[1] < banner_end then return nil end
  local style = tonumber(vim.w.netrw_liststyle)
    or tonumber(vim.g.netrw_liststyle) or 0
  local displayed
  if style == 0 then
    displayed = line:gsub("\t%s*%-%->.*$", "")
  elseif style == 1 then
    displayed = line:match("^(.*%S)%s%s+%-?%d+%s")
  elseif style == 2 then
    displayed = netrw_wide_column(line)
  elseif style == 3 then
    displayed = netrw_strip_tree_depth(line)
    displayed = displayed:gsub("\t%s*%-%->.*$", "")
  end
  if type(displayed) ~= "string" or displayed == "" then
    displayed = vim.fn.expand("<cfile>")
  end
  if type(displayed) ~= "string" then return nil end
  displayed = displayed:gsub("%s+$", ""):gsub("[/*@=|]$", "")
  return displayed ~= "" and displayed or nil
end

local function netrw_entry()
  if vim.bo.filetype ~= "netrw" then return nil end
  local line = vim.api.nvim_get_current_line()
  local root = type(vim.b.netrw_curdir) == "string" and vim.b.netrw_curdir
    or vim.api.nvim_buf_get_name(0)
  local manager = {
    name = "netrw", root = bounded(root, 2048),
    currentDirectory = bounded(root, 2048),
  }
  if line:match('^%s*"') then return manager end
  local displayed = netrw_displayed_name(line)
  if not displayed then return manager end
  local path
  local _, tree_indented = netrw_strip_tree_depth(line)
  local tree_root = tonumber(vim.w.netrw_liststyle) == 3
    and not tree_indented
    and displayed == vim.fn.fnamemodify(root, ":t")
  if displayed == "." or tree_root then
    path = root
  elseif displayed == ".." then
    path = vim.fn.fnamemodify(root, ":h")
  else
    path = root:gsub("[/\\]$", "") .. "/" .. displayed
  end
  local raw_type = vim.fn.getftype(path)
  if raw_type == "" then
    raw_type = line:match("/%s*$") and "dir" or (line:match("@") and "link" or "file")
  end
  local marked = false
  for _, match in ipairs(vim.fn.getmatches()) do
    if match.group == "netrwMarkFile" and type(match.pattern) == "string"
      and vim.fn.match(line, match.pattern) >= 0 then
      marked = true
      break
    end
  end
  manager.entry = normalize_entry({
    name = displayed, path = path, type = raw_type,
    marked = marked, selectionState = marked and "marked" or "unmarked",
    size = raw_type == "file" and vim.fn.getfsize(path) or nil,
  })
  return manager
end

local function oil_entry()
  if vim.bo.filetype ~= "oil" then return nil end
  local oil = package.loaded.oil
  if type(oil) ~= "table" then
    local ok, loaded = pcall(require, "oil")
    if not ok then return { name = "oil", root = "" } end
    oil = loaded
  end
  local entry = type(oil.get_cursor_entry) == "function" and oil.get_cursor_entry() or nil
  local root = type(oil.get_current_dir) == "function" and oil.get_current_dir() or ""
  local confirmed_name = entry and entry.name or nil
  local displayed_name = entry and entry.parsed_name or nil
  if type(displayed_name) ~= "string" or displayed_name == "" then
    displayed_name = confirmed_name
  end
  return {
    name = "oil", root = bounded(root, 2048), currentDirectory = bounded(root, 2048),
    entry = normalize_entry(entry and {
      -- Oil's public parsed_name is the name currently visible in its editable
      -- buffer.  entry.name remains the last confirmed filesystem identity
      -- until :write applies the action, so keep it for path construction.
      name = displayed_name,
      path = type(confirmed_name) == "string" and confirmed_name ~= ""
        and (root:gsub("[/\\]$", "") .. "/" .. confirmed_name) or "",
      type = entry.type,
    } or nil),
  }
end

local function nvim_tree_entry()
  if vim.bo.filetype ~= "NvimTree" then return nil end
  local ok, api = pcall(require, "nvim-tree.api")
  if not ok or type(api) ~= "table" then return { name = "nvim-tree", root = "" } end
  local node = api.tree and type(api.tree.get_node_under_cursor) == "function"
    and api.tree.get_node_under_cursor() or nil
  local marked = node and api.marks and type(api.marks.get) == "function"
    and api.marks.get(node) ~= nil or false
  local root_node = node
  local depth = 0
  while type(root_node) == "table" and type(root_node.parent) == "table" and depth < 256 do
    root_node = root_node.parent
    depth = depth + 1
  end
  local current_directory = node and node.type == "directory" and node.absolute_path
    or node and type(node.parent) == "table" and node.parent.absolute_path or ""
  return {
    name = "nvim-tree",
    root = root_node and root_node.absolute_path or "",
    currentDirectory = current_directory,
    entry = normalize_entry(node and {
      name = node.name, path = node.absolute_path, type = node.link_to and "link" or node.type,
      expanded = node.type == "directory" and node.open or nil, marked = marked,
      selectionState = marked and "marked" or "unmarked",
    } or nil),
  }
end

local function neo_tree_entry()
  if vim.bo.filetype ~= "neo-tree" then return nil end
  local ok, manager = pcall(require, "neo-tree.sources.manager")
  if not ok then return { name = "neo-tree", root = "" } end
  local state = manager.get_state_for_window()
  local node = state and state.tree and state.tree:get_node() or nil
  local clipboard = node and state and type(state.clipboard) == "table"
    and state.clipboard[node.id] or nil
  local clipboard_action = type(clipboard) == "table" and clipboard.action or nil
  local clipboard_state = clipboard_action == "copy" and "copied"
    or clipboard_action == "cut" and "cut" or "none"
  local expanded
  if node and node.type == "directory" and type(node.is_expanded) == "function" then
    local expanded_ok, value = pcall(node.is_expanded, node)
    if expanded_ok then expanded = value == true end
  end
  return {
    name = "neo-tree", root = state and state.path or "",
    currentDirectory = state and state.path or "",
    entry = normalize_entry(node and {
      name = node.name, path = node.path or node.id,
      type = node.is_link and "link" or node.type, expanded = expanded,
      marked = clipboard_state ~= "none", clipboardState = clipboard_state,
    } or nil),
  }
end

local function mini_files_entry()
  if vim.bo.filetype ~= "minifiles" then return nil end
  local mini = rawget(_G, "MiniFiles") or package.loaded["mini.files"]
  if type(mini) ~= "table" then return { name = "mini.files", root = "" } end
  local entry = type(mini.get_fs_entry) == "function" and mini.get_fs_entry() or nil
  local state = type(mini.get_explorer_state) == "function" and mini.get_explorer_state() or nil
  local branch = state and type(state.branch) == "table" and state.branch or {}
  local root = branch[1] or ""
  local current_directory = branch[state and state.depth_focus or 1] or root
  return {
    name = "mini.files", root = bounded(root, 2048),
    currentDirectory = bounded(current_directory, 2048),
    entry = normalize_entry(entry and {
      name = entry.name, path = entry.path, type = entry.fs_type,
    } or nil),
  }
end

local built_ins = {
  netrw = { name = "netrw", provider = netrw_entry },
  oil = { name = "oil", provider = oil_entry },
  NvimTree = { name = "nvim-tree", provider = nvim_tree_entry },
  ["neo-tree"] = { name = "neo-tree", provider = neo_tree_entry },
  minifiles = { name = "mini.files", provider = mini_files_entry },
}

function M.register(name, detector, provider)
  assert(type(name) == "string" and bounded(name, 64) == name and name ~= "",
    "bounded UTF-8 adapter name required")
  assert(type(detector) == "function" and type(provider) == "function", "adapter functions required")
  adapters[name] = { detector = detector, provider = provider }
  adapter_runtime[name] = nil
end

function M.unregister(name)
  adapters[name] = nil
  adapter_runtime[name] = nil
end

function M.diagnostics()
  local result = {}
  local now = vim.uv.hrtime()
  for name, runtime in pairs(adapter_runtime) do
    local disabled = 0
    for buffer, value in pairs(runtime.buffers) do
      if not vim.api.nvim_buf_is_valid(buffer) then
        runtime.buffers[buffer] = nil
      elseif value.disabledUntil > now then
        disabled = disabled + 1
      end
    end
    table.insert(result, {
      name = name,
      failureCount = runtime.failureCount,
      slowCallCount = runtime.slowCallCount,
      cooldownCount = runtime.cooldownCount,
      disabledBuffers = disabled,
      lastIssue = runtime.lastIssue,
    })
  end
  table.sort(result, function(left, right) return left.name < right.name end)
  return result
end

function M.forget_buffer(buffer)
  if type(buffer) ~= "number" then return end
  for _, runtime in pairs(adapter_runtime) do runtime.buffers[buffer] = nil end
end

function M.normalize_action(value)
  if type(value) ~= "table" then return nil end
  local manager = bounded(value.manager, 64)
  local action = action_names[value.action] and value.action or nil
  local result = action_results[value.result] and value.result or nil
  if manager == "" or not action or not result then return nil end
  local count = type(value.count) == "number" and math.floor(value.count) or 1
  if count ~= count or count == math.huge or count == -math.huge then count = 1 end
  count = math.max(1, math.min(count, 10000))
  local name = bounded(value.name, 512)
  return {
    manager = manager,
    action = action,
    result = result,
    count = count,
    name = name ~= "" and name or nil,
    entryType = type_names[value.entryType],
  }
end

function M.current()
  local built_in = built_ins[vim.bo.filetype]
  if built_in then
    local disabled, value = adapter_disabled(built_in.name)
    value.active = true
    if disabled then return normalize_manager({ name = built_in.name, root = "" }) end
    local ok, result = protected_call(built_in.name, "provider", built_in.provider)
    if ok and result then return normalize_manager(result) end
    return normalize_manager({ name = built_in.name, root = "" })
  end
  for name, adapter in pairs(adapters) do
    local disabled, runtime = adapter_disabled(name)
    if disabled then
      if runtime.active then return normalize_manager({ name = name, root = "" }) end
    else
      local detected, active = protected_call(name, "detector", adapter.detector)
      runtime.active = detected and active == true
      if runtime.active then
        local ok, value = protected_call(name, "provider", adapter.provider)
        if ok and type(value) == "table" then
          return normalize_manager(value, name)
        end
        return normalize_manager({ name = name, root = "" })
      end
    end
  end
  return nil
end

return M
