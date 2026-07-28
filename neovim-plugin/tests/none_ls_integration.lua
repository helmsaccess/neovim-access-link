local root = vim.fn.getcwd()
local none_ls_root = vim.env.NVIM_NVDA_NONE_LS_ROOT
local plenary_root = vim.env.NVIM_NVDA_PLENARY_ROOT
local fixture_root = vim.env.NVIM_NVDA_NONE_LS_TEST_ROOT

assert(type(none_ls_root) == "string" and vim.fn.isdirectory(none_ls_root) == 1,
  "NVIM_NVDA_NONE_LS_ROOT must name a none-ls.nvim checkout")
assert(type(plenary_root) == "string" and vim.fn.isdirectory(plenary_root) == 1,
  "NVIM_NVDA_PLENARY_ROOT must name a plenary.nvim checkout")
assert(type(fixture_root) == "string" and vim.fn.isdirectory(fixture_root) == 1,
  "NVIM_NVDA_NONE_LS_TEST_ROOT must name an isolated directory")

for _, value in ipairs({ root .. "/neovim-plugin", none_ls_root, plenary_root }) do
  vim.opt.runtimepath:prepend(value)
  package.path = value .. "/lua/?.lua;" .. value .. "/lua/?/init.lua;" .. package.path
end

local assertions = 0
local function truth(value, label)
  assertions = assertions + 1
  assert(value, label)
end

local fixture = fixture_root .. "/trailing.lua"
truth(vim.fn.writefile({ "local value = true  ", "return value" }, fixture) == 0,
  "write none-ls fixture")

local diagnostic_events = 0
vim.api.nvim_create_autocmd("DiagnosticChanged", {
  callback = function(args)
    if args.buf == vim.api.nvim_get_current_buf() then
      diagnostic_events = diagnostic_events + 1
    end
  end,
})

local null_ls = require("null-ls")
truth(type(null_ls.setup) == "function", "none-ls exposes its documented setup entry point")
truth(type(null_ls.builtins.diagnostics.trail_space) == "table",
  "none-ls exposes its built-in trailing-space diagnostic source")
null_ls.setup({
  debounce = 0,
  sources = { null_ls.builtins.diagnostics.trail_space },
})

vim.cmd("edit " .. vim.fn.fnameescape(fixture))
vim.cmd("setfiletype lua")
local buffer = vim.api.nvim_get_current_buf()

truth(vim.wait(10000, function()
  for _, diagnostic in ipairs(vim.diagnostic.get(buffer)) do
    if diagnostic.source == "trail-space" then return true end
  end
  return false
end, 20), "none-ls publishes its diagnostic through vim.diagnostic")

local client_attached = false
local clients
if vim.lsp.get_clients then
  clients = vim.lsp.get_clients({ bufnr = buffer })
else
  clients = vim.lsp.get_active_clients({ bufnr = buffer })
end
for _, client in ipairs(clients) do
  if client.name == "null-ls" then
    client_attached = true
    break
  end
end
truth(client_attached, "none-ls attaches as an LSP client")

local target
for _, diagnostic in ipairs(vim.diagnostic.get(buffer)) do
  if diagnostic.source == "trail-space" then
    target = diagnostic
    break
  end
end
truth(type(target) == "table", "none-ls preserves its provider identity")
truth(target.message == "trailing whitespace"
  and target.severity == vim.diagnostic.severity.WARN,
  "none-ls publishes the expected message and severity")
truth(target.lnum == 0 and target.col == 18
  and target.end_lnum == 0 and target.end_col == 20,
  "none-ls publishes the complete native byte range")
truth(diagnostic_events > 0, "none-ls produces a DiagnosticChanged event")

vim.api.nvim_win_set_cursor(0, { target.lnum + 1, target.col })
local snapshot, count = require("nvim_nvda.diagnostics").snapshot(
  buffer, target.lnum + 1, target.col)
truth(count == 1 and type(snapshot) == "table",
  "none-ls reaches the Access Link diagnostic snapshot")
truth(snapshot.source == "trail-space" and snapshot.code == nil,
  "Access Link preserves none-ls provider identity and optional code")
truth(snapshot.message == target.message and snapshot.severity == "warning",
  "Access Link preserves the none-ls message and severity")
truth(snapshot.line == target.lnum + 1 and snapshot.byteColumn == target.col,
  "Access Link preserves the none-ls range start")
truth(snapshot.endLine == target.end_lnum + 1
  and snapshot.endByteColumn == target.end_col,
  "Access Link preserves the none-ls range end")
truth(snapshot.index == 1 and snapshot.count == 1,
  "Access Link publishes a valid provider-neutral position")

print(string.format("real none-ls diagnostic integration: %d assertions passed", assertions))
vim.cmd("qa!")
