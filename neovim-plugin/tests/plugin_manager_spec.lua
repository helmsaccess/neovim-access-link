local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local plugin_manager = require("nvim_nvda.plugin_manager")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local events = {}
local group = vim.api.nvim_create_augroup("NvimNvdaPluginManagerTest", { clear = true })
plugin_manager.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end, group)

local function user(pattern)
  vim.api.nvim_exec_autocmds("User", { pattern = pattern, modeline = false })
end

user("LazyUpdatePre")
user("LazyUpdate")
equal(2, #events, "standalone lifecycle pair")
equal({ "pluginManagerOperation", "pluginManagerOperation" },
  { events[1].type, events[2].type }, "fixed event type")
equal({ "LazyUpdatePre", "LazyUpdate" }, { events[1].reason, events[2].reason },
  "official event names retained only as reasons")
equal({ "update", "started", "lazyNvim" }, {
  events[1].payload.pluginManagerOperation,
  events[1].payload.pluginManagerPhase,
  events[1].payload.pluginManagerKind,
}, "started payload is fixed")
equal({ "update", "finished" }, {
  events[2].payload.pluginManagerOperation,
  events[2].payload.pluginManagerPhase,
}, "finished payload is fixed")

events = {}
user("LazySyncPre")
user("LazyInstallPre")
user("LazyInstall")
user("LazyCleanPre")
user("LazyClean")
user("LazySync")
equal(2, #events, "sync collapses documented child operations")
equal({ "sync", "started", "sync", "finished" }, {
  events[1].payload.pluginManagerOperation,
  events[1].payload.pluginManagerPhase,
  events[2].payload.pluginManagerOperation,
  events[2].payload.pluginManagerPhase,
}, "sync pair remains neutral")

events = {}
user("LazyCheck")
user("UnrelatedPluginManagerEvent")
equal(0, #events, "unpaired and unrelated events fail open")

user("LazyLogPre")
user("LazyLogPre")
user("LazyLog")
equal(1, #events, "nested duplicate start is announced once")
user("LazyLog")
equal(2, #events, "nested duplicate finish is announced once")

local lazy_buffer = vim.api.nvim_create_buf(false, true)
vim.bo[lazy_buffer].buftype = "nofile"
vim.bo[lazy_buffer].filetype = "lazy"
vim.api.nvim_buf_set_lines(lazy_buffer, 0, -1, false, {
  "",
  "   lazy.nvim 󰒲   Install (I)   Update (U)   Sync (S)  ",
  "   Clean (X)   Check (C)   Log (L)   Restore (R)   Profile (P)  ",
  "   Debug (D)   Help (?) ",
  "",
  "  Total: 1 plugins",
})
equal(
  "lazy.nvim 󰒲   Install (I)   Update (U)   Sync (S) Clean (X)   Check (C)   "
    .. "Log (L)   Restore (R)   Profile (P) Debug (D)   Help (?)",
  plugin_manager.overview(lazy_buffer),
  "public Lazy header is joined across display-width wrapping"
)
vim.api.nvim_set_current_buf(lazy_buffer)
equal(
  plugin_manager.overview(lazy_buffer),
  require("nvim_nvda.state").snapshot("lazyOverviewTest").pluginManagerOverview,
  "canonical state carries the bounded Lazy overview"
)

local ordinary_buffer = vim.api.nvim_create_buf(false, true)
vim.api.nvim_buf_set_lines(ordinary_buffer, 0, -1, false, { "lazy.nvim Install (I)" })
equal(nil, plugin_manager.overview(ordinary_buffer), "ordinary buffers are not interpreted")
vim.api.nvim_buf_delete(lazy_buffer, { force = true })
vim.api.nvim_buf_delete(ordinary_buffer, { force = true })

print(string.format("Plugin manager tests: %d assertions passed", assertions))
vim.cmd("qa!")
