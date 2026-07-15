local root = vim.fn.getcwd()
if vim.loader and vim.loader.enable then vim.loader.enable(false) end
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
assert(package.searchpath("nvim_nvda.session", package.path) == root .. "/neovim-plugin/lua/nvim_nvda/session.lua", "test checkout is first on package.path")

local function truth(value, label)
  assert(value, label)
end

pcall(function() require("nvim_nvda.session").stop() end)
vim.g.loaded_nvim_nvda_access = nil
for name in pairs(package.loaded) do
  if name == "nvim_nvda" or name:match("^nvim_nvda%.") then package.loaded[name] = nil end
end
package.loaded["nvim_nvda"] = nil
package.loaded["nvim_nvda.session"] = dofile(root .. "/neovim-plugin/lua/nvim_nvda/session.lua")
local session = package.loaded["nvim_nvda.session"]
local component_config = dofile(root .. "/neovim-plugin/lua/nvim_nvda/component_config.lua")
local configured = component_config.load(root .. "/neovim-plugin/config/linux-components.json")
truth(configured.sessionClaim.neovimKey == "<F12>", "packaged claim key is loaded")
local invalid_config = vim.fn.tempname()
vim.fn.writefile({ '{"format":1,"sessionClaim":{"neovimKey":"<F9>","nvdaGesture":"kb:f9"}}' }, invalid_config)
truth(component_config.load(invalid_config).sessionClaim.neovimKey == "<F9>", "matching alternate key is loaded")
vim.fn.writefile({ '{"format":1,"sessionClaim":{"neovimKey":"<F9>","nvdaGesture":"kb:f12"}}' }, invalid_config)
truth(component_config.load(invalid_config).sessionClaim.neovimKey == "<F12>", "mismatched gestures fail safe")
vim.fn.delete(invalid_config)
vim.env.NVIM_NVDA_SESSION_NAME = "Documentation"
local claim_on_key
local original_on_key = vim.on_key
vim.on_key = function(callback, namespace)
  claim_on_key = callback
  return original_on_key(callback, namespace)
end
dofile(root .. "/neovim-plugin/plugin/nvim_nvda.lua")
vim.on_key = original_on_key
local mapping = vim.fn.maparg("<F12>", "n", false, true)
truth(type(mapping) == "table" and next(mapping) == nil, "F12 remains unbound for direct terminal delivery")
truth(type(claim_on_key) == "function", "typed-key observer is registered")

local runtime = vim.env.XDG_RUNTIME_DIR
if not runtime or runtime == "" then runtime = "/tmp/nvim-nvda-" .. tostring(vim.fn.getuid()) end
local registry = runtime .. "/nvim-nvda/sessions/" .. tostring(vim.fn.getpid()) .. ".json"
local value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
truth(value.version == 2, "current registry schema")
truth(value.pid == vim.fn.getpid(), "registry identifies this process")
truth(type(value.startedMonotonic) == "number" and value.startedMonotonic > 0, "start timestamp recorded")
truth(type(value.startedUnix) == "number" and value.startedUnix > 0, "wall clock start time recorded")
truth(value.name == "Documentation", "environment session name recorded")
truth(value.claimedMonotonic == 0, "registry starts unclaimed")
truth(value.claimSequence == 0, "registry claim sequence starts at zero")

local notifications = 0
local original_notify = vim.notify
vim.notify = function() notifications = notifications + 1 end
local f12 = vim.api.nvim_replace_termcodes("<F12>", true, false, true)
claim_on_key(f12, f12)
value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
truth(value.claimSequence == 0, "on_key defers registry writes")
truth(vim.wait(1000, function()
  local current = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
  return current.claimSequence == 1
end, 10), "scheduled typed F12 claim completes")
vim.notify = original_notify
value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
truth(type(value.claimedMonotonic) == "number" and value.claimedMonotonic > 0, "claim timestamp recorded")
truth(value.claimSequence == 1, "first claim increments sequence")
session.claim()
value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
truth(value.claimSequence == 2, "repeated claim increments sequence again")
truth(notifications == 0, "F12 claim is silent in the terminal")

vim.cmd("NvimNvdaSessionName Programming")
value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
truth(value.name == "Programming", "session name can be changed at runtime")

print("session registry tests: 19 assertions passed")
vim.cmd("qa!")
