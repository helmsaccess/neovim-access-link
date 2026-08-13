local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;"
  .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local event_channel = require("nvim_nvda.event_channel")

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

local notifications = {}
local closed = {}
local disconnected = {}
local original_rpcnotify = vim.rpcnotify
local original_chanclose = vim.fn.chanclose
vim.rpcnotify = function(channel, method, event)
  notifications[#notifications + 1] = { channel = channel, method = method, event = event }
  return true
end
vim.fn.chanclose = function(channel)
  closed[#closed + 1] = channel
  return 1
end

local fail_snapshot = false
local channel = event_channel.new({
  snapshot = function(reason)
    if fail_snapshot then error("snapshot failed") end
    return { reason = reason }
  end,
  decorate = function(payload)
    payload.decorated = true
  end,
  on_disconnect = function(reason)
    disconnected[#disconnected + 1] = reason
  end,
})

equal(false, channel.emit("modeChanged", "disconnected"), "disconnected emit is ignored")
channel.connect(7)
equal(true, channel.emit("modeChanged", "first", { detail = "one" }), "connected emit succeeds")
equal(1, notifications[1].event.sequence, "first connection sequence starts at one")
equal("first", notifications[1].event.payload.reason, "snapshot reason is retained")
equal("one", notifications[1].event.payload.detail, "event details are merged")
equal(true, notifications[1].event.payload.decorated, "payload is decorated once")

channel.emit("messageReceived", "message", { message = "duplicate" })
equal(false, channel.emit("messageReceived", "message", { message = "duplicate" }),
  "immediate duplicate message is suppressed")
equal(2, #notifications, "duplicate suppression does not consume a sequence")

fail_snapshot = true
equal(false, channel.emit("modeChanged", "broken"), "snapshot failure rejects event")
equal({ 7 }, closed, "snapshot failure closes the RPC channel")
equal({ "snapshotFailure" }, disconnected, "snapshot failure resets dependants")
equal(false, channel.is_connected(), "snapshot failure clears connection")

fail_snapshot = false
channel.connect(9)
channel.emit("modeChanged", "reconnected")
equal(1, notifications[#notifications].event.sequence, "reconnect resets sequence")
equal(false, channel.disconnect(8), "wrong channel cannot disconnect active consumer")
equal(true, channel.disconnect(9), "matching channel disconnects consumer")
equal("unregisterChannel", disconnected[#disconnected], "explicit disconnect resets dependants")

vim.rpcnotify = original_rpcnotify
vim.fn.chanclose = original_chanclose
print(string.format("event channel assertions: %d", assertions))
vim.cmd("qa!")
