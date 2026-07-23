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

local exploration_id = 0
local request_id = 0
local action_index = 0

local function begin()
  exploration.reset()
  exploration_id = exploration_id + 1
  action_index = 0
end

local function request(action, extra)
  request_id = request_id + 1
  action_index = action_index + 1
local snapshot = state.snapshot("explorationTest")
truth(vim.tbl_contains(snapshot.pluginCapabilities, "exploration"), "plugin advertises exploration")
  local payload = {
    requestId = request_id,
    explorationId = exploration_id,
    actionIndex = action_index,
    action = action,
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    tabpageId = snapshot.tabpageId,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    cursorLine = snapshot.cursor.line,
    cursorByteColumn = snapshot.cursor.byteColumn,
    cursorVirtualColumn = snapshot.cursor.virtualColumn,
  }
  return vim.tbl_extend("force", payload, extra or {})
end

vim.api.nvim_buf_set_lines(0, 0, -1, true, {
  "alpha, beta",
  "xy",
  "\t界🙂 word",
  "",
  "last line",
})
vim.api.nvim_win_set_cursor(0, { 1, 0 })

local original_cursor = vim.api.nvim_win_get_cursor(0)
local original_view = vim.fn.winsaveview()
local original_tick = vim.api.nvim_buf_get_changedtick(0)
local original_lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)

begin()
local right = exploration.step(request("characterRight"))
equal({ "l", 1, 1, 1 }, {
  right.text, right.line, right.byteColumn, right.characterColumn,
}, "character navigation uses a virtual cursor")
right = exploration.step(request("characterRight", { count = 3 }))
equal({ "a", 4 }, { right.text, right.byteColumn }, "bounded repeat is applied in Lua")
right = exploration.step(request("characterRight", { count = 6 }))
equal({ "a", 10 }, { right.text, right.byteColumn }, "repeat reaches the last character")
local character_boundary = exploration.step(request("characterRight"))
equal({ "boundary", "a", 10 }, {
  character_boundary.resultCode, character_boundary.text, character_boundary.byteColumn,
}, "character movement does not cross a line")

begin()
local next_word = exploration.step(request("wordNext"))
equal({ ",", 5, "word" }, {
  next_word.text, next_word.byteColumn, next_word.unit,
}, "punctuation is an individual word target")
next_word = exploration.step(request("wordNext"))
equal({ "beta", 7 }, { next_word.text, next_word.byteColumn }, "next keyword follows punctuation")
local previous_word = exploration.step(request("wordPrevious"))
equal({ ",", 5 }, { previous_word.text, previous_word.byteColumn }, "previous punctuation is exact")
previous_word = exploration.step(request("wordPrevious"))
equal({ "alpha", 0 }, { previous_word.text, previous_word.byteColumn }, "previous keyword finds its start")
equal("boundary", exploration.step(request("wordPrevious")).resultCode, "buffer start is bounded")

begin()
local down = exploration.step(request("lineDown"))
equal({ "xy", 2, 0, "line" }, {
  down.text, down.line, down.byteColumn, down.unit,
}, "vertical movement returns the target line")
down = exploration.step(request("lineDown"))
equal({ "\t界🙂 word", 3, 0, 7 }, {
  down.text, down.line, down.byteColumn, down.virtualColumn,
}, "vertical movement preserves desired virtual column")
down = exploration.step(request("lineDown"))
equal({ "", 4, 0 }, { down.text, down.line, down.byteColumn }, "empty lines are represented exactly")
local up = exploration.step(request("lineUp"))
equal({ "\t界🙂 word", 3 }, { up.text, up.line }, "line movement is reversible")

vim.api.nvim_win_set_cursor(0, { 3, 1 })
begin()
local unicode = exploration.step(request("characterRight"))
equal({ "🙂", 4, 2 }, {
  unicode.text, unicode.byteColumn, unicode.characterColumn,
}, "UTF-8 byte and character columns remain distinct")
unicode = exploration.step(request("wordNext"))
equal({ "word", 9, 4 }, {
  unicode.text, unicode.byteColumn, unicode.characterColumn,
}, "word movement crosses multibyte text safely")

