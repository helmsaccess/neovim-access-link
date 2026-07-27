local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local spelling = require("nvim_nvda.spelling")
local numbered_choice = require("nvim_nvda.numbered_choice")
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
local choices = numbered_choice.spell_suggestions(
  'Change "mispelled" to:\n 1 "misspelled"\n 2 "misapplied"\n'
)
equal(2, #choices, "numbered spell choice count")
equal("misspelled", choices[1], "number removed from first spell choice")
local detailed_choices = numbered_choice.spell_suggestions(
  'Change "mispelled" to:\n 1 "misspelled" < "mispelled" (123)\n'
)
equal("misspelled", detailed_choices[1], "native replacement and score suffix ignored")
local numbered_choices = { "Prompt" }
for index = 1, 12 do
  numbered_choices[#numbered_choices + 1] = string.format('%d "item %d"', index, index)
end
equal(12, #numbered_choice.spell_suggestions(table.concat(numbered_choices, "\n")), "multi-digit choices")
local legacy_choices = numbered_choice.spell_suggestions(
  'Change "mispelled" to:\n 1 "misspelled"\n 2 "misapplied"\n'
    .. "Type number and <Enter> or click with the mouse (q or empty cancels):"
)
equal(2, #legacy_choices, "legacy native prompt accepted")
equal(nil, numbered_choice.spell_suggestions('Prompt\n 1 "first"\n 3 "third"\n'), "gap rejected")
equal(nil, numbered_choice.spell_suggestions('Prompt\n 1 "first"\nother\n'), "mixed content rejected")
equal(
  nil,
  numbered_choice.spell_suggestions('Prompt\n 1 "first"\nType number and <Enter>\n'),
  "incomplete native prompt rejected"
)
equal(
  nil,
  numbered_choice.spell_suggestions(
    'Prompt\n 1 "first"\nType number and <Enter>:\nType number and <Enter>:\n'
  ),
  "duplicate native prompt rejected"
)
equal(
  nil,
  numbered_choice.spell_suggestions('Prompt\n 1 "' .. string.rep("x", 4097) .. '"\n'),
  "oversized item rejected"
)
local too_many_choices = { "Prompt" }
for index = 1, 129 do
  too_many_choices[#too_many_choices + 1] = string.format('%d "item %d"', index, index)
end
equal(
  nil,
  numbered_choice.spell_suggestions(table.concat(too_many_choices, "\n")),
  "oversized choice list rejected"
)

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

print("spelling/diagnostic tests: 32 assertions passed")
vim.cmd("qa!")
