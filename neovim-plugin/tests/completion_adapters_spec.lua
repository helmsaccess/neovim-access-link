local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local adapters = dofile(root .. "/neovim-plugin/lua/nvim_nvda/completion_adapters.lua")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local lsp = adapters.normalize_item({
  label = "printf", kind = 3, detail = "stdio", documentation = { value = "Print formatted output" },
}, "nvim_lsp", "entry:1")
equal("printf", lsp.word, "LSP label")
equal("function", lsp.kind, "numeric LSP kind")
equal("stdio", lsp.menu, "LSP detail")
equal("nvim_lsp", lsp.source, "source name")
equal("Print formatted output", lsp.info, "markup documentation")
equal("entry:1", lsp.stableId, "stable ID")
equal(true, adapters.is_selection_key("<C-N>"), "Ctrl+N is a completion selection key")
equal(false, adapters.is_selection_key("<Tab>"), "unrelated Insert key is not suppressed")

local all_kinds = {
  "text", "method", "function", "constructor", "field", "variable", "class",
  "interface", "module", "property", "unit", "value", "enum", "keyword",
  "snippet", "color", "file", "reference", "folder", "enum member", "constant",
  "struct", "event", "operator", "type parameter",
}
for index, expected in ipairs(all_kinds) do
  equal(expected, adapters.normalize_item({ label = "item", kind = index }).kind,
    "adapter kind " .. tostring(index))
end

local cmp = adapters.normalize_item({
  abbr = "print(value)", word = "print", kind = "function", menu = "[LSP]", info = "docs",
})
equal("print", cmp.word, "cmp word")
equal("print(value)", cmp.abbr, "cmp abbreviation")
equal("[LSP]", cmp.menu, "cmp menu")
equal("docs", cmp.info, "cmp docs")
equal("", adapters.normalize_item(nil).word, "nil item")

local callbacks, calls, lifecycle_calls = {}, {}, {}
local first = {
  id = 41,
  completion_item = { label = "printf", kind = 3 },
  source = { name = "nvim_lsp" },
  get_completion_item = function() error("deprecated accessor used") end,
}
local second = {
  id = 42,
  completion_item = { label = "print", kind = 3 },
  source = { name = "buffer" },
  get_completion_item = function() error("deprecated accessor used") end,
}
local selected = first
local cmp_entries = {}
package.loaded.cmp = {
  event = { on = function(_, name, callback) callbacks[name] = callback end },
  get_entries = function() return cmp_entries end,
  get_selected_entry = function() return selected end,
}
local owner = {
  accessible_menu_begin = function(options)
    lifecycle_calls[#lifecycle_calls + 1] = { type = "begin", kind = options.kind }
  end,
  accessible_menu_update = function(item, options)
    calls[#calls + 1] = {
      type = "update", item = item, selected = options.selected,
      item_count = options.item_count, kind = options.kind,
    }
  end,
  accessible_menu_close = function() calls[#calls + 1] = { type = "close" } end,
}
local group = vim.api.nvim_create_augroup("NvimNvdaAdapterTest", { clear = true })
adapters.setup(owner, group)
callbacks.menu_opened()
equal("begin", lifecycle_calls[#lifecycle_calls].type, "cmp lifecycle opens immediately")
equal("nvim-cmp", lifecycle_calls[#lifecycle_calls].kind, "cmp lifecycle kind")
equal(true, adapters.is_active(), "cmp adapter reports active menu")
callbacks.menu_opened()
equal(1, #lifecycle_calls, "duplicate cmp open does not restart lifecycle")
vim.wait(80)
equal(0, #calls, "empty initial cmp data does not close accessible lifecycle")
cmp_entries = { first, second }
vim.wait(200, function() return #calls >= 1 end)
equal("update", calls[1].type, "cmp opens adapter menu")
equal(1, calls[1].selected, "cmp initial selection")
equal(2, calls[1].item_count, "cmp full item count")
equal("nvim_lsp", calls[1].item.source, "cmp selected source")
equal("entry:41", calls[1].item.stableId, "cmp entry identity")

local call_count = #calls
vim.wait(80)
equal(call_count, #calls, "unchanged cmp selection suppressed")

first.completion_item.documentation = { value = "resolved later" }
vim.wait(200, function() return #calls > call_count end)
equal("resolved later", calls[#calls].item.info, "cmp resolved documentation republished")

selected = second
vim.wait(200, function() return calls[#calls].selected == 2 end)
equal("buffer", calls[#calls].item.source, "cmp moved selection source")
callbacks.menu_closed()
equal("close", calls[#calls].type, "cmp closes adapter menu")
equal(false, adapters.is_active(), "cmp adapter reports closed menu")

local blink_items = {
  { label = "alpha", kind = 6, source_id = "lsp", source_name = "LSP" },
  { label = "beta", kind = 15, source_id = "snippets", source_name = "Snippets" },
}
local blink_selected = 1
local blink_visible = false
local blink_error = false
package.loaded["blink.cmp"] = {
  is_menu_visible = function()
    if blink_error then error("simulated item API failure") end
    return blink_visible
  end,
  get_items = function() return blink_items end,
  get_selected_item_idx = function() return blink_selected end,
  get_selected_item = function() error("identity fallback used") end,
}
vim.api.nvim_exec_autocmds("User", { pattern = "BlinkCmpMenuOpen" })
equal("begin", lifecycle_calls[#lifecycle_calls].type, "blink lifecycle opens immediately")
equal("blink.cmp", lifecycle_calls[#lifecycle_calls].kind, "blink lifecycle kind")
equal(true, adapters.is_active(), "blink adapter reports active menu")
local calls_before_blink_items = #calls
vim.wait(80)
equal(calls_before_blink_items, #calls, "invisible initial blink data does not close lifecycle")
blink_visible = true
vim.wait(200, function()
  return calls[#calls].kind == "blink.cmp" and calls[#calls].selected == 1
end)
equal("LSP", calls[#calls].item.source, "blink source")
equal(2, calls[#calls].item_count, "blink item count")

callbacks.menu_closed()
equal("update", calls[#calls].type, "stale cmp close does not close blink")
blink_selected = 2
vim.wait(200, function() return calls[#calls].selected == 2 end)
equal("snippet", calls[#calls].item.kind, "blink selected kind")
equal("Snippets", calls[#calls].item.source, "blink selected source")
local calls_before_blink_error = #calls
blink_error = true
vim.wait(200, function() return adapters.diagnostics().errorCount > 0 end)
equal(calls_before_blink_error, #calls, "poll error does not invent close lifecycle")
vim.api.nvim_exec_autocmds("User", { pattern = "BlinkCmpMenuClose" })
equal("close", calls[#calls].type, "blink closes adapter menu")
equal(false, adapters.is_active(), "blink adapter reports closed menu")

local diagnostics = adapters.diagnostics()
equal(nil, diagnostics.activeKind, "diagnostics report inactive adapter")
equal("public-selected-index", diagnostics.apiVariant, "diagnostics report API variant")
equal(35, diagnostics.pollIntervalMilliseconds, "diagnostics report poll interval")

adapters.stop()
package.loaded.cmp = nil
package.loaded["blink.cmp"] = nil

print(string.format("completion adapter tests: %d assertions passed", assertions))
vim.cmd("qa!")
