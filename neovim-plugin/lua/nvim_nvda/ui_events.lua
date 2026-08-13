local menu = require("nvim_nvda.menu")
local numbered_choice = require("nvim_nvda.numbered_choice")
local state = require("nvim_nvda.state")
local text = require("nvim_nvda.text")
local native_operations = require("nvim_nvda.native_operations")

local M = {}

local function bounded_increment(value)
  return value >= 2147483647 and 1 or value + 1
end

local function prompt_class(value)
  local normalized = tostring(value or ""):lower()
  if normalized == "" then return "" end
  if normalized:find("swap", 1, true) then return "swap" end
  if normalized:find("overwrite", 1, true) then return "overwrite" end
  if normalized:find("write", 1, true) or normalized:find("save", 1, true)
    or normalized:find("changed", 1, true) or normalized:find("modified", 1, true) then
    return "unsavedChanges"
  end
  if normalized:find("delete", 1, true) then return "delete" end
  if normalized:find("quit", 1, true) or normalized:find("exit", 1, true) then return "quit" end
  return "other"
end

local function is_blocking_prompt_mode(mode)
  return mode == "r" or mode == "rm" or mode == "r?"
end

function M.new(options)
  assert(type(options) == "table", "UI event options required")
  assert(type(options.emit) == "function", "event emitter required")
  assert(type(options.emit_prebuilt) == "function", "prebuilt emitter required")
  assert(type(options.command_line) == "table", "command-line controller required")
  assert(type(options.set_prompt_diagnostics) == "function", "prompt diagnostics callback required")
  assert(type(options.clear_prompt_diagnostics) == "function", "prompt reset callback required")

  local emit = options.emit
  local ui_namespace = vim.api.nvim_create_namespace("nvim_nvda_ui")
  local ui_select_menu = menu.new()
  local current = {
    notify_wrapped = false,
    ui_wrapped = false,
    confirm_wrapped = false,
    wrapped_confirm_active = false,
    recent_confirm_prompt = nil,
    recent_confirm_time = 0,
    message_prompt_kind = nil,
    pending_spell_choice = nil,
    active_numbered_choice = nil,
    numbered_choice_id = 0,
  }
  local instance = {}

  local function emit_menu_events(events, reason)
    for _, menu_event in ipairs(events) do
      emit(menu_event.type, reason, menu_event.payload)
    end
  end

  local function message_text(content, maximum, reject_oversize)
    local chunks = {}
    for _, chunk in ipairs(type(content) == "table" and content or {}) do
      chunks[#chunks + 1] = type(chunk) == "table" and tostring(chunk[2] or "") or ""
    end
    local value = table.concat(chunks):gsub("^%s+", ""):gsub("%s+$", "")
    if reject_oversize and #value > (maximum or 2048) then return nil end
    return text.bounded(value, maximum or 2048)
  end

  local function clear_message_prompt()
    current.message_prompt_kind = nil
    options.clear_prompt_diagnostics()
  end

  function instance.close_numbered_choice(reason)
    if not current.active_numbered_choice then return end
    local choice = current.active_numbered_choice
    current.active_numbered_choice = nil
    emit("numberedChoiceClosed", reason, {
      choiceKind = choice.kind,
      choiceId = choice.id,
    })
  end

  local function close_message_prompt(reason)
    instance.close_numbered_choice(reason)
    if not current.message_prompt_kind then return end
    local kind = current.message_prompt_kind
    clear_message_prompt()
    emit("promptClosed", reason, { promptKind = kind, answered = true })
  end

  function instance.set_spell_candidate(candidate)
    current.pending_spell_choice = candidate
  end

  function instance.reset()
    current.pending_spell_choice = nil
    current.active_numbered_choice = nil
    clear_message_prompt()
  end

  function instance.detach(scheduled)
    local detach = function() pcall(vim.ui_detach, ui_namespace) end
    if scheduled then vim.schedule(detach) else detach() end
  end

  local function open_legacy_spell_choice(content)
    local candidate = current.pending_spell_choice
    current.pending_spell_choice = nil
    if not candidate or type(candidate.snapshot) ~= "table" then return false end
    local age = vim.uv.hrtime() - candidate.timestamp
    local items = age >= 0 and age <= 1000000000
      and numbered_choice.spell_suggestions(message_text(content, 65536, true)) or nil
    if not items then return false end
    current.numbered_choice_id = bounded_increment(current.numbered_choice_id)
    current.active_numbered_choice = {
      kind = "spellSuggestions",
      id = current.numbered_choice_id,
    }
    return options.emit_prebuilt("numberedChoiceOpened", candidate.snapshot, {
      choiceKind = current.active_numbered_choice.kind,
      choiceId = current.active_numbered_choice.id,
      items = items,
    })
  end

  local function handle_ui_event(event, command_line_snapshot, ...)
    if event == "msg_show" then
      local kind, content = ...
      if kind == "search_count" then return end
      local kind_of_prompt = kind == "confirm" and "confirm"
        or kind == "confirm_sub" and "confirmSub"
        or kind == "return_prompt" and "more"
      if kind_of_prompt then
        if kind_of_prompt == "confirmSub" and native_operations.is_active() then return end
        local value = message_text(content)
        if kind_of_prompt == "confirm" and current.pending_spell_choice then
          local candidate = current.pending_spell_choice
          current.pending_spell_choice = nil
          local age = vim.uv.hrtime() - candidate.timestamp
          local exact_context = age >= 0 and age <= 1000000000
            and vim.api.nvim_get_current_buf() == candidate.bufferId
            and vim.api.nvim_get_current_win() == candidate.windowId
            and vim.api.nvim_get_current_tabpage() == candidate.tabpageId
            and vim.api.nvim_buf_get_changedtick(candidate.bufferId) == candidate.changedtick
          local items = exact_context
            and numbered_choice.spell_suggestions(message_text(content, 65536, true)) or nil
          if items then
            current.numbered_choice_id = bounded_increment(current.numbered_choice_id)
            current.active_numbered_choice = {
              kind = "spellSuggestions",
              id = current.numbered_choice_id,
            }
            emit("numberedChoiceOpened", "spellSuggestions", {
              choiceKind = current.active_numbered_choice.kind,
              choiceId = current.active_numbered_choice.id,
              items = items,
            })
            return
          end
        end
        if kind_of_prompt == "confirm" then
          local recent_duplicate = type(current.recent_confirm_prompt) == "string"
            and vim.uv.hrtime() - current.recent_confirm_time < 1000000000
            and value:find(current.recent_confirm_prompt, 1, true) == 1
          if current.wrapped_confirm_active or recent_duplicate then return end
        end
        current.message_prompt_kind = kind_of_prompt
        options.set_prompt_diagnostics({
          promptActive = true,
          promptKind = kind_of_prompt,
          promptClass = prompt_class(value),
          promptLength = #value,
        })
        emit("promptOpened", "uiMessage", {
          promptKind = kind_of_prompt,
          prompt = value ~= "" and value or "Continue",
        })
      elseif kind == "emsg" or kind == "echoerr" or kind == "lua_error" or kind == "rpc_error" then
        local value = message_text(content)
        local error_code = value:match("E%d+")
        if not options.command_line.consume_predicted_error(error_code) and value ~= "" then
          emit("errorReceived", "uiMessage", { message = value })
        end
      else
        local value = message_text(content)
        if value ~= "" then
          local command_line_return = options.command_line.consume_ui_message(
            value,
            command_line_snapshot
          )
          if command_line_return ~= nil then
            emit("messageReceived", "uiMessage", {
              message = value, commandLineReturn = command_line_return,
            })
          end
        end
      end
      return
    elseif event == "msg_clear" then
      close_message_prompt("uiMessage")
      return
    end
    if not command_line_snapshot.active then return end
    options.command_line.handle_popupmenu(event, ...)
  end

  function instance.attach()
    instance.detach(false)
    local legacy_blocking_messages = vim.fn.has("nvim-0.12") == 0
    pcall(vim.ui_attach, ui_namespace, {
      ext_popupmenu = true,
      ext_messages = true,
    }, function(event, ...)
      local arguments = { ... }
      local command_line_snapshot = options.command_line.state()
      local function dispatch()
        handle_ui_event(event, command_line_snapshot, unpack(arguments))
      end
      if legacy_blocking_messages and event == "msg_show"
        and current.pending_spell_choice then
        open_legacy_spell_choice(arguments[2])
        return
      end
      if legacy_blocking_messages and event == "msg_show"
        and arguments[1] == "confirm_sub" and native_operations.is_substitute_active() then
        local snapshot_ok, snapshot = pcall(state.snapshot, "substitutePromptContext")
        if snapshot_ok then native_operations.capture_substitute_prompt_snapshot(snapshot) end
        native_operations.open_legacy_substitute_prompt()
        return
      end
      vim.schedule(dispatch)
    end)
  end

  function instance.setup(group)
    if not current.notify_wrapped then
      local original = vim.notify
      vim.notify = function(message, level, notify_options)
        native_operations.note_notification()
        emit("messageReceived", "vim.notify", {
          message = text.bounded(tostring(message), 2048),
          messageLevel = tonumber(level),
          messageTitle = type(notify_options) == "table" and notify_options.title or nil,
        })
        return original(message, level, notify_options)
      end
      current.notify_wrapped = true
    end

    if not current.ui_wrapped then
      local original_input = vim.ui.input
      local original_select = vim.ui.select
      vim.ui.input = function(input_options, on_confirm)
        input_options = input_options or {}
        emit("promptOpened", "vim.ui.input", {
          promptKind = "input",
          prompt = text.bounded(tostring(input_options.prompt or "Input"), 2048),
          defaultValuePresent = input_options.default ~= nil
            and tostring(input_options.default) ~= "",
        })
        return original_input(input_options, function(value)
          emit("promptClosed", "vim.ui.input", {
            promptKind = "input", accepted = value ~= nil,
          })
          return on_confirm(value)
        end)
      end
      vim.ui.select = function(items, select_options, on_choice)
        select_options = select_options or {}
        items = type(items) == "table" and items or {}
        local formatter = type(select_options.format_item) == "function"
          and select_options.format_item or tostring
        local normalized = {}
        for index, item in ipairs(items) do
          local ok, label = pcall(formatter, item)
          normalized[index] = { word = text.bounded(ok and tostring(label) or tostring(item), 512) }
        end
        emit("promptOpened", "vim.ui.select", {
          promptKind = "select",
          prompt = text.bounded(tostring(select_options.prompt or "Select"), 2048),
          itemCount = #normalized,
        })
        emit_menu_events(ui_select_menu:update({
          mode = "select", pum_visible = #normalized > 0,
          selected = #normalized > 0 and 0 or -1,
          items = normalized,
        }), "vim.ui.select")
        return original_select(items, select_options, function(choice, index)
          local selected_index = tonumber(index)
          if choice ~= nil and not selected_index then
            for candidate_index, candidate in ipairs(items) do
              if candidate == choice then selected_index = candidate_index break end
            end
          end
          emit_menu_events(ui_select_menu:close("choiceMade"), "vim.ui.select")
          emit("promptClosed", "vim.ui.select", {
            promptKind = "select", accepted = choice ~= nil,
            selectedIndex = selected_index,
            selectedLabel = choice ~= nil and normalized[selected_index or 0]
              and normalized[selected_index or 0].word or nil,
          })
          return on_choice(choice, index)
        end)
      end
      current.ui_wrapped = true
    end

    if not current.confirm_wrapped then
      local original_confirm = vim.fn.confirm
      vim.fn.confirm = function(message, choices, default_choice, dialog_type)
        local prompt = text.bounded(tostring(message or "Confirm"), 2048)
        local labels = {}
        for label in tostring(choices or ""):gmatch("[^\n]+") do
          labels[#labels + 1] = text.bounded(label:gsub("&", ""):gsub("\t.*$", ""), 512)
        end
        emit("promptOpened", "vim.fn.confirm", {
          promptKind = "confirm", prompt = prompt, itemCount = #labels,
        })
        current.wrapped_confirm_active = true
        local ok, result = pcall(original_confirm, message, choices, default_choice, dialog_type)
        current.wrapped_confirm_active = false
        if not ok then error(result) end
        current.recent_confirm_prompt = prompt
        current.recent_confirm_time = vim.uv.hrtime()
        local selected_index = tonumber(result)
        local accepted = selected_index ~= nil and selected_index > 0
        emit("promptClosed", "vim.fn.confirm", {
          promptKind = "confirm", answered = true, accepted = accepted,
          selectedIndex = selected_index,
          selectedLabel = accepted and labels[selected_index] or nil,
        })
        return result
      end
      current.confirm_wrapped = true
    end

    vim.api.nvim_create_autocmd("ModeChanged", {
      group = group,
      callback = function(event)
        local change = vim.v.event or {}
        local old_mode = tostring(change.old_mode or "")
        local new_mode = tostring(change.new_mode or "")
        if is_blocking_prompt_mode(old_mode) and not is_blocking_prompt_mode(new_mode) then
          options.command_line.reset_for_prompt_transition()
          if current.wrapped_confirm_active then
            clear_message_prompt()
          else
            close_message_prompt(event.event)
          end
        end
        if current.active_numbered_choice
          and old_mode:sub(1, 1) == "c" and new_mode:sub(1, 1) ~= "c" then
          instance.close_numbered_choice(event.event)
        end
        emit("modeChanged", event.event)
      end,
    })
  end

  return instance
end

return M
