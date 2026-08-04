local call_context = require("nvim_nvda.call_context")
local text = require("nvim_nvda.text")
local M = {}

local METHOD = "textDocument/signatureHelp"
local MAX_SIGNATURES = 100
local MAX_PARAMETERS = 100
local AUTOMATIC_DELAY_MS = 120
local emitter
local active = false
local last_signature
local legacy_wrapped = false
local request_all_wrapped = false
local original_request_all

local automatic_enabled = false
local automatic_generation = 0
local automatic_timer
local automatic_cancel
local pending_trigger_character
local active_help
local active_help_call
local last_automatic_identity
local last_automatic_signature

local function nonnegative_integer(value)
  value = tonumber(value)
  if not value or value < 0 or value > 2147483646 or value % 1 ~= 0 then return nil end
  return value
end

local function parameter_label(signature, active_parameter)
  if type(signature) ~= "table" or type(signature.parameters) ~= "table" then return "" end
  local parameter = signature.parameters[active_parameter + 1]
  if type(parameter) ~= "table" then return "" end
  if type(parameter.label) == "string" then
    return text.bounded(parameter.label, 512)
  end
  if type(parameter.label) == "table" then
    return text.utf16_slice(
      signature.label, parameter.label[1], parameter.label[2], 512
    )
  end
  return ""
end

local function close(reason)
  if not active then return end
  active = false
  last_signature = nil
  emitter("signatureClosed", reason or "lspSignatureHelp", {})
end

