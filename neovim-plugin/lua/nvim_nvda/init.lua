local state = require("nvim_nvda.state")
local menu = require("nvim_nvda.menu")
local completion_adapters = require("nvim_nvda.completion_adapters")
local file_manager = require("nvim_nvda.file_manager")
local file_manager_events = require("nvim_nvda.file_manager_events")
local file_manager_prompt = require("nvim_nvda.file_manager_prompt")
local clipboard = require("nvim_nvda.clipboard")
local M = {}

local channel
local sequence = 0
local pending_navigation = false
local group
local key_namespace = vim.api.nvim_create_namespace("nvim_nvda_keys")
local pending_motion
local pending_search_direction
local pending_matching
local pending_g = false
local pending_bracket
local pending_edit
local suppress_next_text_change = false
local pending_z
local pending_mark_prefix
local pending_macro_prefix = false
local pending_register_prefix = false
local pending_motion_details
local completion_menu = menu.new()
local adapter_menu = menu.new()
local command_line_menu = menu.new()
local command_line_menu_items = {}
local ui_select_menu = menu.new()
local adapter_info
local signature_handler_wrapped = false
local notify_wrapped = false
local ui_wrapped = false
local ui_namespace = vim.api.nvim_create_namespace("nvim_nvda_ui")
local ui_message_prompt_kind
local confirm_wrapped = false
local wrapped_confirm_active = false
local recent_wrapped_confirm_prompt
local recent_wrapped_confirm_time = 0
local oil_confirmation_buffer
local oil_confirmation_choice
local command_line_active = false
local command_line_text = ""
local command_line_type = ""
local command_changedtick = 0
local command_line_generated_keys = false
local last_command_line_echo = ""
local predicted_ui_error_code
local last_message_text
local last_message_time = 0
local emit
local key_observer_diagnostics = { observerErrorCount = 0 }

-- Keep protocol fields byte-bounded without producing an invalid UTF-8 tail.
-- Values handled here originate in Neovim's Lua/UI APIs; walking backwards
-- over continuation bytes is therefore sufficient and version-independent.
local function bounded_utf8(value, maximum)
  if type(value) ~= "string" then return "" end
  if #value <= maximum then return value end
  local boundary = maximum
  while boundary > 0 do
    local following = value:byte(boundary + 1)
    if not following or following < 0x80 or following >= 0xc0 then break end
    boundary = boundary - 1
  end
  return value:sub(1, boundary)
end

local function fixed_error_kind(value)
  local text = tostring(value or "")
  if text == "" then return "" end
  if text:find("textlock", 1, true) then return "textlock" end
  if text:find("keytrans", 1, true) then return "keytrans" end
  if text:find("fs_rename", 1, true) then return "registryRename" end
  if text:find("nvim_nvda", 1, true) then return "nvimNvdaLua" end
  return "other"
end

local function fixed_prompt_kind(value)
  local text = tostring(value or ""):lower()
  if text == "" then return "" end
  if text:find("swap", 1, true) then return "swap" end
  if text:find("overwrite", 1, true) then return "overwrite" end
  if text:find("write", 1, true) or text:find("save", 1, true)
    or text:find("changed", 1, true) or text:find("modified", 1, true) then
    return "unsavedChanges"
  end
  if text:find("delete", 1, true) then return "delete" end
  if text:find("quit", 1, true) or text:find("exit", 1, true) then return "quit" end
  return "other"
end

local motion_events = {
  h = "characterMoved", l = "characterMoved",
  ["<Left>"] = "characterMoved", ["<Right>"] = "characterMoved",
  w = "wordMoved", W = "wordMoved", b = "wordMoved", B = "wordMoved",
  e = "wordMoved", E = "wordMoved",
  ["<C-Left>"] = "wordMoved", ["<C-Right>"] = "wordMoved",
  j = "lineChanged", k = "lineChanged",
  ["<Down>"] = "lineChanged", ["<Up>"] = "lineChanged",
  ["<C-N>"] = "lineChanged", ["<C-P>"] = "lineChanged",
  ["0"] = "lineStart", ["^"] = "lineStart", ["<Home>"] = "lineStart",
  ["$"] = "lineEnd", ["<End>"] = "lineEnd",
  G = "fileEnd",
  n = "searchMatchChanged", N = "searchMatchChanged",
  ["%"] = "matchingPairMoved",
  i = "suppress", I = "suppress", a = "suppress", A = "suppress",
  o = "suppress", O = "suppress",
  ["<Esc>"] = "suppress",
}

-- Printable keys have a completely different meaning in Insert mode.  In
-- particular, typing words containing h/j/k/l/w/e/b/n must not be mistaken
-- for Normal-mode navigation.  Only keys which genuinely move the Insert-mode
-- cursor are accepted here.
local insert_motion_events = {
  ["<Left>"] = "characterMoved", ["<Right>"] = "characterMoved",
  ["<C-Left>"] = "wordMoved", ["<C-Right>"] = "wordMoved",
  ["<Down>"] = "lineChanged", ["<Up>"] = "lineChanged",
  ["<C-N>"] = "lineChanged", ["<C-P>"] = "lineChanged",
  ["<Home>"] = "lineStart", ["<End>"] = "lineEnd",
}

