local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path
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

local original_get_client = vim.lsp.get_client_by_id
vim.lsp.get_client_by_id = function(client_id)
  return client_id == 17 and { name = "lua_ls" } or nil
end
local native_source = menu.normalize_item({
  word = "vim", user_data = {
    nvim = { lsp = {
      client_id = 17,
      completion_item = { label = "vim", kind = 9 },
    } },
  },
})
vim.lsp.get_client_by_id = original_get_client
equal("lua_ls", native_source.source, "native LSP client source")

local all_kinds = {
  "text", "method", "function", "constructor", "field", "variable", "class",
  "interface", "module", "property", "unit", "value", "enum", "keyword",
  "snippet", "color", "file", "reference", "folder", "enum member", "constant",
  "struct", "event", "operator", "type parameter",
}
for index, expected in ipairs(all_kinds) do
  equal(expected, menu.normalize_item({ word = "item", kind = index }).kind,
    "LSP kind " .. tostring(index))
end

local sourced = menu.normalize_item({
  word = "same", detail = "callable", source_name = "pyright",
})
equal("pyright", sourced.source, "source preserved")
equal("callable", sourced.detail, "detail preserved")

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

local detailed = model:update({
  mode = "omni", pum_visible = true, selected = 0,
  items = {
    { word = "printf", abbr = "printf(format, ...)", kind = "f", info = "resolved docs" },
    { word = "print", abbr = "print(value)", kind = "f" },
  },
})
equal(1, #detailed, "detail update emitted")
equal("menuItemUpdated", detailed[1].type, "detail update is silent event")
equal("resolved docs", detailed[1].payload.item.documentation, "resolved documentation included")

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

local unicode = menu.normalize_item({
  word = string.rep("界", 171), info = string.rep("😀", 513),
})
equal(510, #unicode.label, "label bounded on UTF-8 boundary")
equal(2048, #unicode.documentation, "four-byte documentation boundary")
equal(true, vim.str_utfindex(unicode.label) > 0, "bounded label remains valid UTF-8")
equal("", menu.normalize_item({ word = "\255invalid" }).label, "invalid UTF-8 rejected")

local many_items = {}
for index = 1, 250 do many_items[index] = { word = "item" .. tostring(index) } end
local normalization_count = 0
local original_normalize = menu.normalize_item
menu.normalize_item = function(item)
  normalization_count = normalization_count + 1
  return original_normalize(item)
end
local later = menu.new():update({
  mode = "omni", pum_visible = true, selected = 224, items = many_items,
})
menu.normalize_item = original_normalize
equal(1, normalization_count, "only selected item normalized")
equal("item225", later[2].payload.item.label, "selection beyond item 200 announced")
equal(250, later[2].payload.itemCount, "full item count retained")

print(string.format("menu tests: %d assertions passed", assertions))
vim.cmd("qa!")
