local root = vim.fn.getcwd()
vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", "diagnostics")
vim.fn.setenv("ACCESS_LINK_HUMAN_DRY_RUN", "1")

dofile(root .. "/tests/human/framework/init.lua")

local assertions = 0
local function truthy(value, label)
  assertions = assertions + 1
  assert(value, label)
end

truthy(vim.fn.exists(":AccessLinkHumanTestInfo") == 2,
  "human-test info command is available")
truthy(vim.g.access_link_human_config_ready == 1,
  "dry-run configuration reports successful completion")
for _, key in ipairs({ "<F1>", "<F2>", "<F3>", "<F4>", "<F5>", "<F6>", "<F7>", "<F8>",
    "<F9>", "<F10>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and mapping.desc ~= nil,
    "normal-mode mapping missing for " .. key)
end
local insert_f2 = vim.fn.maparg("<F2>", "i", false, true)
truthy(type(insert_f2) == "table" and insert_f2.desc ~= nil,
  "insert-mode task reminder is available")
truthy(vim.o.shiftwidth == 2 and vim.o.tabstop == 2 and vim.o.expandtab,
  "isolated editing defaults are deterministic")

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
