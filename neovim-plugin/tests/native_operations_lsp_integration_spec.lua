local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local operations = require("nvim_nvda.native_operations")
local assertions = 0

local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local python = vim.env.NAL_TEST_PYTHON or vim.fn.exepath(vim.fn.has("win32") == 1 and "python" or "python3")
equal(true, python ~= "", "Python interpreter is available")
local server = root .. "/neovim-plugin/tests/fixtures/lsp_test_server.py"
equal(1, vim.fn.filereadable(server), "test LSP server exists")

local primary = vim.api.nvim_get_current_buf()
local secondary = vim.api.nvim_create_buf(true, false)
vim.api.nvim_buf_set_name(primary, root .. "/native_operations_primary.py")
vim.api.nvim_buf_set_name(secondary, root .. "/native_operations_secondary.py")
vim.api.nvim_buf_set_lines(primary, 0, -1, true, { "def shared_name(value):", "  return value" })
vim.api.nvim_buf_set_lines(secondary, 0, -1, true, { "shared_name = 1" })
vim.bo[primary].filetype = "python"
vim.bo[secondary].filetype = "python"
vim.bo[primary].modified = false
vim.bo[secondary].modified = false
vim.api.nvim_win_set_cursor(0, { 1, 4 })

local events = {}
local group = vim.api.nvim_create_augroup("NvimNvdaNativeOperationsLspSpec", { clear = true })
operations.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end, group)

local client_id = vim.lsp.start({
  name = "access-link-test-lsp",
  cmd = { python, server },
  root_dir = root,
})
equal("number", type(client_id), "real LSP client starts")
equal(true, vim.wait(5000, function()
  local client = vim.lsp.get_client_by_id(client_id)
  return client ~= nil and client.initialized
end, 10), "real LSP client initializes")
equal(true, vim.lsp.buf_is_attached(primary, client_id), "real LSP client attaches")

vim.lsp.buf.rename("renamed_name")
equal(true, vim.wait(5000, function()
  return vim.iter(events):any(function(event) return event.type == "lspRenameCompleted" end)
end, 10), "native rename completion is observed")

local rename = vim.iter(events):filter(function(event)
  return event.type == "lspRenameCompleted"
end):totable()[1]
equal("changesObserved", rename.payload.renameResult, "rename reports observed changes")
equal(2, rename.payload.changedBufferCount, "rename reports both changed buffers")
equal(2, rename.payload.modifiedBufferCount, "rename reports both unsaved buffers")
equal("def renamed_name(value):", vim.api.nvim_buf_get_lines(primary, 0, 1, true)[1],
  "native handler edits current buffer")
equal("renamed_name = 1", vim.api.nvim_buf_get_lines(secondary, 0, 1, true)[1],
  "native handler edits non-current buffer")

local client = assert(vim.lsp.get_client_by_id(client_id), "real LSP client remains available")
client:stop(true)
vim.wait(3000, function() return vim.lsp.get_client_by_id(client_id) == nil end, 10)
operations.reset()
pcall(vim.api.nvim_del_augroup_by_id, group)
pcall(vim.api.nvim_buf_delete, secondary, { force = true })

print(string.format("real native-operation LSP tests: %d assertions passed", assertions))
vim.cmd("qa!")
