local text = require("nvim_nvda.text")
local M = {}

local MAX_CLIENTS = 32

function M.snapshot()
  local clients = {}
  local ok, values
  if vim.lsp and type(vim.lsp.get_clients) == "function" then
    ok, values = pcall(vim.lsp.get_clients, { bufnr = vim.api.nvim_get_current_buf() })
  elseif vim.lsp and type(vim.lsp.get_active_clients) == "function" then
    ok, values = pcall(vim.lsp.get_active_clients, { bufnr = vim.api.nvim_get_current_buf() })
  end
  if ok and type(values) == "table" then
    local seen = {}
    for _, client in ipairs(values) do
      local name = type(client) == "table" and text.bounded(client.name, 256) or ""
      if name ~= "" and not seen[name] then
        seen[name] = true
        clients[#clients + 1] = name
        if #clients >= MAX_CLIENTS then break end
      end
    end
  end
  table.sort(clients)
  return {
    clients = clients,
    clientCount = #clients,
  }
end

function M.setup(emit)
  pcall(vim.api.nvim_del_user_command, "NvimNvdaLspStatus")
  vim.api.nvim_create_user_command("NvimNvdaLspStatus", function()
    emit("lspStatus", "lspStatusCommand", M.snapshot())
  end, {
    desc = "Report attached LSP clients through Neovim Access Link",
  })
end

return M
