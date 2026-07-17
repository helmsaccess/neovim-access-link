local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local manager = require("nvim_nvda.file_manager")
local events = require("nvim_nvda.file_manager_events")
local prompt = require("nvim_nvda.file_manager_prompt")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

-- The narrow Oil fallback accepts only its fixed action grammar. Typical
-- programming and writing names may contain spaces, Unicode and punctuation,
-- but none of those names or their parent paths may enter the prompt payload.
local oil_cases = {
  { "CREATE /private/project/src/new module.lua", "create" },
  { "CHANGE /private/project/README.md", "change" },
  { "COPY /private/manuscript/Chapter 1 – Draft.md -> /private/manuscript/Chapter 1 – Copy.md",
    "copy or duplicate" },
  { "MOVE /private/project/old name.lua -> /private/project/new name.lua", "rename or move" },
  { "DELETE /private/manuscript/Discarded scene.md", "delete" },
  { "TRASH /private/manuscript/Archive/old.md", "move to trash" },
  { "RESTORE /private/manuscript/Archive/old.md", "restore" },
  { "PURGE /private/manuscript/Archive/old.md", "permanently delete" },
}
for index, specification in ipairs(oil_cases) do
  local value = prompt.oil_confirmation({ "  " .. specification[1] })
  equal("Oil confirmation, " .. specification[2] .. " 1 item. Y yes, N no", value.prompt,
    "Oil workflow action " .. index)
  equal(nil, value.prompt:find("private", 1, true), "Oil workflow path omitted " .. index)
end
local too_many = {}
for index = 1, 201 do too_many[index] = "DELETE /private/item-" .. index end
local bounded_many = prompt.oil_confirmation(too_many)
equal("Oil confirmation, delete 200 items. Y yes, N no", bounded_many.prompt,
  "Oil oversized action list is bounded")
equal(nil, bounded_many.prompt:find("private", 1, true), "Oil oversized paths remain omitted")
equal(nil, prompt.oil_confirmation({ "delete /private/lowercase-is-not-oil-rendering" }),
  "Oil lowercase lookalike fails open")
equal(nil, prompt.oil_confirmation({ "note DELETE /private/not-at-line-start" }),
  "Oil embedded action word fails open")

vim.cmd("enew")
vim.bo.filetype = ""
local active_manager = "workflow"
local entry_state = {
  name = "Chapter 1 – Einführung.md", path = "/private/Book/Chapter 1 – Einführung.md",
  type = "file", selectionState = "unmarked", clipboardState = "none",
}
manager.register("workflow", function() return true end, function()
  return {
    name = active_manager, root = "/private/Book", currentDirectory = "/private/Book",
    entry = entry_state,
  }
end)

local nvim_tree_callbacks = {}
package.loaded["nvim-tree.api"] = {
  events = {
    Event = {
      TreeRendered = "TreeRendered", NodeRenamed = "NodeRenamed",
      FileCreated = "FileCreated", FileRemoved = "FileRemoved",
      FolderCreated = "FolderCreated", FolderRemoved = "FolderRemoved",
    },
    subscribe = function(name, callback) nvim_tree_callbacks[name] = callback end,
  },
}
local neo_tree_callbacks = {}
package.loaded["neo-tree.events"] = {
  AFTER_RENDER = "after_render",
  NEO_TREE_CLIPBOARD_CHANGED = "clipboard_changed",
  FILE_ADDED = "file_added", FILE_DELETED = "file_deleted",
  FILE_MOVED = "file_moved", FILE_RENAMED = "file_renamed",
  FILE_RESTORED = "file_restored",
  unsubscribe = function(handler) neo_tree_callbacks[handler.event] = nil end,
  subscribe = function(handler) neo_tree_callbacks[handler.event] = handler.handler end,
}

local state_publications = {}
local actions = {}
local group = vim.api.nvim_create_augroup("NvimNvdaFileManagerWorkflows", { clear = true })
events.setup(
  function(reason) table.insert(state_publications, reason) end,
  function(action) table.insert(actions, action) end,
  group
)
events.observe(manager.current())

