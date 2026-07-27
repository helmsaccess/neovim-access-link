local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;"
  .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local exploration = require("nvim_nvda.exploration")
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

local function request(snapshot, exploration_id, action_index, action, desired, target_column)
  return {
    requestId = exploration_id * 10 + action_index,
    explorationId = exploration_id,
    actionIndex = action_index,
    action = action,
    count = 1,
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    tabpageId = snapshot.tabpageId,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    cursorLine = snapshot.cursor.line,
    cursorByteColumn = snapshot.cursor.byteColumn,
    cursorVirtualColumn = snapshot.cursor.virtualColumn,
    desiredVirtualColumn = desired,
    targetColumn = target_column or "preferred",
  }
end

vim.api.nvim_buf_set_lines(0, 0, -1, true, {
  "0123456789",
  "x",
  "abcdefghij",
  "\tZ",
})
vim.api.nvim_win_set_cursor(0, { 1, 7 })
exploration.reset()
local snapshot = state.snapshot("brailleExplorationTest")
truth(
  vim.tbl_contains(snapshot.pluginCapabilities, "brailleExploration"),
  "plugin advertises independent Braille exploration"
)
local original_tick = vim.api.nvim_buf_get_changedtick(0)
local original_lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)

local speech = exploration.step(
  request(snapshot, 1, 1, "characterRight", snapshot.cursor.virtualColumn),
  "speech"
)
equal({ "8", 8 }, { speech.text, speech.byteColumn }, "speech exploration starts independently")

local braille = exploration.step(
  request(snapshot, 2, 1, "lineDown", 7),
  "braille"
)
equal({ "x", 2, 0, "line" }, {
  braille.text, braille.line, braille.byteColumn, braille.unit,
}, "Braille exploration reads the next short line")

speech = exploration.step(
  request(snapshot, 1, 2, "characterRight", snapshot.cursor.virtualColumn),
  "speech"
)
equal({ "9", 9 }, {
  speech.text, speech.byteColumn,
}, "Braille requests do not reset speech exploration")

braille = exploration.step(
  request(snapshot, 2, 2, "lineDown", 7),
  "braille"
)
equal({ "abcdefghij", 3, 7 }, {
  braille.text, braille.line, braille.byteColumn,
}, "Braille preferred column returns on a longer line")

vim.api.nvim_win_set_cursor(0, { 2, 0 })
braille = exploration.step(
  request(snapshot, 2, 3, "lineDown", 7, "end"),
  "braille"
)
equal({ "\tZ", 4, 1, 8 }, {
  braille.text, braille.line, braille.byteColumn, braille.virtualColumn,
}, "real cursor motion does not move or invalidate the virtual Braille cursor")

braille = exploration.step(
  request(snapshot, 2, 4, "lineUp", 8, "start"),
  "braille"
)
equal({ "abcdefghij", 3, 0, 0 }, {
  braille.text, braille.line, braille.byteColumn, braille.virtualColumn,
}, "a forward-wrap returns to the adjacent line start")

equal(original_tick, vim.api.nvim_buf_get_changedtick(0), "Braille exploration never edits text")
equal(original_lines, vim.api.nvim_buf_get_lines(0, 0, -1, true), "all lines remain unchanged")
equal({ 2, 0 }, vim.api.nvim_win_get_cursor(0), "virtual movement never changes the moved real cursor")

vim.api.nvim_buf_set_lines(0, 0, 1, true, { "typed while exploring" })
local rebased_snapshot = vim.deepcopy(snapshot)
rebased_snapshot.changedtick = vim.api.nvim_buf_get_changedtick(0)
braille = exploration.step(
  request(rebased_snapshot, 2, 5, "lineDown", 0, "end"),
  "braille"
)
equal({ "\tZ", 4, 1 }, {
  braille.text, braille.line, braille.byteColumn,
}, "text input does not move virtual Braille")
equal(
  rebased_snapshot.changedtick,
  exploration._test_active("braille").changedtick,
  "text input advances the correlated Braille snapshot"
)

truth(
  exploration.finish({ requestId = 99, explorationId = 2 }, "braille"),
  "Braille cleanup succeeds"
)
truth(exploration._test_active("braille") == nil, "Braille cleanup clears only its channel")
truth(exploration._test_active("speech") ~= nil, "speech exploration remains active")

print(string.format("Braille exploration assertions: %d", assertions))
vim.cmd("qa!")