local fold_actions = {
  c = "close", o = "open", a = "toggle", C = "closeRecursive", O = "openRecursive",
  M = "closeAll", R = "openAll", j = "next", k = "previous",
}

local function fold_at_cursor()
  local line = vim.api.nvim_win_get_cursor(0)[1]
  local first = vim.fn.foldclosed(line)
  if first < 0 then return { line = line, level = vim.fn.foldlevel(line), closed = false } end
  return {
    line = line, level = vim.fn.foldlevel(line), closed = true,
    startLine = first, endLine = vim.fn.foldclosedend(line),
  }
end

local function search_details(pattern, direction)
  local count = vim.fn.searchcount({ recompute = 1, maxcount = 9999, timeout = 50 })
  local cursor = vim.api.nvim_win_get_cursor(0)
  return {
    searchPattern = pattern or vim.fn.getreg("/"),
    searchDirection = direction,
    matchIndex = tonumber(count.current) or 0,
    matchCount = tonumber(count.total) or 0,
    matchIncomplete = tonumber(count.incomplete) or 0,
    matchLine = cursor[1],
    matchByteColumn = cursor[2],
  }
end

local function is_word_terminator(key)
  return type(key) == "string" and #key == 1 and key ~= "'"
    and (key:match("%s") ~= nil or key:match("[%p]") ~= nil)
end

local buffer_navigation_commands = {
  bp = true, bprevious = true, bN = true, bNext = true,
  bn = true, bnext = true,
  bf = true, bfirst = true, brewind = true,
  bl = true, blast = true,
}

local function trimmed_command(value)
  return tostring(value or ""):gsub("^%s+", ""):gsub("%s+$", "")
end

local function listed_buffer_count()
  local count = 0
  for _, buffer in ipairs(vim.api.nvim_list_bufs()) do
    if vim.fn.buflisted(buffer) == 1 then count = count + 1 end
  end
  return count
end

local function emit_command_preflight(command)
  local normalized = trimmed_command(command)
  if vim.bo.buftype == "terminal" and (normalized == "bd" or normalized == "bdelete") then
    local job = tonumber(vim.b.terminal_job_id)
    local status = job and job > 0 and vim.fn.jobwait({ job }, 0)[1] or nil
    if status == -1 then
      predicted_ui_error_code = "E89"
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

local function error_ending_at(snapshot, byte_column)
  local nearest
  for _, item in ipairs(snapshot.spellingErrors or {}) do
    if item.endByteColumn == byte_column then nearest = item end
  end
  return nearest
end

local function emit_typed_spelling_error(before)
  local snapshot = state.snapshot("spellingTypingCheck")
  local cursor = snapshot.cursor or {}
  local nearest = error_ending_at(snapshot, math.max(0, (cursor.byteColumn or 0) - 1))
    or error_ending_at(before or {}, ((before or {}).cursor or {}).byteColumn)
  if nearest then emit("spellingErrorTyped", "spellingTypingCheck", { spellingError = nearest }) end
end

emit = function(event_type, reason, extra)
  if not channel then
    return
  end
  if (event_type == "messageReceived" or event_type == "errorReceived")
    and type(extra) == "table" and type(extra.message) == "string" then
    local now = vim.uv.hrtime()
    if extra.message == last_message_text and now - last_message_time < 500000000 then return end
    last_message_text = extra.message
    last_message_time = now
  end
  sequence = sequence + 1
  local snapshot_ok, payload = pcall(state.snapshot, reason)
  if not snapshot_ok then
    -- Never turn an accessibility snapshot bug into a Neovim hit-enter
    -- prompt. Closing the RPC channel makes the NVDA side disconnect and
    -- restore native terminal output fail-open.
    pcall(vim.fn.chanclose, channel)
    pcall(vim.ui_detach, ui_namespace)
    channel = nil
    pending_navigation = false
    return
  end
  if extra then
    for key, value in pairs(extra) do
      payload[key] = value
    end
  end
  if reason == "oilConfirmationFallback" then
    -- Oil renders full paths in its private confirmation float. The semantic
    -- fallback deliberately publishes only fixed verbs and a count.
    payload.lineText = ""
    payload.character = ""
    payload.word = ""
  end
  file_manager_events.observe(payload.fileManager)
  local current_error = tostring(vim.v.errmsg or "")
  payload.currentErrorCode = current_error:match("E%d+") or ""
  payload.currentErrorKind = fixed_error_kind(current_error)
  payload.keyObserverDiagnostics = vim.deepcopy(key_observer_diagnostics)
  local ok = pcall(vim.rpcnotify, channel, "nvim_nvda_event", {
    sequence = sequence,
    timestampMonotonic = vim.uv.hrtime(),
    type = event_type,
    payload = payload,
  })
  if not ok then
    pcall(vim.ui_detach, ui_namespace)
    channel = nil
    pending_navigation = false
  end
end

local function emit_oil_confirmation()
  local details = file_manager_prompt.current_oil_confirmation()
  if not details then return false end
  local buffer = vim.api.nvim_get_current_buf()
  if oil_confirmation_buffer ~= buffer then
    oil_confirmation_buffer = buffer
    oil_confirmation_choice = nil
    emit("promptOpened", "oilConfirmationFallback", details)
  end
  return true
