local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;"
  .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local plugin = require("nvim_nvda")
local state = require("nvim_nvda.state")

local assertions = 0
local function truth(value, label)
  assertions = assertions + 1
  assert(value, label)
end
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s",
    label,
    vim.inspect(expected),
    vim.inspect(actual)
  ))
end

vim.api.nvim_buf_set_lines(0, 0, -1, true, {
  "0123456789",
  "x",
  "abcdefghij",
  "\tZ",
  "",
  "ä🙂z",
})
vim.api.nvim_win_set_cursor(0, { 1, 0 })

local snapshot = state.snapshot("brailleNavigation")
truth(
  vim.tbl_contains(snapshot.pluginCapabilities, "brailleLineNavigation"),
  "plugin advertises Braille line navigation"
)
truth(
  plugin.request_route_cursor({
    target = "editor",
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = 1,
    byteColumn = 7,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
  }),
  "routing establishes the preferred virtual column"
)

snapshot = state.snapshot("afterRoute")
equal(7, snapshot.cursor.preferredVirtualColumn, "snapshot exposes Neovim curswant")
truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "preferred",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "next line is accepted"
)
snapshot = state.snapshot("shortLine")
equal({ 2, 0, 7 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "a short line keeps the preferred virtual column")

truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "preferred",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "next long line is accepted"
)
snapshot = state.snapshot("longLine")
equal({ 3, 7, 7 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "the preferred column is restored on a longer line")

truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "preferred",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "tabbed line is accepted"
)
snapshot = state.snapshot("tabbedLine")
equal({ 4, 0, 7 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "virtual columns map safely into a tab")

truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "end",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "the end of an empty line is accepted"
)
snapshot = state.snapshot("emptyLineEnd")
equal({ 5, 0, 0 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "an empty line has one safe start/end position")

truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "end",
    preferredVirtualColumn = 79,
  }),
  "the normal-mode end of a Unicode line is accepted"
)
snapshot = state.snapshot("unicodeLineEnd")
equal({ 6, 6, 3 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "normal mode ends on the final Unicode character")

truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "previous",
    targetColumn = "start",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "a horizontal back-wrap targets the previous line start only when requested"
)
snapshot = state.snapshot("emptyLineStart")
equal({ 5, 0, 0 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "line-start targeting resets the preferred column")

truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "previous",
    targetColumn = "end",
    preferredVirtualColumn = 79,
  }),
  "a horizontal back-wrap targets the previous line end"
)
snapshot = state.snapshot("tabbedLineEnd")
equal({ 4, 1, 8 }, {
  snapshot.cursor.line,
  snapshot.cursor.byteColumn,
  snapshot.cursor.preferredVirtualColumn,
}, "normal-mode line end is UTF-8 and tab aware")

truth(
  not plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "middle",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "an unknown target-column policy is rejected"
)

vim.api.nvim_win_set_cursor(0, { 5, 0 })
snapshot = state.snapshot("beforeInsertEnd")
local original_get_mode = vim.api.nvim_get_mode
local original_set_cursor = vim.api.nvim_win_set_cursor
local requested_insert_cursor
vim.api.nvim_get_mode = function() return { mode = "i", blocking = false } end
vim.api.nvim_win_set_cursor = function(window, position)
  requested_insert_cursor = { window, vim.deepcopy(position) }
end
truth(
  plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = "i",
    direction = "next",
    targetColumn = "end",
    preferredVirtualColumn = 79,
  }),
  "insert mode can target the position after the final Unicode character"
)
vim.api.nvim_get_mode = original_get_mode
vim.api.nvim_win_set_cursor = original_set_cursor
equal({ snapshot.windowId, { 6, 7 } }, requested_insert_cursor,
  "insert-mode line end is the insertion point after the text")

vim.api.nvim_win_set_cursor(0, { 6, 6 })
snapshot = state.snapshot("lastLine")
truth(
  not plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    direction = "next",
    targetColumn = "preferred",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "last-line boundary is rejected"
)
truth(
  not plugin.request_move_braille_line({
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    changedtick = snapshot.changedtick + 1,
    modeRaw = snapshot.modeRaw,
    direction = "previous",
    targetColumn = "preferred",
    preferredVirtualColumn = snapshot.cursor.preferredVirtualColumn,
  }),
  "stale changedtick is rejected"
)

print(string.format("braille navigation assertions: %d", assertions))
