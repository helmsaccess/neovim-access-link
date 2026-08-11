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
equal(false, plugin_manager.details_expanded(lazy_buffer), "closed details have semantic state")
vim.api.nvim_exec_autocmds("BufEnter", { buffer = lazy_buffer, modeline = false })
vim.wait(50)
events = {}
vim.api.nvim_buf_set_lines(lazy_buffer, 5, 5, false, { "      dir /tmp/example" })
local lazy_namespace = vim.api.nvim_create_namespace("NvimNvdaLazyPublicDetailTest")
vim.api.nvim_buf_set_extmark(lazy_buffer, lazy_namespace, 5, 6, {
  end_col = 9,
  hl_group = "LazyProp",
})
equal(true, plugin_manager.details_expanded(lazy_buffer), "documented LazyProp dir opens details")
equal(
  true,
  require("nvim_nvda.state").snapshot("lazyDetailsTest").pluginManagerDetailsExpanded,
  "canonical state carries semantic Lazy details"
)
vim.api.nvim_exec_autocmds("TextChanged", { buffer = lazy_buffer, modeline = false })
equal(true, vim.wait(100, function() return #events == 1 end), "expanded transition emitted")
equal({ "pluginManagerDetailsChanged", "lazyNvim", true }, {
  events[1].type,
  events[1].payload.pluginManagerKind,
  events[1].payload.pluginManagerDetailsExpanded,
}, "expanded transition is fixed semantic state")

events = {}
vim.api.nvim_buf_clear_namespace(lazy_buffer, lazy_namespace, 0, -1)
vim.api.nvim_buf_set_lines(lazy_buffer, 5, 6, false, {})
vim.api.nvim_exec_autocmds("TextChanged", { buffer = lazy_buffer, modeline = false })
equal(true, vim.wait(100, function() return #events == 1 end), "collapsed transition emitted")
equal(false, events[1].payload.pluginManagerDetailsExpanded, "collapsed transition is semantic")

vim.api.nvim_buf_set_lines(lazy_buffer, 5, 5, false, { "      dir /tmp/plain-text" })
equal(false, plugin_manager.details_expanded(lazy_buffer), "unhighlighted dir text is not semantic")
vim.api.nvim_buf_set_lines(lazy_buffer, 5, 6, false, {
  "      dir /tmp/one",
  "      dir /tmp/two",
})
vim.api.nvim_buf_set_extmark(lazy_buffer, lazy_namespace, 5, 6, {
  end_col = 9,
  hl_group = "LazyProp",
})
vim.api.nvim_buf_set_extmark(lazy_buffer, lazy_namespace, 6, 6, {
  end_col = 9,
  hl_group = "LazyProp",
})
equal(nil, plugin_manager.details_expanded(lazy_buffer), "ambiguous details fail open")

local ordinary_buffer = vim.api.nvim_create_buf(false, true)
vim.api.nvim_buf_set_lines(ordinary_buffer, 0, -1, false, { "lazy.nvim Install (I)" })
equal(nil, plugin_manager.overview(ordinary_buffer), "ordinary buffers are not interpreted")
equal(nil, plugin_manager.details_expanded(ordinary_buffer), "ordinary details are not interpreted")
vim.api.nvim_buf_delete(lazy_buffer, { force = true })
vim.api.nvim_buf_delete(ordinary_buffer, { force = true })

print(string.format("Plugin manager tests: %d assertions passed", assertions))
vim.cmd("qa!")
