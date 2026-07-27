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
local function execute_queued_normal_keys()
  vim.api.nvim_feedkeys("", "x", false)
end
local function payload(snapshot, action, line_start)
  local result = {
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = snapshot.cursor.line,
    byteColumn = snapshot.cursor.byteColumn,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
    action = action,
  }
  if line_start then result.lineStart = line_start end
  return result
end

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "alpha beta" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
local snapshot = state.snapshot("brailleRoutingActions")
truth(
  vim.tbl_contains(snapshot.pluginCapabilities, "brailleRoutingActions"),
  "plugin advertises repeated Braille routing actions"
)

truth(
  plugin.request_braille_route_action(payload(snapshot, "deleteWord")),
  "delete-word request is accepted in Normal mode"
)
execute_queued_normal_keys()
equal("beta", vim.api.nvim_get_current_line(), "dw deletes the routed word")

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "  alpha beta" })
vim.api.nvim_win_set_cursor(0, { 1, 8 })
snapshot = state.snapshot("deleteFromIndentation")
truth(
  plugin.request_braille_route_action(payload(snapshot, "deleteLine", "indentation")),
  "delete-line request from indentation is accepted"
)
execute_queued_normal_keys()
equal("  ", vim.api.nvim_get_current_line(), "caret d-dollar preserves indentation")

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "  alpha beta" })
vim.api.nvim_win_set_cursor(0, { 1, 8 })
snapshot = state.snapshot("deleteFromBeginning")
truth(
  plugin.request_braille_route_action(payload(snapshot, "deleteLine", "beginning")),
  "delete-line request from beginning is accepted"
)
execute_queued_normal_keys()
equal("", vim.api.nvim_get_current_line(), "zero d-dollar deletes from the absolute line beginning")

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "alpha beta" })
vim.api.nvim_win_set_cursor(0, { 1, 5 })
snapshot = state.snapshot("wordWhitespace")
truth(
  not plugin.request_braille_route_action(payload(snapshot, "deleteWord")),
  "word action on whitespace is rejected"
)
vim.api.nvim_win_set_cursor(0, { 1, 0 })
truth(
  not plugin.request_braille_route_action({
    action = "deleteWord",
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    line = 1,
    byteColumn = 0,
    changedtick = vim.api.nvim_buf_get_changedtick(0) + 1,
    modeRaw = "n",
  }),
  "stale changedtick is rejected"
)
snapshot = state.snapshot("extraField")
local extra = payload(snapshot, "deleteWord")
extra.command = "dd"
truth(
  not plugin.request_braille_route_action(extra),
  "extra or untrusted command fields are rejected"
)

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "alpha" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
snapshot = state.snapshot("readOnly")
vim.bo.readonly = true
truth(
  not plugin.request_braille_route_action(payload(snapshot, "deleteWord")),
  "read-only buffers reject repeated routing edits"
)
vim.bo.readonly = false

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "äx" })
vim.api.nvim_win_set_cursor(0, { 1, 1 })
snapshot = state.snapshot("insideUtf8")
truth(
  not plugin.request_braille_route_action(payload(snapshot, "deleteWord")),
  "a byte column inside a UTF-8 character is rejected"
)

print(string.format("braille routing action assertions: %d", assertions))
