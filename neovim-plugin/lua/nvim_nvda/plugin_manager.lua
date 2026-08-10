local M = {}

local MANAGER_KIND = "lazyNvim"
local MAX_NESTING = 16

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

return M
