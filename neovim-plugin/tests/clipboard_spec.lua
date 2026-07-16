local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local clipboard = require("nvim_nvda.clipboard")
local state = require("nvim_nvda.state")

local function truth(value, label) assert(value, label) end
local function equal(expected, actual, label)
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end
local function request(snapshot, request_id)
  return {
    requestId = request_id,
    bufferId = snapshot.bufferId,
    windowId = snapshot.windowId,
    tabpageId = snapshot.tabpageId,
    changedtick = snapshot.changedtick,
    modeRaw = snapshot.modeRaw,
  }
end

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "alpha", "beta 😀" })
vim.cmd("normal! gg0yy")
local snapshot = state.snapshot("clipboardTest")
local copied = clipboard.copy_text(vim.tbl_extend("force", request(snapshot, 1), {
  source = "yankRegister",
}))
truth(copied.ok, "register zero copy succeeds")
equal("alpha\n", copied.clipboardText, "linewise yank preserves newline")
equal(1, copied.copiedLineCount, "linewise copied line count excludes trailing empty line")

vim.cmd("normal! gg0v3l")
snapshot = state.snapshot("clipboardVisualCharacter")
local visual_character = clipboard.copy_text(vim.tbl_extend("force", request(snapshot, 11), {
  source = "visualSelection",
}))
truth(visual_character.ok, "characterwise Visual copy succeeds")
equal("alph", visual_character.clipboardText, "characterwise Visual copy is exact")
vim.cmd("normal! \27")

vim.cmd("normal! ggVj")
snapshot = state.snapshot("clipboardVisualLine")
local visual_line = clipboard.copy_text(vim.tbl_extend("force", request(snapshot, 12), {
  source = "visualSelection",
}))
truth(visual_line.ok, "linewise Visual copy succeeds")
equal("alpha\nbeta 😀\n", visual_line.clipboardText, "linewise Visual copy preserves newline")
vim.cmd("normal! \27")

vim.cmd("normal! gg0\22j2l")
snapshot = state.snapshot("clipboardVisualBlock")
local visual_block = clipboard.copy_text(vim.tbl_extend("force", request(snapshot, 13), {
  source = "visualSelection",
}))
truth(visual_block.ok, "blockwise Visual copy succeeds")
equal("alp\nbet", visual_block.clipboardText, "blockwise Visual copy preserves rows")
vim.cmd("normal! \27")

vim.cmd("normal! ggdd")
snapshot = state.snapshot("clipboardRegisterAfterDelete")
local yank_after_delete = clipboard.copy_text(vim.tbl_extend("force", request(snapshot, 14), {
  source = "yankRegister",
}))
equal("alpha\n", yank_after_delete.clipboardText, "register zero is not replaced by a delete")

local register_stored = clipboard.set_register(vim.tbl_extend("force", request(snapshot, 17), {
  text = "from Windows\r\nsecond line\r\n",
}))
truth(register_stored.ok, "Windows text is stored in the unnamed paste register")
equal("V", register_stored.registerType, "trailing newline creates a linewise register")
equal("from Windows\nsecond line\n", vim.fn.getreg('"'), "register text normalizes CRLF")
equal("from Windows\nsecond line\n", vim.fn.getreg("0"), "register zero backs the unnamed register")
vim.cmd("normal! p")
equal(
  { "beta 😀", "from Windows", "second line" },
  vim.api.nvim_buf_get_lines(0, 0, -1, true),
  "normal p uses the replaced current register"
)

snapshot = state.snapshot("clipboardStaleRegister")
local stale_register = clipboard.set_register(vim.tbl_extend("force", request(snapshot, 18), {
  changedtick = snapshot.changedtick - 1,
  text = "must not replace the register",
}))
equal("staleState", stale_register.resultCode, "stale register replacement is rejected")
equal("from Windows\nsecond line\n", vim.fn.getreg('"'), "stale replacement preserves unnamed register")
equal("from Windows\nsecond line\n", vim.fn.getreg("0"), "stale replacement preserves register zero")

local stale = clipboard.paste_text(vim.tbl_extend("force", request(snapshot, 2), {
  changedtick = snapshot.changedtick - 1,
  text = "must not appear",
}))
equal("staleState", stale.resultCode, "stale paste rejected")
truth(not table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, true), "\n"):find("must not appear", 1, true),
  "stale paste does not mutate buffer")

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
snapshot = state.snapshot("clipboardPaste")
local pasted = clipboard.paste_text(vim.tbl_extend("force", request(snapshot, 3), {
  text = "one 😀\ntwo",
}))
truth(pasted.ok, "Unicode multiline paste succeeds")
equal({ "one 😀", "two" }, vim.api.nvim_buf_get_lines(0, 0, -1, true), "paste uses Neovim API")

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
snapshot = state.snapshot("clipboardCrLfPaste")
local crlf_pasted = clipboard.paste_text(vim.tbl_extend("force", request(snapshot, 15), {
  text = "left\r\nright",
}))
truth(crlf_pasted.ok, "CRLF paste succeeds")
equal({ "left", "right" }, vim.api.nvim_buf_get_lines(0, 0, -1, true), "CRLF is normalized by Neovim")

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
snapshot = state.snapshot("clipboardRepeatPaste")
local repeatable = clipboard.paste_text(vim.tbl_extend("force", request(snapshot, 16), {
  text = "xy",
}))
truth(repeatable.ok, "repeatable paste succeeds")
vim.cmd("normal! .")
equal({ "xyxy" }, vim.api.nvim_buf_get_lines(0, 0, -1, true), "paste is available to dot repeat")

snapshot = state.snapshot("clipboardReadonly")
vim.bo.modifiable = false
local blocked = clipboard.paste_text(vim.tbl_extend("force", request(snapshot, 4), {
  text = "blocked",
}))
equal("bufferNotEditable", blocked.resultCode, "nonmodifiable buffer rejected")
vim.bo.modifiable = true

snapshot = state.snapshot("clipboardInvalid")
local invalid = clipboard.paste_text(vim.tbl_extend("force", request(snapshot, 5), {
  text = "bad\0text",
}))
equal("invalidRequest", invalid.resultCode, "NUL text rejected")

print("clipboard tests: 28 assertions passed")
vim.cmd("qa!")
