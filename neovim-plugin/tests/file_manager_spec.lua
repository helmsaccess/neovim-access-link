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
equal("marked", manager.current().entry.selectionState, "netrw mark semantics")

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
equal("marked", nvim_tree.entry.selectionState, "nvim-tree bookmark semantics")
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
equal("copied", neo_tree.entry.clipboardState, "neo-tree copy semantics")
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

local normalized_action = manager.normalize_action({
  manager = "tree", action = "copy", result = "success", count = 99999,
  name = "item.txt", entryType = "file",
})
equal("copy", normalized_action.action, "action allowlist accepts copy")
equal("success", normalized_action.result, "result allowlist accepts success")
equal(10000, normalized_action.count, "action count is bounded")
equal(nil, manager.normalize_action({
  manager = "tree", action = "execute", result = "success",
}), "unknown action rejected")
equal(nil, manager.normalize_action({
  manager = "tree", action = "copy", result = "maybe",
}), "unknown result rejected")
equal(nil, manager.normalize_action({
  manager = "tree" .. string.char(0xff), action = "copy", result = "success",
}), "invalid UTF-8 manager rejected")

local event_layer = require("nvim_nvda.file_manager_events")
local event_group = vim.api.nvim_create_augroup("NvimNvdaFileManagerSpec", { clear = true })
local event_state = {
  name = "event-manager", root = "/events",
  entry = {
    name = "same", path = "/events/same", type = "file",
    selectionState = "unmarked",
  },
}
manager.register("event-manager", function() return true end, function() return event_state end)
local publications = {}
local action_publications = {}
event_layer.setup(
  function(reason) table.insert(publications, reason) end,
  function(action) table.insert(action_publications, action) end,
  event_group
)
event_layer.observe(manager.current())

