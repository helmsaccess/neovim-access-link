local diagnostics = require("nvim_nvda.diagnostics")
local text = require("nvim_nvda.text")
local M = {}

local MAX_ITEMS = 100
local MAX_PARAMETERS = 100
local MAX_SIGNATURE = 4096
local MAX_DOCUMENTATION = 8192
local MAX_TOTAL_TEXT = 256 * 1024
local METHOD_SIGNATURE = "textDocument/signatureHelp"
local METHOD_HOVER = "textDocument/hover"
local MODERN_STRING_INDICES = vim.fn.has("nvim-0.11") == 1

local function integer(value, minimum)
  return type(value) == "number" and value % 1 == 0
    and value >= minimum and value <= 2147483647
end

local function valid_request(payload)
  if type(payload) ~= "table" then return false end
  local fields = {
    requestId = true,
    bufferId = true,
    windowId = true,
    tabpageId = true,
    changedtick = true,
    line = true,
    byteColumn = true,
  }
  local count = 0
  for key in pairs(payload) do
    if not fields[key] then return false end
    count = count + 1
  end
  return count == 7
    and integer(payload.requestId, 1)
    and integer(payload.bufferId, 1)
    and integer(payload.windowId, 1)
    and integer(payload.tabpageId, 1)
    and integer(payload.changedtick, 0)
    and integer(payload.line, 1)
    and integer(payload.byteColumn, 0)
end

local function exact_context(payload)
  if not valid_request(payload)
    or not vim.api.nvim_buf_is_valid(payload.bufferId)
    or not vim.api.nvim_win_is_valid(payload.windowId) then
    return false
  end
  local cursor = vim.api.nvim_win_get_cursor(payload.windowId)
  return vim.api.nvim_get_current_buf() == payload.bufferId
    and vim.api.nvim_get_current_win() == payload.windowId
    and vim.api.nvim_get_current_tabpage() == payload.tabpageId
    and vim.api.nvim_buf_get_changedtick(payload.bufferId) == payload.changedtick
    and cursor[1] == payload.line
    and cursor[2] == payload.byteColumn
end

