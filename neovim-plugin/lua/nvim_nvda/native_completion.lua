local M = {}

local METHOD = "completionItem/resolve"
local generation = 0
local pending_client
local pending_request_id
local diagnostics = {
  cancelCount = 0,
  errorCount = 0,
  resolveCount = 0,
}

local function cancel_pending()
  if pending_client and pending_request_id
    and type(pending_client.cancel_request) == "function" then
    local ok, canceled = pcall(
      pending_client.cancel_request,
      pending_client,
      pending_request_id
    )
    if ok and canceled then diagnostics.cancelCount = diagnostics.cancelCount + 1 end
  end
  pending_client = nil
  pending_request_id = nil
end

function M.stop()
  generation = generation + 1
  cancel_pending()
end

local function selected_lsp_item(info)
  if type(info) ~= "table" then return nil end
  local selected = tonumber(info.selected) or -1
  local item = type(info.items) == "table" and info.items[selected + 1] or nil
  if type(item) ~= "table" then return nil end
  local lsp = vim.tbl_get(item, "user_data", "nvim", "lsp")
  if type(lsp) ~= "table" or type(lsp.completion_item) ~= "table" then return nil end
  return item, lsp.completion_item, tonumber(lsp.client_id)
end

local function has_documentation(item, completion_item)
  if type(item.info) == "string" and item.info ~= "" then return true end
  local documentation = completion_item.documentation
  if type(documentation) == "string" then return documentation ~= "" end
  return type(documentation) == "table"
    and type(documentation.value) == "string"
    and documentation.value ~= ""
end

local function apply_result(info, result)
  local item, completion_item = selected_lsp_item(info)
  if not item then return false end
  local changed = false
  if result.documentation ~= nil then
    completion_item.documentation = vim.deepcopy(result.documentation)
    changed = true
  end
  if type(result.detail) == "string" and result.detail ~= "" then
    completion_item.detail = result.detail
    changed = true
  end
  return changed
end

function M.resolve(info, callback, bufnr)
  M.stop()
  local item, completion_item, client_id = selected_lsp_item(info)
  if not item or not client_id or has_documentation(item, completion_item) then return false end

  local client = vim.lsp and vim.lsp.get_client_by_id(client_id) or nil
  local completion_provider = client
    and type(client.server_capabilities) == "table"
    and client.server_capabilities.completionProvider
    or nil
  if type(client) ~= "table"
    or type(client.request) ~= "function"
    or type(completion_provider) ~= "table"
    or completion_provider.resolveProvider ~= true then
    return false
  end

  local current_generation = generation
  local request_buffer = tonumber(bufnr) or vim.api.nvim_get_current_buf()
  local ok, sent, request_id = pcall(
    client.request,
    client,
    METHOD,
    vim.deepcopy(completion_item),
    function(error, result)
      if current_generation ~= generation then return end
      pending_client = nil
      pending_request_id = nil
      if error or type(result) ~= "table" then
        if error then diagnostics.errorCount = diagnostics.errorCount + 1 end
        return
      end
      local visible_ok, visible = pcall(vim.fn.pumvisible)
      local info_ok, current_info = pcall(
        vim.fn.complete_info,
        { "mode", "pum_visible", "items", "selected" }
      )
      if not visible_ok or not info_ok then
        diagnostics.errorCount = diagnostics.errorCount + 1
        return
      end
      if visible ~= 1 or current_generation ~= generation then return end
      current_info = vim.deepcopy(current_info)
      if not apply_result(current_info, result) then return end
      diagnostics.resolveCount = diagnostics.resolveCount + 1
      local callback_ok = pcall(callback, current_info)
      if not callback_ok then diagnostics.errorCount = diagnostics.errorCount + 1 end
    end,
    request_buffer
  )
  if not ok or not sent then
    diagnostics.errorCount = diagnostics.errorCount + 1
    return false
  end
  pending_client = client
  pending_request_id = request_id
  return true
end

function M.diagnostics()
  return vim.deepcopy(diagnostics)
end

return M
