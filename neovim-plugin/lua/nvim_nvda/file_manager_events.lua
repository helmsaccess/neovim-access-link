local file_manager = require("nvim_nvda.file_manager")

local M = {}
local publish
local publish_action
local observed
local pending = false
local pending_action
local pending_action_target
local action_scheduled = false
local nvim_tree_subscribed = false

local function copy(value)
  return type(value) == "table" and vim.deepcopy(value) or nil
end

local function target_is_current(target)
  if type(target) ~= "table" then return true end
  if type(target.bufferId) == "number"
    and target.bufferId ~= vim.api.nvim_get_current_buf() then
    return false
  end
  if type(target.windowId) == "number"
    and target.windowId ~= vim.api.nvim_get_current_win() then
    return false
  end
  if type(target.tabpageId) == "number"
    and target.tabpageId ~= vim.api.nvim_get_current_tabpage() then
    return false
  end
  return true
end

local function basename(value)
  if type(value) ~= "string" or value == "" then return nil end
  local trimmed = value:gsub("[/\\]+$", "")
  local name = trimmed:match("([^/\\]+)$")
  return name ~= "" and name or nil
end

local function manager_is_current(name)
  local current = file_manager.current()
  return type(current) == "table" and current.name == name
end

local function emit_action(value)
  if type(publish_action) ~= "function" or type(value) ~= "table"
    or not manager_is_current(value.manager) then
    return
  end
  local normalized = file_manager.normalize_action(value)
  if not normalized then return end
  local target = {
    bufferId = vim.api.nvim_get_current_buf(),
    windowId = vim.api.nvim_get_current_win(),
    tabpageId = vim.api.nvim_get_current_tabpage(),
  }
  if pending_action and pending_action.manager == normalized.manager
    and vim.deep_equal(pending_action_target, target) then
    pending_action.count = math.min(10000, pending_action.count + normalized.count)
    if pending_action.action ~= normalized.action then pending_action.action = "multiple" end
    if pending_action.result ~= normalized.result then
      if pending_action.result == "failed" or normalized.result == "failed" then
        pending_action.result = "failed"
      elseif pending_action.result == "cancelled" or normalized.result == "cancelled" then
        pending_action.result = "cancelled"
      end
    end
    pending_action.name = nil
    if pending_action.entryType ~= normalized.entryType then pending_action.entryType = nil end
  else
    pending_action = normalized
    pending_action_target = target
  end
  if action_scheduled then return end
  action_scheduled = true
  vim.schedule(function()
    action_scheduled = false
    local action = pending_action
    local action_target = pending_action_target
    pending_action = nil
    pending_action_target = nil
    if action and target_is_current(action_target) and manager_is_current(action.manager) then
      publish_action(action)
    end
  end)
end

local function action_path(action)
  if type(action) ~= "table" then return nil end
  if action.type == "delete" then return action.url or action.src_url end
  return action.dest_url or action.url or action.src_url
end

local function oil_action_result(data)
  data = type(data) == "table" and data or {}
  local actions = type(data.actions) == "table" and data.actions or {}
  if #actions == 0 then return end
  local first_type = type(actions[1]) == "table" and actions[1].type or nil
  local action = first_type
  for index = 2, #actions do
    if type(actions[index]) ~= "table" or actions[index].type ~= first_type then
      action = "multiple"
      break
    end
  end
  local err = type(data.err) == "string" and data.err or nil
  local result = err and (err:lower():find("cancel", 1, true) and "cancelled" or "failed")
    or "success"
  local single = #actions == 1 and actions[1] or nil
  emit_action({
    manager = "oil",
    action = action,
    result = result,
    count = #actions,
    name = single and basename(action_path(single)) or nil,
    entryType = single and single.entry_type or nil,
  })
end

function M.observe(value)
  observed = copy(value)
end

function M.refresh(reason, target)
  if type(publish) ~= "function" or pending or not target_is_current(target) then return end
  pending = true
  vim.schedule(function()
    pending = false
    if not target_is_current(target) then return end
    local current = file_manager.current()
    if type(current) ~= "table" or vim.deep_equal(current, observed) then return end
    observed = copy(current)
    publish(reason)
  end)
end