end

local function close_oil_confirmation(buffer, reason)
  if oil_confirmation_buffer ~= buffer then return end
  local choice = oil_confirmation_choice
  oil_confirmation_buffer = nil
  oil_confirmation_choice = nil
  local accepted
  if choice == "yes" then
    accepted = true
  elseif choice == "no" then
    accepted = false
  end
  emit("promptClosed", reason, {
    promptKind = "confirm",
    accepted = accepted,
  })
end

local function clear_ui_message_prompt()
  ui_message_prompt_kind = nil
  key_observer_diagnostics.promptActive = false
  key_observer_diagnostics.promptKind = nil
  key_observer_diagnostics.promptClass = nil
  key_observer_diagnostics.promptLength = nil
end

local function close_ui_message_prompt(reason)
  if not ui_message_prompt_kind then return end
  local prompt_kind = ui_message_prompt_kind
  clear_ui_message_prompt()
  emit("promptClosed", reason, {
    promptKind = prompt_kind,
    answered = true,
  })
end

local function is_blocking_prompt_mode(mode)
  return mode == "r" or mode == "rm" or mode == "r?"
end

local function schedule_navigation(reason)
  if pending_navigation then
    return
  end
  pending_navigation = true
  local motion = pending_motion
  local motion_details = pending_motion_details
  local search_direction = pending_search_direction
  pending_motion = nil
  pending_motion_details = nil
  pending_search_direction = nil
  vim.schedule(function()
    pending_navigation = false
    if oil_confirmation_buffer == vim.api.nvim_get_current_buf() then return end
    local raw = vim.api.nvim_get_mode().mode
    if raw:sub(1, 1) == "i" and not motion then
      return
    end
    if motion == "suppress" then
      return
    end
    local event_type = (raw == "v" or raw == "V" or raw == "\22") and "selectionChanged"
      or motion or "cursorMoved"
    if file_manager.current() then event_type = "fileManagerEntryChanged" end
    if motion == "matchingPairMoved" then pending_matching = nil end
    local extra
    if event_type == "searchMatchChanged" then
      extra = search_details(nil, search_direction)
    elseif motion_details then
      extra = motion_details
    end
    emit(event_type, reason, extra)
  end)
end

local function emit_menu_events(events, reason)
  for _, menu_event in ipairs(events) do
    emit(menu_event.type, reason, menu_event.payload)
  end
end

local function setup_signature_help()
  if signature_handler_wrapped or not vim.lsp or not vim.lsp.handlers then return end
  local method = "textDocument/signatureHelp"
  local original = vim.lsp.handlers[method]
  if type(original) ~= "function" then return end
  vim.lsp.handlers[method] = function(error, result, context, config)
    if not error and type(result) == "table" and type(result.signatures) == "table" then
      local signature_index = (tonumber(result.activeSignature) or 0) + 1
      local signature = result.signatures[signature_index] or result.signatures[1]
      if type(signature) == "table" then
        local active_parameter = tonumber(result.activeParameter)
        if active_parameter == nil then active_parameter = tonumber(signature.activeParameter) end
        local parameter
        if active_parameter and type(signature.parameters) == "table" then
          local value = signature.parameters[active_parameter + 1]
          if type(value) == "table" then parameter = value.label end
        end
        emit("signatureChanged", "lspSignatureHelp", {
          signature = type(signature.label) == "string" and signature.label:sub(1, 2048) or "",
          activeParameter = active_parameter and active_parameter + 1 or nil,
          parameter = type(parameter) == "string" and parameter:sub(1, 512) or "",
          signatureIndex = signature_index,
          signatureCount = #result.signatures,
        })
      end
    end
    return original(error, result, context, config)
  end
  signature_handler_wrapped = true
end

local function setup_notifications()
  if notify_wrapped then return end
  local original = vim.notify
  vim.notify = function(message, level, options)
    emit("messageReceived", "vim.notify", {
      message = tostring(message):sub(1, 2048), messageLevel = tonumber(level),
      messageTitle = type(options) == "table" and options.title or nil,
    })
    return original(message, level, options)
  end
  notify_wrapped = true
end

