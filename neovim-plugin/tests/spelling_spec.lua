local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local spelling = require("nvim_nvda.spelling")
local state = dofile(root .. "/neovim-plugin/lua/nvim_nvda/state.lua")

local function equal(expected, actual, label)
  assert(expected == actual, string.format("%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
end

equal("spelling", spelling.diagnostic_kind({ source = "cspell" }), "cspell source")
equal("spelling", spelling.diagnostic_kind({ source = "spellwarn" }), "spellwarn source")
equal("spelling", spelling.diagnostic_kind({ source = "typos" }), "typos source")
equal("spelling", spelling.diagnostic_kind({ source = "LTeX", code = "MORFOLOGIK_RULE_EN_US" }), "ltex spelling")
equal("grammar", spelling.diagnostic_kind({ user_data = { nvim_nvda_kind = "grammar" } }), "explicit grammar")
equal("grammar", spelling.diagnostic_kind({ source = "Harper" }), "harper grammar")
equal(nil, spelling.diagnostic_kind({ source = "pyright", message = "undefined name" }), "ordinary diagnostic")

vim.opt.spelllang = "en_us"
vim.wo.spell = true
local native, current = spelling.for_line(0, 1, "hello mispelled world", 8)
equal("mispelled", current.word, "native misspelled word")
equal(6, current.startByteColumn, "native start")
equal(15, current.endByteColumn, "native end")

vim.wo.spell = false
local namespace = vim.api.nvim_create_namespace("nvim_nvda_test_spell")
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "a wrong word" })
vim.api.nvim_win_set_cursor(0, { 1, 4 })
vim.diagnostic.set(namespace, 0, {{
  lnum = 0, col = 2, end_lnum = 0, end_col = 7,
  message = "Unknown word", source = "cspell", severity = vim.diagnostic.severity.WARN,
}})
local diagnostics, diagnostic_current = spelling.for_line(0, 1, "a wrong word", 4)
equal(1, #diagnostics, "diagnostic count")
equal("spelling", diagnostic_current.kind, "diagnostic kind")
equal(2, diagnostic_current.startByteColumn, "diagnostic start")
equal(7, diagnostic_current.endByteColumn, "diagnostic end")
vim.api.nvim_win_set_cursor(0, { 1, 4 })
local snapshot = state.snapshot("diagnosticTest")
equal(4, snapshot.cursor.byteColumn, "snapshot cursor column")
equal(1, snapshot.diagnosticCount, "snapshot diagnostic total")
equal("cspell", snapshot.diagnostic.source, "snapshot diagnostic source")
equal(1, snapshot.diagnostic.index, "snapshot diagnostic index")
equal(1, snapshot.diagnostic.count, "snapshot diagnostic count")
vim.diagnostic.reset(namespace, 0)
vim.diagnostic.set(namespace, 0, {{
  lnum = 0, col = 0, end_lnum = 0, end_col = 5,
  message = "Double quote to prevent globbing", source = "shellcheck",
  code = "SC2086", severity = vim.diagnostic.severity.WARN,
}})
vim.api.nvim_win_set_cursor(0, { 1, 2 })
local shellcheck = state.snapshot("shellcheckTest").diagnostic
equal("shellcheck", shellcheck.source, "shellcheck source")
equal("warning", shellcheck.severity, "shellcheck severity")
equal("SC2086", shellcheck.code, "shellcheck code")
equal("Double quote to prevent globbing", shellcheck.message, "shellcheck message")
vim.diagnostic.reset(namespace, 0)

print("spelling/diagnostic tests: 24 assertions passed")
vim.cmd("qa!")
