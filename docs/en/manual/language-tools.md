# Setting up LSP, completion, and linters

Neovim Access Link makes information accessible that Neovim already receives
from language servers and linters. The add-on does not install these tools.

- A **language server (LSP)** provides completion, function signatures, hover
  text, definitions, and diagnostics.
- A **linter** reports additional errors, warnings, or style problems. It is
  optional when the language server's diagnostics are sufficient.
- The **Neovim configuration** starts the tools. Access Link reads their
  results through Neovim's public LSP and diagnostic APIs.

Language servers and linters run on the same computer as Neovim:

| Neovim runs | Install the tools on |
|---|---|
| locally as `nvim.exe` in Windows Terminal | Windows |
| after an SSH login | the Linux target |
| in tmux on the Linux target | the Linux target |

Pyright installed on Windows is not available to a remote Linux Neovim. Reopen
the terminal after installation so a changed `PATH` takes effect.

## Access Link plugin and plugin managers

The add-on's component command already installs the Access Link plugin. Do not
install a second copy from a plugin repository or load it again with
`require()`.

An unchanged or simple Neovim configuration loads the installed copy as a
start package. A plugin manager that replaces `packpath` or start-package
loading must instead register this exact local copy. [Small Python
configuration with Lazy and Oil](example-configuration.md) demonstrates this
special case for `lazy.nvim`.

After restarting Neovim, confirm that the plugin is loaded:

```vim
:echo exists(':NvimNvdaSessionName')
```

The result `2` confirms that the command is available.

## Recommended beginner path for Python

The following example uses Neovim 0.12, Git, Pyright, and Ruff. Access Link
supports Neovim 0.10.1 and later, but the short configuration with `vim.pack`
and `vim.lsp.enable` requires the newer Neovim API.

Check first:

```text
nvim --version
git --version
```

### Install the tools

On Windows with PowerShell and WinGet:

```powershell
winget install --id Neovim.Neovim -e
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
npm install --global pyright
```

Install Ruff by following its
[official installation guide](https://docs.astral.sh/ruff/installation/), for
example with `pipx install ruff` when `pipx` is configured.

On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

On Fedora:

```bash
sudo dnf install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

Distribution packages sometimes contain an older Neovim version. Check
`nvim --version` and use Neovim 0.12 for this example. Then check in the same
terminal:

```text
pyright --version
ruff --version
```

PowerShell shows the resolved server with `Get-Command pyright-langserver`.
On Linux, use `command -v pyright-langserver`.

### Create init.lua

Neovim's main configuration is normally stored here:

| System | File |
|---|---|
| Windows | `%LOCALAPPDATA%\nvim\init.lua` |
| Linux, including SSH | `~/.config/nvim/init.lua` |

Back up an existing configuration. If a plugin manager or LSP setup already
exists, copy only the required parts and do not start the same language server
twice.

The following minimal `init.lua` installs `nvim-lspconfig` and `nvim-lint`,
starts Pyright, enables Neovim's built-in completion, and runs Ruff after a
Python file is saved:

```lua
vim.g.mapleader = " "

vim.opt.completeopt = { "menu", "menuone", "noselect", "popup" }
vim.diagnostic.config({
  signs = true,
  underline = true,
  virtual_text = true,
  severity_sort = true,
  update_in_insert = false,
})

vim.pack.add({
  { src = "https://github.com/neovim/nvim-lspconfig" },
  { src = "https://github.com/mfussenegger/nvim-lint" },
})

vim.lsp.enable("pyright")

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

local lint = require("lint")
lint.linters_by_ft = {
  python = { "ruff" },
}

vim.api.nvim_create_autocmd("BufWritePost", {
  callback = function()
    lint.try_lint()
  end,
})

vim.keymap.set("n", "<leader>ll", function()
  lint.try_lint()
end, { desc = "Run the linter now" })

vim.keymap.set("n", "[d", "<Cmd>NvimNvdaDiagnosticPrevious<CR>",
  { desc = "Previous diagnostic" })
vim.keymap.set("n", "]d", "<Cmd>NvimNvdaDiagnosticNext<CR>",
  { desc = "Next diagnostic" })
vim.keymap.set("n", "[D", "<Cmd>NvimNvdaDiagnosticFirst<CR>",
  { desc = "First diagnostic" })
vim.keymap.set("n", "]D", "<Cmd>NvimNvdaDiagnosticLast<CR>",
  { desc = "Last diagnostic" })
vim.keymap.set("n", "<leader>dd", "<Cmd>NvimNvdaDiagnosticCurrent<CR>",
  { desc = "Diagnostic at the current position" })
vim.keymap.set("n", "<leader>ls", "<Cmd>NvimNvdaLspStatus<CR>",
  { desc = "Report LSP status with Access Link" })
```

`vim.pack.add` downloads the two missing plugins on the first start. After
saving, exit Neovim completely, restart it, and open a Python file in the root
directory of a small project.

Automatic linting runs tools with your user permissions. Use it only in
trusted projects. Some linters deliberately prefer an executable from the
current project.

## Verify the setup

The example maps the sequence `Space`, `l`, `s` to the LSP status. Press the
three keys in order. NVDA names the active client, for example Pyright.

This sequence is a **Neovim command without the NVDA key**: Neovim executes it,
and Access Link makes the result accessible. Combinations with the NVDA key
belong to screen-reader control and are handled by Access Link only in the
appropriate connected Neovim context.

If no client is active, check:

1. `pyright-langserver` is found on the computer where Neovim runs.
2. The open file has the `python` file type.
3. Neovim was restarted after installation.
4. Neovim was opened in the project directory.
5. An existing configuration does not start a second conflicting client.

For technical details, `:checkhealth vim.lsp` shows Neovim's own LSP status.

## Use completion and diagnostics

The example uses these Neovim keys without the NVDA key:

| Key or sequence | Task |
|---|---|
| `Ctrl+Space` | request completion in Insert mode |
| `Ctrl+N` / `Ctrl+P` | select the next / previous item |
| `Ctrl+Y` / `Ctrl+E` | accept the selection / close the menu |
| `[d` / `]d` | previous / next diagnostic |
| `[D` / `]D` | first / last diagnostic |
| `Space`, `d`, `d` | report the diagnostic at the current position |
| `Space`, `l`, `l` | run Ruff immediately |

Access Link speaks and displays on Braille the information supplied by Neovim.
The complete operation of completion, function signatures, and diagnostics is
documented in [Menus, completion, and diagnostics](menus-and-completion.md).

## Other languages and existing plugins

Access Link processes valid completion, LSP, and `vim.diagnostic` data provided
by Neovim. For another language, install its server using the server's official
instructions and enable the appropriate `nvim-lspconfig` name. For example:

```lua
vim.lsp.enable({ "pyright", "bashls", "gopls", "rust_analyzer" })
```

Pyright and Ruff are among the practically tested combinations. Other real or
isolated automated checks cover C/C++, Markdown, shell, Go, Rust, Ruby, Lua,
PHP, JavaScript/TypeScript, and Java. This is not a guarantee for every tool
version and project configuration. The current test status is listed in the
[compatibility overview](../development/compatibility.md).

Existing setups with `nvim-cmp`, `blink.cmp`, ALE, or `none-ls.nvim` can remain
in use when they publish results through the Neovim interfaces supported by
Access Link. Use only one completion system for a buffer and do not start the
same language server more than once.
