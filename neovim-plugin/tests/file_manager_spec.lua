local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local manager = require("nvim_nvda.file_manager")
local manager_prompt = require("nvim_nvda.file_manager_prompt")

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
vim.fn.writefile({ "space" }, directory .. "/name with spaces.txt")
vim.fn.writefile({ "double" }, directory .. "/two  spaces.txt")
vim.fn.writefile({ "tab" }, directory .. "/tab\tname.txt")
vim.fn.writefile({ "unicode" }, directory .. "/Grüße.txt")
vim.fn.writefile({ "wide" }, directory .. "/second with spaces.txt")
vim.fn.system({ "ln", "-s", "item.txt", directory .. "/link" })
vim.fn.system({ "ln", "-s", "item.txt", directory .. "/link with spaces" })
vim.cmd("Explore " .. vim.fn.fnameescape(directory))

local oil_prompt = manager_prompt.oil_confirmation({
  "DELETE /private/project/secret.txt",
  "DELETE /private/project/other.txt",
  "",
})
equal("confirm", oil_prompt.promptKind, "Oil fallback prompt kind")
equal("delete", oil_prompt.promptClass, "Oil fallback fixed class")
equal("Oil confirmation, delete 2 items. Y yes, N no", oil_prompt.prompt,
  "Oil fallback omits names and paths")
equal(2, oil_prompt.itemCount, "Oil fallback exposes fixed choices")
equal(nil, manager_prompt.oil_confirmation({ "unrecognized private rendering" }),
  "unknown Oil rendering fails open")
local mixed_oil_prompt = manager_prompt.oil_confirmation({
  "MOVE /private/a /private/b", "CREATE /private/c",
})
equal("Oil confirmation, 2 file actions. Y yes, N no", mixed_oil_prompt.prompt,
  "mixed Oil fallback remains compact")

local lines
local function refresh_lines()
  lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
end
local function move_to(pattern, at_match)
  for index, line in ipairs(lines) do
    local column = line:find(pattern, 1, true)
    if column then
      vim.api.nvim_win_set_cursor(0, { index, at_match and column - 1 or 0 })
      return
    end
  end
  error("missing netrw line " .. pattern)
end
local function reopen_netrw(style)
  vim.cmd("bwipeout!")
  vim.g.netrw_liststyle = style
  vim.w.netrw_liststyle = style
  vim.cmd("Explore " .. vim.fn.fnameescape(directory))
  refresh_lines()
end
refresh_lines()

move_to("folder/")
local folder = manager.current()
equal("netrw", folder.name, "netrw detected")
equal(directory, folder.root, "netrw displayed root")
equal(directory, folder.currentDirectory, "netrw current directory")
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

move_to("name with spaces.txt")
equal("name with spaces.txt", manager.current().entry.name, "thin-list spaces preserved")
move_to("tab\tname.txt")
equal("tab\tname.txt", manager.current().entry.name, "thin-list tab preserved")
move_to("Grüße.txt")
equal("Grüße.txt", manager.current().entry.name, "thin-list Unicode preserved")
move_to("link with spaces@")
equal("link with spaces", manager.current().entry.name, "symlink target decoration removed")
equal("symbolicLink", manager.current().entry.type, "spaced symlink metadata")

reopen_netrw(1)
move_to("two  spaces.txt")
equal("two  spaces.txt", manager.current().entry.name, "long-list repeated spaces preserved")
move_to("name with spaces.txt")
equal("name with spaces.txt", manager.current().entry.name, "long-list metadata removed")

vim.bo.modifiable = true
vim.bo.readonly = false
vim.api.nvim_buf_set_lines(0, 0, -1, false, {
  "alpha.txt" .. string.rep(" ", 15) .. "second with spaces.txt",
})
vim.w.netrw_liststyle = 2
vim.w.netrw_bannercnt = 1
vim.b.netrw_cpf = 24
refresh_lines()
move_to("second with spaces.txt", true)
equal("second with spaces.txt", manager.current().entry.name, "wide-list cursor column selected")