local function publish(signatures, selected, reason)
  if #signatures == 0 then close(reason); return end
  selected = math.max(1, math.min(nonnegative_integer(selected) or 1, #signatures))
  local current = signatures[selected]
  local signature = current.signature
  if type(signature) ~= "table" then close(reason); return end
  local active_parameter = nonnegative_integer(signature.activeParameter)
  if active_parameter == nil then active_parameter = nonnegative_integer(current.activeParameter) end
  local payload = {
    signature = text.bounded(signature.label, 2048),
    activeParameter = active_parameter and active_parameter + 1 or nil,
    parameter = active_parameter and parameter_label(signature, active_parameter) or "",
    signatureIndex = selected,
    signatureCount = #signatures,
  }
  if payload.signature == "" then close(reason); return end
  local key = vim.inspect(payload)
  if key == last_signature then return end
  active = true
  last_signature = key
  emitter("signatureChanged", reason or "lspSignatureHelp", payload)
end

local function single_result(result, reason)
  local signatures = {}
  if type(result) == "table" and type(result.signatures) == "table" then
    for _, signature in ipairs(result.signatures) do
      if type(signature) == "table" then
        signatures[#signatures + 1] = {
          signature = signature,
          activeParameter = result.activeParameter,
        }
        if #signatures >= MAX_SIGNATURES then break end
      end
    end
  end
  publish(signatures, (nonnegative_integer(result and result.activeSignature) or 0) + 1, reason)
end

local function combined_results(results, reason)
  local signatures = {}
  local selected
  local client_ids = {}
  for client_id in pairs(type(results) == "table" and results or {}) do
    client_ids[#client_ids + 1] = client_id
  end
  table.sort(client_ids, function(left, right) return tostring(left) < tostring(right) end)
  for _, client_id in ipairs(client_ids) do
    local response = results[client_id]
    local result = type(response) == "table" and response.result or nil
    if type(result) == "table" and type(result.signatures) == "table" then
      local first_index = #signatures + 1
      for _, signature in ipairs(result.signatures) do
        if type(signature) == "table" then
          signatures[#signatures + 1] = {
            signature = signature,
            activeParameter = result.activeParameter,
          }
          if #signatures >= MAX_SIGNATURES then break end
        end
      end
      if not selected and #signatures >= first_index then
        selected = first_index + math.min(
          nonnegative_integer(result.activeSignature) or 0,
          #signatures - first_index
        )
      end
      if #signatures >= MAX_SIGNATURES then break end
    end
  end
  publish(signatures, selected or 1, reason)
end

local function automatic_mode()
  local ok, value = pcall(vim.api.nvim_get_mode)
  return ok and type(value) == "table" and tostring(value.mode or ""):sub(1, 1) == "i"
end

local function call_key(bufnr, resolved)
  return table.concat({
    tostring(bufnr), tostring(resolved.openLine), tostring(resolved.openByteColumn),
  }, ":")
end

local function clear_automatic()
  active_help = nil
  active_help_call = nil
  last_automatic_identity = nil
  last_automatic_signature = nil
end

local function stop_automatic_work()
  automatic_generation = automatic_generation + 1
  if automatic_timer then
    pcall(vim.fn.timer_stop, automatic_timer)
    automatic_timer = nil
  end
  if type(automatic_cancel) == "function" then pcall(automatic_cancel) end
  automatic_cancel = nil
  pending_trigger_character = nil
end

local function reset_automatic()
  stop_automatic_work()
  clear_automatic()
end

local function bounded_signature_help(result)
  if type(result) ~= "table" or type(result.signatures) ~= "table" then return nil end
  local signatures = {}
  for _, signature in ipairs(result.signatures) do
    if type(signature) == "table" and type(signature.label) == "string" then
      local label = text.bounded(signature.label, 2048)
      if label ~= "" then
        local parameters = {}
        for _, parameter in ipairs(type(signature.parameters) == "table"
          and signature.parameters or {}) do
          if type(parameter) == "table" then
            local parameter_value = { label = parameter.label }
            if type(parameter.label) == "string" then
              parameter_value.label = text.bounded(parameter.label, 512)
            elseif type(parameter.label) == "table" then
              parameter_value.label = { parameter.label[1], parameter.label[2] }
            end
            parameters[#parameters + 1] = parameter_value
            if #parameters >= MAX_PARAMETERS then break end
          end
        end
        signatures[#signatures + 1] = {
          label = label,
          parameters = parameters,
          activeParameter = nonnegative_integer(signature.activeParameter),
        }
        if #signatures >= MAX_SIGNATURES then break end
      end
    end
  end
  if #signatures == 0 then return nil end
  return {
    signatures = signatures,
    activeSignature = nonnegative_integer(result.activeSignature) or 0,
    activeParameter = nonnegative_integer(result.activeParameter),
  }
end

local function automatic_details(result)
  local normalized = bounded_signature_help(result)
  if not normalized then return nil end
  local signature_index = math.min(normalized.activeSignature, #normalized.signatures - 1)
  local signature = normalized.signatures[signature_index + 1]
  local active_parameter = nonnegative_integer(signature.activeParameter)
  if active_parameter == nil then active_parameter = normalized.activeParameter end
  if active_parameter == nil or active_parameter >= #signature.parameters then return nil end
  local label = parameter_label(signature, active_parameter)
  return {
    normalized = normalized,
    signature = signature.label,
    signatureIndex = signature_index + 1,
    signatureCount = #normalized.signatures,
    activeParameter = active_parameter + 1,
    parameterCount = #signature.parameters,
    parameter = label,
  }
end

local function publish_automatic(result, resolved, bufnr)
  local details = automatic_details(result)
  if not details then return false end
  local current_call = call_key(bufnr, resolved)
  local identity = table.concat({
    current_call, tostring(details.signatureIndex), tostring(details.activeParameter),
  }, ":")
  local same_call = active_help_call == current_call
  local signature_changed = same_call and last_automatic_signature ~= nil
    and last_automatic_signature ~= details.signatureIndex
  active_help = details.normalized
  active_help_call = current_call
  if identity == last_automatic_identity then return false end
  local reason = not same_call and "callEntered"
    or signature_changed and "signatureChanged"
    or "parameterChanged"
  last_automatic_identity = identity
  last_automatic_signature = details.signatureIndex
  emitter("activeParameterChanged", "automaticSignatureHelp", {
    callName = text.bounded(resolved.name, 512),
    callStartLine = resolved.openLine,
    callStartByteColumn = resolved.openByteColumn,
    signature = details.signature,
    signatureIndex = details.signatureIndex,
    signatureCount = details.signatureCount,
    activeParameter = details.activeParameter,
    parameterCount = details.parameterCount,
    parameter = details.parameter,
    hintReason = reason,
  })
  return true
end

local function first_result(results)
  local identifiers = {}
  for identifier in pairs(type(results) == "table" and results or {}) do
    identifiers[#identifiers + 1] = identifier
  end
  table.sort(identifiers, function(left, right)
    local left_number, right_number = tonumber(left), tonumber(right)
    if left_number and right_number then return left_number < right_number end
    return tostring(left) < tostring(right)
  end)
  for _, identifier in ipairs(identifiers) do
    local response = results[identifier]
    local result = type(response) == "table" and response.result or nil
    if bounded_signature_help(result) then return result end
  end
  return nil
end

local function utf16_index(value, byte_column)
  if vim.fn.has("nvim-0.11") == 1 then
    local ok, index = pcall(vim.str_utfindex, value, "utf-16", byte_column, false)
    return ok and index or nil
  end
  local ok, _, index = pcall(vim.str_utfindex, value, byte_column)
  return ok and index or nil
end

local function position_params(bufnr, line_number, byte_column)
  local ok, params = pcall(vim.lsp.util.make_position_params, 0, "utf-16")
  if not ok or type(params) ~= "table" or type(params.position) ~= "table" then return nil end
  local lines = vim.api.nvim_buf_get_lines(bufnr, line_number - 1, line_number, true)
  local line = type(lines) == "table" and lines[1] or nil
  if type(line) ~= "string" or byte_column > #line then return nil end
  local character = utf16_index(line, byte_column)
  if type(character) ~= "number" then return nil end
  params.position.line = line_number - 1
  params.position.character = character
  return params
end

local function client_trigger_sets(bufnr)
  local trigger, retrigger = {}, {}
  local clients = {}
  if vim.lsp and type(vim.lsp.get_clients) == "function" then
    local ok, values = pcall(vim.lsp.get_clients, { bufnr = bufnr, method = METHOD })
    if ok and type(values) == "table" then clients = values end
  elseif vim.lsp and type(vim.lsp.get_active_clients) == "function" then
    local ok, values = pcall(vim.lsp.get_active_clients, { bufnr = bufnr })
    if ok and type(values) == "table" then clients = values end
  end
  for _, client in ipairs(clients) do
    local provider = type(client.server_capabilities) == "table"
      and client.server_capabilities.signatureHelpProvider or nil
    if type(provider) == "table" then
      for _, value in ipairs(type(provider.triggerCharacters) == "table"
        and provider.triggerCharacters or {}) do
        if type(value) == "string" and #value > 0 then
          trigger[value] = true
          retrigger[value] = true
        end
      end
      for _, value in ipairs(type(provider.retriggerCharacters) == "table"
        and provider.retriggerCharacters or {}) do
        if type(value) == "string" and #value > 0 then retrigger[value] = true end
      end
    end
  end
  return trigger, retrigger
end

local function exact_automatic_context(snapshot)
  if not automatic_enabled or automatic_generation ~= snapshot.generation
    or not vim.api.nvim_buf_is_valid(snapshot.bufnr)
    or not vim.api.nvim_win_is_valid(snapshot.winid)
    or vim.api.nvim_get_current_buf() ~= snapshot.bufnr
    or vim.api.nvim_get_current_win() ~= snapshot.winid
    or vim.api.nvim_buf_get_changedtick(snapshot.bufnr) ~= snapshot.changedtick
    or not automatic_mode() then
    return nil
  end
  local cursor = vim.api.nvim_win_get_cursor(snapshot.winid)
  if cursor[1] ~= snapshot.line or cursor[2] ~= snapshot.byteColumn then return nil end
  local resolved = call_context.resolve_automatic(
    snapshot.bufnr, snapshot.line, snapshot.byteColumn, "i"
  )
  if not resolved or call_key(snapshot.bufnr, resolved) ~= snapshot.callKey then return nil end
  return resolved
end

local function request_automatic(trigger_character)
  if not automatic_enabled or not automatic_mode() or vim.fn.pumvisible() == 1 then return false end
  local bufnr = vim.api.nvim_get_current_buf()
  local winid = vim.api.nvim_get_current_win()
  local cursor = vim.api.nvim_win_get_cursor(winid)
  local resolved = call_context.resolve_automatic(bufnr, cursor[1], cursor[2], "i")
  if not resolved then clear_automatic(); return false end
  local current_call = call_key(bufnr, resolved)
  local params = position_params(bufnr, resolved.queryLine, resolved.queryByteColumn)
  if not params then return false end
  local is_retrigger = active_help_call == current_call and active_help ~= nil
  local triggers, retriggers = client_trigger_sets(bufnr)
  local trigger_kind = is_retrigger and 3 or 1
  if type(trigger_character) == "string" and #trigger_character > 0
    and (triggers[trigger_character] or is_retrigger and retriggers[trigger_character]) then
    trigger_kind = 2
  else
    trigger_character = nil
  end
  params.context = {
    triggerKind = trigger_kind,
    isRetrigger = is_retrigger,
    activeSignatureHelp = is_retrigger and active_help or nil,
  }
  if trigger_kind == 2 then params.context.triggerCharacter = trigger_character end
  local snapshot = {
    generation = automatic_generation,
    bufnr = bufnr,
    winid = winid,
    changedtick = vim.api.nvim_buf_get_changedtick(bufnr),
    line = cursor[1],
    byteColumn = cursor[2],
    callKey = current_call,
  }
  local request = original_request_all or vim.lsp.buf_request_all
  if type(request) ~= "function" then return false end
  local ok, cancel = pcall(request, bufnr, METHOD, params, function(results)
    automatic_cancel = nil
    local current = exact_automatic_context(snapshot)
    if not current then return end
    local result = first_result(results)
    if not result then clear_automatic(); return end
    publish_automatic(result, current, bufnr)
  end)
  if not ok then return false end
  automatic_cancel = type(cancel) == "function" and cancel or nil
  return true
end

local function schedule_automatic(trigger_character, delay)
  if not automatic_enabled then return end
  if type(trigger_character) == "string" and #trigger_character > 0 then
    pending_trigger_character = trigger_character
  end
  automatic_generation = automatic_generation + 1
  if type(automatic_cancel) == "function" then pcall(automatic_cancel) end
  automatic_cancel = nil
  if automatic_timer then pcall(vim.fn.timer_stop, automatic_timer) end
  local generation = automatic_generation
  automatic_timer = vim.fn.timer_start(delay or AUTOMATIC_DELAY_MS, function()
    automatic_timer = nil
    if generation ~= automatic_generation then return end
    local character = pending_trigger_character
    pending_trigger_character = nil
    request_automatic(character)
  end)
end

local function wrap_legacy_handler()
  if legacy_wrapped or not vim.lsp or not vim.lsp.handlers then return end
  local original = vim.lsp.handlers[METHOD]
  if type(original) ~= "function" then return end
  vim.lsp.handlers[METHOD] = function(error, result, context, config)
    if not error and not (automatic_enabled and automatic_mode())
      and (not context or not context.bufnr
        or context.bufnr == vim.api.nvim_get_current_buf()) then
      single_result(result, "lspSignatureHelp")
    end
    return original(error, result, context, config)
  end
  legacy_wrapped = true
end

local function wrap_request_all()
  if request_all_wrapped or not vim.lsp or type(vim.lsp.buf_request_all) ~= "function" then return end
  original_request_all = vim.lsp.buf_request_all
  vim.lsp.buf_request_all = function(bufnr, method, params, handler)
    if method ~= METHOD or type(handler) ~= "function" then
      return original_request_all(bufnr, method, params, handler)
    end
    local request_buffer = bufnr == 0 and vim.api.nvim_get_current_buf() or bufnr
    return original_request_all(bufnr, method, params, function(results, ...)
      if not (automatic_enabled and automatic_mode())
        and request_buffer == vim.api.nvim_get_current_buf() then
        combined_results(results, "lspSignatureHelp")
      end
      return handler(results, ...)
    end)
  end
  request_all_wrapped = true
end

function M.note_insert_key(key, typed)
  if not automatic_enabled or not automatic_mode() then return end
  local value = type(typed) == "string" and typed ~= "" and typed or key
  if type(value) == "string" and #value == 1 then pending_trigger_character = value end
end

function M.set_connected(value)
  automatic_enabled = value == true
  reset_automatic()
  if automatic_enabled and automatic_mode() then schedule_automatic(nil, 0) end
end

function M.setup(emit, group)
  emitter = emit
  wrap_legacy_handler()
  wrap_request_all()
  if group then
    vim.api.nvim_create_autocmd({ "CursorMovedI", "TextChangedI" }, {
      group = group,
      callback = function(event)
        if event.event == "TextChangedI" and vim.fn.pumvisible() == 1 then return end
        schedule_automatic(pending_trigger_character)
      end,
    })
    vim.api.nvim_create_autocmd({ "InsertEnter", "CompleteDone" }, {
      group = group,
      callback = function() schedule_automatic(nil) end,
    })
    vim.api.nvim_create_autocmd({ "InsertLeave", "BufLeave", "BufWipeout" }, {
      group = group,
      callback = function(event)
        if event.event == "BufWipeout" then call_context.clear_cache(event.buf) end
        reset_automatic()
        close("signatureContextLeft")
      end,
    })
  end
end

function M._test_single_result(result)
  single_result(result, "testSignature")
end

function M._test_combined_results(results)
  combined_results(results, "testSignature")
end

function M._test_publish_automatic(result, resolved, bufnr)
  return publish_automatic(result, resolved, bufnr or vim.api.nvim_get_current_buf())
end

function M._test_first_result(results)
  return first_result(results)
end

function M._test_clear_automatic()
  clear_automatic()
end

return M