local function wait_for_state(count)
  assert(vim.wait(250, function() return #state_publications >= count end), "missing state event")
end
local function wait_for_action(count)
  assert(vim.wait(250, function() return #actions >= count end), "missing action event")
end
local function expect_action(trigger, expected, label)
  local count = #actions + 1
  trigger()
  wait_for_action(count)
  local actual = actions[count]
  for key, value in pairs(expected) do equal(value, actual[key], label .. " " .. key) end
  equal(nil, tostring(vim.inspect(actual)):find("/private/", 1, true), label .. " full path omitted")
end

-- Same-entry changes cover multi-selection, copy/cut preparation and tree
-- expansion without relying on cursor movement or periodic refreshes.
entry_state.selectionState = "marked"
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
wait_for_state(1)
entry_state.selectionState = "unmarked"
entry_state.clipboardState = "copied"
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
wait_for_state(2)
entry_state.clipboardState = "cut"
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
wait_for_state(3)
entry_state.clipboardState = "none"
entry_state.type = "directory"
entry_state.expanded = false
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
wait_for_state(4)
entry_state.expanded = true
vim.api.nvim_exec_autocmds("User", { pattern = "MiniFilesBufferUpdate", modeline = false })
wait_for_state(5)
equal(5, #state_publications, "workflow state changes are event-driven and deduplicated")

-- mini.files publishes successful filesystem actions after its shared
-- Yes/No/Cancel synchronization prompt. Exercise every official action.
active_manager = "mini.files"
local mini_cases = {
  { "Create", { action = "create", from = nil, to = "/private/Book/New chapter.md" },
    { action = "create", result = "success", name = "New chapter.md" } },
  { "Rename", { action = "rename", from = "/private/Book/old.md", to = "/private/Book/new.md" },
    { action = "rename", result = "success", name = "new.md" } },
  { "Copy", { action = "copy", from = "/private/Book/template.md", to = "/private/Book/template copy.md" },
    { action = "copy", result = "success", name = "template copy.md" } },
  { "Move", { action = "move", from = "/private/Book/draft.md", to = "/private/Book/Archive/draft.md" },
    { action = "move", result = "success", name = "draft.md" } },
  { "Delete", { action = "delete", from = "/private/Book/discard.md", to = nil },
    { action = "delete", result = "success", name = "discard.md" } },
}
for _, specification in ipairs(mini_cases) do
  expect_action(function()
    vim.api.nvim_exec_autocmds("User", {
      pattern = "MiniFilesAction" .. specification[1], modeline = false,
      data = specification[2],
    })
  end, specification[3], "mini.files " .. specification[1])
end

-- nvim-tree exposes create/remove/rename completion events. Directory actions
-- retain their semantic type after normalization.
vim.api.nvim_exec_autocmds("FileType", { pattern = "NvimTree", modeline = false })
active_manager = "nvim-tree"
local nvim_tree_cases = {
  { "FileCreated", { fname = "/private/Code/new.lua" },
    { action = "create", name = "new.lua", entryType = "file" } },
  { "FolderCreated", { folder_name = "/private/Code/new module" },
    { action = "create", name = "new module", entryType = "directory" } },
  { "NodeRenamed", { old_name = "/private/Code/old.lua", new_name = "/private/Code/new.lua" },
    { action = "rename", name = "new.lua" } },
  { "FileRemoved", { fname = "/private/Code/dead.lua" },
    { action = "delete", name = "dead.lua", entryType = "file" } },
  { "FolderRemoved", { folder_name = "/private/Code/old module" },
    { action = "delete", name = "old module", entryType = "directory" } },
}
for _, specification in ipairs(nvim_tree_cases) do
  expect_action(function() nvim_tree_callbacks[specification[1]](specification[2]) end,
    vim.tbl_extend("force", { result = "success" }, specification[3]),
    "nvim-tree " .. specification[1])
end

-- Neo-tree exposes add/delete/move/rename/restore after completion. Its
-- clipboard event is already covered above through the common state contract.
vim.api.nvim_exec_autocmds("FileType", { pattern = "neo-tree", modeline = false })
active_manager = "neo-tree"
local neo_cases = {
  { "file_added", "/private/Code/added.lua", { action = "add", name = "added.lua" } },
  { "file_deleted", "/private/Book/deleted scene.md", { action = "delete", name = "deleted scene.md" } },
  { "file_moved", { destination = "/private/Book/Archive/moved.md" },
    { action = "move", name = "moved.md" } },
  { "file_renamed", { destination = "/private/Book/renamed.md" },
    { action = "rename", name = "renamed.md" } },
  { "file_restored", "/private/Book/restored.md", { action = "restore", name = "restored.md" } },
}
for _, specification in ipairs(neo_cases) do
  expect_action(function() neo_tree_callbacks[specification[1]](specification[2]) end,
    vim.tbl_extend("force", { result = "success" }, specification[3]),
    "neo-tree " .. specification[1])
end

-- Oil reports the complete action set in one post-action event, including
-- typed failure/cancellation. Mixed batches become one privacy-safe summary.
active_manager = "oil"
local oil_action_cases = {
  { { type = "create", dest_url = "oil:///private/Code/new.lua", entry_type = "file" },
    { action = "create", result = "success", name = "new.lua", entryType = "file" } },
  { { type = "copy", dest_url = "oil:///private/Book/Chapter copy.md", entry_type = "file" },
    { action = "copy", result = "success", name = "Chapter copy.md" } },
  { { type = "move", dest_url = "oil:///private/Book/Archive/Chapter.md", entry_type = "file" },
    { action = "move", result = "success", name = "Chapter.md" } },
  { { type = "change", url = "oil:///private/Book/Chapter.md", entry_type = "file" },
    { action = "change", result = "success", name = "Chapter.md" } },
  { { type = "delete", url = "oil:///private/Book/discard.md", entry_type = "file" },
    { action = "delete", result = "success", name = "discard.md" } },
}
for index, specification in ipairs(oil_action_cases) do
  expect_action(function()
    vim.api.nvim_exec_autocmds("User", {
      pattern = "OilActionsPost", modeline = false, data = { actions = { specification[1] } },
    })
  end, specification[2], "Oil action " .. index)
end
expect_action(function()
  vim.api.nvim_exec_autocmds("User", {
    pattern = "OilActionsPost", modeline = false,
    data = { err = "operation cancelled", actions = {
      { type = "delete", url = "oil:///private/Book/keep.md", entry_type = "file" },
    } },
  })
end, { action = "delete", result = "cancelled", name = "keep.md" }, "Oil cancellation")
expect_action(function()
  vim.api.nvim_exec_autocmds("User", {
    pattern = "OilActionsPost", modeline = false,
    data = { err = "permission denied", actions = {
      { type = "move", dest_url = "oil:///private/Book/blocked.md", entry_type = "file" },
    } },
  })
end, { action = "move", result = "failed", name = "blocked.md" }, "Oil failure")
expect_action(function()
  vim.api.nvim_exec_autocmds("User", {
    pattern = "OilActionsPost", modeline = false, data = { actions = {
      { type = "copy", dest_url = "oil:///private/Book/a-copy.md", entry_type = "file" },
      { type = "create", dest_url = "oil:///private/Book/new.md", entry_type = "file" },
    } },
  })
end, { action = "multiple", result = "success", count = 2, name = nil }, "Oil mixed batch")

package.loaded["nvim-tree.api"] = nil
package.loaded["neo-tree.events"] = nil
manager.unregister("workflow")
vim.api.nvim_del_augroup_by_id(group)
print(string.format("file manager workflow tests: %d assertions passed", assertions))
vim.cmd("qa!")
