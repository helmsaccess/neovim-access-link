local prompt = require("nvim_nvda.file_manager_prompt")

local M = {}

function M.new(emit)
  assert(type(emit) == "function", "event emitter required")
  local instance = {}
  local current = { buffer = nil, choice = nil }

  function instance.emit_if_active()
    local details = prompt.current_oil_confirmation()
    if not details then return false end
    local buffer = vim.api.nvim_get_current_buf()
    if current.buffer ~= buffer then
      current.buffer = buffer
      current.choice = nil
      emit("promptOpened", "oilConfirmationFallback", details)
    end
    return true
  end

  function instance.is_active_buffer()
    return current.buffer == vim.api.nvim_get_current_buf()
  end

  function instance.observe_key(translated)
    if not current.buffer then return false end
    if translated ~= "" then
      local choice = translated:lower()
      current.choice = choice == "y" and "yes" or choice == "n" and "no" or nil
    end
    return true
  end

  local function close(buffer, reason)
    if current.buffer ~= buffer then return end
    local choice = current.choice
    current.buffer = nil
    current.choice = nil
    local accepted
    if choice == "yes" then
      accepted = true
    elseif choice == "no" then
      accepted = false
    end
    emit("promptClosed", reason, { promptKind = "confirm", accepted = accepted })
  end

  function instance.setup(group)
    vim.api.nvim_create_autocmd({ "BufLeave", "BufWipeout" }, {
      group = group,
      callback = function(event)
        -- Oil closes its confirmation float from the Y/N buffer mapping. Defer
        -- until vim.on_key has observed the directly typed key.
        local buffer = event.buf
        local reason = event.event
        vim.schedule(function() close(buffer, reason) end)
      end,
    })
  end

  return instance
end

return M
