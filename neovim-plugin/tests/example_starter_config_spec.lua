local root = vim.fn.getcwd()
local example = root .. "/examples/neovim-starter/init.lua"
local test_root = root .. "/tmp/example-starter-config-" .. vim.fn.getpid()
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
    error("the starter configuration tried to download lazy.nvim although it already existed")
  end,
}, { __index = original_fn })

vim.api.nvim_create_autocmd("FileType", {
  pattern = "python",
  callback = function(args)
    vim.bo[args.buf].expandtab = true
    vim.bo[args.buf].tabstop = 4
    vim.bo[args.buf].softtabstop = 4
    vim.bo[args.buf].shiftwidth = 4
  end,
})

local captured_specs
local captured_options
package.preload.lazy = function()
  return {
    setup = function(specs, options)
      captured_specs = specs
      captured_options = options
      vim.go.loadplugins = false
      vim.go.packpath = vim.env.VIMRUNTIME
      vim.opt.rtp:prepend(specs[1].dir)
      dofile(specs[1].dir .. "/plugin/nvim_nvda.lua")
    end,
  }
end

dofile(example)

equal(access_link_path, captured_specs[1].dir,
  "Access Link uses the add-on installation directory")
equal("nvim-nvda", captured_specs[1].name, "Access Link plugin name")
equal(false, captured_specs[1].lazy, "Access Link is eagerly loaded")
equal(1000, captured_specs[1].priority, "Access Link startup priority")
equal(1, vim.g.example_access_link_loaded,
  "Access Link loads despite lazy.nvim resetting package discovery")

local oil = captured_specs[2]
equal("stevearc/oil.nvim", oil[1], "Oil is the only downloaded plugin")
equal(false, oil.lazy, "Oil follows upstream eager loading")
equal({ "type", "size" }, oil.opts.columns,
  "Oil avoids an optional icon dependency")
equal(false, oil.opts.skip_confirm_for_simple_edits,
  "Oil keeps edit confirmations")
equal(false, oil.opts.delete_to_trash,
  "the portable starter configuration does not assume a trash helper")
equal("<leader>o", oil.keys[1][1], "Oil uses the documented leader mapping")
equal("<Cmd>Oil<CR>", oil.keys[1][2], "Oil mapping opens the file manager")
equal(false, captured_options.defaults.lazy, "plugins are eager by default")
equal(false, captured_options.checker.enabled,
  "the starter configuration does not run background update checks")

equal(false, vim.o.number, "line numbers remain disabled")
equal(false, vim.o.relativenumber, "relative line numbers remain disabled")
equal(false, vim.o.expandtab, "Tab inserts a tab character")
equal(2, vim.o.tabstop, "displayed Tab width is two columns")
equal(0, vim.o.softtabstop, "Tab follows the two-column tabstop")
equal(2, vim.o.shiftwidth, "automatic indentation width is two columns")
vim.cmd("enew")
vim.bo.filetype = "python"
equal(false, vim.bo.expandtab,
  "starter indentation overrides the Python filetype space default")
equal(2, vim.bo.tabstop,
  "starter tabstop overrides the Python filetype width")
equal(0, vim.bo.softtabstop,
  "starter softtabstop overrides the Python filetype width")
equal(2, vim.bo.shiftwidth,
  "starter shiftwidth overrides the Python filetype width")
local tab_keys = vim.api.nvim_replace_termcodes("i<Tab><Esc>", true, false, true)
vim.api.nvim_feedkeys(tab_keys, "xt", false)
equal("\t", vim.api.nvim_get_current_line(),
  "pressing Tab inserts an actual tab character")
equal(true, vim.o.ignorecase, "search ignores case by default")
equal(true, vim.o.smartcase, "uppercase search remains case-sensitive")
equal(true, vim.o.splitbelow, "horizontal splits open below")
equal(true, vim.o.splitright, "vertical splits open to the right")
equal("<Cmd>Lazy<CR>", vim.fn.maparg("<leader>l", "n"),
  "Lazy uses the documented leader mapping")
truthy(type(captured_specs) == "table", "lazy.nvim received a plugin spec")

vim.fn = original_fn
vim.fn.delete(test_root, "rf")
print(string.format("starter config specs passed: %d assertions", assertions))
