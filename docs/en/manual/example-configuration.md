# Small Python configuration with Lazy and Oil

This chapter provides a complete `init.lua` that can be copied directly. It is
intended for users without an extensive existing Neovim configuration and
includes:

- `lazy.nvim` as the plugin manager;
- Oil as a simple accessible file manager;
- Pyright as the Python language server;
- Neovim's native LSP auto-completion;
- Ruff through `nvim-lint`;
- practical LSP, linter, and Access Link mappings.

The preceding chapter,
[Setting up LSP, completion, and linters](language-tools.md), explains the
general behavior, additional languages, and the alternative `vim.pack` setup.

## Installing prerequisites

This configuration needs Neovim 0.12 or newer, Git, Node.js with npm, Pyright,
Ruff, and the Access Link components installed through the NVDA add-on. Lazy
downloads Oil, `nvim-lspconfig`, and `nvim-lint` itself on the first start. No
additional Python provider for Neovim or icon plugin is required.

The complete WinGet, apt, and dnf instructions are in the preceding chapter.
Before configuring Neovim, these checks must work in the same terminal in
which Neovim will run:

```text
nvim --version
git --version
pyright --version
ruff --version
```

When using Neovim through SSH or in tmux, install the Linux packages on the
Linux target. A Windows installation of Pyright or Ruff is not visible to the
remote Neovim process.

## Backing up an existing configuration

Neovim's configuration file is `%LOCALAPPDATA%\nvim\init.lua` on Windows and
`~/.config/nvim/init.lua` on Linux. Back up an existing file first. This
example replaces an existing `init.lua`; do not paste it alongside a
configuration already managed by LazyVim or another plugin manager.

On Windows, create and open the file with:

```powershell
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\nvim"
nvim "$env:LOCALAPPDATA\nvim\init.lua"
```

On Linux:

```bash
mkdir -p ~/.config/nvim
nvim ~/.config/nvim/init.lua
```

## Complete init.lua

Copy all of the following content and save it. The same tested file is
available in the
[GitHub repository](https://github.com/helmsaccess/neovim-access-link/blob/main/examples/neovim-lazy-python/init.lua).

<!-- BEGIN lazy-python-example -->
```lua
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
```
<!-- END lazy-python-example -->

## Why Access Link is explicitly listed for Lazy

By default, `lazy.nvim` resets Neovim's `packpath` and `runtimepath` and
disables normal start-plugin loading. The add-on installs its Neovim plugin in
Neovim's standard
`stdpath("data")/site/pack/nvim-nvda/start/nvim-nvda` location.

The example checks that path and passes it to Lazy as a local plugin with
`dir = access_link_path`. Lazy therefore loads the copy already installed by
the add-on even though normal package discovery is disabled. Do not remove
these lines or install another copy of the plugin from GitHub.

If the directory is missing, a warning is shown. Run the add-on's component
installation command from the NVDA menu first and restart Neovim. Building the
path from `stdpath("data")` works both for local Windows Neovim and for a
component installed on a Linux target.

## First start

Exit Neovim completely after saving and start it again. Lazy downloads its
three internet plugins on the first start, which can take a little time. Use
these checks afterwards:

| Check | Expected result |
|---|---|
| `:checkhealth lazy` | Lazy reports no fundamental installation error |
| `:checkhealth vim.lsp` | the Pyright configuration is enabled |
| `Space`, `l`, `s` | Access Link names Pyright after the server attaches to a Python file |
| `:Lazy` | Oil, `nvim-lspconfig`, and `nvim-lint` are shown as loaded |

In this variant, update plugins with `:Lazy update`, not `:packupdate`. The
generated `lazy-lock.json` records the plugin versions that were actually used.
Keep it together with a backed-up configuration.

## Operation

The keys in the following table are Neovim keys without the NVDA key. Neovim
executes the mapped actions; Access Link makes their results accessible through
speech and Braille.

| Key | Effect |
|---|---|
| `-` in Normal mode | open the current file's directory through Oil |
| `Enter` in Oil | open a file or subdirectory |
| `-` in Oil | move to the parent directory |
| `:write` in Oil | apply renamed, moved, or deleted entries after confirmation |
| `K` | request LSP hover text |
| `g`, then `d` | jump to the definition |
| `Ctrl+Space` in Insert mode | open native LSP completion |
| `Space`, `l`, `l` | run Ruff immediately |
| `[d` / `]d` | announce the previous / next diagnostic |
| `[D` / `]D` | announce the first / last diagnostic |
| `Space`, `d`, `d` | repeat the diagnostic at the cursor position |

Oil is deliberately not lazy-loaded, as recommended by its upstream
instructions. Deletions do not automatically go to the trash in this small,
portable configuration; Oil continues to show its confirmations, which Access
Link makes accessible.

The contextual NVDA gestures `NVDA+Space` for function signatures and
`NVDA+Shift+Space` for diagnostics are already built in. Access Link takes
them over only in the exact active connected Neovim pane; NVDA's standard
function remains available elsewhere. They are not reassigned in this
`init.lua` or in NVDA. Only detailed completion documentation may receive an
NVDA input gesture, as described in the preceding chapter.
