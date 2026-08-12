vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

vim.opt.number = false
vim.opt.relativenumber = false
vim.opt.expandtab = false
vim.opt.tabstop = 2
vim.opt.softtabstop = 0
vim.opt.shiftwidth = 2
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.splitbelow = true
vim.opt.splitright = true

vim.api.nvim_create_autocmd("FileType", {
  desc = "Keep starter indentation consistent across file types",
  callback = function(args)
    vim.bo[args.buf].expandtab = false
    vim.bo[args.buf].tabstop = 2
    vim.bo[args.buf].softtabstop = 0
    vim.bo[args.buf].shiftwidth = 2
  end,
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
      { "<leader>o", "<Cmd>Oil<CR>", desc = "Open file manager" },
    },
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

vim.keymap.set("n", "<leader>l", "<Cmd>Lazy<CR>", {
  desc = "Open plugin manager",
})