local function markup(value, limit)
  if type(value) == "string" then return text.bounded(value, limit) end
  if type(value) ~= "table" then return "" end
  if type(value.value) == "string" then return text.bounded(value.value, limit) end
  local lines = {}
  for _, part in ipairs(value) do
    local item = markup(part, limit)
    if item ~= "" then lines[#lines + 1] = item end
  end
  return text.bounded(table.concat(lines, "\n"), limit)
end

local function parameter_label(signature, parameter)
  if type(parameter) ~= "table" then return "" end
  if type(parameter.label) == "string" then return text.bounded(parameter.label, 1024) end
  if type(parameter.label) == "table" then
    return text.utf16_slice(signature.label, parameter.label[1], parameter.label[2], 1024)
  end
  return ""
end

local function signature_items(results)
  local items = {}
  local active_item = 0
  local active_parameter = 0
  local active_selected = false
  local remaining_text = MAX_TOTAL_TEXT
  local client_ids = {}
  for client_id in pairs(type(results) == "table" and results or {}) do
    client_ids[#client_ids + 1] = client_id
  end
  table.sort(client_ids, function(left, right) return tostring(left) < tostring(right) end)
  for _, client_id in ipairs(client_ids) do
    local response = results[client_id]
    local result = type(response) == "table" and response.result or nil
    local signatures = type(result) == "table" and result.signatures or nil
    if type(signatures) == "table" then
      local first = #items
      for _, signature in ipairs(signatures) do
        if type(signature) == "table" and type(signature.label) == "string" then
          local signature_text = text.bounded(signature.label, MAX_SIGNATURE)
          if signature_text ~= "" then
            local documentation = markup(signature.documentation, MAX_DOCUMENTATION)
            local item_size = #signature_text + #documentation
            if item_size > remaining_text then break end
            local parameters = {}
            for _, parameter in ipairs(type(signature.parameters) == "table"
              and signature.parameters or {}) do
              local label = parameter_label(signature, parameter)
              local parameter_documentation = markup(parameter.documentation, 2048)
              if parameter_documentation ~= "" then
                label = label .. ". " .. parameter_documentation
              end
              label = text.bounded(label, 3072)
              if item_size + #label > remaining_text then break end
              parameters[#parameters + 1] = label
              item_size = item_size + #label
              if #parameters >= MAX_PARAMETERS then break end
            end
            items[#items + 1] = {
              signature = signature_text,
              parameters = parameters,
              documentation = documentation,
            }
            remaining_text = remaining_text - item_size
            if #items >= MAX_ITEMS then break end
          end
        end
      end
      if #items > first and not active_selected then
        local selected = integer(result.activeSignature, 0) and result.activeSignature or 0
        active_item = first + math.max(0, math.min(selected, #items - first - 1))
        local parameters = items[active_item + 1].parameters
        local selected_parameter = integer(result.activeParameter, 0)
          and result.activeParameter or 0
        active_parameter = math.max(
          0,
          math.min(selected_parameter, math.max(0, #parameters - 1))
        )
        active_selected = true
      end
    end
    if #items >= MAX_ITEMS then break end
  end
  return items, active_item, active_parameter
end

local function hover_items(results)
  local client_ids = {}
  for client_id in pairs(type(results) == "table" and results or {}) do
    client_ids[#client_ids + 1] = client_id
  end
  table.sort(client_ids, function(left, right) return tostring(left) < tostring(right) end)
  for _, client_id in ipairs(client_ids) do
    local response = results[client_id]
    local result = type(response) == "table" and response.result or nil
    local value = type(result) == "table" and markup(result.contents, MAX_DOCUMENTATION) or ""
    if value ~= "" then
      return {
        {
          signature = value,
          parameters = {},
          documentation = "",
        },
      }
    end
  end
  return {}
end

local function position_params()
  local ok, params = pcall(vim.lsp.util.make_position_params, 0, "utf-16")
  return ok and params or nil
end

local function utf16_index(value, byte_column)
  if MODERN_STRING_INDICES then
    local ok, index = pcall(vim.str_utfindex, value, "utf-16", byte_column, false)
    return ok and index or nil
  end
  local ok, _, index = pcall(vim.str_utfindex, value, byte_column)
  return ok and index or nil
end

local function identifier_byte(value)
  return value and (
    value >= 128
    or value >= string.byte("0") and value <= string.byte("9")
    or value >= string.byte("A") and value <= string.byte("Z")
    or value == string.byte("_")
    or value >= string.byte("a") and value <= string.byte("z")
  )
end

-- Language servers commonly return signature help only inside an argument
-- list. When the real cursor is on a callable name or its opening parenthesis,
-- query just after that delimiter without moving or editing the buffer. A
-- position on the closing parenthesis already denotes the inside of that
-- argument list in LSP coordinates, so it can be used unchanged. Hover still
-- uses the real cursor position as its unstructured fallback.
local function callable_position_params(payload, params)
  if type(params) ~= "table" or type(params.position) ~= "table" then return params end
  local lines = vim.api.nvim_buf_get_lines(
    payload.bufferId, payload.line - 1, payload.line, true
  )
  local line = type(lines) == "table" and lines[1] or nil
  if type(line) ~= "string" or payload.byteColumn >= #line then return params end
  local offset = payload.byteColumn + 1
  if line:sub(offset, offset) == "(" then
    local character = utf16_index(line, offset)
    if type(character) ~= "number" then return params end
    local adjusted = vim.deepcopy(params)
    adjusted.position.character = character
    return adjusted
  end
  if line:sub(offset, offset) == ")" then return params end
  if not identifier_byte(line:byte(offset)) then return params end
  while identifier_byte(line:byte(offset)) do offset = offset + 1 end
  while line:sub(offset, offset):match("%s") do offset = offset + 1 end
  if line:sub(offset, offset) ~= "(" then return params end
  local character = utf16_index(line, offset)
  if type(character) ~= "number" then return params end
  local adjusted = vim.deepcopy(params)
  adjusted.position.character = character
  return adjusted
end

local function request_all(buf, method, params, handler)
  return pcall(vim.lsp.buf_request_all, buf, method, params, handler)
end

local function result(payload, ok, result_code, items, active_item, active_parameter)
  return {
    requestId = payload.requestId,
    bufferId = payload.bufferId,
    windowId = payload.windowId,
    tabpageId = payload.tabpageId,
    changedtick = payload.changedtick,
    line = payload.line,
    byteColumn = payload.byteColumn,
    ok = ok,
    resultCode = result_code,
    items = items,
    activeItem = active_item,
    activeParameter = active_parameter,
  }
end

local function failure(payload, result_code)
  return result(payload, false, result_code, {}, 0, 0)
end

function M.request_callable(payload, emit)
  if not exact_context(payload) or type(emit) ~= "function" then
    if valid_request(payload) and type(emit) == "function" then
      emit("callableContextResult", "callableContextRequest", failure(
        payload, "invalidOrStaleRequest"
      ))
    end
    return false
  end
  local hover_params = position_params()
  if not hover_params or type(vim.lsp.buf_request_all) ~= "function" then
    emit("callableContextResult", "callableContextRequest", failure(payload, "requestFailed"))
    return false
  end
  local signature_params = callable_position_params(payload, hover_params)
  local requested = request_all(payload.bufferId, METHOD_SIGNATURE, signature_params, function(results)
    if not exact_context(payload) then
      emit("callableContextResult", "callableContextRequest", failure(
        payload, "invalidOrStaleRequest"
      ))
      return
    end
    local items, active_item, active_parameter = signature_items(results)
    if #items > 0 then
      emit("callableContextResult", "callableContextRequest", result(
        payload, true, "ok", items, active_item, active_parameter
      ))
      return
    end
    local hover_requested = request_all(
      payload.bufferId, METHOD_HOVER, hover_params, function(hover_results)
        if not exact_context(payload) then
          emit("callableContextResult", "callableContextRequest", failure(
            payload, "invalidOrStaleRequest"
          ))
          return
        end
        local hover = hover_items(hover_results)
        emit(
          "callableContextResult",
          "callableContextRequest",
          #hover > 0 and result(payload, true, "ok", hover, 0, 0)
            or failure(payload, "noResult")
        )
      end
    )
    if not hover_requested then
      emit("callableContextResult", "callableContextRequest", failure(
        payload, "requestFailed"
      ))
    end
  end)
  if not requested then
    emit("callableContextResult", "callableContextRequest", failure(payload, "requestFailed"))
    return false
  end
  return true
end

function M.request_diagnostics(payload, emit)
  if not valid_request(payload) or type(emit) ~= "function" then return false end
  if not exact_context(payload) then
    emit("diagnosticContextResult", "diagnosticContextRequest", failure(
      payload, "invalidOrStaleRequest"
    ))
    return false
  end
  local items = diagnostics.context(
    payload.bufferId,
    payload.line,
    payload.byteColumn
  )
  emit(
    "diagnosticContextResult",
    "diagnosticContextRequest",
    #items > 0 and result(payload, true, "ok", items, 0, 0)
      or failure(payload, "noResult")
  )
  return #items > 0
end

return M
