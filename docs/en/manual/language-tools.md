# Setting up LSP, auto-completion, and linters

Neovim Access Link makes existing LSP and diagnostic information accessible
to NVDA. It does not install programming languages, language servers, or
linters. A working setup therefore has three parts:

1. A **language server** provides features such as definitions, hover text,
   function signatures, completion, and often diagnostics.
2. A **linter** checks source code for additional errors, warnings, or style
   issues. A separate linter is optional if the language server's diagnostics
   are sufficient.
3. The **Neovim configuration** starts these tools and publishes their results
   through Neovim's public LSP and `vim.diagnostic` APIs. Access Link reads
   exactly this public data.

Do not install the Access Link plugin again in `init.lua` or load it with
`require()`. The add-on's component command already sets it up. The following
steps concern only the user's development tools.

Users who prefer a small complete configuration with `lazy.nvim`, Oil,
Pyright, and Ruff can follow the installation instructions and then continue
with [Small Python configuration with Lazy and Oil](example-configuration.md).
That chapter explicitly loads Access Link as an already installed local plugin
because Lazy changes Neovim's plugin search paths.

## Which computer needs the tools?

Language servers and linters must be available on the computer where Neovim
runs:

| Neovim is started as | Install language servers and linters on |
|---|---|
| local `nvim.exe` in Windows Terminal | Windows |
| `nvim` after an SSH login | the Linux target, from within the SSH session |
| `nvim` in tmux on a Linux target | the Linux target, not Windows |

For example, Pyright installed on Windows cannot be launched by a remote Linux
Neovim. Reopen the affected terminal after installation so a changed `PATH`
takes effect.

## Recommended beginner path

The complete example in this chapter requires Neovim 0.12 and Git. Access Link
itself also supports Neovim 0.10.1 and later, but the short modern `vim.pack`
and `vim.lsp.enable` configuration requires newer Neovim versions. For a new
configuration, updating to Neovim 0.12 is simpler and less error-prone than
following a parallel legacy setup.

First check the versions in the terminal:

```text
nvim --version
git --version
```

The Python example also needs Node.js with npm, Pyright, and Ruff. The
following commands install the base packages. Packages already present do not
need to be reinstalled.

### Windows with PowerShell and WinGet

```powershell
winget install --id Neovim.Neovim -e
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
npm install --global pyright
```

