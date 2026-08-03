vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

vim.opt.completeopt = { "menu", "menuone", "noselect", "popup" }
vim.opt.number = true
vim.opt.signcolumn = "yes"
vim.opt.updatetime = 300

vim.diagnostic.config({
  signs = true,
  underline = true,
  virtual_text = true,
  severity_sort = true,
  update_in_insert = false,
})

local uv = vim.uv or vim.loop
local data_path = vim.fn.stdpath("data")
local lazy_path = vim.fs.joinpath(data_path, "lazy", "lazy.nvim")

if not uv.fs_stat(lazy_path) then
  local output = vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "--branch=stable",
    "https://github.com/folke/lazy.nvim.git",
    lazy_path,
  })
  if vim.v.shell_error ~= 0 then
    error("Could not install lazy.nvim:\n" .. output)
  end
end

vim.opt.rtp:prepend(lazy_path)

local plugins = {
  {
    "stevearc/oil.nvim",
    lazy = false,
    opts = {
      columns = { "type", "size" },
      delete_to_trash = false,
      skip_confirm_for_simple_edits = false,
    },
    keys = {
      { "-", "<Cmd>Oil<CR>", desc = "Open parent directory" },
    },
  },
  {
    "neovim/nvim-lspconfig",
    lazy = false,
    config = function()
      vim.lsp.enable("pyright")
    end,
  },
  {
    "mfussenegger/nvim-lint",
    lazy = false,
    config = function()
      local lint = require("lint")
      lint.linters_by_ft = {
        python = { "ruff" },
      }

      local group = vim.api.nvim_create_augroup("example_python_lint", {
        clear = true,
      })
      vim.api.nvim_create_autocmd({ "BufReadPost", "BufWritePost" }, {
        group = group,
        pattern = "*.py",
        callback = function()
          lint.try_lint()
        end,
      })
    end,
  },
}

local access_link_path = vim.fs.joinpath(
  data_path,
  "site",
  "pack",
  "nvim-nvda",
  "start",
  "nvim-nvda"
)

if uv.fs_stat(access_link_path) then
  table.insert(plugins, 1, {
    dir = access_link_path,
    name = "nvim-nvda",
    lazy = false,
    priority = 1000,
  })
else
  vim.schedule(function()
    vim.notify(
      "Neovim Access Link plugin not found; install the add-on components first",
      vim.log.levels.WARN
    )
  end)
end

require("lazy").setup(plugins, {
  defaults = { lazy = false },
  install = { colorscheme = { "habamax" } },
  checker = { enabled = false },
})

vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(event)
    local client = vim.lsp.get_client_by_id(event.data.client_id)
    local options = { buffer = event.buf, silent = true }

    vim.keymap.set("n", "K", vim.lsp.buf.hover, options)
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, options)

    if client and client:supports_method("textDocument/completion") then
      vim.lsp.completion.enable(true, client.id, event.buf, {
        autotrigger = true,
      })
      vim.keymap.set("i", "<C-Space>", vim.lsp.completion.get, options)
    end
  end,
})

vim.keymap.set("n", "<leader>ll", function()
  require("lint").try_lint()
end, { desc = "Run Python linter" })

vim.keymap.set("n", "[d", "<Cmd>NvimNvdaDiagnosticPrevious<CR>",
  { desc = "Previous diagnostic" })
vim.keymap.set("n", "]d", "<Cmd>NvimNvdaDiagnosticNext<CR>",
  { desc = "Next diagnostic" })
vim.keymap.set("n", "[D", "<Cmd>NvimNvdaDiagnosticFirst<CR>",
  { desc = "First diagnostic" })
vim.keymap.set("n", "]D", "<Cmd>NvimNvdaDiagnosticLast<CR>",
  { desc = "Last diagnostic" })
vim.keymap.set("n", "<leader>dd", "<Cmd>NvimNvdaDiagnosticCurrent<CR>",
  { desc = "Read diagnostic at cursor" })
vim.keymap.set("n", "<leader>ls", "<Cmd>NvimNvdaLspStatus<CR>",
  { desc = "Read LSP status" })
