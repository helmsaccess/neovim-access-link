local root = vim.fn.getcwd()
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
for _, key in ipairs({ "<F1>", "<F2>", "<F3>", "<F4>", "<F5>", "<F6>", "<F7>", "<F8>",
    "<F9>", "<F10>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and mapping.desc ~= nil,
    "normal-mode mapping missing for " .. key)
end
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
