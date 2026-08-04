local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local function equal(expected, actual, label)
  assert(expected == actual, string.format("%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
end

local events = {}
local original_rpcnotify = vim.rpcnotify
vim.rpcnotify = function(_, method, event)
  if method == "nvim_nvda_event" then table.insert(events, event) end
  return true
end

local plugin = require("nvim_nvda")
plugin.setup()
plugin.register_channel(1)
events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "" })

-- These characters are Normal-mode motions or command prefixes, but ordinary
-- text in Insert mode.  None may escape as semantic navigation.
vim.api.nvim_feedkeys("ihjklwebn%[d sample", "xt", false)
vim.wait(500, function() return vim.api.nvim_get_current_line() == "hjklwebn%[d sample" end)
vim.wait(100)
local forbidden = {
  characterMoved = true, wordMoved = true, lineChanged = true,
  searchMatchChanged = true, matchingPairMoved = true,
  matchingPairNotFound = true, diagnosticMoved = true,
}
for _, event in ipairs(events) do
  assert(not forbidden[event.type], "inserted text emitted navigation event " .. event.type)
end
equal("hjklwebn%[d sample", vim.api.nvim_get_current_line(), "inserted motion-like text")

vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "xt", false)
vim.wait(50)

-- One physical arrow motion must publish one authoritative semantic event.
-- A following generic cursor event would make NVDA speak the same character
-- a second time.
events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "abc" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Right>", true, false, true), "xt", false)
vim.wait(500, function() return vim.api.nvim_win_get_cursor(0)[2] == 1 end)
-- Neovim 0.10 headless may move the cursor without dispatching CursorMoved.
-- Re-running the autocmd is harmless on newer versions because the plugin
-- deduplicates the unchanged cursor position.
vim.api.nvim_exec_autocmds("CursorMoved", { modeline = false })
vim.wait(100)
local arrow_events = {}
for _, event in ipairs(events) do
  if event.type == "characterMoved" or event.type == "cursorMoved" then
    table.insert(arrow_events, event.type)
  end
end
equal(1, #arrow_events, "arrow motion publishes one navigation event")
equal("characterMoved", arrow_events[1], "arrow motion keeps its semantic unit")

-- Text typed on the Ex command line must not be retained as a Normal-mode
-- motion.  The final `l` in commands such as `:terminal` previously leaked
-- into the first cursor event of the resulting buffer as characterMoved.
events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "abc" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
vim.api.nvim_feedkeys(":normal! l\r", "xt", false)
vim.wait(500, function() return vim.api.nvim_win_get_cursor(0)[2] == 1 end)
-- Neovim 0.10 headless does not dispatch CursorMoved for this feedkeys/Ex
-- combination even though the cursor moved. Exercise the plugin callback
-- explicitly so the semantic assertion is identical on supported versions.
vim.api.nvim_exec_autocmds("CursorMoved", { modeline = false })
vim.wait(100)
local cursor_event
for _, event in ipairs(events) do
  if event.type == "cursorMoved" or event.type == "characterMoved" then
    cursor_event = event.type
  end
end
equal("cursorMoved", cursor_event, "Ex text does not become semantic motion")

-- Custom completion menus publish selection changes through their semantic
-- adapter. nvim-cmp's default Insert selection behavior temporarily replaces
-- the candidate suffix and moves the Insert-mode cursor. Neither operation
-- may leak as typing, a replacement cue, navigation, or a boundary cue.
local cmp_callbacks = {}
local first_entry = {
  id = 1, completion_item = { label = "first", kind = 3 },
  source = { name = "nvim_lsp" },
}
local second_entry = {
  id = 2, completion_item = { label = "second", kind = 3 },
  source = { name = "nvim_lsp" },
}
local selected_entry = first_entry
package.loaded.cmp = {
  event = { on = function(_, name, callback) cmp_callbacks[name] = callback end },
  get_entries = function() return { first_entry, second_entry } end,
  get_selected_entry = function() return selected_entry end,
}
vim.api.nvim_exec_autocmds("User", { pattern = "CmpReady" })
cmp_callbacks.menu_opened()
vim.wait(100)
events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "first" })
vim.api.nvim_win_set_cursor(0, { 1, 5 })
vim.keymap.set("i", "<C-N>", function()
  selected_entry = second_entry
  vim.api.nvim_set_current_line("second")
  vim.api.nvim_win_set_cursor(0, { 1, 6 })
end, { buffer = true })
vim.cmd("stopinsert")
vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("i<C-N>", true, false, true), "xt", false)
vim.wait(200, function()
  for _, event in ipairs(events) do
    if event.type == "menuSelectionChanged" and event.payload.itemIndex == 2 then return true end
  end
  return false
end)
equal("second", vim.api.nvim_get_current_line(), "completion preview mapping changed the buffer")
vim.api.nvim_exec_autocmds("CursorMovedI", { modeline = false })
vim.wait(100)
for _, event in ipairs(events) do
  assert(not forbidden[event.type],
    "completion selection emitted navigation event " .. event.type)
  assert(event.type ~= "textChanged",
    "completion preview edit escaped as ordinary typing")
end
local selected_second = false
for _, event in ipairs(events) do
  if event.type == "menuSelectionChanged" and event.payload.itemIndex == 2 then
    selected_second = true
  end
end
equal(true, selected_second, "completion adapter remains authoritative for preview selection")
cmp_callbacks.menu_closed()
vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "xt", false)
vim.wait(50)
package.loaded.cmp = nil

vim.rpcnotify = original_rpcnotify
print("navigation tests: 8 assertions passed")
vim.cmd("qa!")
