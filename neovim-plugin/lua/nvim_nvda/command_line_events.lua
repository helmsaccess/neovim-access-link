local menu = require("nvim_nvda.menu")
local text = require("nvim_nvda.text")
local state = require("nvim_nvda.state")
local native_operations = require("nvim_nvda.native_operations")

local M = {}

local buffer_navigation_commands = {
  bp = true, bprevious = true, bN = true, bNext = true,
  bn = true, bnext = true,
  bf = true, bfirst = true, brewind = true,
  bl = true, blast = true,
}

local function trimmed(value)
  return tostring(value or ""):gsub("^%s+", ""):gsub("%s+$", "")
end

local function listed_buffer_count()
  local count = 0
  for _, buffer in ipairs(vim.api.nvim_list_bufs()) do
    if vim.fn.buflisted(buffer) == 1 then count = count + 1 end
  end
  return count
end

function M.new(options)
  assert(type(options) == "table", "command-line event options required")
  assert(type(options.emit) == "function", "event emitter required")
  assert(type(options.close_numbered_choice) == "function", "choice closer required")
  assert(type(options.guard) == "function", "connection callback guard required")

  local emit = options.emit
  local command_line_menu
  local current
  local instance = {}

  local function reset_state(synchronize)
    command_line_menu = menu.new()
    current = {
      phase = "idle",
      text = "",
      type = "",
      generated_keys = false,
      last_echo = "",
      output_pending = false,
      predicted_error_code = nil,
      menu_items = {},
    }
    if not synchronize then return end
    local mode_ok, mode = pcall(vim.api.nvim_get_mode)
    if not mode_ok or type(mode) ~= "table"
      or tostring(mode.mode or ""):sub(1, 1) ~= "c" then
      return
    end
    local text_ok, command_text = pcall(vim.fn.getcmdline)
    local type_ok, command_type = pcall(vim.fn.getcmdtype)
    if text_ok and type_ok then
      current.phase = "active"
      current.text = tostring(command_text or "")
      current.type = tostring(command_type or "")
    end
  end

  reset_state(false)

  local function emit_menu_events(events, reason)
    for _, menu_event in ipairs(events) do
      emit(menu_event.type, reason, menu_event.payload)
    end
  end

  local function search_details(pattern, direction)
    return native_operations.search_details(pattern, direction, false)
  end

  local function emit_preflight(command)
    local normalized = trimmed(command)
    if vim.bo.buftype == "terminal" and (normalized == "bd" or normalized == "bdelete") then
      local job = tonumber(vim.b.terminal_job_id)
      local status = job and job > 0 and vim.fn.jobwait({ job }, 0)[1] or nil
      if status == -1 then
        current.predicted_error_code = "E89"
        emit("errorReceived", "terminalCommandGuard", {
          message = "E89: terminal job is still running; the buffer was not closed. "
            .. "Press Enter to continue. Use bd! only when you intend to terminate the job.",
        })
      end
    elseif buffer_navigation_commands[normalized] and listed_buffer_count() <= 1 then
      emit("messageReceived", "terminalBufferNavigation", {
        message = "no other listed buffer; the buffer command did not switch",
      })
    end
  end

  function instance.state()
    return {
      active = current.phase == "active",
      text = current.text,
      type = current.type,
      generated_keys = current.generated_keys,
    }
  end

  function instance.reset(synchronize)
    reset_state(synchronize == true)
  end

  function instance.reset_for_prompt_transition()
    current.phase = "idle"
    current.text = ""
    current.type = ""
  end

  function instance.consume_predicted_error(error_code)
    if current.predicted_error_code and error_code == current.predicted_error_code then
      current.predicted_error_code = nil
      return true
    end
    return false
  end

  function instance.consume_ui_message(message, captured)
    captured = captured or {}
    local command_echo = message == current.last_echo
      or (captured.type ~= "" and message == captured.type .. captured.text)
    if command_echo then return nil end
    local command_line_return = current.output_pending
    current.output_pending = false
    return command_line_return
  end

  function instance.handle_popupmenu(event, ...)
    if event == "popupmenu_show" then
      local raw_items, selected = ...
      local items = {}
      for index, raw in ipairs(type(raw_items) == "table" and raw_items or {}) do
        items[index] = {
          word = tostring(raw[1] or ""), kind = tostring(raw[2] or ""),
          menu = tostring(raw[3] or ""), info = tostring(raw[4] or ""),
        }
      end
      current.menu_items = items
      emit_menu_events(command_line_menu:update({
        mode = "wildmenu",
        pum_visible = #items > 0,
        selected = tonumber(selected) or -1,
        items = items,
      }), "wildmenu")
    elseif event == "popupmenu_select" then
      local selected = ...
      if #current.menu_items > 0 then
        emit_menu_events(command_line_menu:update({
          mode = "wildmenu", pum_visible = true,
          selected = tonumber(selected) or -1,
          items = current.menu_items,
        }), "wildmenu")
      end
    elseif event == "popupmenu_hide" then
      current.menu_items = {}
      emit_menu_events(command_line_menu:close("hidden"), "wildmenu")
    end
  end

  function instance.setup(group)
    vim.api.nvim_create_autocmd({ "CmdlineEnter", "CmdlineChanged" }, {
      group = group,
      callback = function(event)
        if event.event == "CmdlineEnter" then
          current.phase = "active"
          current.output_pending = false
          current.generated_keys = false
          current.predicted_error_code = nil
          current.text = ""
          current.type = vim.fn.getcmdtype()
          native_operations.command_line_enter(current.type)
          vim.v.errmsg = ""
          vim.v.statusmsg = ""
        end
        current.text = vim.fn.getcmdline()
        native_operations.command_line_changed(current.type, current.text)
        emit("commandLineChanged", event.event, { commandLineType = current.type })
      end,
    })

    vim.api.nvim_create_autocmd("CmdlineLeave", {
      group = group,
      callback = function()
        options.close_numbered_choice("CmdlineLeave")
        current.menu_items = {}
        emit_menu_events(command_line_menu:close("commandLineLeave"), "CmdlineLeave")
        current.phase = "idle"
        local command = current.text
        local command_type = current.type
        local native_active = native_operations.command_line_leave(command_type, command)
        if native_active and native_operations.is_substitute_active() then
          local snapshot_ok, snapshot = pcall(state.snapshot, "substitutePromptContext")
          if snapshot_ok then native_operations.capture_substitute_prompt_snapshot(snapshot) end
        end
        current.last_echo = command_type .. command
        current.text = ""
        current.type = ""
        current.generated_keys = command_type == ":"
        current.output_pending = command_type == ":" and trimmed(command) ~= ""
        vim.schedule(options.guard(function() current.generated_keys = false end))
        if command_type == ":" then emit_preflight(command) end
        local guarded = vim.bo.modified
          and (command:match("^%s*q%s*$") or command:match("^%s*quit%s*$"))
        if guarded then
          emit("errorReceived", "commandGuard", {
            message = "E37: No write since last change; use :q! to discard changes or :write to save",
          })
        end
        vim.defer_fn(options.guard(function()
          local message = vim.v.errmsg
          if not guarded and current.phase ~= "active"
            and type(message) == "string" and message ~= "" then
            native_operations.cancel_command()
            vim.v.errmsg = ""
            emit("errorReceived", "commandError", { message = text.bounded(message, 2048) })
          elseif current.phase ~= "active" and (command_type == "/" or command_type == "?") then
            local ok, details = pcall(search_details, command, command_type)
            if ok then emit("searchMatchChanged", "searchCommand", details) end
          elseif current.phase ~= "active" and not native_operations.is_active() then
            local status = vim.v.statusmsg
            if type(status) == "string" and status ~= "" then
              vim.v.statusmsg = ""
              local command_line_return = current.output_pending
              current.output_pending = false
              emit("messageReceived", "commandStatus", {
                message = text.bounded(status, 2048),
                commandLineReturn = command_line_return,
              })
            end
          end
          if not native_operations.is_active() then current.output_pending = false end
        end), 20)
      end,
    })

    vim.api.nvim_create_autocmd("SafeState", {
      group = group,
      callback = function()
        local status = text.bounded(vim.v.statusmsg, 2048)
        local recognized, native_emitted = native_operations.finish_command(status)
        if not recognized then return end
        if native_emitted then
          vim.v.statusmsg = ""
        elseif type(status) == "string" and status ~= "" then
          emit("messageReceived", "commandStatus", {
            message = status, commandLineReturn = current.output_pending,
          })
        end
        current.output_pending = false
      end,
    })
  end

  return instance
end

return M