local function setup_ui_functions()
  if ui_wrapped then return end
  local original_input = vim.ui.input
  local original_select = vim.ui.select
  vim.ui.input = function(options, on_confirm)
    options = options or {}
    emit("promptOpened", "vim.ui.input", {
      promptKind = "input",
      prompt = bounded_utf8(tostring(options.prompt or "Input"), 2048),
      defaultValuePresent = options.default ~= nil and tostring(options.default) ~= "",
    })
    return original_input(options, function(value)
      emit("promptClosed", "vim.ui.input", {
        promptKind = "input", accepted = value ~= nil,
      })
      return on_confirm(value)
    end)
  end
  vim.ui.select = function(items, options, on_choice)
    options = options or {}
    items = type(items) == "table" and items or {}
    local formatter = type(options.format_item) == "function" and options.format_item or tostring
    local normalized = {}
    for index, item in ipairs(items) do
      local ok, label = pcall(formatter, item)
      normalized[index] = {
        word = bounded_utf8(ok and tostring(label) or tostring(item), 512),
      }
    end
    emit("promptOpened", "vim.ui.select", {
      promptKind = "select",
      prompt = bounded_utf8(tostring(options.prompt or "Select"), 2048),
      itemCount = #normalized,
    })
    emit_menu_events(ui_select_menu:update({
      mode = "select", pum_visible = #normalized > 0, selected = #normalized > 0 and 0 or -1,
      items = normalized,
    }), "vim.ui.select")
    return original_select(items, options, function(choice, index)
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
  ui_wrapped = true

  if not confirm_wrapped then
    local original_confirm = vim.fn.confirm
    vim.fn.confirm = function(message, choices, default_choice, dialog_type)
      local prompt = bounded_utf8(tostring(message or "Confirm"), 2048)
      local labels = {}
      for label in tostring(choices or ""):gmatch("[^\n]+") do
        labels[#labels + 1] = bounded_utf8(
          label:gsub("&", ""):gsub("\t.*$", ""), 512
        )
      end
      emit("promptOpened", "vim.fn.confirm", {
        promptKind = "confirm", prompt = prompt, itemCount = #labels,
      })
      wrapped_confirm_active = true
      local ok, result = pcall(original_confirm, message, choices, default_choice, dialog_type)
      wrapped_confirm_active = false
      if not ok then error(result) end
      recent_wrapped_confirm_prompt = prompt
      recent_wrapped_confirm_time = vim.uv.hrtime()
      local selected_index = tonumber(result)
      emit("promptClosed", "vim.fn.confirm", {
        promptKind = "confirm", answered = true,
        selectedIndex = selected_index,
        selectedLabel = selected_index and labels[selected_index] or nil,
      })
      return result
    end
    confirm_wrapped = true
  end
end

local function setup_ui_events()
  local function message_text(content)
    local chunks = {}
    for _, chunk in ipairs(type(content) == "table" and content or {}) do
      chunks[#chunks + 1] = type(chunk) == "table" and tostring(chunk[2] or "") or ""
    end
    local text = table.concat(chunks):gsub("^%s+", ""):gsub("%s+$", "")
    return bounded_utf8(text, 2048)
  end
  local function handle_ui_event(event, command_line_was_active, command_text, command_type, ...)
    if event == "msg_show" then
      local kind, content = ...
      if kind == "search_count" then
        return
      end
      local prompt_kind = kind == "confirm" and "confirm"
        or kind == "confirm_sub" and "confirmSub"
        or kind == "return_prompt" and "more"
      if prompt_kind then
        local text = message_text(content)
        if prompt_kind == "confirm" then
          local recent_duplicate = type(recent_wrapped_confirm_prompt) == "string"
            and vim.uv.hrtime() - recent_wrapped_confirm_time < 1000000000
            and text:find(recent_wrapped_confirm_prompt, 1, true) == 1
          if wrapped_confirm_active or recent_duplicate then return end
        end
        ui_message_prompt_kind = prompt_kind
        key_observer_diagnostics.promptActive = true
        key_observer_diagnostics.promptKind = prompt_kind
        key_observer_diagnostics.promptClass = fixed_prompt_kind(text)
        key_observer_diagnostics.promptLength = #text
        emit("promptOpened", "uiMessage", {
          promptKind = prompt_kind, prompt = text ~= "" and text or "Continue",
        })
      elseif kind == "emsg" or kind == "echoerr" or kind == "lua_error" or kind == "rpc_error" then
        local text = message_text(content)
        local error_code = text:match("E%d+")
        if predicted_ui_error_code and error_code == predicted_ui_error_code then
          predicted_ui_error_code = nil
        elseif text ~= "" then
          emit("errorReceived", "uiMessage", { message = text })
        end
      else
        -- An empty kind is the normal UI-protocol fallback for messages which
        -- do not have a more specific classification. Treat it, and future
        -- non-prompt message kinds, as ordinary status output so command
        -- results are not silently lost.
        local text = message_text(content)
        local command_echo = text == last_command_line_echo
          or (command_type ~= "" and text == command_type .. command_text)
        if text ~= "" and not command_echo then
          emit("messageReceived", "uiMessage", { message = text })
        end
      end
      return
    elseif event == "msg_clear" then
      close_ui_message_prompt("uiMessage")
      return
    end
    if not command_line_was_active then return end
    if event == "popupmenu_show" then
      local raw_items, selected = ...
      local items = {}
      for index, raw in ipairs(type(raw_items) == "table" and raw_items or {}) do
        items[index] = {
          word = tostring(raw[1] or ""), kind = tostring(raw[2] or ""),
          menu = tostring(raw[3] or ""), info = tostring(raw[4] or ""),
        }
      end
      command_line_menu_items = items
      emit_menu_events(command_line_menu:update({
        mode = "wildmenu", pum_visible = #items > 0, selected = tonumber(selected) or -1, items = items,
      }), "wildmenu")
    elseif event == "popupmenu_select" then
      local selected = ...
      if #command_line_menu_items > 0 then
        emit_menu_events(command_line_menu:update({
          mode = "wildmenu", pum_visible = true, selected = tonumber(selected) or -1,
          items = command_line_menu_items,
        }), "wildmenu")
      end
    elseif event == "popupmenu_hide" then
      command_line_menu_items = {}
      emit_menu_events(command_line_menu:close("hidden"), "wildmenu")
    end
  end
  pcall(vim.ui_detach, ui_namespace)
  pcall(vim.ui_attach, ui_namespace, { ext_popupmenu = true, ext_messages = true }, function(event, ...)
    local arguments = { ... }
    local command_line_was_active = command_line_active
    local command_text = command_line_text
    local command_type = command_line_type
    -- Neovim 0.12 enforces the fast-event boundary for vim.ui_attach. State
    -- snapshots and RPC notifications must run after the callback returns.
    vim.schedule(function()
      handle_ui_event(
        event, command_line_was_active, command_text, command_type, unpack(arguments)
      )
    end)
  end)
end

function M.register_channel(rpc_channel)
  assert(type(rpc_channel) == "number" and rpc_channel > 0, "valid RPC channel required")
  channel = rpc_channel
  sequence = 0
  -- ext_messages/ext_popupmenu transfer ownership away from the native TUI.
  -- Attach only while an authenticated consumer exists, otherwise startup
  -- prompts (notably swap-file recovery) become invisible and violate the
  -- required fail-open behavior.
  setup_ui_events()
  local error_text = tostring(vim.v.errmsg or "")
  local error_code = error_text:match("E%d+") or ""
  local error_kind = error_text:find("str_utfindex", 1, true) and "strUtfIndex"
    or error_text:find("textlock", 1, true) and "textlock"
    or error_text:find("fs_rename", 1, true) and "registryRename"
    or error_text:find("nvim_nvda", 1, true) and "nvimNvdaLua"
    or error_text ~= "" and "other"
    or ""
  emit("fullState", "registerChannel", {
    preConnectErrorCode = error_code,
    preConnectErrorKind = error_kind,
    keyObserverDiagnostics = key_observer_diagnostics,
  })
end

function M.unregister_channel(rpc_channel)
  if channel == rpc_channel then
    pcall(vim.ui_detach, ui_namespace)
    channel = nil
  end
end

function M.key_observer_diagnostics()
  return vim.deepcopy(key_observer_diagnostics)
end

function M.request_copy_text(payload)
  local result = clipboard.copy_text(payload)
  emit("copyTextResult", "copyTextRequest", result)
  return result.ok
end

function M.request_paste_text(payload)
  local result = clipboard.paste_text(payload)
  emit("pasteTextResult", "pasteTextRequest", result)
  return result.ok
end

function M.request_set_register(payload)
  local result = clipboard.set_register(payload)
  emit("setRegisterResult", "setRegisterRequest", result)
  return result.ok
end

function M.request_leave_terminal_input(payload)
  local result = {
    requestId = type(payload) == "table" and payload.requestId or -1,
    ok = false,
    resultCode = "invalidRequest",
  }
  if type(payload) == "table"
    and type(payload.requestId) == "number"
    and payload.requestId % 1 == 0
    and payload.requestId >= 0 and payload.requestId <= 2147483647
    and type(payload.bufferId) == "number"
    and type(payload.windowId) == "number"
    and type(payload.tabpageId) == "number"
    and payload.modeRaw == "t" then
    local current_mode = vim.api.nvim_get_mode().mode
    local exact_context = vim.api.nvim_get_current_buf() == payload.bufferId
      and vim.api.nvim_get_current_win() == payload.windowId
      and vim.api.nvim_get_current_tabpage() == payload.tabpageId
      and current_mode == payload.modeRaw
      and vim.bo[payload.bufferId].buftype == "terminal"
    if exact_context then
      local stopped = pcall(vim.cmd, "stopinsert")
      result.ok = stopped
      result.resultCode = stopped and "ok" or "stopFailed"
    else
      result.resultCode = "staleState"
    end
  end
  emit("leaveTerminalInputResult", "leaveTerminalInputRequest", result)
  return result.ok
end

function M.setup()
  local component_config = require("nvim_nvda.component_config").load()
  group = vim.api.nvim_create_augroup("NvimNvda", { clear = true })
  setup_signature_help()
  setup_notifications()
  setup_ui_functions()
  completion_adapters.stop()
  file_manager_events.setup(function(reason)
    emit("fileManagerEntryChanged", reason)
  end, function(action)
    emit("fileManagerActionResult", "fileManagerAction", { fileManagerAction = action })
  end, group)
  vim.on_key(function(key, typed)
    local observer_ok, observer_error = pcall(function()
    local translated = vim.fn.keytrans(key)
    local typed_translated = vim.fn.keytrans(typed or "")
    if oil_confirmation_buffer then
      if typed_translated ~= "" then
        local choice = typed_translated:lower()
        if choice == "y" then
          oil_confirmation_choice = "yes"
        elseif choice == "n" then
          oil_confirmation_choice = "no"
        else
          oil_confirmation_choice = nil
        end
      end
      -- The key still continues to Oil's buffer-local mapping. It must not
      -- also seed editor motion/operator state in this observer.
      return
    end
    if typed_translated:lower() == component_config.sessionClaim.neovimKey:lower() then
      key_observer_diagnostics.keyByteLength = #key
      key_observer_diagnostics.typedByteLength = #(typed or "")
      key_observer_diagnostics.translatedKey = translated
      key_observer_diagnostics.translatedTyped = typed_translated
      local claim_mode = vim.api.nvim_get_mode().mode
      if claim_mode:sub(1, 1) == "r" then
        key_observer_diagnostics.claimSkippedMode = claim_mode
        return
      end
      key_observer_diagnostics.claimSkippedMode = ""
      -- Registry writes call regular Vim functions and filesystem APIs. Keep
      -- them outside the input callback: newer Neovim versions enforce the
      -- on_key/textlock boundary more strictly and otherwise enter a hit-enter
      -- error state even though the physical key was recognized correctly.
      vim.schedule(function()
        local claim_ok, claim_error = pcall(require("nvim_nvda.session").claim)
        key_observer_diagnostics.claimErrorKind = claim_ok and "" or fixed_error_kind(claim_error)
        local mode_ok, mode_value = pcall(vim.api.nvim_get_mode)
        key_observer_diagnostics.modeAfterClaim = mode_ok and mode_value.mode or "unavailable"
      end)
      return
    end
    if command_line_generated_keys and (typed == nil or typed == "") then
      -- Ex commands such as :normal may execute Normal-mode keys after
      -- CmdlineLeave. They are command output, not a directly typed motion.
      pending_motion = nil
      return
    end
    local raw_mode = vim.api.nvim_get_mode().mode
    -- Neovim 0.10 can still report raw Normal mode from vim.on_key while its
    -- command line is active. The explicit CmdlineEnter state is authoritative
    -- so command text such as the final `l` in `:normal! l` cannot become a
    -- pending editor motion.
    local operator_context = raw_mode:sub(1, 1) == "n" and not command_line_active
    local visual_context = not command_line_active
      and (raw_mode == "v" or raw_mode == "V" or raw_mode == "\22")
    if operator_context and pending_register_prefix then
      pending_register_prefix = false
      if #translated == 1 then
        local contents = vim.fn.getreg(translated)
        emit("registerSelected", "registerCommand", {
          registerName = translated, registerType = vim.fn.getregtype(translated),
          registerText = type(contents) == "string" and contents:sub(1, 2048) or "",
        })
      end
      return
    elseif operator_context and translated == '"' then
      pending_register_prefix = true
      return
    end
    if operator_context and pending_macro_prefix then
      pending_macro_prefix = false
      if #translated == 1 or translated == "@" then
        local name = translated == "@" and vim.fn.reg_executing() or translated
        vim.defer_fn(function()
          emit("macroPlayed", "macroCommand", { registerName = name ~= "" and name or "last" })
        end, 20)
      end
      return
    elseif operator_context and translated == "@" then
      pending_macro_prefix = true
      return
    end
    if operator_context and pending_z then
      local action = fold_actions[translated]
      local before = pending_z.before
      pending_z = nil
      if action == "next" or action == "previous" then
        pending_motion = "foldMoved"
        pending_motion_details = { foldAction = action }
      elseif action then
        vim.defer_fn(function()
          local details = fold_at_cursor()
          details.foldAction = action
          if not details.closed and before and before.closed then
            details.startLine, details.endLine = before.startLine, before.endLine
          end
          emit("foldChanged", "foldCommand", details)
        end, 20)
      end
      return
    elseif operator_context and translated == "z" then
      pending_z = { before = fold_at_cursor() }
      return
    end
    if operator_context and pending_mark_prefix then
      local prefix = pending_mark_prefix
      pending_mark_prefix = nil
      if #translated == 1 then
        if prefix == "m" then
          vim.defer_fn(function()
            local position = vim.fn.getpos("'" .. translated)
            emit("markSet", "markCommand", {
              markName = translated, markLine = position[2], markByteColumn = math.max(0, position[3] - 1),
            })
          end, 20)
        else
          pending_motion = "suppress"
          vim.defer_fn(function()
            emit("markMoved", "markCommand", {
              markName = translated, markExact = prefix == "`",
            })
          end, 20)
        end
      end
      return
    elseif operator_context and (translated == "m" or translated == "'" or translated == "`") then
      pending_mark_prefix = translated
      return
    end
    if operator_context and translated == "d" then
      if pending_edit and pending_edit.operator == "d" then
        pending_edit.linewise = true
      else
        pending_edit = { operator = "d", kind = "textDeleted", beforeText = vim.api.nvim_get_current_line() }
      end
    elseif operator_context and translated == "c" then
      if pending_edit and pending_edit.operator == "c" then
        pending_edit.linewise = true
      else
        pending_edit = { operator = "c", kind = "textReplaced", beforeText = vim.api.nvim_get_current_line() }
      end
    elseif operator_context and translated == "C" then
      pending_edit = { operator = "c", kind = "textReplaced", beforeText = vim.api.nvim_get_current_line() }
    elseif translated == "<Esc>" then
      -- With feedkeys, Escape can arrive before TextChanged for a completed
      -- change operator. Classify an actual buffer change now, but discard a
      -- genuinely cancelled operator so it cannot leak into later typing.
      if pending_edit and vim.api.nvim_get_current_line() ~= pending_edit.beforeText then
        emit(pending_edit.kind, "operatorEscape", {
          beforeText = pending_edit.beforeText,
          linewise = pending_edit.linewise or false,
        })
        suppress_next_text_change = true
      end
      pending_edit = nil
    end
    if translated == "g" then
      if pending_g then
        pending_motion = "fileStart"
        pending_g = false
      else
        pending_g = true
      end
      return
    end
    if operator_context and (translated == "[" or translated == "]") then
      pending_bracket = translated
      return
    elseif operator_context and pending_bracket then
      if translated == "d" then
        pending_motion = "diagnosticMoved"
      elseif translated == "s" then
        pending_motion = "wordMoved"
      end
      pending_bracket = nil
      return
    end
    -- Motions belonging to an edit operator (for example the `w` in `cw`)
    -- must never escape later as navigation. Neovim may not expose Insert
    -- mode to vim.on_key until the first replacement character is processed;
    -- retaining `wordMoved` here would therefore announce the following word
    -- when that first character is typed.
    if raw_mode:sub(1, 1) == "i" then
      pending_motion = insert_motion_events[translated]
    elseif pending_edit and operator_context then
      pending_motion = "suppress"
    elseif operator_context or visual_context then
      pending_motion = motion_events[translated]
    else
      -- Command-line and direct-terminal input is text, even when a typed
      -- character is a Normal-mode motion such as h, j, k, or l.  Retaining
      -- such a character can misclassify the next automatic cursor update in
      -- a newly created terminal buffer as explicit navigation.
      pending_motion = nil
    end
    if operator_context and translated == "n" then pending_search_direction = "next" end
    if operator_context and translated == "N" then pending_search_direction = "previous" end
    if operator_context and translated == "%" then
      local attempt = {}
      pending_matching = attempt
      vim.defer_fn(function()
        if pending_matching == attempt then
          pending_matching = nil
          emit("matchingPairNotFound", "percentMotion")
        end
      end, 30)
    end
    if raw_mode:sub(1, 1) == "i" and is_word_terminator(key) then
      local before = state.snapshot("beforeSpellingTerminator")
      vim.defer_fn(function() emit_typed_spelling_error(before) end, 50)
    end
    pending_g = false
    end)
    if not observer_ok then
      key_observer_diagnostics.observerErrorCount = key_observer_diagnostics.observerErrorCount + 1
      key_observer_diagnostics.observerErrorKind = fixed_error_kind(observer_error)
    end
  end, key_namespace)
  vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
    group = group,
    callback = function(event)
      schedule_navigation(event.event)
    end,
  })
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI", "TextChangedP" }, {
    group = group,
    callback = function(event)
      if emit_oil_confirmation() then return end
      if suppress_next_text_change then
        suppress_next_text_change = false
        return
      end
      -- Completion selection temporarily edits the buffer as the highlighted
      -- candidate changes. Its structured menu event is the authoritative
      -- output; speaking this as normal typing produces fragments such as the
      -- candidate index or suffix over the menu announcement.
      if event.event == "TextChangedP" and vim.fn.pumvisible() == 1 then
        return
      end
      if pending_edit then
        emit(pending_edit.kind, event.event, {
          beforeText = pending_edit.beforeText,
          linewise = pending_edit.linewise or false,
        })
        pending_edit = nil
      else
        emit("textChanged", event.event)
      end
    end,
  })
  vim.api.nvim_create_autocmd({ "CmdlineEnter", "CmdlineChanged" }, {
    group = group,
    callback = function(event)
      if event.event == "CmdlineEnter" then
        command_line_active = true
        command_line_generated_keys = false
        predicted_ui_error_code = nil
        command_line_text = ""
        command_line_type = vim.fn.getcmdtype()
        command_changedtick = vim.api.nvim_buf_get_changedtick(0)
        vim.v.errmsg = ""
        vim.v.statusmsg = ""
      end
      command_line_text = vim.fn.getcmdline()
      emit("commandLineChanged", event.event, {
        commandLineType = command_line_type,
      })
    end,
  })
  vim.api.nvim_create_autocmd("CmdlineLeave", {
    group = group,
    callback = function()
      command_line_menu_items = {}
      emit_menu_events(command_line_menu:close("commandLineLeave"), "CmdlineLeave")
      command_line_active = false
      local command = command_line_text
      local command_type = command_line_type
      last_command_line_echo = command_type .. command
      local before_tick = command_changedtick
      command_line_text = ""
      command_line_type = ""
      command_line_generated_keys = command_type == ":"
      vim.schedule(function() command_line_generated_keys = false end)
      if command_type == ":" then emit_command_preflight(command) end
      local guarded = vim.bo.modified and (command:match("^%s*q%s*$") or command:match("^%s*quit%s*$"))
      if guarded then
        emit("errorReceived", "commandGuard", {
          message = "E37: No write since last change; use :q! to discard changes or :write to save",
        })
      end
      vim.defer_fn(function()
        local message = vim.v.errmsg
        if not guarded and not command_line_active and type(message) == "string" and message ~= "" then
          vim.v.errmsg = ""
          emit("errorReceived", "commandError", { message = message:sub(1, 2048) })
        elseif not command_line_active and (command_type == "/" or command_type == "?") then
          local ok, details = pcall(search_details, command, command_type)
          if ok then emit("searchMatchChanged", "searchCommand", details) end
        elseif not command_line_active and command_type == ":"
          and (command:match("^%s*%%?s[^%w%s]") or command:match("^%s*substitute%s+"))
          and vim.api.nvim_buf_get_changedtick(0) ~= before_tick then
          local status = vim.v.statusmsg
          emit("replacementPerformed", "substituteCommand", {
            replacementMessage = type(status) == "string" and status:sub(1, 2048) or "",
          })
        elseif not command_line_active and type(vim.v.statusmsg) == "string"
          and vim.v.statusmsg ~= "" then
          local status = vim.v.statusmsg
          vim.v.statusmsg = ""
          emit("messageReceived", "commandStatus", { message = status:sub(1, 2048) })
        end
      end, 20)
    end,
  })
  vim.api.nvim_create_autocmd("CompleteChanged", {
    group = group,
    callback = function(event)
      local info = vim.fn.complete_info({ "mode", "pum_visible", "items", "selected" })
      emit_menu_events(completion_menu:update(info), event.event)
    end,
  })
  vim.api.nvim_create_autocmd("CompleteDonePre", {
    group = group,
    callback = function(event)
      emit_menu_events(completion_menu:close("completionDone"), event.event)
    end,
  })
  vim.api.nvim_create_autocmd("InsertLeave", {
    group = group,
    callback = function(event)
      emit_menu_events(completion_menu:close("insertLeave"), event.event)
    end,
  })
  vim.api.nvim_create_autocmd("ModeChanged", {
    group = group,
    callback = function(event)
      local change = vim.v.event or {}
      local old_mode = tostring(change.old_mode or "")
      local new_mode = tostring(change.new_mode or "")
      if is_blocking_prompt_mode(old_mode) and not is_blocking_prompt_mode(new_mode) then
        -- confirm()/hit-enter transitions may not produce msg_clear or
        -- CmdlineLeave. The semantic mode transition is the authoritative
        -- close event; clear the synthetic command-line state as well.
        command_line_active = false
        command_line_text = ""
        command_line_type = ""
        if wrapped_confirm_active then
          -- The public confirm() wrapper publishes the answer after the
          -- blocking call returns. Avoid a second, less informative close.
          clear_ui_message_prompt()
        else
          close_ui_message_prompt(event.event)
        end
      end
      emit("modeChanged", event.event)
    end,
  })
  vim.api.nvim_create_autocmd("TermClose", {
    group = group,
    callback = function()
      -- v:event is scoped to this autocmd; copy its scalar before any
      -- scheduling. Terminal screen output itself remains native WT output.
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
      local contents = vim.fn.getreg(name)
      emit("registerChanged", event.event, {
        registerName = name, registerType = details.regtype,
        registerText = type(contents) == "string" and contents:sub(1, 2048) or "",
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
        registerText = type(name) == "string" and vim.fn.getreg(name):sub(1, 2048) or "",
      })
    end,
  })
  vim.api.nvim_create_autocmd({
    "BufEnter", "BufWinEnter", "WinEnter", "TabEnter", "TermOpen", "TermEnter", "TermLeave",
  }, {
    group = group,
    callback = function(event)
      local reason = event.event
      vim.schedule(function()
        if not emit_oil_confirmation() then emit("contextChanged", reason) end
      end)
    end,
  })
  vim.api.nvim_create_autocmd({ "BufLeave", "BufWipeout" }, {
    group = group,
    callback = function(event)
      -- Oil closes its confirmation float from the Y/N buffer mapping. Defer
      -- the close event until vim.on_key has observed the directly typed key;
      -- no timer or polling is involved.
      local buffer = event.buf
      local reason = event.event
      vim.schedule(function() close_oil_confirmation(buffer, reason) end)
    end,
  })
  vim.schedule(function() completion_adapters.setup(M, group) end)
