local mode, lazy_source, plugin_root, sandbox = arg[1], arg[2], arg[3], arg[4]
assert(mode == "install" or mode == "update" or mode == "sync")
assert(lazy_source and plugin_root and sandbox)

local function run(arguments)
  local result = vim.system(arguments, { text = true }):wait(30000)
  assert(result.code == 0,
    table.concat(arguments, " ") .. ": " .. (result.stderr or ""))
  return vim.trim(result.stdout or "")
end

vim.fn.delete(sandbox, "rf")
local source = vim.fs.joinpath(sandbox, "source")
local remote_root = vim.fs.joinpath(sandbox, "origins")
local plugins = vim.fs.joinpath(sandbox, "plugins")
vim.fn.mkdir(vim.fs.joinpath(source, "plugin"), "p")
vim.fn.mkdir(remote_root, "p")
vim.fn.mkdir(plugins, "p")
run({ "git", "init", "--initial-branch=main", source })
local fixture_file = vim.fs.joinpath(source, "plugin", "access_link_lazy_fixture.lua")
vim.fn.writefile({ 'vim.g.access_link_lazy_fixture_version = "A"' }, fixture_file)
run({ "git", "-C", source, "add", "plugin/access_link_lazy_fixture.lua" })
run({ "git", "-C", source, "-c", "user.name=Access Link Test",
  "-c", "user.email=human-test.invalid", "commit", "-m", "Fixture A" })
local revision_a = run({ "git", "-C", source, "rev-parse", "HEAD" })
vim.fn.writefile({ 'vim.g.access_link_lazy_fixture_version = "B"' }, fixture_file)
run({ "git", "-C", source, "add", "plugin/access_link_lazy_fixture.lua" })
run({ "git", "-C", source, "-c", "user.name=Access Link Test",
  "-c", "user.email=human-test.invalid", "commit", "-m", "Fixture B" })
local revision_b = run({ "git", "-C", source, "rev-parse", "HEAD" })

local function remote(name)
  return vim.fs.joinpath(remote_root, name .. ".git")
end

local function make_remote(name)
  run({ "git", "clone", "--bare", source, remote(name) })
end

local function clone(name, revision)
  local destination = vim.fs.joinpath(plugins, name)
  run({ "git", "clone", remote(name), destination })
  if revision then
    run({ "git", "-C", destination, "checkout", "--detach", revision })
  end
  return destination
end

local specifications
if mode == "install" then
  make_remote("access-link-install-target")
  specifications = {
    { url = remote("access-link-install-target"), name = "access-link-install-target" },
  }
elseif mode == "update" then
  make_remote("access-link-update-target")
  clone("access-link-update-target", revision_a)
  specifications = {
    { url = remote("access-link-update-target"), name = "access-link-update-target" },
  }
else
  for _, name in ipairs({
    "access-link-install-target", "access-link-update-target", "access-link-stale-target",
  }) do
    make_remote(name)
  end
  clone("access-link-update-target", revision_a)
  clone("access-link-stale-target")
  specifications = {
    { url = remote("access-link-install-target"), name = "access-link-install-target" },
    { url = remote("access-link-update-target"), name = "access-link-update-target" },
  }
end

vim.opt.runtimepath:prepend(lazy_source)
vim.go.loadplugins = true
package.path = vim.fs.joinpath(plugin_root, "lua", "?.lua") .. ";"
  .. vim.fs.joinpath(plugin_root, "lua", "?", "init.lua") .. ";" .. package.path
local semantic = {}
local group = vim.api.nvim_create_augroup("AccessLinkLazyOperationProbe", { clear = true })
require("nvim_nvda.plugin_manager").setup(function(event_type, reason, payload)
  semantic[#semantic + 1] = {
    event_type = event_type,
    reason = reason,
    operation = payload.pluginManagerOperation,
    phase = payload.pluginManagerPhase,
  }
end, group)

local finished = false
vim.api.nvim_create_autocmd("User", {
  group = group,
  pattern = "Lazy" .. mode:sub(1, 1):upper() .. mode:sub(2),
  callback = function() finished = true end,
})
require("lazy").setup(specifications, {
  root = plugins,
  lockfile = vim.fs.joinpath(sandbox, "lazy-lock.json"),
  install = { missing = false },
  checker = { enabled = false },
  change_detection = { enabled = false, notify = false },
  readme = { enabled = false },
  rocks = { enabled = false },
})
vim.cmd("Lazy " .. mode)
assert(vim.wait(60000, function() return finished end, 20),
  "public Lazy command did not finish")

assert(#semantic == 2, "operation did not collapse to one semantic lifecycle pair")
assert(semantic[1].event_type == "pluginManagerOperation"
    and semantic[1].operation == mode and semantic[1].phase == "started")
assert(semantic[2].event_type == "pluginManagerOperation"
    and semantic[2].operation == mode and semantic[2].phase == "finished")
local expected_plugins = {}
for _, specification in ipairs(specifications) do
  expected_plugins[#expected_plugins + 1] = {
    name = specification.name,
    expectedRevision = revision_b,
  }
end
local fixture = {
  root = plugins,
  plugins = expected_plugins,
  absent = mode == "sync" and {
    vim.fs.joinpath(plugins, "access-link-stale-target"),
  } or vim.NIL,
}
local fixture_support = dofile(vim.fs.joinpath(
  vim.fs.dirname(plugin_root), "tests", "human", "framework", "lazy_fixture.lua"))
local verification_problems, verified_revisions, verified_absent =
  fixture_support.verify(fixture)
assert(#verification_problems == 0,
  "F5 fixture verification failed: " .. table.concat(verification_problems, ", "))
assert(#verified_revisions == #specifications,
  "F5 fixture verification omitted an expected Git revision")
assert(#verified_absent == (mode == "sync" and 1 or 0),
  "F5 fixture verification omitted an expected removal")
print(string.format("Lazy %s probe passed", mode))
