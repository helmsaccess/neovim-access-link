local root = vim.fn.getcwd()
local cmp_root = vim.env.NVIM_NVDA_NVIM_CMP_ROOT
local blink_root = vim.env.NVIM_NVDA_BLINK_CMP_ROOT
local blink_lib_root = vim.env.NVIM_NVDA_BLINK_LIB_ROOT
assert(type(cmp_root) == "string" and vim.fn.isdirectory(cmp_root) == 1,
  "NVIM_NVDA_NVIM_CMP_ROOT must name an nvim-cmp checkout")
assert(type(blink_root) == "string" and vim.fn.isdirectory(blink_root) == 1,
  "NVIM_NVDA_BLINK_CMP_ROOT must name a blink.cmp checkout")

local lua_roots = {
  root .. "/neovim-plugin",
  cmp_root,
  blink_root,
}
if type(blink_lib_root) == "string" and blink_lib_root ~= "" then
  assert(vim.fn.isdirectory(blink_lib_root) == 1,
    "NVIM_NVDA_BLINK_LIB_ROOT must name a blink.lib checkout")
  lua_roots[#lua_roots + 1] = blink_lib_root
end
for _, value in ipairs(lua_roots) do
  vim.opt.runtimepath:prepend(value)
  package.path = value .. "/lua/?.lua;" .. value .. "/lua/?/init.lua;" .. package.path
end

local assertions = 0
local function truth(value, label)
  assertions = assertions + 1
  assert(value, label)
end

local cmp = require("cmp")
truth(type(cmp.event) == "table" and type(cmp.event.on) == "function"
  and type(cmp.event.emit) == "function", "nvim-cmp exposes its documented event API")
truth(type(cmp.get_entries) == "function" and type(cmp.get_selected_entry) == "function",
  "nvim-cmp exposes documented selection APIs")

local blink = require("blink.cmp")
truth(type(blink.get_items) == "function" and type(blink.get_selected_item_idx) == "function",
  "blink.cmp exposes documented selection APIs")
truth(type(blink.is_menu_visible) == "function", "blink.cmp exposes menu visibility")

local cmp_entry = {
  id = 700,
  completion_item = {
    label = "actual_cmp_api", kind = 3, documentation = { value = "nvim-cmp docs" },
  },
  source = { name = "nvim_lsp" },
}
local cmp_entry_second = {
  id = 701,
  completion_item = { label = "actual_cmp_second", kind = 3 },
  source = { name = "nvim_lsp" },
}
local blink_item = {
  label = "actual_blink_api", kind = 6, source_id = "lsp", source_name = "LSP",
  documentation = { value = "blink docs" },
}
local blink_item_second = {
  label = "actual_blink_second", kind = 6, source_id = "lsp", source_name = "LSP",
}
local original_cmp_entries = cmp.get_entries
local original_cmp_selected = cmp.get_selected_entry
local original_blink_visible = blink.is_menu_visible
local original_blink_items = blink.get_items
local original_blink_index = blink.get_selected_item_idx
local cmp_selected = cmp_entry
local blink_selected = 1
cmp.get_entries = function() return { cmp_entry, cmp_entry_second } end
cmp.get_selected_entry = function() return cmp_selected end
blink.is_menu_visible = function() return true end
blink.get_items = function() return { blink_item, blink_item_second } end
blink.get_selected_item_idx = function() return blink_selected end

local calls = {}
local lifecycle_calls = {}
local owner = {
  accessible_menu_begin = function(options)
    lifecycle_calls[#lifecycle_calls + 1] = { type = "begin", kind = options.kind }
  end,
  accessible_menu_update = function(item, options)
    calls[#calls + 1] = { type = "update", item = item, options = options }
  end,
  accessible_menu_close = function() calls[#calls + 1] = { type = "close" } end,
}
local adapters = require("nvim_nvda.completion_adapters")
local group = vim.api.nvim_create_augroup("NvimNvdaRealCompletionPlugins", { clear = true })
local setup = adapters.setup(owner, group)
truth(setup.nvim_cmp == true and setup.blink_cmp == true, "both real modules attach")

cmp.event:emit("menu_opened", {})
truth(lifecycle_calls[#lifecycle_calls].kind == "nvim-cmp",
  "real nvim-cmp open event begins accessible lifetime")
truth(vim.wait(500, function()
  return calls[#calls] and calls[#calls].item
    and calls[#calls].item.word == "actual_cmp_api"
end, 10), "real nvim-cmp event reaches adapter")
truth(calls[#calls].item.source == "nvim_lsp", "real nvim-cmp entry source is preserved")
local cmp_lifetimes = #lifecycle_calls
cmp_selected = cmp_entry_second
truth(vim.wait(500, function()
  return calls[#calls] and calls[#calls].options
    and calls[#calls].options.selected == 2
end, 10), "real nvim-cmp selection change reaches adapter")
truth(#lifecycle_calls == cmp_lifetimes,
  "real nvim-cmp selection does not restart accessible lifetime")
cmp.event:emit("menu_closed", {})
truth(calls[#calls].type == "close", "real nvim-cmp close event reaches adapter")

vim.api.nvim_exec_autocmds("User", { pattern = "BlinkCmpMenuOpen" })
truth(lifecycle_calls[#lifecycle_calls].kind == "blink.cmp",
  "real blink.cmp open event begins accessible lifetime")
truth(vim.wait(500, function()
  return calls[#calls] and calls[#calls].item
    and calls[#calls].item.word == "actual_blink_api"
end, 10), "real blink.cmp module reaches adapter")
truth(calls[#calls].item.source == "LSP", "real blink.cmp source is preserved")
local blink_lifetimes = #lifecycle_calls
blink_selected = 2
truth(vim.wait(500, function()
  return calls[#calls] and calls[#calls].options
    and calls[#calls].options.selected == 2
end, 10), "real blink.cmp selection change reaches adapter")
truth(#lifecycle_calls == blink_lifetimes,
  "real blink.cmp selection does not restart accessible lifetime")
vim.api.nvim_exec_autocmds("User", { pattern = "BlinkCmpMenuClose" })
truth(calls[#calls].type == "close", "real blink.cmp close event reaches adapter")

adapters.stop()
cmp.get_entries = original_cmp_entries
cmp.get_selected_entry = original_cmp_selected
blink.is_menu_visible = original_blink_visible
blink.get_items = original_blink_items
blink.get_selected_item_idx = original_blink_index

print(string.format("real completion plugin integration: %d assertions passed", assertions))
vim.cmd("qa!")
