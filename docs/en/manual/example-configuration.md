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

## Set up configuration through the component dialog

The `NVDA menu → Neovim Access Link → Install or update components...` dialog
offers three choices under `Neovim configuration`. The default `Do not change
Neovim configuration` changes only the Access Link components.

Component removal does not change this configuration or its backups. If the
configuration explicitly loads Access Link as a local plugin, remove or
disable that entry yourself after removing the components.

### Install a smaller basic configuration

`Install the basic Neovim configuration with lazy.nvim and Oil` creates a
smaller `init.lua` with Lazy, Oil, the bundled Access Link copy, and a few
straightforward defaults:

- Line numbers remain disabled.
- Tab inserts an actual tab character. Neovim uses two-column tab stops and a
  two-column indentation width. The basic configuration reapplies these
  values after Neovim's filetype-specific defaults, so they also apply to
  Python files, for which Neovim otherwise uses four spaces.
- Searches ignore case unless the search text contains an uppercase letter.
- New horizontal splits open below and vertical splits open to the right.
- In Normal mode, `Space`, then `o` opens Oil and `Space`, then `l` opens Lazy.
  These are sequential keys; Space is the leader.

LSP, language servers, and linters are not part of this basic configuration.

The option applies to every target selected in the same dialog. If the add-on
finds an `init.lua` or `init.vim` there, it first moves every existing file to
a uniquely named backup in the same directory and only then installs the new
`init.lua`. The results dialog names the new file and every backup path. If the
backup or atomic replacement cannot finish safely, that target reports a
failure. Symbolic links and unusual file types are not replaced.

On its first Neovim start, the basic configuration needs Git and access to
GitHub to download Lazy and Oil.

Use Neovim's normal navigation keys in Oil. `Enter` opens an entry, `-` moves
to the parent directory, and `Ctrl+C` closes the Oil buffer. Only `:write`
starts Oil's save and confirmation. Close Lazy with `q`. [Setting up LSP,
completion, and
linters](language-tools.md#update-plugins-with-lazynvim) describes accessible
Lazy operation.

The complete Python configuration below is a more extensive alternative. Use
it when Pyright, Ruff, and the documented LSP and linter keys should also be
configured.

### Copy the local Windows configuration to Linux

`Copy this computer's Neovim configuration to selected Linux connections`
transfers the complete contents of `%LOCALAPPDATA%\nvim` to every Linux
connection selected in the dialog. The local Windows entry can receive its
Access Link components at the same time; its configuration remains the source
and is not replaced.

On every Linux target, an existing Neovim configuration is first backed up as
a complete, uniquely named directory. The transferred configuration replaces
the target only after every file has been validated. Links and unusual file
types are not transferred. Component removal deletes neither the imported
configuration nor its backup.

Neovim reads Lua and Vimscript files without execute permission. Windows does
not provide reliable Linux execute permissions for custom helper scripts;
make directly invoked scripts executable on the Linux target when required.
You must also adjust Windows-specific absolute paths, programs, and shell
commands. The add-on does not rewrite user configuration.
Review the local directory for credentials and other content not intended for
the Linux target before copying it.

When the copied configuration uses Lazy, it must explicitly list the
installed Access Link copy as a local plugin with `dir = access_link_path`.
The configuration below builds `access_link_path` portably from
`stdpath("data")`, so the same code finds the installed copy on Windows and
Linux. The add-on does not insert this Lua statement automatically.

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
This code block is generated from that real Lua file, so the GitHub view and
the built manual remain identical to the executable source.

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
