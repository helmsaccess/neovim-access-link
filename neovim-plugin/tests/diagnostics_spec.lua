local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local diagnostics = require("nvim_nvda.diagnostics")
local assertions = 0

local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local namespace_names = {
  [3] = "provider-z",
  [4] = "provider-a",
}
local function resolve_namespace(namespace)
  return namespace_names[namespace] or ""
end

local values = {
  {
    lnum = 0, col = 1, end_lnum = 0, end_col = 10,
    message = "wide warning", severity = vim.diagnostic.severity.WARN,
    source = "future-provider", code = "WIDE", namespace = 3,
  },
  {
    lnum = 0, col = 2, end_lnum = 0, end_col = 5,
    message = "small error", severity = vim.diagnostic.severity.ERROR,
    source = "", code = 42, namespace = 4,
  },
  {
    lnum = 0, col = 2, end_lnum = 0, end_col = 5,
    message = "same range later provider", severity = vim.diagnostic.severity.ERROR,
    source = "z-source", code = "Z", namespace = 3,
  },
  { lnum = -1, message = "negative line" },
  { lnum = 0, col = 5, end_lnum = 0, end_col = 4, message = "backwards" },
  { lnum = 0, message = "\255invalid UTF-8" },
  { lnum = 0, message = true },
}

local current, count = diagnostics.snapshot_values(values, 1, 3, resolve_namespace)
equal(3, count, "invalid producer records rejected")
equal("small error", current.message, "highest severity and smallest range selected")
equal("provider-a", current.source, "namespace name supplies a missing source")
equal(42, current.code, "integer code retained")
equal("error", current.severity, "severity normalized")
equal(2, current.byteColumn, "start byte column")
equal(5, current.endByteColumn, "end byte column")
equal(1, current.line, "one-based line")

local ordered = diagnostics.normalized(values, resolve_namespace)
equal("wide warning", ordered[1].message, "location precedes severity in navigation order")
equal("small error", ordered[2].message, "namespace makes equal ranges deterministic")
equal("same range later provider", ordered[3].message, "second equal-range provider stable")

local zero_width = {
  { lnum = 0, col = 4, end_lnum = 0, end_col = 4, message = "point" },
}
equal("point", diagnostics.snapshot_values(zero_width, 1, 4).message, "zero-width start selected")
equal(nil, diagnostics.snapshot_values(zero_width, 1, 5), "zero-width range is one byte only")

local multiline = {
  {
    lnum = 1, col = 3, end_lnum = 3, end_col = 2,
    message = "multi", source = "generic",
  },
}
equal(nil, diagnostics.snapshot_values(multiline, 2, 2), "before multiline start excluded")
equal("multi", diagnostics.snapshot_values(multiline, 3, 0).message, "middle multiline row selected")
equal("multi", diagnostics.snapshot_values(multiline, 4, 1).message, "before multiline end selected")
equal(nil, diagnostics.snapshot_values(multiline, 4, 2), "multiline end excluded")

local long_source = string.rep("x", 300)
local bounded = diagnostics.snapshot_values({
  { lnum = 0, message = string.rep("m", 3000), source = long_source, code = long_source },
}, 1, 0)
equal(2048, #bounded.message, "message bounded")
equal(256, #bounded.source, "source bounded")
equal(256, #bounded.code, "code bounded")

local many = {}
for index = 1, 2000 do
  many[index] = {
    lnum = index - 1,
    message = "diagnostic " .. index,
    source = index % 2 == 0 and "gopls" or "rust-analyzer",
  }
end
local last, many_count = diagnostics.snapshot_values(many, 2000, 0)
equal(2000, many_count, "large provider-neutral list retained")
equal("diagnostic 2000", last.message, "large list remains addressable")

local group = vim.api.nvim_create_augroup("NvimNvdaDiagnosticCacheSpec", { clear = true })
diagnostics.setup(function() end, group)
local namespace = vim.api.nvim_create_namespace("cached-future-provider")
vim.api.nvim_buf_set_lines(0, 0, -1, true, { "cached value" })
vim.diagnostic.set(namespace, 0, {
  { lnum = 0, col = 0, end_lnum = 0, end_col = 6, message = "before update" },
})
local cached = diagnostics.snapshot(0, 1, 0)
equal("before update", cached.message, "buffer snapshot cached")
equal("cached-future-provider", cached.source, "real namespace fallback")
vim.diagnostic.set(namespace, 0, {
  { lnum = 0, col = 0, end_lnum = 0, end_col = 6, message = "after update" },
})
equal(true, vim.wait(500, function()
  return diagnostics.snapshot(0, 1, 0).message == "after update"
end, 10), "DiagnosticChanged invalidates buffer cache")

print(string.format("diagnostic contract tests: %d assertions passed", assertions))
vim.cmd("qa!")
