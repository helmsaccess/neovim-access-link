local state = require("nvim_nvda.state")
local text = require("nvim_nvda.text")
local native_operations = require("nvim_nvda.native_operations")

local M = {}

function M.new(options)
  assert(type(options) == "table", "context event options required")
  assert(type(options.emit) == "function", "event emitter required")
  assert(type(options.emit_oil_confirmation) == "function", "Oil prompt callback required")

  local emit = options.emit
  local current = {
    change_pending = false,
    reason = nil,
    suppressed = false,
  }
  local instance = {}

  function instance.setup(group)
    vim.api.nvim_create_autocmd("TermClose", {
      group = group,
      callback = function()
        local status = tonumber((vim.v.event or {}).status) or -1
        local message = status >= 0
          and ("terminal process exited, status " .. tostring(status))
          or "terminal process exited, status unknown"
        emit("messageReceived", "TermClose", {
          message = message,
          messageTitle = "Terminal",
          messageLevel = status == 0 and 2 or 4,
          terminalExitStatus = status,
        })
        vim.schedule(function() emit("contextChanged", "TermClose") end)
      end,
    })

    vim.api.nvim_create_autocmd("DiagnosticChanged", {
      group = group,
      callback = function(event) emit("diagnosticChanged", event.event) end,
    })
    vim.api.nvim_create_autocmd("TextYankPost", {
      group = group,
      callback = function(event)
        local details = vim.v.event or {}
        if details.operator ~= "y" then return end
        local name = details.regname ~= "" and details.regname or '"'
        emit("registerChanged", event.event, {
          registerName = name,
          registerType = details.regtype,
          registerText = text.bounded(vim.fn.getreg(name), 2048),
        })
      end,
    })
    vim.api.nvim_create_autocmd("RecordingEnter", {
      group = group,
      callback = function(event)
        emit("macroRecordingStarted", event.event, { registerName = vim.fn.reg_recording() })
      end,
    })
    vim.api.nvim_create_autocmd("RecordingLeave", {
      group = group,
      callback = function(event)
        local name = vim.fn.reg_recording()
        if name == "" then name = vim.fn.reg_recorded() end
        emit("macroRecordingStopped", event.event, {
          registerName = name,
          registerText = type(name) == "string" and text.bounded(vim.fn.getreg(name), 2048) or "",
        })
      end,
    })

    vim.api.nvim_create_autocmd({
      "BufEnter", "BufWinEnter", "WinEnter", "TabEnter",
      "TermOpen", "TermEnter", "TermLeave",
    }, {
      group = group,
      callback = function(event)
        current.reason = event.event
        if native_operations.consume_intermediate_update("context") then
          if native_operations.is_substitute_active() then
            local snapshot_ok, snapshot = pcall(state.snapshot, "substitutePromptContext")
            if snapshot_ok then native_operations.capture_substitute_prompt_snapshot(snapshot) end
          end
          native_operations.note_intermediate_update()
          current.suppressed = true
        end
        if current.change_pending then return end
        current.change_pending = true
        vim.schedule(function()
          current.change_pending = false
          local final_reason = current.reason or event.event
          current.reason = nil
          local suppressed = current.suppressed
          current.suppressed = false
          if suppressed then return end
          if not options.emit_oil_confirmation() then
            emit("contextChanged", final_reason)
          end
        end)
      end,
    })
  end

  return instance
end

return M
