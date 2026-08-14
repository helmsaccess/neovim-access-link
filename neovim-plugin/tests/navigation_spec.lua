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
vim.api.nvim_feedkeys("ihjklwebng%[d sample", "xt", false)
vim.wait(500, function() return vim.api.nvim_get_current_line() == "hjklwebng%[d sample" end)
vim.wait(100)
local forbidden = {
  characterMoved = true, wordMoved = true, lineChanged = true,
  searchMatchChanged = true, matchingPairMoved = true,
  matchingPairNotFound = true, diagnosticMoved = true,
}
for _, event in ipairs(events) do
  assert(not forbidden[event.type], "inserted text emitted navigation event " .. event.type)
end
equal("hjklwebng%[d sample", vim.api.nvim_get_current_line(), "inserted motion-like text")

vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "xt", false)
vim.wait(50)

-- Prefixes are one tagged state. The @ in g@ belongs to Neovim's operatorfunc
-- command and must not start the unrelated top-level macro prefix.
events = {}
_G.nvim_nvda_test_operator = function() end
vim.go.operatorfunc = "v:lua.nvim_nvda_test_operator"
vim.api.nvim_feedkeys("g@l", "xt", false)
vim.wait(100)
for _, event in ipairs(events) do
  assert(event.type ~= "macroPlayed", "g@ operator command escaped as macro playback")
end
equal("n", vim.api.nvim_get_mode().mode, "g@ motion completes in Normal mode")

-- The real gg transition remains semantic after replacing the independent
-- flags with the tagged prefix state.
events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "one", "two", "three" })
vim.api.nvim_win_set_cursor(0, { 3, 0 })
vim.api.nvim_feedkeys("gg", "xt", false)
vim.wait(100)
vim.api.nvim_exec_autocmds("CursorMoved", { modeline = false })
vim.wait(100)
local saw_file_start = false
for _, event in ipairs(events) do
  if event.type == "fileStart" then saw_file_start = true end
end
equal(true, saw_file_start, "gg keeps its file-start semantic event")
_G.nvim_nvda_test_operator = nil

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

-- A queued navigation callback belongs to the connection generation in which
-- it was observed. A fast disconnect/reconnect must not publish it to the new
-- consumer.
local scheduled = {}
local original_schedule = vim.schedule
vim.schedule = function(callback) scheduled[#scheduled + 1] = callback end
events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "abc" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
vim.api.nvim_feedkeys("l", "xt", false)
vim.api.nvim_exec_autocmds("CursorMoved", { modeline = false })
assert(#scheduled > 0, "navigation callback was not scheduled")
plugin.unregister_channel(1)
plugin.register_channel(1)
events = {}
vim.schedule = original_schedule
for _, callback in ipairs(scheduled) do callback() end
for _, event in ipairs(events) do
  assert(event.type ~= "characterMoved" and event.type ~= "cursorMoved",
    "pre-disconnect navigation escaped into the reconnected channel")
end

-- Menu models are connection-scoped as well. A new consumer must never
-- receive a close for a menu which only the previous consumer saw.
events = {}
local reconnect_item = { word = "same", abbr = "same", kind = "v" }
plugin.accessible_menu_open({ reconnect_item }, { kind = "plugin", selected = 1 })
plugin.unregister_channel(1)
plugin.register_channel(1)
events = {}
plugin.accessible_menu_update(reconnect_item, {
  kind = "plugin", selected = 1, item_count = 1,
})
plugin.accessible_menu_close()
local reconnect_menu_events = {}
for _, event in ipairs(events) do
  if event.type:sub(1, 4) == "menu" then
    reconnect_menu_events[#reconnect_menu_events + 1] = event.type
  end
end
equal(3, #reconnect_menu_events, "reconnected menu event count")
equal("menuOpened", reconnect_menu_events[1], "reconnected menu opens")
equal("menuSelectionChanged", reconnect_menu_events[2], "reconnected menu selects")
equal("menuClosed", reconnect_menu_events[3], "reconnected menu closes")

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
print("navigation tests: 11 assertions passed")
vim.cmd("qa!")