local function wait_for_publications(count)
  assert(vim.wait(200, function() return #publications == count end), "missing event publication")
end

local function wait_for_actions(count)
  assert(vim.wait(200, function() return #action_publications == count end), "missing action")
end

event_state.entry.selectionState = "marked"
vim.api.nvim_exec_autocmds("User", {
  pattern = "MiniFilesBufferUpdate", modeline = false,
  data = { buf_id = vim.api.nvim_get_current_buf() },
})
wait_for_publications(1)
equal("MiniFilesBufferUpdate", publications[1], "mini.files update published")

vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
vim.wait(20)
equal(1, #publications, "unchanged semantic state suppressed")

event_state.entry.selectionState = "unmarked"
event_state.name = "mini.files"
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
vim.api.nvim_exec_autocmds("User", {
  pattern = "MiniFilesActionRename", modeline = false,
  data = { action = "rename", from = "/private/old.txt", to = "/private/new.txt" },
})
vim.api.nvim_exec_autocmds("User", {
  pattern = "MiniFilesActionRename", modeline = false,
  data = { action = "rename", from = "/private/two.txt", to = "/private/second.txt" },
})
wait_for_publications(2)
equal(2, #publications, "rapid semantic updates coalesced")
wait_for_actions(1)
equal("rename", action_publications[1].action, "mini.files action type")
equal("success", action_publications[1].result, "mini.files action result")
equal(2, action_publications[1].count, "mini.files actions coalesced")
equal(nil, action_publications[1].name, "batch action omits private paths")

event_state.entry.selectionState = "marked"
vim.api.nvim_exec_autocmds("User", {
  pattern = "MiniFilesBufferUpdate", modeline = false,
  data = { buf_id = vim.api.nvim_get_current_buf() + 999 },
})
vim.wait(20)
equal(2, #publications, "inactive mini.files buffer ignored")

local nvim_tree_callbacks = {}
package.loaded["nvim-tree.api"] = {
  events = {
    Event = {
      TreeRendered = "TreeRendered", NodeRenamed = "NodeRenamed",
      FileCreated = "FileCreated", FileRemoved = "FileRemoved",
      FolderCreated = "FolderCreated", FolderRemoved = "FolderRemoved",
    },
    subscribe = function(event, callback) nvim_tree_callbacks[event] = callback end,
  },
}
vim.api.nvim_exec_autocmds("FileType", { pattern = "NvimTree", modeline = false })
equal("function", type(nvim_tree_callbacks.TreeRendered), "nvim-tree event subscribed")
equal("function", type(nvim_tree_callbacks.NodeRenamed), "nvim-tree action subscribed")
event_state.name = "nvim-tree"
nvim_tree_callbacks.TreeRendered({
  bufnr = vim.api.nvim_get_current_buf(), winnr = vim.api.nvim_get_current_win(),
})
wait_for_publications(3)
equal("NvimTreeTreeRendered", publications[3], "nvim-tree render published")
nvim_tree_callbacks.NodeRenamed({ old_name = "/private/old", new_name = "/private/new" })
wait_for_actions(2)
equal("rename", action_publications[2].action, "nvim-tree rename action")
equal("new", action_publications[2].name, "nvim-tree sends basename only")
package.loaded["nvim-tree.api"] = nil

local neo_tree_callbacks = {}
package.loaded["neo-tree.events"] = {
  AFTER_RENDER = "after_render",
  NEO_TREE_CLIPBOARD_CHANGED = "clipboard_changed",
  FILE_ADDED = "file_added",
  FILE_DELETED = "file_deleted",
  FILE_MOVED = "file_moved",
  FILE_RENAMED = "file_renamed",
  FILE_RESTORED = "file_restored",
  unsubscribe = function(handler) neo_tree_callbacks[handler.event] = nil end,
  subscribe = function(handler) neo_tree_callbacks[handler.event] = handler.handler end,
}
vim.api.nvim_exec_autocmds("FileType", { pattern = "neo-tree", modeline = false })
equal("function", type(neo_tree_callbacks.after_render), "neo-tree render subscribed")
equal("function", type(neo_tree_callbacks.clipboard_changed), "neo-tree clipboard subscribed")
equal("function", type(neo_tree_callbacks.file_moved), "neo-tree action subscribed")
event_state.name = "neo-tree"
event_state.entry.selectionState = "unmarked"
neo_tree_callbacks.after_render({
  bufnr = vim.api.nvim_get_current_buf(), winid = vim.api.nvim_get_current_win(),
})
wait_for_publications(4)
equal("NeoTreeAfterRender", publications[4], "neo-tree render published")
event_state.entry.clipboardState = "copied"
neo_tree_callbacks.clipboard_changed({ state = {
  bufnr = vim.api.nvim_get_current_buf(), winid = vim.api.nvim_get_current_win(),
} })
wait_for_publications(5)
equal("NeoTreeClipboardChanged", publications[5], "neo-tree clipboard published")
neo_tree_callbacks.file_moved({ source = "/private/from", destination = "/private/to" })
wait_for_actions(3)
equal("move", action_publications[3].action, "neo-tree move action")
equal("to", action_publications[3].name, "neo-tree sends basename only")

event_state.name = "oil"
vim.api.nvim_exec_autocmds("User", {
  pattern = "OilActionsPost", modeline = false,
  data = { actions = {
    { type = "copy", src_url = "oil:///private/a", dest_url = "oil:///private/a-copy" },
    { type = "copy", src_url = "oil:///private/b", dest_url = "oil:///private/b-copy" },
  } },
})
wait_for_actions(4)
equal("copy", action_publications[4].action, "Oil action type")
equal(2, action_publications[4].count, "Oil action count")
equal(nil, action_publications[4].name, "Oil batch omits private paths")
vim.api.nvim_exec_autocmds("User", {
  pattern = "OilActionsPost", modeline = false,
  data = { err = "operation failed", actions = {
    { type = "delete", url = "oil:///private/locked.txt", entry_type = "file" },
  } },
})
wait_for_actions(5)
equal("failed", action_publications[5].result, "Oil failure is typed")
equal("locked.txt", action_publications[5].name, "Oil failure sends basename only")

event_state.name = "neo-tree"
neo_tree_callbacks.file_deleted("/private/inactive.txt")
event_state.name = "event-manager"
vim.wait(20)
equal(5, #action_publications, "action dropped after manager focus changed")
package.loaded["neo-tree.events"] = nil
manager.unregister("event-manager")
vim.api.nvim_del_augroup_by_id(event_group)

vim.fn.delete(directory, "rf")
print(string.format("file manager tests: %d assertions passed", assertions))
vim.cmd("qa!")
