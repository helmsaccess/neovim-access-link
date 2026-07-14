local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local adapters = dofile(root .. "/neovim-plugin/lua/nvim_nvda/completion_adapters.lua")

local function equal(expected, actual, label)
  assert(expected == actual, string.format("%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
end

local lsp = adapters.normalize_item({
  label = "printf", kind = 3, detail = "stdio", documentation = { value = "Print formatted output" },
})
equal("printf", lsp.word, "LSP label")
equal("function", lsp.kind, "numeric LSP kind")
equal("stdio", lsp.menu, "LSP detail")
equal("Print formatted output", lsp.info, "markup documentation")

local cmp = adapters.normalize_item({
  abbr = "print(value)", word = "print", kind = "function", menu = "[LSP]", info = "docs",
})
equal("print", cmp.word, "cmp word")
equal("print(value)", cmp.abbr, "cmp abbreviation")
equal("[LSP]", cmp.menu, "cmp source")
equal("docs", cmp.info, "cmp docs")

local empty = adapters.normalize_item(nil)
equal("", empty.word, "nil item")

local callbacks, calls = {}, {}
local first = { get_completion_item = function() return { label = "printf", kind = 3 } end }
local second = { get_completion_item = function() return { label = "print", kind = 3 } end }
local selected = first
package.loaded.cmp = {
  event = { on = function(_, name, callback) callbacks[name] = callback end },
  get_entries = function() return { first, second } end,
  get_selected_entry = function() return selected end,
  visible = function() return true end,
}
local owner = {
  accessible_menu_open = function(items, options)
    table.insert(calls, { type = "open", items = items, selected = options.selected })
  end,
  accessible_menu_close = function() table.insert(calls, { type = "close" }) end,
}
local group = vim.api.nvim_create_augroup("NvimNvdaAdapterTest", { clear = true })
adapters.setup(owner, group)
callbacks.menu_opened()
vim.wait(200, function() return #calls >= 1 end)
equal("open", calls[1].type, "cmp opens adapter menu")
equal(2, #calls[1].items, "cmp item count")
equal(1, calls[1].selected, "cmp initial selection")
selected = second
vim.wait(200, function() return #calls >= 2 end)
equal(2, calls[#calls].selected, "cmp selection polling")
callbacks.menu_closed()
equal("close", calls[#calls].type, "cmp closes adapter menu")
adapters.stop()
package.loaded.cmp = nil

print("completion adapter tests: 14 assertions passed")
vim.cmd("qa!")
