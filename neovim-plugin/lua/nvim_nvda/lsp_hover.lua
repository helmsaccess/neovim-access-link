local text = require("nvim_nvda.text")
local M = {}

local METHOD = "textDocument/hover"
local MAX_DOCUMENTATION_BYTES = 8192
local MAX_CLIENTS = 32
local emitter
local active = false
local last_documentation
local legacy_wrapped = false
local request_all_wrapped = false

local function content_text(value)
  if type(value) == "string" then return value end
  if type(value) ~= "table" then return "" end
  if type(value.value) == "string" then return value.value end
  local parts = {}
  for _, item in ipairs(value) do
    local part = content_text(item)
    if part ~= "" then parts[#parts + 1] = part end
  end
  return table.concat(parts, "\n\n")
end

local function summary(documentation)
  for line in (documentation .. "\n"):gmatch("(.-)\n") do
    if not line:match("^%s*```") then
      local stripped = line:gsub("^%s*[#>*%-]+%s*", ""):gsub("%s+$", "")
      stripped = stripped:gsub("^`+", ""):gsub("`+$", "")
      if stripped ~= "" then return text.bounded(stripped, 512) end
    end
  end
  return ""
end

local function close(reason)
  if not active then return end
  active = false
  last_documentation = nil
  emitter("hoverClosed", reason or "lspHover", {})
end

local function publish(documents, reason)
  local unique, seen = {}, {}
  for _, value in ipairs(documents) do
    local bounded = text.bounded(value, MAX_DOCUMENTATION_BYTES)
    if bounded ~= "" and not seen[bounded] then
      seen[bounded] = true
      unique[#unique + 1] = bounded
    end
  end
  local documentation = text.bounded(table.concat(unique, "\n\n"), MAX_DOCUMENTATION_BYTES)
  local short = summary(documentation)
  if documentation == "" or short == "" then close(reason); return end
  if documentation == last_documentation then return end
  active = true
  last_documentation = documentation
  emitter("hoverChanged", reason or "lspHover", {
    summary = short,
    documentation = documentation,
    sourceCount = #unique,
  })
end

local function single_result(result, reason)
  local documentation = type(result) == "table" and content_text(result.contents) or ""
  publish({ documentation }, reason)
end

local function combined_results(results, reason)
  local documents = {}
  local client_ids = {}
  for client_id in pairs(type(results) == "table" and results or {}) do
    client_ids[#client_ids + 1] = client_id
    if #client_ids >= MAX_CLIENTS then break end
  end
  table.sort(client_ids, function(left, right) return tostring(left) < tostring(right) end)
  for _, client_id in ipairs(client_ids) do
    local response = results[client_id]
    local result = type(response) == "table" and response.result or nil
    if type(result) == "table" then
      documents[#documents + 1] = content_text(result.contents)
    end
  end
  publish(documents, reason)
end

local function wrap_legacy_handler()
  if legacy_wrapped or not vim.lsp or not vim.lsp.handlers then return end
  local original = vim.lsp.handlers[METHOD]
  if type(original) ~= "function" then return end
  vim.lsp.handlers[METHOD] = function(error, result, context, config)
    if not error and (not context or not context.bufnr
      or context.bufnr == vim.api.nvim_get_current_buf()) then
      single_result(result, "lspHover")
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
        combined_results(results, "lspHover")
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
    vim.api.nvim_create_autocmd({
      "CursorMoved", "CursorMovedI", "ModeChanged", "InsertLeave", "BufLeave",
    }, {
      group = group,
      callback = function() close("hoverContextLeft") end,
    })
  end
end

function M._test_single_result(result)
  single_result(result, "testHover")
end

function M._test_combined_results(results)
  combined_results(results, "testHover")
end

return M
