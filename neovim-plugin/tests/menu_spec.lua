local root = vim.fn.getcwd()
local menu = dofile(root .. "/neovim-plugin/lua/nvim_nvda/menu.lua")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local normalized = menu.normalize_item({
  word = "printf", abbr = "printf(format, ...)", kind = "f", menu = "[LSP]", info = "Print formatted output",
})
equal("printf", normalized.label, "signature label")
equal("format, ...", normalized.parameters, "signature parameters")
equal("function", normalized.kind, "kind name")

local lsp = menu.normalize_item({
  word = "map", kind = "Function", user_data = {
    nvim = { lsp = { completion_item = {
      label = "map", kind = 3, detail = "map(callback, values)",
      documentation = { value = "Apply callback to every value" },
    } } },
  },
})
equal("function", lsp.kind, "LSP kind")
equal("callback, values", lsp.parameters, "LSP detail parameters")
equal("Apply callback to every value", lsp.documentation, "LSP documentation")

local model = menu.new()
local opened = model:update({
  mode = "omni", pum_visible = true, selected = 0,
  items = {
    { word = "printf", abbr = "printf(format, ...)", kind = "f" },
    { word = "print", abbr = "print(value)", kind = "f" },
  },
})
equal(2, #opened, "open and initial selection")
equal("menuOpened", opened[1].type, "open event")
equal(1, opened[2].payload.itemIndex, "one-based position")
equal(2, opened[2].payload.itemCount, "item count")

equal(0, #model:update({
  mode = "omni", pum_visible = true, selected = 0,
  items = {
    { word = "printf", abbr = "printf(format, ...)", kind = "f" },
    { word = "print", abbr = "print(value)", kind = "f" },
  },
}), "duplicate selection suppressed")

local moved = model:update({
  mode = "omni", pum_visible = true, selected = 1,
  items = {
    { word = "printf", abbr = "printf(format, ...)", kind = "f" },
    { word = "print", abbr = "print(value)", kind = "f" },
  },
})
equal(1, #moved, "one selection event")
equal("print", moved[1].payload.item.label, "second item")
equal(2, moved[1].payload.itemIndex, "second position")

local closed = model:close("done")
equal(1, #closed, "one close event")
equal("menuClosed", closed[1].type, "close type")
equal(0, #model:close("again"), "duplicate close suppressed")

local no_selection = menu.new():update({
  mode = "keyword", pum_visible = true, selected = -1,
  items = {{ word = "one" }, { word = "two" }},
})
equal(1, #no_selection, "open without selected item")
equal("menuOpened", no_selection[1].type, "no-selection open type")

local empty = menu.new():update({ mode = "keyword", pum_visible = true, selected = -1, items = {} })
equal(0, #empty, "empty menu remains closed")

local long = menu.normalize_item({ word = string.rep("x", 800), info = string.rep("d", 3000) })
equal(512, #long.label, "label bounded")
equal(2048, #long.documentation, "documentation bounded")

print(string.format("menu tests: %d assertions passed", assertions))
vim.cmd("qa!")
