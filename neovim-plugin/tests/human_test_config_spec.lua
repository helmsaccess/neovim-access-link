local root = vim.fn.getcwd()
vim.fn.setenv("ACCESS_LINK_HUMAN_PROFILE", "diagnostics")
vim.fn.setenv("ACCESS_LINK_HUMAN_DRY_RUN", "1")

dofile(root .. "/tests/human/framework/init.lua")

local assertions = 0
local function truthy(value, label)
  assertions = assertions + 1
  assert(value, label)
end

truthy(vim.fn.exists(":AccessLinkHumanTestInfo") == 2,
  "human-test info command is available")
truthy(vim.g.access_link_human_config_ready == 1,
  "dry-run configuration reports successful completion")
for _, key in ipairs({ "<F1>", "<F2>", "<F3>", "<F5>", "<F6>", "<F7>", "<F8>",
    "<F9>", "<F10>" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and mapping.desc ~= nil,
    "normal-mode mapping missing for " .. key)
end
local insert_f2 = vim.fn.maparg("<F2>", "i", false, true)
truthy(type(insert_f2) == "table" and insert_f2.desc ~= nil,
  "insert-mode task reminder is available")
truthy(vim.o.shiftwidth == 2 and vim.o.tabstop == 2 and vim.o.expandtab,
  "isolated editing defaults are deterministic")

print(string.format("human-test config specs passed: %d assertions", assertions))
vim.cmd("qa!")
