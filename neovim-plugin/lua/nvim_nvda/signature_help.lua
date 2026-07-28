local text = require("nvim_nvda.text")
local M = {}

local METHOD = "textDocument/signatureHelp"
local MAX_SIGNATURES = 100
local emitter
local active = false
local last_signature
local legacy_wrapped = false
local request_all_wrapped = false

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

local function wrap_legacy_handler()
  if legacy_wrapped or not vim.lsp or not vim.lsp.handlers then return end
  local original = vim.lsp.handlers[METHOD]
  if type(original) ~= "function" then return end
  vim.lsp.handlers[METHOD] = function(error, result, context, config)
    if not error and (not context or not context.bufnr
      or context.bufnr == vim.api.nvim_get_current_buf()) then
      single_result(result, "lspSignatureHelp")
    end
    return original(error, result, context, config)
  end
  legacy_wrapped = true
end

local function wrap_request_all()
  if request_all_wrapped or not vim.lsp or type(vim.lsp.buf_request_all) ~= "function" then return end
  local original = vim.lsp.buf_request_all
  vim.lsp.buf_request_all = function(bufnr, method, params, handler)
    if method ~= METHOD or type(handler) ~= "function" then
      return original(bufnr, method, params, handler)
    end
    local request_buffer = bufnr == 0 and vim.api.nvim_get_current_buf() or bufnr
    return original(bufnr, method, params, function(results, ...)
      if request_buffer == vim.api.nvim_get_current_buf() then
        combined_results(results, "lspSignatureHelp")
      end
      return handler(results, ...)
    end)
  end
  request_all_wrapped = true
end

function M.setup(emit, group)
  emitter = emit
  wrap_legacy_handler()
  wrap_request_all()
  if group then
    vim.api.nvim_create_autocmd({ "InsertLeave", "BufLeave" }, {
      group = group,
      callback = function() close("signatureContextLeft") end,
    })
  end
end

function M._test_single_result(result)
  single_result(result, "testSignature")
end

function M._test_combined_results(results)
  combined_results(results, "testSignature")
end

return M
