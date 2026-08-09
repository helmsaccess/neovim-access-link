local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path
vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", "diagnostics")
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "L2")
vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "automatic-parameters")
vim.fn.setenv("ACCESS_LINK_HUMAN_LANGUAGE", "en")
vim.fn.setenv("ACCESS_LINK_HUMAN_CONTEXT", "Fixture context")
vim.fn.setenv("ACCESS_LINK_HUMAN_TASK", "Fixture task")
vim.fn.setenv("ACCESS_LINK_HUMAN_EXPECTED", "Fixture expectation")
vim.fn.setenv("ACCESS_LINK_HUMAN_DRY_RUN", "1")
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "def calculate_total():", "  pass" })
vim.bo.filetype = "python"

dofile(root .. "/tests/human/framework/init.lua")

local assertions = 0
local function truthy(value, label)
  assertions = assertions + 1
  assert(value, label)
end

truthy(vim.fn.exists(":AccessLinkHumanTestInfo") == 2,
  "human-test info command is available")
local notification = nil
local original_notify = vim.notify
vim.notify = function(message) notification = message end
vim.cmd.AccessLinkHumanTestInfo()
vim.notify = original_notify
truthy(type(notification) == "string" and notification:find("Test ID L2.", 1, true) == 1,
  "F2 task information starts with the stable short test ID")
truthy(vim.g.access_link_human_config_ready == 1,
  "dry-run configuration reports successful completion")
