local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", "native")
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "L4")
vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "native-search-replacement")
vim.fn.setenv("ACCESS_LINK_HUMAN_LANGUAGE", "en")
vim.fn.setenv("ACCESS_LINK_HUMAN_DRY_RUN", "1")
dofile(root .. "/tests/human/framework/init.lua")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
end

local events = {}
local original_rpcnotify = vim.rpcnotify
local original_ui_attach = vim.ui_attach
local original_ui_detach = vim.ui_detach
vim.rpcnotify = function(_, method, event)
  if method == "nvim_nvda_event" then events[#events + 1] = event end
  return true
end
-- The test records the semantic RPC boundary directly. Native prompt UI is
-- exercised by the existing real-TUI tests and remains owned by Neovim.
vim.ui_attach = function() return true end
vim.ui_detach = function() return true end

local plugin = require("nvim_nvda")
plugin.setup()
plugin.register_channel(1)
vim.cmd.lcd(root .. "/tests/human/fixtures")
vim.cmd.edit("lsp_features.py")
vim.wait(100, function() return false end, 10)

local function mapping(key)
  local value = vim.fn.maparg(key, "n", false, true)
  assert(type(value.callback) == "function", "missing callable mapping " .. key)
  return value.callback
end

local function run(key, answers)
  events = {}
  if answers then vim.api.nvim_feedkeys(answers, "t", false) end
  mapping(key)()
  vim.wait(250, function() return false end, 10)
  return events
end

local function matching(values, event_type)
  return vim.tbl_filter(function(event) return event.type == event_type end, values)
end

local search = run("<F3>")
local result_lists = matching(search, "resultListChanged")
equal(1, #result_lists, "F3 emits one result-list update")
equal(4, result_lists[1].payload.itemCount, "F3 reports all fixture results")
equal("quickfix", result_lists[1].payload.windowType, "F3 opens the Quickfix window")
equal(1, result_lists[1].payload.resultIndex, "F3 opens the first result")
local quickfix_window = vim.api.nvim_get_current_win()
equal(0, #matching(search, "commandLineChanged"),
  "F3 does not expose generated command typing")

local next_result = run("<F4>")
equal(quickfix_window, vim.api.nvim_get_current_win(), "F4 keeps the Quickfix window focused")
equal(2, vim.fn.getqflist({ idx = 0 }).idx, "F4 selects the second result")
equal(0, #matching(next_result, "contextChanged"), "F4 does not reopen the Quickfix window")

local previous_result = run("<F5>")
local previous_list = vim.fn.getqflist({ idx = 0 })
equal(1, previous_list.idx, "F5 returns to the first Quickfix row")
equal(0, #matching(previous_result, "contextChanged"),
  "F5 does not reopen a source window")

local first_result = run("<F5>")
local first_messages = matching(first_result, "messageReceived")
equal(1, #first_messages, "F5 at the first result emits one boundary message")
equal("Already at the first Quickfix result.", first_messages[1].payload.message,
  "F5 reports the first-result boundary clearly")
equal(0, #matching(first_result, "errorReceived"),
  "F5 at the first result does not expose a native No more items error")

run("<F4>")
run("<F4>")
local last_move = run("<F4>")
local last_list = vim.fn.getqflist({ idx = 0 })
equal(4, last_list.idx, "F4 selects the last Quickfix row")
equal(0, #matching(last_move, "contextChanged"),
  "repeated F4 does not reopen a source window")
local last_result = run("<F4>")
local last_messages = matching(last_result, "messageReceived")
equal(1, #last_messages, "F4 at the last result emits one boundary message")
equal("Already at the last Quickfix result.", last_messages[1].payload.message,
  "F4 reports the last-result boundary clearly")
equal(0, #matching(last_result, "errorReceived"),
  "F4 at the last result does not expose a native No more items error")

local replacement = run("<F6>", "yna")
local replacement_context = matching(replacement, "contextChanged")
local replacement_results = matching(replacement, "replacementPerformed")
equal(0, #replacement_context, "F6 suppresses internal bulk-replacement buffer context")
equal(1, #replacement_results, "F6 emits one replacement summary")
equal(2, replacement_results[1].payload.changedBufferCount,
  "F6 reports both changed fixture buffers")
equal(0, #matching(replacement, "cursorMoved"),
  "F6 emits no redundant character navigation")

vim.cmd.cclose()
local function restore_fixture(name)
  local path = vim.fn.fnamemodify(name, ":p")
  local buffer = vim.fn.bufnr(path)
  if buffer < 0 then buffer = vim.fn.bufadd(path) end
  vim.fn.bufload(buffer)
  vim.api.nvim_buf_set_lines(buffer, 0, -1, true, vim.fn.readfile(path))
  vim.bo[buffer].modified = false
  return buffer
end

local primary = restore_fixture("lsp_features.py")
restore_fixture("lsp_rename_consumer.py")
vim.api.nvim_set_current_buf(primary)
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "L6")
vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "native-buffer-replacement")
vim.api.nvim_del_user_command("AccessLinkHumanTestInfo")
dofile(root .. "/tests/human/framework/init.lua")

local buffer_replacement = run("<F3>")
local buffer_results = matching(buffer_replacement, "replacementPerformed")
equal(1, #buffer_results, "L6 F3 emits one buffer-list replacement summary")
equal("buffers", buffer_results[1].payload.replacementScope,
  "L6 uses Neovim's buffer-list scope")
equal(2, buffer_results[1].payload.changedBufferCount,
  "L6 reports both changed fixture buffers")
equal(2, buffer_results[1].payload.modifiedBufferCount,
  "L6 reports both changed fixture buffers as unsaved")
equal(0, #matching(buffer_replacement, "contextChanged"),
  "L6 suppresses internal buffer-list context changes")
equal(0, #matching(buffer_replacement, "cursorMoved"),
  "L6 suppresses internal buffer-list cursor changes")

local first_buffer_report = matching(run("<F4>"), "messageReceived")
equal(1, #first_buffer_report, "L6 first F4 emits one verification report")
equal(true, first_buffer_report[1].payload.message:find(
  "lsp_features.py: 2 occurrences of calculate_tip_buffered", 1, true) ~= nil,
  "L6 first F4 verifies the primary fixture")
local second_buffer_report = matching(run("<F4>"), "messageReceived")
equal(1, #second_buffer_report, "L6 second F4 emits one verification report")
equal(true, second_buffer_report[1].payload.message:find(
  "lsp_rename_consumer.py: 2 occurrences of calculate_tip_buffered", 1, true) ~= nil,
  "L6 second F4 verifies the reference fixture")

plugin.unregister_channel(1)
vim.rpcnotify = original_rpcnotify
vim.ui_attach = original_ui_attach
vim.ui_detach = original_ui_detach
print(string.format("human native workflow integration specs passed: %d assertions", assertions))
