local root = vim.fn.getcwd()
if vim.loader and vim.loader.enable then vim.loader.enable(false) end
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
assert(package.searchpath("nvim_nvda.session", package.path) == root .. "/neovim-plugin/lua/nvim_nvda/session.lua",
  "test checkout is first on package.path")

local function truth(value, label)
  assert(value, label)
end

local temporary = vim.fn.tempname()
vim.fn.mkdir(temporary, "p")
vim.env.LOCALAPPDATA = temporary
vim.env.NVIM_NVDA_TEST_WINDOWS = "1"
package.loaded["nvim_nvda.session"] = nil
local session = dofile(root .. "/neovim-plugin/lua/nvim_nvda/session.lua")
local address = session.start()
local registry_matches = vim.fn.glob(
  temporary .. "/nvim-nvda/sessions/" .. tostring(vim.fn.getpid()) .. "-*.json", false, true)
truth(#registry_matches == 1, "one nonce-qualified local registry file created")
local registry = registry_matches[1]
truth(vim.fn.filereadable(registry) == 1,
  "local registry is created: " .. vim.inspect(vim.fn.glob(temporary .. "/**/*", true, true)))
local value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))

truth(address:match("^127%.0%.0%.1:%d+$") ~= nil, "local Windows endpoint uses IPv4 loopback")
truth(value.transportKind == "localWindowsTcp", "local connection kind is registered")
truth(value.host == "127.0.0.1", "registry host is exact loopback")
truth(type(value.port) == "number" and value.port >= 1 and value.port <= 65535,
  "registry contains the allocated port")
truth(value.socket == address, "registry address matches the Neovim server")
truth(value.version == 3, "local registry uses current schema")
truth(type(value.sessionNonce) == "string" and #value.sessionNonce == 32,
  "local registry records a session nonce")
truth(value.ownsSocket == true, "local plugin owns its loopback endpoint")

session.claim()
value = vim.json.decode(table.concat(vim.fn.readfile(registry), "\n"))
truth(type(value.claimedMonotonic) == "number" and value.claimedMonotonic > 0,
  "local claim is persisted")
truth(value.claimSequence == 1, "local claim sequence increments")

session.stop()
truth(vim.fn.filereadable(registry) == 0, "local registry is removed on stop")
vim.fn.delete(temporary, "rf")
print("local Windows session tests: registry lifecycle assertions passed")
vim.cmd("qa!")
