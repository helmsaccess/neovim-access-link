local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local original_get_clients = vim.lsp.get_clients
vim.lsp.get_clients = function()
  return {
    { name = "pyright" },
    { name = "null-ls" },
    { name = "pyright" },
    { name = "\255invalid" },
  }
end

local status = require("nvim_nvda.lsp_status")
local snapshot = status.snapshot()
equal({ "null-ls", "pyright" }, snapshot.clients, "client names bounded, unique and sorted")
equal(2, snapshot.clientCount, "client count")

vim.lsp.get_clients = function()
  local clients = {}
  for index = 1, 40 do clients[index] = { name = string.format("client-%02d", index) } end
  return clients
end
snapshot = status.snapshot()
equal(32, snapshot.clientCount, "attached client list is bounded")
equal("client-32", snapshot.clients[32], "client bound is deterministic")

vim.lsp.get_clients = function() error("simulated LSP client query failure") end
snapshot = status.snapshot()
equal({}, snapshot.clients, "LSP client query failure is contained")
equal(0, snapshot.clientCount, "failed client query reports an empty state")

vim.lsp.get_clients = function()
  return {
    { name = "pyright" },
    { name = "null-ls" },
  }
end
local events = {}
status.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end)
vim.cmd("NvimNvdaLspStatus")
equal(1, #events, "one status event")
equal("lspStatus", events[1].type, "status event type")
equal("lspStatusCommand", events[1].reason, "status reason")
equal({ "null-ls", "pyright" }, events[1].payload.clients, "status payload")

vim.lsp.get_clients = function() return {} end
vim.cmd("NvimNvdaLspStatus")
equal(0, events[2].payload.clientCount, "empty attached-client state")

vim.lsp.get_clients = original_get_clients
pcall(vim.api.nvim_del_user_command, "NvimNvdaLspStatus")

print(string.format("LSP status tests: %d assertions passed", assertions))
vim.cmd("qa!")
