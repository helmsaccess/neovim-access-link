local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local manager = require("nvim_nvda.file_manager")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local directory = "/tmp/nvim-nvda-file-manager-spec"
vim.fn.delete(directory, "rf")
vim.fn.mkdir(directory .. "/folder", "p")
vim.fn.writefile({ "content" }, directory .. "/item.txt")
vim.fn.system({ "ln", "-s", "item.txt", directory .. "/link" })
vim.cmd("Explore " .. vim.fn.fnameescape(directory))

local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
local function move_to(pattern)
  for index, line in ipairs(lines) do
    if line:find(pattern, 1, true) then
      vim.api.nvim_win_set_cursor(0, { index, 0 })
      return
    end
  end
  error("missing netrw line " .. pattern)
end

move_to("folder/")
local folder = manager.current()
equal("netrw", folder.name, "netrw detected")
equal("folder", folder.entry.name, "directory name normalized")
equal("directory", folder.entry.type, "directory metadata")

move_to("item.txt")
local file = manager.current()
equal("file", file.entry.type, "file metadata")
equal(8, file.entry.size, "file size")
vim.fn.matchadd("netrwMarkFile", "item\\.txt")
equal(true, manager.current().entry.marked, "netrw marked metadata")

move_to("link@")
equal("symbolicLink", manager.current().entry.type, "link metadata")

vim.cmd("enew")
manager.register("test-manager", function() return true end, function()
  return { root = "/virtual", entry = { name = "node", type = "dir", expanded = true } }
end)
local adapted = manager.current()
equal("test-manager", adapted.name, "adapter manager name")
equal("directory", adapted.entry.type, "adapter type normalized")
equal(true, adapted.entry.expanded, "adapter expansion state")
manager.unregister("test-manager")

vim.bo.filetype = "oil"
package.loaded.oil = {
  get_current_dir = function() return "/oil-root" end,
  get_cursor_entry = function() return { name = "archive.zip", type = "file" } end,
}
equal("file", manager.current().entry.type, "oil public API")
package.loaded.oil = nil

vim.bo.filetype = "NvimTree"
local built_in_long_root = "/" .. string.rep("r", 2046) .. "ä" .. "x"
local marked_node = {
  name = "source", absolute_path = built_in_long_root .. "/source",
  type = "directory", open = true,
}
package.loaded["nvim-tree.api"] = {
  tree = { get_node_under_cursor = function() return marked_node end },
  marks = { get = function(node) return node == marked_node and node or nil end },
}
local nvim_tree = manager.current()
equal("directory", nvim_tree.entry.type, "nvim-tree public API")
equal(true, nvim_tree.entry.expanded, "nvim-tree expanded directory")
equal(true, nvim_tree.entry.marked, "nvim-tree public bookmark API")
equal("/" .. string.rep("r", 2046), nvim_tree.root, "nvim-tree root normalized centrally")
package.loaded["nvim-tree.api"] = nil

vim.bo.filetype = "neo-tree"
package.loaded["neo-tree.sources.manager"] = { get_state_for_window = function()
  local node = {
    id = "/neo/link", name = "link", path = "/neo/link", type = "file", is_link = true,
  }
  return { path = built_in_long_root, clipboard = { ["/neo/link"] = { action = "copy" } },
    tree = { get_node = function() return node end } }
end }
local neo_tree = manager.current()
equal("symbolicLink", neo_tree.entry.type, "neo-tree public state")
equal(true, neo_tree.entry.marked, "neo-tree clipboard metadata")
equal("/" .. string.rep("r", 2046), neo_tree.root, "neo-tree root normalized centrally")
package.loaded["neo-tree.sources.manager"] = nil

vim.bo.filetype = "minifiles"
_G.MiniFiles = {
  get_fs_entry = function() return { name = "docs", path = "/mini/docs", fs_type = "directory" } end,
  get_explorer_state = function() return { branch = { "/mini" }, depth_focus = 1 } end,
}
equal("directory", manager.current().entry.type, "mini.files public API")
_G.MiniFiles = nil

vim.bo.filetype = ""
local long_name = string.rep("a", 510) .. "ä" .. "x"
local split_name = string.rep("b", 511) .. "ä"
local wide_name = string.rep("w", 509) .. "界" .. "x"
local emoji_name = string.rep("c", 508) .. "😀" .. "x"
local long_path = "/" .. string.rep("d", 2046) .. "ä" .. "x"
manager.register("unicode-boundaries", function() return true end, function()
  return {
    root = long_path,
    entry = { name = long_name, path = long_path, type = "file" },
  }
end)
local unicode = manager.current()
equal(string.rep("a", 510) .. "ä", unicode.entry.name, "UTF-8 name kept at byte boundary")
equal("/" .. string.rep("d", 2046), unicode.root, "UTF-8 root not split")
equal("/" .. string.rep("d", 2046), unicode.entry.path, "UTF-8 path not split")
manager.unregister("unicode-boundaries")

manager.register("split-boundary", function() return true end, function()
  return { entry = { name = split_name, type = "file" } }
end)
equal(string.rep("b", 511), manager.current().entry.name, "split codepoint omitted")
manager.unregister("split-boundary")

manager.register("wide-boundary", function() return true end, function()
  return { entry = { name = wide_name, type = "file" } }
end)
equal(string.rep("w", 509) .. "界", manager.current().entry.name, "wide character kept intact")
manager.unregister("wide-boundary")

manager.register("emoji-boundary", function() return true end, function()
  return { entry = { name = emoji_name, type = "file" } }
end)
equal(string.rep("c", 508) .. "😀", manager.current().entry.name, "emoji kept intact")
manager.unregister("emoji-boundary")

manager.register("invalid-path", function() return true end, function()
  return { entry = { name = "node", path = "/bad" .. string.char(0xff), type = "file" } }
end)
equal("", manager.current().entry.path, "invalid UTF-8 field discarded")
manager.unregister("invalid-path")

manager.register("invalid-utf8", function() return true end, function()
  return { entry = { name = "node" .. string.char(0xff), type = "file" } }
end)
equal(nil, manager.current().entry, "invalid UTF-8 entry discarded")
manager.unregister("invalid-utf8")

vim.fn.delete(directory, "rf")
print(string.format("file manager tests: %d assertions passed", assertions))
vim.cmd("qa!")