end

function M._test_emit(event_type)
  emit(event_type, "test")
end

function M._test_menu_update(info)
  emit_menu_events(completion_menu:update(info), "testMenu")
end

function M._test_menu_close()
  emit_menu_events(completion_menu:close("testDone"), "testMenu")
end

-- Public adapter for plugins which draw a custom menu instead of using
-- Neovim's built-in completion popup. Items use complete-item fields.
function M.accessible_menu_open(items, options)
  options = options or {}
  adapter_info = {
    mode = options.kind or "plugin",
    pum_visible = true,
    selected = (options.selected or 1) - 1,
    items = items or {},
  }
  emit_menu_events(adapter_menu:update(adapter_info), "pluginMenu")
end

function M.accessible_menu_select(one_based_index)
  if not adapter_info then return end
  adapter_info.selected = (tonumber(one_based_index) or 0) - 1
  emit_menu_events(adapter_menu:update(adapter_info), "pluginMenu")
end

function M.accessible_menu_close()
  adapter_info = nil
  emit_menu_events(adapter_menu:close("pluginClosed"), "pluginMenu")
end

-- Public adapter for file managers which do not use netrw. Detector and
-- provider must be synchronous, bounded, and free of I/O and polling. The
-- detector returns true while its view is active; the provider returns root
-- and entry. Repeated errors or calls over the runtime budget fail open.
function M.register_file_manager_adapter(name, detector, provider)
  file_manager.register(name, detector, provider)
end

function M.unregister_file_manager_adapter(name)
  file_manager.unregister(name)
end

return M
