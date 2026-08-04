local root = vim.fn.getcwd()
local example = root .. "/examples/neovim-lazy-python/init.lua"
local test_root = root .. "/tmp/example-lazy-python-config-" .. vim.fn.getpid()
local data_path = test_root .. "/data/nvim"
local lazy_path = data_path .. "/lazy/lazy.nvim"
local access_link_path = data_path
  .. "/site/pack/nvim-nvda/start/nvim-nvda"

vim.fn.delete(test_root, "rf")
vim.fn.mkdir(lazy_path, "p")
vim.fn.mkdir(access_link_path .. "/plugin", "p")
vim.fn.writefile({ "vim.g.example_access_link_loaded = 1" },
  access_link_path .. "/plugin/nvim_nvda.lua")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)))
end

local function truthy(value, label)
  assertions = assertions + 1
  assert(value, label)
end

local original_fn = vim.fn
vim.fn = setmetatable({
  stdpath = function(kind)
    if kind == "data" then return data_path end
    return original_fn.stdpath(kind)
  end,
  system = function()
    error("the example tried to download lazy.nvim although it already existed")
  end,
}, { __index = original_fn })

local lint_calls = 0
local fake_lint = {
  linters_by_ft = {},
  try_lint = function()
    lint_calls = lint_calls + 1
  end,
}
package.preload.lint = function() return fake_lint end

local enabled_server
vim.lsp.enable = function(name)
  enabled_server = name
end

local completion_enable
vim.lsp.completion = {
  enable = function(enabled, client_id, buffer, options)
    completion_enable = {
      enabled = enabled,
      client_id = client_id,
      buffer = buffer,
      options = options,
    }
  end,
  get = function() end,
}

local captured_specs
local captured_options
package.preload.lazy = function()
  return {
    setup = function(specs, options)
      captured_specs = specs
      captured_options = options

      -- Match the relevant lazy.nvim startup behavior: normal package loading
      -- and the original packpath can no longer make Access Link visible.
      vim.go.loadplugins = false
      vim.go.packpath = vim.env.VIMRUNTIME

      local access_spec = specs[1]
      vim.opt.rtp:prepend(access_spec.dir)
      dofile(access_spec.dir .. "/plugin/nvim_nvda.lua")

      for _, spec in ipairs(specs) do
        if spec.config then spec.config() end
      end
    end,
  }
end

dofile(example)

truthy(type(captured_specs) == "table", "lazy.nvim received a plugin spec")
equal(access_link_path, captured_specs[1].dir,
  "Access Link uses the add-on installation directory")
equal("nvim-nvda", captured_specs[1].name, "Access Link plugin name")
equal(false, captured_specs[1].lazy, "Access Link is eagerly loaded")
equal(1000, captured_specs[1].priority, "Access Link startup priority")
equal(1, vim.g.example_access_link_loaded,
  "Access Link loads despite lazy.nvim resetting package discovery")

local by_name = {}
for _, spec in ipairs(captured_specs) do
  if type(spec[1]) == "string" then by_name[spec[1]] = spec end
end
truthy(by_name["stevearc/oil.nvim"] ~= nil, "Oil is installed")
equal(false, by_name["stevearc/oil.nvim"].lazy, "Oil follows upstream eager loading")
equal({ "type", "size" }, by_name["stevearc/oil.nvim"].opts.columns,
  "Oil avoids an optional icon dependency")
equal(false, by_name["stevearc/oil.nvim"].opts.skip_confirm_for_simple_edits,
  "Oil keeps edit confirmations")
equal(false, by_name["stevearc/oil.nvim"].opts.delete_to_trash,
  "the portable Oil example does not assume a trash helper")
equal("-", by_name["stevearc/oil.nvim"].keys[1][1],
  "Oil has a simple parent-directory mapping")
truthy(by_name["neovim/nvim-lspconfig"] ~= nil, "nvim-lspconfig is installed")
truthy(by_name["mfussenegger/nvim-lint"] ~= nil, "nvim-lint is installed")
equal("pyright", enabled_server, "Pyright configuration is enabled")
equal({ "ruff" }, fake_lint.linters_by_ft.python, "Ruff handles Python files")
equal(false, captured_options.defaults.lazy, "plugins are eager by default")
equal(false, captured_options.checker.enabled,
  "the small example does not run background update checks")

equal(true, vim.o.number, "line numbers are enabled")
equal("yes", vim.o.signcolumn, "diagnostic sign column is stable")
truthy(vim.o.completeopt:find("menuone", 1, true) ~= nil,
  "native completion menu options are configured")

for _, key in ipairs({ "[d", "]d", "[D", "]D", "<Space>dd", "<Space>ls",
    "<Space>ll" }) do
  local mapping = vim.fn.maparg(key, "n", false, true)
  truthy(type(mapping) == "table" and mapping.desc ~= nil,
    "normal-mode mapping missing for " .. key)
end

vim.api.nvim_buf_set_name(0, test_root .. "/sample.py")
vim.api.nvim_exec_autocmds("BufWritePost", { buffer = 0 })
equal(1, lint_calls, "saving Python invokes Ruff")

vim.lsp.get_client_by_id = function(client_id)
  equal(77, client_id, "LspAttach client id")
  return {
    id = client_id,
    supports_method = function(_, method)
      equal("textDocument/completion", method, "completion capability check")
      return true
    end,
  }
end
vim.api.nvim_exec_autocmds("LspAttach", {
  buffer = 0,
  data = { client_id = 77 },
})
equal(true, completion_enable.enabled, "native LSP completion is enabled")
equal(77, completion_enable.client_id, "completion uses the attached client")
equal(vim.api.nvim_get_current_buf(), completion_enable.buffer,
  "completion is buffer-local")
equal(true, completion_enable.options.autotrigger, "completion auto-trigger is enabled")

for _, mapping in ipairs({
  { "K", "n" },
  { "gd", "n" },
  { "<C-Space>", "i" },
}) do
  local value = vim.fn.maparg(mapping[1], mapping[2], false, true)
  truthy(type(value) == "table" and value.buffer == 1,
    "LSP buffer mapping missing for " .. mapping[1])
end

vim.fn = original_fn
vim.fn.delete(test_root, "rf")
print(string.format("lazy Python example config specs passed: %d assertions", assertions))
