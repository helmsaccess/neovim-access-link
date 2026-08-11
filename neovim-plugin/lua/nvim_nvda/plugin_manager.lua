local M = {}

local MANAGER_KIND = "lazyNvim"
local MAX_NESTING = 16
local MAX_OVERVIEW_LINES = 8
local MAX_OVERVIEW_BYTES = 2048
local MAX_PROPERTY_EXTMARKS = 64
local MAX_ROW_EXTMARKS = 32
local text = require("nvim_nvda.text")

local plugin_icon_groups = {
  LazyLocal = true,
  LazyNoCond = true,
  LazySpecial = true,
}

local lifecycle_events = {
  LazyInstallPre = { operation = "install", phase = "started" },
  LazyInstall = { operation = "install", phase = "finished" },
  LazyUpdatePre = { operation = "update", phase = "started" },
  LazyUpdate = { operation = "update", phase = "finished" },
  LazyCleanPre = { operation = "clean", phase = "started" },
  LazyClean = { operation = "clean", phase = "finished" },
  LazyCheckPre = { operation = "check", phase = "started" },
  LazyCheck = { operation = "check", phase = "finished" },
  LazyLogPre = { operation = "log", phase = "started" },
  LazyLog = { operation = "log", phase = "finished" },
  LazySyncPre = { operation = "sync", phase = "started" },
  LazySync = { operation = "sync", phase = "finished" },
}

local operation_depth = {}
local current_emit

local function is_lazy_buffer(buf)
  return vim.api.nvim_buf_is_valid(buf)
    and vim.bo[buf].buftype == "nofile"
    and vim.bo[buf].filetype == "lazy"
end

local function manager_payload(details)
  return {
    pluginManagerKind = MANAGER_KIND,
    pluginManagerOperation = details.operation,
    pluginManagerPhase = details.phase,
  }
end

local function publish(event_name, details)
  if type(current_emit) == "function" then
    current_emit("pluginManagerOperation", event_name, manager_payload(details))
  end
end

local function handle(event_name)
  local details = lifecycle_events[event_name]
  if not details then return end
  local operation = details.operation
  local depth = operation_depth[operation] or 0
  local sync_active = (operation_depth.sync or 0) > 0
  if details.phase == "started" then
    operation_depth[operation] = math.min(MAX_NESTING, depth + 1)
    if depth == 0 and (operation == "sync" or not sync_active) then
      publish(event_name, details)
    end
    return
  end
  if depth == 0 then return end
  operation_depth[operation] = depth - 1
  if operation == "sync" then
    if depth == 1 then
      publish(event_name, details)
      for name in pairs(operation_depth) do operation_depth[name] = 0 end
    end
  elseif depth == 1 and not sync_active then
    publish(event_name, details)
  end
end

function M.setup(emit, group)
  current_emit = emit
  operation_depth = {}
  local patterns = {}
  for pattern in pairs(lifecycle_events) do table.insert(patterns, pattern) end
  table.sort(patterns)
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = patterns,
    callback = function(event) handle(event.match) end,
  })
end

-- Lazy exposes its window as an ordinary nofile buffer. Read only the first
-- contiguous text block so a wrapped command row remains independent of the
-- terminal width without depending on Lazy internals or terminal scraping.
function M.overview(buf)
  if not is_lazy_buffer(buf) then return nil end
  local stop = math.min(vim.api.nvim_buf_line_count(buf), MAX_OVERVIEW_LINES)
  local lines = vim.api.nvim_buf_get_lines(buf, 0, stop, true)
  local parts, started = {}, false
  for _, line in ipairs(lines) do
    local value = vim.trim(line)
    if value == "" then
      if started then break end
    else
      started = true
      parts[#parts + 1] = value
    end
  end
  local value = text.bounded(table.concat(parts, " "), MAX_OVERVIEW_BYTES)
  return value ~= "" and value or nil
end

-- Lazy highlights the icon prefix of every plugin row with one of these
-- documented groups. The prefix begins at byte column 2, contains Lazy's two
-- layout spaces plus an optional icon and its separator, and is followed
-- immediately by the plugin name. These constraints exclude buttons, help
-- bullets, profile-tree symbols, and ordinary text without reading Lazy's
-- private render objects.
local function is_plugin_row(buf, row)
  if not is_lazy_buffer(buf) or type(row) ~= "number" or row < 1 then return false end
  local line = vim.api.nvim_buf_get_lines(buf, row - 1, row, true)[1]
  if type(line) ~= "string" or line == "" then return false end
  local marks = vim.api.nvim_buf_get_extmarks(buf, -1, { row - 1, 0 }, { row - 1, -1 }, {
    details = true,
    limit = MAX_ROW_EXTMARKS,
  })
  for _, mark in ipairs(marks) do
    local details = mark[4]
    local end_col = type(details) == "table" and details.end_col or nil
    if mark[3] == 2 and type(end_col) == "number" and end_col - mark[3] >= 3
      and plugin_icon_groups[details.hl_group]
      and line:sub(end_col + 1, end_col + 1):match("%S") then
      return true
    end
  end
  return false
end

-- Return a Boolean only while the cursor is on an unambiguous plugin row.
-- Lazy renders the selected plugin's documented `dir` property directly on
-- the following row, so this does not infer state from the key that was used.
function M.entry_expanded(buf, row)
  if not is_plugin_row(buf, row) then return nil end
  local next_row = row + 1
  if next_row > vim.api.nvim_buf_line_count(buf) then return false end
  local line = vim.api.nvim_buf_get_lines(buf, next_row - 1, next_row, true)[1]
  local _, _, key_start, after_key = line:find("^%s*()dir()%s+")
  if not key_start then return false end
  local marks = vim.api.nvim_buf_get_extmarks(
    buf, -1, { next_row - 1, 0 }, { next_row - 1, -1 },
    { details = true, limit = MAX_PROPERTY_EXTMARKS }
  )
  local start_col, end_col = key_start - 1, after_key - 1
  local matches = 0
  for _, mark in ipairs(marks) do
    local details = mark[4]
    if mark[3] <= start_col and type(details) == "table"
      and details.hl_group == "LazyProp"
      and type(details.end_col) == "number" and details.end_col >= end_col then
      matches = matches + 1
    end
  end
  return matches == 1 and true or (matches == 0 and false or nil)
end

return M
