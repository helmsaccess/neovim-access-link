local state = require("nvim_nvda.state")
local completion_adapters = require("nvim_nvda.completion_adapters")
local signature_help = require("nvim_nvda.signature_help")
local lsp_hover = require("nvim_nvda.lsp_hover")
local lsp_status = require("nvim_nvda.lsp_status")
local file_manager = require("nvim_nvda.file_manager")
local file_manager_events = require("nvim_nvda.file_manager_events")
local clipboard = require("nvim_nvda.clipboard")
local exploration = require("nvim_nvda.exploration")
local developer_context = require("nvim_nvda.developer_context")
local native_operations = require("nvim_nvda.native_operations")
local event_channel_factory = require("nvim_nvda.event_channel")
local braille_routing_factory = require("nvim_nvda.braille_routing")
local completion_events_factory = require("nvim_nvda.completion_events")
local input_events_factory = require("nvim_nvda.input_events")
local command_line_events_factory = require("nvim_nvda.command_line_events")
local ui_events_factory = require("nvim_nvda.ui_events")
local file_manager_prompt_events_factory = require("nvim_nvda.file_manager_prompt_events")
local context_events_factory = require("nvim_nvda.context_events")
local M = {}

local event_channel
local input_events
local command_line_events
local ui_events
local file_manager_prompt_events
local context_events
local emit

local function fixed_error_kind(value)
  local text = tostring(value or "")
  if text == "" then return "" end
  if text:find("textlock", 1, true) then return "textlock" end
  if text:find("keytrans", 1, true) then return "keytrans" end
  if text:find("fs_rename", 1, true) then return "registryRename" end
  if text:find("nvim_nvda", 1, true) then return "nvimNvdaLua" end
  return "other"
end

event_channel = event_channel_factory.new({
  snapshot = state.snapshot,
  decorate = function(payload, reason)
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
    payload.keyObserverDiagnostics = input_events and input_events.diagnostics()
      or { observerErrorCount = 0 }
    payload.completionAdapterDiagnostics = completion_adapters.diagnostics()
  end,
  on_disconnect = function(_, scheduled_ui_detach)
    pcall(signature_help.set_connected, false)
    if input_events then pcall(input_events.reset) end
    if ui_events then pcall(ui_events.detach, scheduled_ui_detach) end
  end,
})
emit = event_channel.emit

local emit_prebuilt = event_channel.emit_prebuilt
local braille_routing = braille_routing_factory.new(emit)
local completion_events = completion_events_factory.new(emit)
file_manager_prompt_events = file_manager_prompt_events_factory.new(emit)
command_line_events = command_line_events_factory.new({
  emit = emit,
  close_numbered_choice = function(reason)
    if ui_events then ui_events.close_numbered_choice(reason) end
  end,
})
ui_events = ui_events_factory.new({
  emit = emit,
  emit_prebuilt = emit_prebuilt,
  command_line = command_line_events,
  set_prompt_diagnostics = function(details)
    if input_events then input_events.set_prompt_diagnostics(details) end
  end,
  clear_prompt_diagnostics = function()
    if input_events then input_events.clear_prompt_diagnostics() end
  end,
})
input_events = input_events_factory.new({
  emit = emit,
  command_line_state = command_line_events.state,
  observe_oil_key = file_manager_prompt_events.observe_key,
  oil_confirmation_active = file_manager_prompt_events.is_active_buffer,
  emit_oil_confirmation = file_manager_prompt_events.emit_if_active,
  set_spell_candidate = ui_events.set_spell_candidate,
  search_details = function(pattern, direction)
    return native_operations.search_details(pattern, direction, false)
  end,
  classify_error = fixed_error_kind,
})
context_events = context_events_factory.new({
  emit = emit,
  emit_oil_confirmation = file_manager_prompt_events.emit_if_active,
})

native_operations.set_prebuilt_emitter(emit_prebuilt)

function M.register_channel(rpc_channel)
  exploration.reset()
  native_operations.reset()
  input_events.reset()
  ui_events.reset()
  event_channel.connect(rpc_channel)
  signature_help.set_connected(true)
  -- ext_messages/ext_popupmenu transfer ownership away from the native TUI.
  -- Attach only while an authenticated consumer exists, otherwise startup
  -- prompts (notably swap-file recovery) become invisible and violate the
  -- required fail-open behavior.
  ui_events.attach()
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
    keyObserverDiagnostics = input_events.diagnostics(),
  })
end

function M.unregister_channel(rpc_channel)
  if event_channel.is_connected() then
    local disconnected = event_channel.disconnect(rpc_channel)
    if disconnected then
      exploration.reset()
      native_operations.reset()
      ui_events.reset()
    end
  end
end

function M.key_observer_diagnostics()
  return input_events.diagnostics()
end

function M.request_route_cursor(payload)
  return braille_routing.route_cursor(payload)
end

function M.request_braille_route_action(payload)
  return braille_routing.route_action(payload)
end

function M.request_move_braille_line(payload)
  return braille_routing.move_line(payload)
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

function M.request_explore_text(payload)
  local result = exploration.step(payload)
  emit("exploreTextResult", "exploreTextRequest", result)
  return result.ok
end

function M.request_end_exploration(payload)
  return exploration.finish(payload)
end

function M.request_braille_explore_line(payload)
  local result = exploration.step(payload, "braille")
  emit("brailleExploreLineResult", "brailleExploreLineRequest", result)
  return result.ok
end

function M.request_end_braille_exploration(payload)
  return exploration.finish(payload, "braille")
end

function M.request_callable_context(payload)
  return developer_context.request_callable(payload, emit)
end

function M.request_diagnostic_context(payload)
  return developer_context.request_diagnostics(payload, emit)
end

function M.setup()
  local component_config = require("nvim_nvda.component_config").load()
  local group = vim.api.nvim_create_augroup("NvimNvda", { clear = true })
  signature_help.setup(emit, group)
  lsp_hover.setup(emit, group)
  lsp_status.setup(emit)
  native_operations.setup(emit, group)
  require("nvim_nvda.plugin_manager").setup(emit, group)
  require("nvim_nvda.tutor").setup(emit, group)
  require("nvim_nvda.diagnostics").setup(emit, group)
  completion_events.setup(group)
  file_manager_events.setup(function(reason)
    emit("fileManagerEntryChanged", reason)
  end, function(action)
    emit("fileManagerActionResult", "fileManagerAction", { fileManagerAction = action })
  end, group)
  ui_events.setup(group)
  command_line_events.setup(group)
  file_manager_prompt_events.setup(group)
  input_events.setup(group, component_config)
  context_events.setup(group)
end

function M._test_emit(event_type)
  emit(event_type, "test")
end

M._test_menu_update = completion_events.test_menu_update
M._test_menu_close = completion_events.test_menu_close
M.accessible_menu_begin = completion_events.accessible_menu_begin
M.accessible_menu_open = completion_events.accessible_menu_open
M.accessible_menu_update = completion_events.accessible_menu_update
M.accessible_menu_select = completion_events.accessible_menu_select
M.accessible_menu_close = completion_events.accessible_menu_close

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
