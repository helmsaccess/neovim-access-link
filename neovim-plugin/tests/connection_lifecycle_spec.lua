local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;"
  .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local event_channel_factory = require("nvim_nvda.event_channel")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s",
    label,
    vim.inspect(expected),
    vim.inspect(actual)
  ))
end

local original_schedule = vim.schedule
local original_rpcnotify = vim.rpcnotify
local original_chanclose = vim.fn.chanclose
local original_ui_attach = vim.ui_attach
local original_ui_detach = vim.ui_detach
local scheduled = {}
local notifications = {}
local attached = false
local ui_callback

vim.schedule = function(callback) scheduled[#scheduled + 1] = callback end
vim.rpcnotify = function(channel, _, event)
  notifications[#notifications + 1] = { channel = channel, event = event }
  return true
end
vim.fn.chanclose = function() return 1 end
vim.ui_attach = function(_, _, callback)
  attached = true
  ui_callback = callback
  return true
end
vim.ui_detach = function()
  attached = false
  return true
end

local ui_events
local event_channel = event_channel_factory.new({
  snapshot = function() return {} end,
  decorate = function() end,
  on_disconnect = function(_, scheduled_detach)
    if ui_events then
      ui_events.reset()
      ui_events.detach(scheduled_detach)
    end
  end,
})
ui_events = require("nvim_nvda.ui_events").new({
  emit = event_channel.emit,
  emit_prebuilt = event_channel.emit_prebuilt,
  guard = event_channel.guard,
  command_line = {
    state = function() return { active = false, text = "", type = "" } end,
    consume_predicted_error = function() return false end,
    consume_ui_message = function() return false end,
    handle_popupmenu = function() end,
    reset_for_prompt_transition = function() end,
  },
  set_prompt_diagnostics = function() end,
  clear_prompt_diagnostics = function() end,
})

event_channel.connect(1)
ui_events.attach()
ui_callback("msg_show", "", {{ "", "old connection message" }})
equal(1, #scheduled, "old UI event is queued")
equal(true, event_channel.disconnect(1), "old UI channel disconnects")
event_channel.connect(2)
ui_events.attach()
notifications = {}
for _, callback in ipairs(scheduled) do callback() end
scheduled = {}
equal({}, notifications, "queued UI event cannot cross reconnect")
equal(true, attached, "old UI work leaves the new attachment active")

equal(false, event_channel.emit_prebuilt("promptOpened", nil),
  "invalid fast-event payload disconnects")
equal(1, #scheduled, "fast-event failure schedules UI detach")
event_channel.connect(3)
ui_events.attach()
for _, callback in ipairs(scheduled) do callback() end
scheduled = {}
equal(true, attached, "old scheduled detach cannot remove the new attachment")

local completion_events
local completion_channel = event_channel_factory.new({
  snapshot = function() return {} end,
  decorate = function() end,
  on_disconnect = function()
    if completion_events then completion_events.reset() end
  end,
})
completion_events = require("nvim_nvda.completion_events").new(completion_channel.emit)
local item = { word = "same", abbr = "same", kind = "v" }
completion_channel.connect(4)
completion_events.accessible_menu_open({ item }, { kind = "plugin", selected = 1 })
equal(true, completion_channel.disconnect(4), "menu source channel disconnects")
completion_channel.connect(5)
notifications = {}
completion_events.accessible_menu_update(item, {
  kind = "plugin", selected = 1, item_count = 1,
})
completion_events.accessible_menu_close()
local event_types = {}
for _, notification in ipairs(notifications) do
  equal(5, notification.channel, "reconnected menu event uses current channel")
  event_types[#event_types + 1] = notification.event.type
end
equal({ "menuOpened", "menuSelectionChanged", "menuClosed" }, event_types,
  "reconnected menu lifetime begins before it closes")

vim.schedule = original_schedule
vim.rpcnotify = original_rpcnotify
vim.fn.chanclose = original_chanclose
vim.ui_attach = original_ui_attach
vim.ui_detach = original_ui_detach
print(string.format("connection lifecycle assertions: %d", assertions))
vim.cmd("qa!")
