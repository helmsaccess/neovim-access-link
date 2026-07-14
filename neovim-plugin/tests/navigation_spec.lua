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
vim.rpcnotify = original_rpcnotify
print("navigation tests: 2 assertions passed")
vim.cmd("qa!")