vim.api.nvim_win_set_cursor(0, { 1, 0 })
begin()
local cross_line = exploration.step(request("wordPrevious"))
equal("boundary", cross_line.resultCode, "previous word remains at the first buffer position")
vim.api.nvim_win_set_cursor(0, { 5, 5 })
begin()
local cross_previous = exploration.step(request("wordPrevious"))
equal({ "last", 5, 0 }, {
  cross_previous.text, cross_previous.line, cross_previous.byteColumn,
}, "previous word scans within a line")
cross_previous = exploration.step(request("wordPrevious"))
equal({ "word", 3, 9 }, {
  cross_previous.text, cross_previous.line, cross_previous.byteColumn,
}, "previous word crosses an empty line")
cross_previous = exploration.step(request("wordPrevious"))
equal({ "界🙂", 3, 1, 1 }, {
  cross_previous.text, cross_previous.line, cross_previous.byteColumn,
  cross_previous.characterColumn,
}, "previous word preserves multibyte keyword text")
cross_previous = exploration.step(request("wordPrevious"))
equal({ "xy", 2, 0 }, {
  cross_previous.text, cross_previous.line, cross_previous.byteColumn,
}, "previous word crosses another line")

vim.api.nvim_win_set_cursor(0, { 1, 10 })
begin()
local within_previous = exploration.step(request("wordPrevious"))
equal({ "beta", 7 }, {
  within_previous.text, within_previous.byteColumn,
}, "previous word from inside a keyword reaches that keyword start")
within_previous = exploration.step(request("wordPrevious"))
equal({ ",", 5 }, {
  within_previous.text, within_previous.byteColumn,
}, "previous word then reaches adjacent punctuation")

vim.api.nvim_win_set_cursor(0, { 1, 0 })
begin()
local first_request = request("characterRight")
local accepted = exploration.step(first_request)
truth(accepted.ok, "fresh request is accepted")
local duplicate = exploration.step(vim.tbl_extend("force", first_request, { requestId = request_id + 1 }))
equal("outOfOrder", duplicate.resultCode, "duplicate action index invalidates exploration")
truth(exploration._test_active() == nil, "out-of-order state is discarded")

begin()
local stale = request("characterRight", { changedtick = original_tick - 1 })
equal("invalidOrStaleRequest", exploration.step(stale).resultCode, "stale changedtick is rejected")
truth(exploration._test_active() == nil, "stale state leaves no virtual cursor")

begin()
local invalid = request("characterRight", { action = "vim.cmd('delete')" })
equal("invalidOrStaleRequest", exploration.step(invalid).resultCode, "arbitrary actions are rejected")

begin()
local zero_request = request("characterRight", { requestId = 0 })
equal("invalidOrStaleRequest", exploration.step(zero_request).resultCode, "zero request ID is rejected")
truth(not exploration.finish({ requestId = 0, explorationId = exploration_id }), "zero finish ID is rejected")

begin()
truth(exploration.step(request("characterRight")).ok, "finish setup succeeds")
truth(exploration.finish({ requestId = request_id + 1, explorationId = exploration_id }), "finish is accepted")
truth(exploration._test_active() == nil, "finish clears only ephemeral state")

equal(original_tick, vim.api.nvim_buf_get_changedtick(0), "exploration never changes changedtick")
equal(original_lines, vim.api.nvim_buf_get_lines(0, 0, -1, true), "exploration never changes text")
equal({ 1, 0 }, vim.api.nvim_win_get_cursor(0), "exploration never changes the real cursor")
local final_view = vim.fn.winsaveview()
for _, name in ipairs({ "topline", "leftcol", "skipcol" }) do
  equal(original_view[name], final_view[name], "exploration preserves view field " .. name)
end

print(string.format("exploration tests: %d assertions passed", assertions))
vim.cmd("qa!")