local function subscribe_nvim_tree()
  if nvim_tree_subscribed then return end
  local ok, api = pcall(require, "nvim-tree.api")
  local events = ok and type(api) == "table" and api.events or nil
  local event = type(events) == "table" and type(events.Event) == "table"
    and events.Event.TreeRendered or nil
  if event == nil or type(events.subscribe) ~= "function" then return end
  local subscribed = pcall(events.subscribe, event, function(data)
    data = type(data) == "table" and data or {}
    M.refresh("NvimTreeTreeRendered", {
      bufferId = data.bufnr,
      windowId = data.winnr,
    })
  end)
  nvim_tree_subscribed = subscribed
  if not subscribed then return end
  local action_events = {
    { key = "NodeRenamed", action = "rename", path = "new_name" },
    { key = "FileCreated", action = "create", path = "fname", entryType = "file" },
    { key = "FileRemoved", action = "delete", path = "fname", entryType = "file" },
    {
      key = "FolderCreated", action = "create", path = "folder_name",
      entryType = "directory",
    },
    {
      key = "FolderRemoved", action = "delete", path = "folder_name",
      entryType = "directory",
    },
  }
  for _, specification in ipairs(action_events) do
    local spec = specification
    local action_event = events.Event[spec.key]
    if action_event ~= nil then
      pcall(events.subscribe, action_event, function(data)
        data = type(data) == "table" and data or {}
        emit_action({
          manager = "nvim-tree",
          action = spec.action,
          result = "success",
          name = basename(data[spec.path]),
          entryType = spec.entryType,
        })
      end)
    end
  end
end

local function subscribe_neo_tree()
  local ok, events = pcall(require, "neo-tree.events")
  if not ok or type(events) ~= "table"
    or type(events.subscribe) ~= "function" or type(events.unsubscribe) ~= "function" then
    return
  end
  local handlers = {
    {
      event = events.AFTER_RENDER or "after_render",
      id = "nvim-nvda-access-after-render",
      handler = function(state)
        state = type(state) == "table" and state or {}
        M.refresh("NeoTreeAfterRender", {
          bufferId = state.bufnr,
          windowId = state.winid,
        })
      end,
    },
    {
      event = events.NEO_TREE_CLIPBOARD_CHANGED or "neo_tree_clipboard_changed",
      id = "nvim-nvda-access-clipboard-changed",
      handler = function(args)
        local state = type(args) == "table" and args.state or nil
        state = type(state) == "table" and state or {}
        M.refresh("NeoTreeClipboardChanged", {
          bufferId = state.bufnr,
          windowId = state.winid,
        })
      end,
    },
  }
  local action_handlers = {
    { event = events.FILE_ADDED, action = "add", path = function(args) return args end },
    { event = events.FILE_DELETED, action = "delete", path = function(args) return args end },
    {
      event = events.FILE_MOVED,
      action = "move",
      path = function(args) return type(args) == "table" and args.destination or nil end,
    },
    {
      event = events.FILE_RENAMED,
      action = "rename",
      path = function(args) return type(args) == "table" and args.destination or nil end,
    },
    { event = events.FILE_RESTORED, action = "restore", path = function(args) return args end },
  }
  for _, specification in ipairs(action_handlers) do
    local spec = specification
    if spec.event ~= nil then
      table.insert(handlers, {
        event = spec.event,
        id = "nvim-nvda-access-action-" .. spec.action,
        handler = function(args)
          emit_action({
            manager = "neo-tree",
            action = spec.action,
            result = "success",
            name = basename(spec.path(args)),
          })
        end,
      })
    end
  end
  for _, handler in ipairs(handlers) do
    pcall(events.unsubscribe, handler)
    pcall(events.subscribe, handler)
  end
end

function M.setup(state_callback, action_callback, group)
  assert(type(state_callback) == "function", "file-manager event publisher required")
  assert(type(action_callback) == "function", "file-manager action publisher required")
  publish = state_callback
  publish_action = action_callback
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = {
      "OilMutationComplete",
      "MiniFilesBufferUpdate",
    },
    callback = function(event)
      local data = type(event.data) == "table" and event.data or {}
      M.refresh(event.match, {
        bufferId = data.buf_id,
        windowId = data.win_id,
      })
    end,
  })
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = "OilActionsPost",
    callback = function(event) oil_action_result(event.data) end,
  })
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = {
      "MiniFilesActionCreate",
      "MiniFilesActionDelete",
      "MiniFilesActionRename",
      "MiniFilesActionCopy",
      "MiniFilesActionMove",
    },
    callback = function(event)
      local data = type(event.data) == "table" and event.data or {}
      local action = type(data.action) == "string" and data.action
        or event.match:gsub("^MiniFilesAction", ""):lower()
      local path = action == "delete" and data.from or data.to or data.from
      emit_action({
        manager = "mini.files",
        action = action,
        result = "success",
        name = basename(path),
      })
    end,
  })
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = { "NvimTreeRequired", "NvimTreeSetup" },
    callback = function() vim.schedule(subscribe_nvim_tree) end,
  })
  vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = { "NvimTree", "neo-tree" },
    callback = function(event)
      if event.match == "NvimTree" then
        subscribe_nvim_tree()
      else
        subscribe_neo_tree()
      end
    end,
  })
end

return M
