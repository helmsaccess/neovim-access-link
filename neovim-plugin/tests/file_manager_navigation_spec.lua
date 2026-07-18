local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;"
  .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local function equal(expected, actual, label)
  assert(expected == actual, string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local events = {}
local original_rpcnotify = vim.rpcnotify
vim.rpcnotify = function(_, method, event)
  if method == "nvim_nvda_event" then table.insert(events, event) end
  return true
end

local plugin = require("nvim_nvda")
local manager = require("nvim_nvda.file_manager")
plugin.setup()
plugin.register_channel(1)

local buffer = vim.api.nvim_get_current_buf()
manager.register("navigation-test", function()
  return vim.api.nvim_get_current_buf() == buffer
end, function()
  return {
    entry = {
      name = vim.api.nvim_get_current_line(),
      path = "/confirmed/draft.txt",
      type = "file",
    },
  }
end)

events = {}
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "draft.txt" })
vim.api.nvim_win_set_cursor(0, { 1, 4 })
vim.api.nvim_feedkeys("0", "xt", false)
vim.wait(500, function() return vim.api.nvim_win_get_cursor(0)[2] == 0 end)
-- Neovim 0.10 headless may move the cursor without dispatching CursorMoved.
vim.api.nvim_exec_autocmds("CursorMoved", { modeline = false })
vim.wait(100)

local manager_start
for _, event in ipairs(events) do
  if event.type == "fileManagerEntryChanged"
    and event.payload.fileManagerMotion == "lineStart" then
    manager_start = event
  end
end
equal("lineStart", manager_start and manager_start.payload.fileManagerMotion,
  "file manager retains line-start motion")
equal("draft.txt", manager_start and manager_start.payload.fileManager.entry.name,
  "file manager motion retains semantic entry")

manager.unregister("navigation-test")
vim.rpcnotify = original_rpcnotify
print("file manager navigation tests: 2 assertions passed")
vim.cmd("qa!")
