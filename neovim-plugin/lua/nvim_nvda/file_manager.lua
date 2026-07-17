local M = {}
local adapters = {}

local type_names = {
  file = "file", dir = "directory", link = "symbolicLink", socket = "socket",
  fifo = "fifo", char = "characterDevice", block = "blockDevice",
}

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
  return {
    name = name,
    path = bounded(entry.path, 2048),
    type = type_names[entry.type] or bounded(entry.type, 64),
    marked = entry.marked == true,
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
    entry = normalize_entry(manager.entry),
  }
end

local function netrw_entry()
  if vim.bo.filetype ~= "netrw" then return nil end
  local line = vim.api.nvim_get_current_line()
  local root = type(vim.b.netrw_curdir) == "string" and vim.b.netrw_curdir
    or vim.api.nvim_buf_get_name(0)
  local manager = { name = "netrw", root = bounded(root, 2048) }
  if line:match('^%s*"') then return manager end
  local displayed = vim.fn.expand("<cfile>")
  if type(displayed) ~= "string" or displayed == "" then return manager end
  displayed = displayed:gsub("\t.*$", ""):gsub("[/*@=|]$", "")
  if displayed == "" then return manager end
  local path
  if displayed == "." then
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
    marked = marked,
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
  return {
    name = "oil", root = bounded(root, 2048),
    entry = normalize_entry(entry and {
      name = entry.name, path = root and (root:gsub("[/\\]$", "") .. "/" .. entry.name) or "",
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
  return {
    name = "nvim-tree", root = node and node.absolute_path and vim.fn.fnamemodify(node.absolute_path, ":h") or "",
    entry = normalize_entry(node and {
      name = node.name, path = node.absolute_path, type = node.link_to and "link" or node.type,
      expanded = node.type == "directory" and node.open or nil, marked = marked,
    } or nil),
  }
end

local function neo_tree_entry()
  if vim.bo.filetype ~= "neo-tree" then return nil end
  local ok, manager = pcall(require, "neo-tree.sources.manager")
  if not ok then return { name = "neo-tree", root = "" } end
  local state = manager.get_state_for_window()
  local node = state and state.tree and state.tree:get_node() or nil
  local expanded
  if node and node.type == "directory" and type(node.is_expanded) == "function" then
    local expanded_ok, value = pcall(node.is_expanded, node)
    if expanded_ok then expanded = value == true end
  end
  return {
    name = "neo-tree", root = state and state.path or "",
    entry = normalize_entry(node and {
      name = node.name, path = node.path or node.id,
      type = node.is_link and "link" or node.type, expanded = expanded,
      marked = state and type(state.clipboard) == "table" and state.clipboard[node.id] ~= nil,
    } or nil),
  }
end

local function mini_files_entry()
  if vim.bo.filetype ~= "minifiles" then return nil end
  local mini = rawget(_G, "MiniFiles") or package.loaded["mini.files"]
  if type(mini) ~= "table" then return { name = "mini.files", root = "" } end
  local entry = type(mini.get_fs_entry) == "function" and mini.get_fs_entry() or nil
  local state = type(mini.get_explorer_state) == "function" and mini.get_explorer_state() or nil
  local root = state and state.branch and state.branch[state.depth_focus or 1] or ""
  return {
    name = "mini.files", root = bounded(root, 2048),
    entry = normalize_entry(entry and {
      name = entry.name, path = entry.path, type = entry.fs_type,
    } or nil),
  }
end

function M.register(name, detector, provider)
  assert(type(name) == "string" and name ~= "", "adapter name required")
  assert(type(detector) == "function" and type(provider) == "function", "adapter functions required")
  adapters[name] = { detector = detector, provider = provider }
end

function M.unregister(name)
  adapters[name] = nil
end

function M.current()
  for _, provider in ipairs({ netrw_entry, oil_entry, nvim_tree_entry, neo_tree_entry, mini_files_entry }) do
    local ok, built_in = pcall(provider)
    if ok and built_in then return normalize_manager(built_in) end
  end
  for name, adapter in pairs(adapters) do
    local detected, active = pcall(adapter.detector)
    if detected and active then
      local ok, value = pcall(adapter.provider)
      if ok and type(value) == "table" then
        return normalize_manager(value, name)
      end
      return normalize_manager({ name = name, root = "" })
    end
  end
  return nil
end

return M
