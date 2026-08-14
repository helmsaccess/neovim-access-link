local M = {}

local MAX_DUPLICATE_MESSAGE_AGE_NS = 500000000

function M.new(options)
  assert(type(options) == "table", "event channel options required")
  assert(type(options.snapshot) == "function", "snapshot callback required")
  assert(type(options.decorate) == "function", "payload decorator required")
  assert(type(options.on_disconnect) == "function", "disconnect callback required")

  local instance = {}
  local channel
  local generation = 0
  local sequence = 0
  local last_message_text
  local last_message_time = 0

  local function detach(reason, close_rpc, scheduled)
    local disconnected_channel = channel
    channel = nil
    generation = generation + 1
    if close_rpc and disconnected_channel then
      pcall(vim.fn.chanclose, disconnected_channel)
    end
    pcall(options.on_disconnect, reason, scheduled)
  end

  local function notification(event_type, payload)
    local ok, result = pcall(function()
      sequence = sequence + 1
      return vim.rpcnotify(channel, "nvim_nvda_event", {
        sequence = sequence,
        timestampMonotonic = vim.uv.hrtime(),
        type = event_type,
        payload = payload,
      })
    end)
    return ok and result ~= false
  end

  function instance.connect(rpc_channel)
    assert(type(rpc_channel) == "number" and rpc_channel > 0, "valid RPC channel required")
    if channel then
      detach("channelReplaced", channel ~= rpc_channel, false)
    end
    generation = generation + 1
    channel = rpc_channel
    sequence = 0
    last_message_text = nil
    last_message_time = 0
  end

  function instance.disconnect(rpc_channel)
    if channel ~= rpc_channel then return false end
    detach("unregisterChannel", false, false)
    return true
  end

  function instance.is_connected()
    return channel ~= nil
  end

  function instance.guard(callback)
    assert(type(callback) == "function", "guarded callback required")
    local expected_generation = generation
    return function(...)
      if generation ~= expected_generation then return nil end
      return callback(...)
    end
  end

  function instance.emit(event_type, reason, extra)
    if not channel then return false end
    if (event_type == "messageReceived" or event_type == "errorReceived")
      and type(extra) == "table" and type(extra.message) == "string" then
      local now = vim.uv.hrtime()
      if extra.message == last_message_text
        and now - last_message_time < MAX_DUPLICATE_MESSAGE_AGE_NS then
        return false
      end
      last_message_text = extra.message
      last_message_time = now
    end

    local snapshot_ok, payload = pcall(options.snapshot, reason)
    if not snapshot_ok or type(payload) ~= "table" then
      -- Never turn an accessibility snapshot bug into a Neovim hit-enter
      -- prompt. Closing the RPC channel makes the NVDA side disconnect and
      -- restore native terminal output fail-open.
      detach("snapshotFailure", true, false)
      return false
    end
    local payload_ok = pcall(function()
      for key, value in pairs(extra or {}) do
        payload[key] = value
      end
      options.decorate(payload, reason)
    end)
    if not payload_ok then
      detach("payloadFailure", true, false)
      return false
    end
    local ok = notification(event_type, payload)
    if not ok then detach("notificationFailure", true, false) end
    return ok
  end

  function instance.emit_prebuilt(event_type, payload, extra)
    if not channel then return false end
    if type(payload) ~= "table" then
      detach("payloadFailure", true, true)
      return false
    end
    local payload_ok = pcall(function()
      for key, value in pairs(extra or {}) do
        payload[key] = value
      end
    end)
    if not payload_ok then
      detach("payloadFailure", true, true)
      return false
    end
    local ok = notification(event_type, payload)
    if not ok then detach("notificationFailure", true, true) end
    return ok
  end

  return instance
end

return M