Ruff can be installed using one of the methods in the
[official Ruff instructions](https://docs.astral.sh/ruff/installation/), for
example `pipx install ruff` followed once by `pipx ensurepath` if `pipx` has
already been set up. Before using WinGet, check the currently available
package ID with `winget search ruff`. This is more reliable than copying an ID
that may have changed.

### Debian or Ubuntu

```bash
sudo apt update
sudo apt install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

### Fedora

```bash
sudo dnf install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

Distribution packages may contain an older Neovim. Check `nvim --version`
again and use the [official Neovim releases](https://github.com/neovim/neovim/releases)
if it is older than 0.12. If a global npm installation is denied by the local
npm policy, use the user-level npm setup recommended by Node.js or the
distribution instead of blindly retrying as administrator.

The executables must then be found in the same terminal:

```text
pyright --version
ruff --version
```

In PowerShell, `Get-Command pyright-langserver` shows the resolved path. On
Linux, `command -v pyright-langserver` serves the same purpose.

## Creating a new init.lua

Neovim's main configuration file is named `init.lua`. Common locations are:

| System | File |
|---|---|
| local Windows Neovim | `%LOCALAPPDATA%\nvim\init.lua` |
| Linux Neovim, including over SSH | `~/.config/nvim/init.lua` |

On Windows, create the directory in PowerShell and open the file directly in
Neovim:

```powershell
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\nvim"
nvim "$env:LOCALAPPDATA\nvim\init.lua"
```

On Linux:

```bash
mkdir -p ~/.config/nvim
nvim ~/.config/nvim/init.lua
```

Back up an existing `init.lua` first. If a plugin manager or LSP setup already
exists, copy only the relevant parts and do not install the same plugins a
second time.

## Complete minimal Python example

The following content can be used as a first complete `init.lua`. It

- installs `nvim-lspconfig` and `nvim-lint` on first start through Neovim's
  built-in `vim.pack`;
- starts Pyright for Python files;
- enables Neovim's built-in LSP completion;
- runs Ruff after saving a Python file;
- defines practical keys for LSP status, linting, and diagnostics.

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

-- nvim-lspconfig supplies the server configuration; Pyright itself must be
-- installed on PATH.
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

-- These Access Link commands avoid routine command-line input.
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

`vim.pack.add` downloads missing plugins on the first Neovim start. Later
normal starts do not reinstall them. Updates are deliberate through Neovim's
`:packupdate` workflow. Disable automatic linting for unknown or untrusted
source projects: Some linters, including ESLint, intentionally prefer an
executable from the current project and run it with the user's permissions.

After saving, exit Neovim completely and start it again. The first start can
take longer while the two plugins are downloaded. Then open a Python file
inside a project directory.

## Checking that the language server is running

The example maps Space, then `l`, then `s` to Access Link's LSP status. NVDA
should report a client such as Pyright. Press the keys in sequence, not at the
same time.

For one-time technical troubleshooting, use `:checkhealth vim.lsp` from
Neovim's command mode. Common causes of a missing client are:

- `pyright-langserver` is not on the `PATH` of the computer running Neovim;
- the file does not have the expected file type;
- Neovim was not restarted after installation;
- the server expects a project directory or project file;
- an older `init.lua` starts a second, conflicting client.

Neovim commonly recognizes projects from markers such as `.git`,
`pyproject.toml`, `package.json`, `go.mod`, or `Cargo.toml`. For the first test,
start Neovim in the root directory of a small project.

## Operating auto-completion

When an attached server supports completion, the example enables Neovim's
built-in menu. `autotrigger = true` lets the server open it for the server's
defined trigger characters; that does not necessarily mean every keystroke.
`Ctrl+Space` requests the list manually at any time.

| Insert-mode key | Action |
|---|---|
| `Ctrl+Space` | open LSP completion manually |
| `Ctrl+N` | select the next suggestion |
| `Ctrl+P` | select the previous suggestion |
| `Ctrl+Y` | accept the selected suggestion |
| `Ctrl+E` | cancel completion |

Access Link reports the selected item with position, type, source, and
available details. After the last candidate, Neovim's built-in menu
intentionally has one intermediate state with no selection; another
`Ctrl+N` selects the first item again.

For long documentation, assign a gesture under `NVDA menu → Preferences →
Input gestures... → Neovim Access Link` to “Read documentation for the
selected Neovim completion item or LSP hover”. Moving through and accepting
menu items remains ordinary Neovim input and requires no NVDA gesture.

No additional completion plugin is required. If `nvim-cmp` or `blink.cmp` is
already configured, keep using its existing keys; Access Link contains
adapters for both. Do not set up both plugins and native completion at once
while the source of a problem is still unknown.

## Inspecting function signatures and parameters

In Insert mode, Access Link automatically speaks the active parameter when the
cursor enters a call's argument list. After a comma, it reports the next
parameter selected by the language server. Returning to an already filled
earlier argument speaks that parameter again; movement within the same
argument remains silent. Nested calls select the innermost enclosing function.
With overloads, speech follows only the signature currently selected by the
language server. These brief hints are deliberately speech-only, so Braille
continues to show source text. The profile-aware “Automatically speak the
active function parameter while typing” checkbox under `NVDA menu →
Preferences → Settings... → Neovim Access Link → General` can disable them.

Automatic association uses structured LSP signature help rather than counting
visible commas. Strings, nested calls, and language-specific syntax therefore
do not confuse parameter position. If the language server does not return an
unambiguous active parameter, Access Link safely remains silent.

`NVDA+Shift+P` is already fixed in Access Link's Windows Terminal module. It
does not need to be assigned in NVDA or mapped in Lua. Place the cursor on the
function name or on the call's immediately associated opening or closing
parenthesis, press the gesture, and keep the NVDA key held:

| Held key | Action |
|---|---|
| `NVDA+h` / `NVDA+l` | show the previous / next parameter of the selected signature |
| `NVDA+k` / `NVDA+j` | show the previous / next signature |
| release the NVDA key | close the temporary view |

This feature needs signature help from the language server. If the server
provides only hover text and no structured signature help, Access Link can
show only that unstructured fallback.

The manual query deliberately accepts only unambiguous cursor positions. In
Normal mode it works on the function name and its directly associated opening
or closing parenthesis, but not inside a non-empty argument list. In Insert
mode it works on the function name and either parenthesis of an empty call.
Inside a non-empty argument list, the automatic active-parameter speech above
applies instead.

## Operating linter diagnostics

Pyright diagnostics appear automatically when the server publishes them. Ruff
runs after every save in the example. Press Space, `l`, `l` to run Ruff
manually as well. Messages arrive ready-made from the server or linter. Access
Link localizes severity names and controls but does not translate the tool's
free-form message text.

| Key | Action in the example configuration |
|---|---|
| `[d` / `]d` | previous / next diagnostic, wrapping at the ends |
| `[D` / `]D` | first / last diagnostic |
| Space, `d`, `d` | report the diagnostic at the current position again |
| hold `NVDA+Shift+E` | inspect diagnostics under the cursor, then on the same line |
| then `NVDA+k` / `NVDA+j` | cycle through multiple diagnostics on that line |

Like the parameter query, `NVDA+Shift+E` is already fixed. It requires no Lua
function and no custom NVDA assignment. The optional Lua mappings deliberately
use Access Link's diagnostic commands so that multiple findings from different
providers at the same position remain individually reachable. Errors and
warnings can produce diagnostic cues. Information and hint diagnostics are
spoken and shown in Braille but intentionally have no diagnostic cue.

If Pyright and Ruff report the same problem, two diagnostics with different
sources appear. Access Link has not duplicated or lost state. If this becomes
distracting, disable the overlapping rule in one tool or use only one
diagnostic provider.

## Adding more languages

Adding another language server normally takes two steps:

1. Install its executable by following its official instructions.
2. Add its configuration name to `vim.lsp.enable`.

For example:

```lua
vim.lsp.enable({ "pyright", "bashls", "gopls", "rust_analyzer" })
```

Extend `linters_by_ft` for more linters. List only tools that are actually
installed:

```lua
lint.linters_by_ft = {
  python = { "ruff" },
  c = { "clangtidy" },
  sh = { "shellcheck" },
  go = { "staticcheck" },
  rust = { "clippy" },
  lua = { "luacheck" },
  php = { "phpstan" },
  javascript = { "eslint" },
  typescript = { "eslint" },
  java = { "checkstyle" },
  markdown = { "markdownlint-cli2" },
}
```

Some tools also need project configuration: ESLint needs an
`eslint.config.js`, Checkstyle needs a rules file, and PHPStan normally uses a
`phpstan.neon`. A process can be installed correctly yet return no useful
results without that configuration.

## Language and tool overview

Access Link has no fixed allow-list of programming languages. Any provider
should work in principle when it publishes valid data through Neovim's LSP
client or `vim.diagnostic`. The following table lists common combinations and
their `nvim-lspconfig` and `nvim-lint` names.

| Language | common LSP server / configuration name | possible `nvim-lint` names | Access Link test scope |
|---|---|---|---|
| Python | Pyright / `pyright` | `ruff` | Pyright in practical tests; Ruff in real automated and practical tests |
| C and C++ | clangd / `clangd` | `clangtidy` | Clang-Tidy in real automated and practical tests |
| Markdown | Marksman / `marksman` or markdown-oxide / `markdown_oxide` | `markdownlint-cli2` | markdownlint in real automated and practical tests |
| Bash and POSIX shell | bash-language-server / `bashls` | `shellcheck` | ShellCheck in real automated tests |
| Go | gopls / `gopls` | `staticcheck` | Staticcheck in real automated tests |
| Rust | rust-analyzer / `rust_analyzer` | `clippy` | Clippy in real automated tests |
| Ruby | Ruby LSP / `ruby_lsp` | `rubocop` | RuboCop in real automated tests |
| Lua | Lua Language Server / `lua_ls` | `selene` or `luacheck` | provider and parser paths covered automatically |
| PHP | Intelephense / `intelephense` or Phpactor / `phpactor` | `phpstan` or `phpcs` | provider and parser paths covered automatically |
| JavaScript and TypeScript | typescript-language-server / `ts_ls` | `eslint` | provider and parser paths covered automatically |
| Java | Eclipse JDT LS / `jdtls` | `checkstyle` | Checkstyle SARIF and diagnostic path covered automatically |

“In principle” deliberately does not guarantee every version and project
configuration. Real automated runs currently cover C, Python, Bash, Go, Rust,
Ruby, and Markdown through `nvim-lint` and ALE. For Lua, PHP, JavaScript, and
Java, the public provider and parser contracts are covered, but not every
external tool installation in a real project matrix.

## Typical installation commands for additional tools

The following examples install only the external programs. Their matching
names must still be enabled in `init.lua`.

| Purpose | Windows | Debian/Ubuntu | Fedora |
|---|---|---|---|
| C/C++ with clangd and Clang-Tidy | `winget install --id LLVM.LLVM -e` | `sudo apt install clangd clang-tidy` | `sudo dnf install clang-tools-extra` |
| ShellCheck | `winget install --id koalaman.shellcheck -e` | `sudo apt install shellcheck` | `sudo dnf install ShellCheck` |
| prepare Go tools | `winget install --id GoLang.Go -e` | `sudo apt install golang-go` | `sudo dnf install golang` |
| prepare a Java runtime | select a current JDK ID with `winget search Temurin` | `sudo apt install default-jdk` | `sudo dnf install java-21-openjdk-devel` |
| prepare PHP and Composer | select current IDs with `winget search PHP` and `winget search Composer` | `sudo apt install php-cli composer` | `sudo dnf install php-cli composer` |
| prepare Lua and LuaRocks | select current IDs with `winget search Lua` and `winget search LuaRocks` | `sudo apt install lua5.4 luarocks` | `sudo dnf install lua luarocks` |

Language-specific tools are then commonly installed with the language's own
package manager:

```text
# Node-based servers and tools
npm install --global bash-language-server
npm install --global typescript typescript-language-server
npm install --global markdownlint-cli2

# Go
go install golang.org/x/tools/gopls@latest
go install honnef.co/go/tools/cmd/staticcheck@latest

# Rust with an existing rustup installation
rustup component add rust-analyzer clippy

# Lua
luarocks install luacheck

# PHP within a project
composer require --dev phpstan/phpstan

# JavaScript or TypeScript within a project
npm install --save-dev eslint
```

For Rust, [rustup](https://rustup.rs/) is the official installation route.
Lua Language Server, Eclipse JDT LS, Marksman, and other independently
published servers should be installed according to their respective upstream
instructions. Before adding one to `init.lua`, always verify that its startup
command can be found in the terminal. The commands and project markers expected
by `nvim-lspconfig` are documented in Neovim under `:help lspconfig-all`.

## Existing completion and linter plugins

In addition to Neovim's built-in menu, Access Link explicitly supports
`nvim-cmp` and `blink.cmp`. Diagnostics from ALE and `none-ls.nvim` are also
accessible when they ultimately appear in `vim.diagnostic`. Users who already
have one of these systems working do not need to switch to the minimal example.
The important rules are:

- do not start the same language server more than once;
- do not map multiple completion systems to the same keys;
- ensure linter results are published through `vim.diagnostic`;
- when troubleshooting, start with one language server, native Neovim
  completion, and one linter.

The next chapter, [Menus and completion](menus-and-completion.md), describes
the interaction and details presented by Access Link.