reopen_netrw(3)
move_to("| name with spaces.txt")
equal("name with spaces.txt", manager.current().entry.name, "tree depth removed")
move_to(vim.fn.fnamemodify(directory, ":t") .. "/")
equal(directory, manager.current().entry.path, "tree root path is not duplicated")
vim.api.nvim_win_set_cursor(0, { 1, 0 })
equal(nil, manager.current().entry, "netrw banner has no semantic entry")

vim.cmd("enew")
manager.register("test-manager", function() return true end, function()
  return { root = "/virtual", entry = { name = "node", type = "dir", expanded = true } }
end)
local adapted = manager.current()
equal("test-manager", adapted.name, "adapter manager name")
equal("directory", adapted.entry.type, "adapter type normalized")
equal(true, adapted.entry.expanded, "adapter expansion state")
manager.unregister("test-manager")

local valid_name, invalid_name_error = pcall(
  manager.register, "bad" .. string.char(0xff), function() return true end, function() return {} end
)
equal(false, valid_name, "invalid UTF-8 adapter name rejected")
equal("string", type(invalid_name_error), "invalid adapter name has a bounded error")

local provider_calls = 0
manager.register("failing-manager", function() return true end, function()
  provider_calls = provider_calls + 1
  error("private provider failure")
end)
for _ = 1, 4 do
  equal("failing-manager", manager.current().name, "failing adapter remains fail-open")
end
equal(3, provider_calls, "repeated provider failures enter cooldown")
local failing_diagnostics
for _, value in ipairs(manager.diagnostics()) do
  if value.name == "failing-manager" then failing_diagnostics = value end
end
equal(3, failing_diagnostics.failureCount, "provider failures counted without error text")
equal(1, failing_diagnostics.cooldownCount, "provider cooldown counted")
equal(1, failing_diagnostics.disabledBuffers, "provider cooldown is buffer-local")
equal("providerError", failing_diagnostics.lastIssue, "provider diagnostic is fixed")
manager.forget_buffer(vim.api.nvim_get_current_buf())
for _, value in ipairs(manager.diagnostics()) do
  if value.name == "failing-manager" then failing_diagnostics = value end
end
equal(0, failing_diagnostics.disabledBuffers, "wiped buffer runtime is released")
manager.unregister("failing-manager")

vim.bo.filetype = "oil"
package.loaded.oil = {
  get_current_dir = function() return "/oil-root" end,
  get_cursor_entry = function() return { name = "archive.zip", type = "file" } end,
}
equal("file", manager.current().entry.type, "oil public API")
equal("/oil-root", manager.current().currentDirectory, "oil current directory")
local detector_calls = 0
manager.register("unrelated-manager", function()
  detector_calls = detector_calls + 1
  return true
end, function() return { entry = { name = "wrong" } } end)
equal("oil", manager.current().name, "built-in selected directly by filetype")
equal(0, detector_calls, "external detectors skipped for built-in filetype")
manager.unregister("unrelated-manager")
package.loaded.oil = nil

vim.bo.filetype = "NvimTree"
local built_in_long_root = "/" .. string.rep("r", 2046) .. "ä" .. "x"
local nvim_tree_root = { absolute_path = built_in_long_root, type = "directory" }
local marked_node = {
  name = "source", absolute_path = built_in_long_root .. "/source",
  type = "directory", open = true, parent = nvim_tree_root,
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
equal("/" .. string.rep("r", 2046), neo_tree.currentDirectory,
  "neo-tree current directory normalized centrally")
package.loaded["neo-tree.sources.manager"] = nil

vim.bo.filetype = "minifiles"
_G.MiniFiles = {
  get_fs_entry = function() return { name = "docs", path = "/mini/docs", fs_type = "directory" } end,
  get_explorer_state = function() return {
    branch = { "/mini-root", "/mini" }, depth_focus = 2,
  } end,
}
local mini_files = manager.current()
equal("directory", mini_files.entry.type, "mini.files public API")
equal("/mini-root", mini_files.root, "mini.files branch root")
equal("/mini", mini_files.currentDirectory, "mini.files focused directory")
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
