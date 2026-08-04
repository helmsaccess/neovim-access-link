local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local developer_context = require("nvim_nvda.developer_context")
local assertions = 0

local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local python = vim.fn.exepath("python3")
equal(true, python ~= "", "Python interpreter is available")
local server = root .. "/neovim-plugin/tests/fixtures/lsp_test_server.py"
equal(1, vim.fn.filereadable(server), "test LSP server exists")

vim.api.nvim_buf_set_lines(0, 0, -1, true, {
  "calculate_total(price, quantity)",
})
vim.bo.filetype = "python"
vim.api.nvim_win_set_cursor(0, { 1, 0 })

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
equal(true, vim.lsp.buf_is_attached(0, client_id), "real LSP client attaches")

local request_id = 0
local function request()
  request_id = request_id + 1
  local cursor = vim.api.nvim_win_get_cursor(0)
  return {
    requestId = request_id,
    bufferId = vim.api.nvim_get_current_buf(),
    windowId = vim.api.nvim_get_current_win(),
    tabpageId = vim.api.nvim_get_current_tabpage(),
    changedtick = vim.api.nvim_buf_get_changedtick(0),
    line = cursor[1],
    byteColumn = cursor[2],
  }
end

local emitted
local function emit(event_type, reason, payload)
  emitted = { event_type = event_type, reason = reason, payload = payload }
end

equal(true, developer_context.request_callable(request(), emit), "real signature request accepted")
equal(true, vim.wait(5000, function() return emitted ~= nil end, 10), "signature result arrives")
equal("callableContextResult", emitted.event_type, "signature result event")
equal("callableContextRequest", emitted.reason, "signature result reason")
equal(true, emitted.payload.ok, "signature result succeeds")
equal(
  "calculate_total(price: float, quantity: int) -> float",
  emitted.payload.items[1].signature,
  "real signature reaches Access Link"
)
equal(
  "quantity: int. Number of items.",
  emitted.payload.items[1].parameters[2],
  "real parameter documentation reaches Access Link"
)
equal(1, emitted.payload.activeParameter, "real active parameter is retained")
equal({ 1, 0 }, vim.api.nvim_win_get_cursor(0), "signature query does not move cursor")

emitted = nil
equal(true, developer_context.request_callable(request(), emit), "repeated signature request accepted")
equal(true, vim.wait(5000, function() return emitted ~= nil end, 10), "repeated result arrives")
equal(true, emitted.payload.ok, "repeated signature result succeeds")
equal(2, #emitted.payload.items[1].parameters, "repeated result retains parameters")
equal({ 1, 0 }, vim.api.nvim_win_get_cursor(0), "repeated query still does not move cursor")

for _, position in ipairs({
  { column = 15, label = "opening parenthesis" },
  { column = 31, label = "closing parenthesis" },
}) do
  vim.api.nvim_win_set_cursor(0, { 1, position.column })
  emitted = nil
  equal(true, developer_context.request_callable(request(), emit),
    "signature request accepted on " .. position.label)
  equal(true, vim.wait(5000, function() return emitted ~= nil end, 10),
    "signature result arrives on " .. position.label)
  equal(true, emitted.payload.ok, "signature succeeds on " .. position.label)
  equal(
    "calculate_total(price: float, quantity: int) -> float",
    emitted.payload.items[1].signature,
    "signature reaches Access Link on " .. position.label
  )
  equal({ 1, position.column }, vim.api.nvim_win_get_cursor(0),
    "signature query does not move cursor from " .. position.label)
end

vim.api.nvim_win_set_cursor(0, { 1, 20 })
emitted = nil
equal(false, developer_context.request_callable(request(), emit),
  "normal-mode argument interior is deliberately rejected")
equal("noResult", emitted.payload.resultCode, "interior rejection is explicit")
equal(0, #emitted.payload.items, "interior rejection starts no hover fallback")
equal({ 1, 20 }, vim.api.nvim_win_get_cursor(0), "rejected query does not move cursor")

vim.lsp.stop_client(client_id, true)
vim.wait(3000, function() return vim.lsp.get_client_by_id(client_id) == nil end, 10)

print(string.format("real developer-context LSP tests: %d assertions passed", assertions))
vim.cmd("qa!")
