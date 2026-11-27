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
local scheduled_disconnects = {}
local original_rpcnotify = vim.rpcnotify
local original_chanclose = vim.fn.chanclose
local fail_notification = false
vim.rpcnotify = function(channel, method, event)
  if fail_notification then error("notification failed") end
  notifications[#notifications + 1] = { channel = channel, method = method, event = event }
  return true
end
vim.fn.chanclose = function(channel)
  closed[#closed + 1] = channel
  return 1
end

local fail_snapshot = false
local invalid_snapshot = false
local fail_decorate = false
local channel = event_channel.new({
  snapshot = function(reason)
    if fail_snapshot then error("snapshot failed") end
    if invalid_snapshot then return nil end
    return { reason = reason }
  end,
  decorate = function(payload)
    if fail_decorate then error("decorate failed") end
    payload.decorated = true
  end,
  on_disconnect = function(reason, scheduled)
    disconnected[#disconnected + 1] = reason
    scheduled_disconnects[#scheduled_disconnects + 1] = scheduled == true
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
equal(true, channel.emit("messageReceived", "message", { message = "duplicate" }),
  "reconnect resets duplicate suppression")

invalid_snapshot = true
equal(false, channel.emit("modeChanged", "invalid"), "invalid snapshot rejects event")
equal(9, closed[#closed], "invalid snapshot closes the RPC channel")
equal("snapshotFailure", disconnected[#disconnected], "invalid snapshot fails open")

invalid_snapshot = false
channel.connect(10)
fail_decorate = true
equal(false, channel.emit("modeChanged", "brokenDecorator"), "decorator failure rejects event")
equal(10, closed[#closed], "decorator failure closes the RPC channel")
equal("payloadFailure", disconnected[#disconnected], "decorator failure fails open")
equal(false, channel.is_connected(), "decorator failure clears connection")

fail_decorate = false
channel.connect(11)
fail_notification = true
equal(false, channel.emit("modeChanged", "brokenNotification"), "notification failure rejects event")
equal(11, closed[#closed], "notification failure closes the RPC channel")
equal("notificationFailure", disconnected[#disconnected], "notification failure resets dependants")
equal(false, scheduled_disconnects[#scheduled_disconnects], "regular notification detaches synchronously")

fail_notification = false
channel.connect(12)
equal(false, channel.emit_prebuilt("promptOpened", {}, "invalid extra"),
  "invalid prebuilt details reject event")
equal(12, closed[#closed], "prebuilt payload failure closes the RPC channel")
equal("payloadFailure", disconnected[#disconnected], "prebuilt payload failure resets dependants")
equal(true, scheduled_disconnects[#scheduled_disconnects], "prebuilt failure schedules UI detach")

channel.connect(13)
fail_notification = true
equal(false, channel.emit_prebuilt("promptOpened", {}), "prebuilt notification failure rejects event")
equal(13, closed[#closed], "prebuilt notification failure closes the RPC channel")
equal("notificationFailure", disconnected[#disconnected],
  "prebuilt notification failure resets dependants")
equal(true, scheduled_disconnects[#scheduled_disconnects],
  "prebuilt notification failure schedules UI detach")

channel.connect(14)
fail_notification = false
equal(false, channel.emit_prebuilt("promptOpened", nil), "invalid prebuilt payload rejects event")
equal(14, closed[#closed], "invalid prebuilt payload closes the RPC channel")
equal("payloadFailure", disconnected[#disconnected], "invalid prebuilt payload fails open")

channel.connect(15)
local guarded_calls = 0
local guarded = channel.guard(function() guarded_calls = guarded_calls + 1 end)
equal(true, channel.disconnect(15), "guard source channel disconnects")
channel.connect(16)
guarded()
equal(0, guarded_calls, "old connection callback is invalidated")
equal(false, channel.disconnect(8), "wrong channel cannot disconnect active consumer")
equal(true, channel.disconnect(16), "matching channel disconnects consumer")
equal("unregisterChannel", disconnected[#disconnected], "explicit disconnect resets dependants")

vim.rpcnotify = original_rpcnotify
vim.fn.chanclose = original_chanclose

-- A serialization failure occurs before a notification reaches a still-valid
-- RPC transport. Verify the real channel is closed instead of relying only on
-- the chanclose spy above.
local real_disconnect
local real_channel = event_channel.new({
  snapshot = function() return { unserializable = function() end } end,
  decorate = function() end,
  on_disconnect = function(reason) real_disconnect = reason end,
})
local python = vim.env.NAL_TEST_PYTHON or (vim.fn.has("win32") == 1 and "python" or "python3")
local rpc_job_ready = false
local rpc_job = vim.fn.jobstart({
  python, "-u", "-c", "import sys; print('ready', file=sys.stderr); sys.stdin.buffer.read()",
}, {
  rpc = true,
  on_stderr = function(_, data)
    for _, line in ipairs(data) do
      if vim.trim(line) == "ready" then rpc_job_ready = true end
    end
  end,
})
assert(rpc_job > 0, "disposable RPC job starts")
assert(vim.wait(5000, function() return rpc_job_ready end), "disposable RPC job is ready")
equal(-1, vim.fn.jobwait({ rpc_job }, 0)[1], "RPC peer is still waiting on its input")
real_channel.connect(rpc_job)
equal(false, real_channel.emit("modeChanged", "serializationFailure"),
  "real serialization failure rejects event")
equal("notificationFailure", real_disconnect, "real serialization failure fails open")
equal(false, real_channel.is_connected(), "real serialization failure clears plugin channel")
local exit_status = vim.fn.jobwait({ rpc_job }, 3000)[1]
assert(exit_status >= 0, "real serialization failure closes RPC transport, job status " .. exit_status)

print(string.format("event channel assertions: %d", assertions))
vim.cmd("qa!")
