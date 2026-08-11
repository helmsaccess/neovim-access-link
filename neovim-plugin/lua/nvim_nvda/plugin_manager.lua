local M = {}

local MANAGER_KIND = "lazyNvim"
local MAX_NESTING = 16
local MAX_OVERVIEW_LINES = 8
local MAX_OVERVIEW_BYTES = 2048
local MAX_DETAILS_LINES = 4096
local MAX_DETAILS_BYTES = 262144
local MAX_PROPERTY_EXTMARKS = 64
local text = require("nvim_nvda.text")

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
local details_by_buffer = {}
local details_cache = {}
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
  details_by_buffer = {}
  details_cache = {}
  local patterns = {}
  for pattern in pairs(lifecycle_events) do table.insert(patterns, pattern) end
  table.sort(patterns)
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = patterns,
    callback = function(event) handle(event.match) end,
  })
  vim.api.nvim_create_autocmd({ "BufEnter", "TextChanged" }, {
    group = group,
    callback = function(event)
      local buf, reason = event.buf, event.event
      details_cache[buf] = nil
      vim.schedule(function()
        if not vim.api.nvim_buf_is_valid(buf) then return end
        local expanded = M.details_expanded(buf)
        if type(expanded) ~= "boolean" then
          details_by_buffer[buf] = nil
          return
        end
        local previous = details_by_buffer[buf]
        details_by_buffer[buf] = expanded
        if type(previous) == "boolean" and previous ~= expanded
          and type(current_emit) == "function" then
          current_emit("pluginManagerDetailsChanged", reason, {
            pluginManagerKind = MANAGER_KIND,
            pluginManagerDetailsExpanded = expanded,
          })
        end
      end)
    end,
  })
  vim.api.nvim_create_autocmd({ "BufDelete", "BufWipeout" }, {
    group = group,
    callback = function(event)
      details_by_buffer[event.buf] = nil
      details_cache[event.buf] = nil
    end,
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

-- Lazy renders an opened plugin detail block into its public nofile buffer.
-- The first detail property is `dir`, highlighted with Lazy's documented
-- LazyProp group. Requiring both the text and its public extmark avoids key
-- inference, private Lazy objects, and unrelated lines which merely say dir.
function M.details_expanded(buf)
  if not is_lazy_buffer(buf) then return nil end
  local changedtick = vim.api.nvim_buf_get_changedtick(buf)
  local cached = details_cache[buf]
  if cached and cached.changedtick == changedtick then return cached.value end
  local function finish(value)
    details_cache[buf] = { changedtick = changedtick, value = value }
    return value
  end
  local line_count = vim.api.nvim_buf_line_count(buf)
  if line_count > MAX_DETAILS_LINES then return finish(nil) end
  local lines = vim.api.nvim_buf_get_lines(buf, 0, line_count, true)
  local total_bytes, matches = 0, 0
  for row, line in ipairs(lines) do
    total_bytes = total_bytes + #line
    if total_bytes > MAX_DETAILS_BYTES then return finish(nil) end
    local _, _, key_start, after_key = line:find("^%s*()dir()%s+")
    if key_start then
      local marks = vim.api.nvim_buf_get_extmarks(buf, -1, { row - 1, 0 }, { row - 1, -1 }, {
        details = true,
        limit = MAX_PROPERTY_EXTMARKS,
      })
      local start_col, end_col = key_start - 1, after_key - 1
      for _, mark in ipairs(marks) do
        local details = mark[4]
        if mark[3] == start_col and type(details) == "table"
          and details.hl_group == "LazyProp"
          and type(details.end_col) == "number" and details.end_col >= end_col then
          matches = matches + 1
          break
        end
      end
    end
  end
  if matches > 1 then return finish(nil) end
  return finish(matches == 1)
end

return M