for _, key in ipairs({ "<F2>", "<F3>", "<F4>", "<F5>", "<F6>", "<F7>", "<F8>",
    "<F9>", "<F10>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and mapping.desc ~= nil,
    "normal-mode mapping missing for " .. key)
end
truthy(vim.fn.maparg("<F1>", "n") == "",
  "F1 remains available for Neovim help")
truthy(vim.fn.maparg("<F11>", "n") == "",
  "F11 remains available to Windows Terminal instead of being a dead Neovim mapping")
local preparation = vim.fn.maparg("<F3>", "n", false, true)
truthy(type(preparation.callback) == "function",
  "F3 preparation uses a callable task-specific mapping")
preparation.callback()
local prepared_lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)
local marker = "automatic_total = calculate_total()"
truthy(prepared_lines[#prepared_lines] == marker,
  "automatic-parameter task prepares its empty call through F3")
local opening = assert(marker:find("(", 1, true)) - 1
local cursor = vim.api.nvim_win_get_cursor(0)
truthy(cursor[1] == #prepared_lines and cursor[2] == opening + 1,
  "F3 leaves the insertion cursor between the prepared parentheses")
local insert_f2 = vim.fn.maparg("<F2>", "i", false, true)
truthy(type(insert_f2) == "table" and insert_f2.desc ~= nil,
  "insert-mode task reminder is available")
truthy(vim.o.shiftwidth == 2 and vim.o.tabstop == 2 and vim.o.expandtab,
  "isolated editing defaults are deterministic")

for _, case in ipairs({
  { profile = "native", step = "completion-presentation", id = "C1" },
  { profile = "cmp", step = "menu-presentation", id = "C2" },
  { profile = "blink", step = "menu-presentation", id = "C3" },
}) do
  vim.cmd.stopinsert()
  vim.api.nvim_buf_set_lines(0, 0, -1, true, { "completion fixture" })
  vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", case.profile)
  vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", case.step)
  vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", case.id)
  vim.api.nvim_del_user_command("AccessLinkHumanTestInfo")
  dofile(root .. "/tests/human/framework/init.lua")
  local completion_preparation = vim.fn.maparg("<F3>", "n", false, true)
  completion_preparation.callback()
  local completion_lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)
  truthy(completion_lines[#completion_lines] == "completion_probe = calculate_",
    case.id .. " prepares the insertion point described by its task")
end

vim.cmd.stopinsert()
vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", "native")
vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "native-search-replacement")
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "L4")
vim.api.nvim_del_user_command("AccessLinkHumanTestInfo")
dofile(root .. "/tests/human/framework/init.lua")
local l4_mappings = {}
for _, key in ipairs({ "<F3>", "<F4>", "<F5>", "<F6>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and type(mapping.callback) == "function",
    "L4 " .. key .. " uses a callable helper without generated command typing")
  truthy(mapping.rhs == nil or mapping.rhs == "",
    "L4 " .. key .. " does not expose an Ex command as mapped keystrokes")
  l4_mappings[key] = mapping
end
local native_events = {}
local native_operations = require("nvim_nvda.native_operations")
local native_group = vim.api.nvim_create_augroup(
  "AccessLinkHumanNativeOperationSpec", { clear = true })
native_operations.setup(function(event_type, reason, payload)
  native_events[#native_events + 1] = {
    type = event_type, reason = reason, payload = payload,
  }
end, native_group)
vim.cmd.lcd(root .. "/tests/human/fixtures")
l4_mappings["<F3>"].callback()
truthy(vim.wait(1000, function()
  return #native_events > 0 and native_events[#native_events].type == "resultListChanged"
end, 10), "L4 F3 emits the production native result-list event")
truthy(native_events[#native_events].payload.itemCount == 4,
  "L4 project search has four deterministic fixture results")
l4_mappings["<F4>"].callback()
local quickfix = vim.fn.getqflist({ idx = 0, size = 0 })
local window = vim.fn.getwininfo(vim.api.nvim_get_current_win())[1] or {}
truthy(quickfix.idx == 2 and window.quickfix == 1,
  "L4 F4 selects the second result in the open Quickfix list")
l4_mappings["<F5>"].callback()
quickfix = vim.fn.getqflist({ idx = 0, size = 0 })
window = vim.fn.getwininfo(vim.api.nvim_get_current_win())[1] or {}
truthy(quickfix.idx == 1 and window.quickfix == 1,
  "L4 F5 selects the previous result without leaving Quickfix")
vim.api.nvim_feedkeys("yna", "t", false)
l4_mappings["<F6>"].callback()
truthy(vim.wait(1000, function()
  return #native_events > 1 and native_events[#native_events].type == "replacementPerformed"
end, 10), "L4 F6 completes the production replacement observation")
truthy(native_events[#native_events].payload.changedBufferCount == 2,
  "L4 confirmed replacement changes both fixture buffers")
truthy(native_events[#native_events].payload.modifiedBufferCount == 2,
  "L4 confirmed replacement leaves both fixture buffers unsaved")
vim.cmd.cclose()
vim.cmd.lcd(root)
native_operations.reset()
pcall(vim.api.nvim_del_augroup_by_id, native_group)

vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "native-lsp-rename")
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "L5")
vim.api.nvim_del_user_command("AccessLinkHumanTestInfo")
dofile(root .. "/tests/human/framework/init.lua")
for _, key in ipairs({ "<F3>", "<F4>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and type(mapping.callback) == "function",
    "L5 " .. key .. " uses a callable native LSP test helper")
end

vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "native-buffer-replacement")
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "L6")
vim.api.nvim_del_user_command("AccessLinkHumanTestInfo")
dofile(root .. "/tests/human/framework/init.lua")
truthy(vim.fn.buflisted(vim.fn.bufnr(vim.fn.fnamemodify(
  "lsp_rename_consumer.py", ":p"))) == 1,
  "L6 explicitly lists the prepared second buffer for native bufdo")
for _, key in ipairs({ "<F3>", "<F4>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and type(mapping.callback) == "function",
    "L6 " .. key .. " uses a callable buffer-list test helper")
end

vim.cmd.stopinsert()
vim.api.nvim_buf_set_lines(0, 0, -1, true, {
  "int main(void) {",
  "  int first = missing_first;",
  "  return first + missing_second;",
  "}",
})
vim.bo.filetype = "c"
vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", "c-diagnostics")
vim.fn.setenv("ACCESS_LINK_HUMAN_STEP_ID", "clang-tidy-presentation")
vim.fn.setenv("ACCESS_LINK_HUMAN_TEST_ID", "D3")
vim.api.nvim_del_user_command("AccessLinkHumanTestInfo")
dofile(root .. "/tests/human/framework/init.lua")
for _, key in ipairs({ "<F2>", "<F3>", "<F4>", "<F5>", "<F6>", "<F7>",
    "<F8>", "<F9>", "<F10>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and mapping.desc ~= nil,
    "D3 task mapping missing for " .. key)
end
local d3_f5 = vim.fn.maparg("<F5>", "n", false, true)
truthy(type(d3_f5.callback) == "function",
  "D3 gives an explicit response for its unused F5 key")
notification = nil
vim.notify = function(message) notification = message end
d3_f5.callback()
vim.notify = original_notify
truthy(notification == "F5 has no action in this task.",
  "D3 does not leave F5 as a silent dead key")
local d3_f2 = vim.fn.maparg("<F2>", "n", false, true)
notification = nil
vim.notify = function(message) notification = message end
d3_f2.callback()
vim.notify = original_notify
truthy(type(notification) == "string" and notification:find("Test ID D3.", 1, true) == 1,
  "D3 repeats its stable ID through F2")

local parentheses = dofile(root .. "/tests/human/framework/completion_parentheses.lua")
local function_item = {
  label = "calculate_total",
  kind = vim.lsp.protocol.CompletionItemKind.Function,
}
local converted = parentheses.native_convert(function_item)
truthy(converted.word == "calculate_total()",
  "native function completion gains a bracket pair")
truthy(next(parentheses.native_convert({
  label = "total",
  kind = vim.lsp.protocol.CompletionItemKind.Variable,
})) == nil, "native variable completion remains unchanged")
truthy(next(parentheses.native_convert({
  label = "calculate_total",
  kind = vim.lsp.protocol.CompletionItemKind.Function,
  insertText = "calculate_total(${1:value})",
  insertTextFormat = vim.lsp.protocol.InsertTextFormat.Snippet,
})) == nil, "native function snippet remains owned by the provider")

local line, column, changed = parentheses.plan("calculate_total", 15, function_item)
truthy(line == "calculate_total()" and column == 16 and changed,
  "plain function completion gains parentheses with cursor inside")
line, column, changed = parentheses.plan("calculate_total()", 17, function_item)
truthy(line == "calculate_total()" and column == 16 and not changed,
  "existing parentheses are not duplicated and cursor moves inside")
line, column, changed = parentheses.plan("calculate_total()", 15, function_item)
truthy(line == "calculate_total()" and column == 16 and not changed,
  "cursor before existing opening parenthesis moves inside")
local provider_item = vim.tbl_extend("force", function_item, {
  insertText = "calculate_total(value)",
})
line, column, changed = parentheses.plan(
  "calculate_total(value)", #provider_item.insertText, provider_item)
truthy(line == "calculate_total(value)" and column == 16 and not changed,
  "provider-owned non-empty parentheses are not duplicated")

print(string.format("human-test config specs passed: %d assertions", assertions))
vim.cmd("qa!")
