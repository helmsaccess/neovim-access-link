# Compatibility

This page separates approved platform boundaries, automated plugin contracts,
and practical reference checks. An automated contract is not a promise for
every user setting or presentation.

## Confirmed reference platform

| Component | Reference state |
|---|---|
| Windows | Windows 11 25H2, 64-bit |
| NVDA | 2026.1.1; manifest minimum 2026.1 |
| Terminal frontend | Windows Terminal 1.24.x |
| Local Neovim | 0.12.3 practical; 0.10.1 automated |
| SSH client | OpenSSH for Windows 9.5p2 with key-based login |
| Linux | Rocky Linux 10.2, kernel 6.12.0-211.28.1.el10_2 |
| Remote Neovim | 0.10.1 and 0.12.3 |
| Linux bridge | Python 3.12.13 in the reference environment |

Neovim 0.10.1 is the provisional minimum. Newer optional APIs are used only
after a feature check. On Neovim 0.10, the plugin creates a silent `<Ignore>`
mapping for an otherwise unbound F12 in Insert mode because only Neovim 0.11
and later can consume keys through the return value of `vim.on_key`. Existing
user mappings remain unchanged.

## Approved scope and limits

- Windows Terminal is the only approved frontend. Other terminals and
  graphical Neovim frontends need dedicated identity, focus, presentation,
  and fail-open adapters.
- Windows supports the normal `%LOCALAPPDATA%\nvim-data` layout. Portable
  installations and data paths separated with `NVIM_APPNAME` are not approved.
- Local Windows Neovim, Linux Neovim over SSH, and tmux within an SSH session
  are implemented. Mixed local and remote tabs, panes, and windows have been
  practically exercised.
- Configurable terminal commands belong to the Windows Terminal AppModule.
  Dispatch revalidates the concrete AppModule and control identity.
- Verification is risk-based and not exhaustive. Other Windows, NVDA, Neovim,
  SSH, language, and Braille combinations may contain undiscovered defects.

## Plugin and tool contracts

The test matrix runs the versions pinned by the test tools on Neovim 0.10.1
and 0.12.3. It includes:

- `nvim-cmp` and `blink.cmp` for completion;
- `nvim-lint`, ALE, and `none-ls.nvim` for provider-neutral diagnostics through
  `vim.diagnostic`;
- Clang-Tidy, Ruff, ShellCheck, Staticcheck, Clippy, RuboCop, and
  `markdownlint-cli2` as real linter processes.

The checkouts, language runtimes, and tools are test dependencies and are not
shipped. Languages are not hard-coded into the add-on. Another language server
or linter is described as automated coverage only after a real pinned contract
test confirms the same semantic path.

Oil, netrw, mini.files, nvim-tree, and Neo-tree use public APIs or documented
events. If a required event is absent or a public API changes incompatibly,
cursor-driven output remains active; the add-on does not start general polling
as a replacement. Only Oil is practically tested under Windows/NVDA. The
other file managers have automated or isolated coverage.

## Braille scope

Braille routing, standard navigation, speech exploration, Braille exploration,
and the `z=` suggestion view have been practically exercised in the reference
path with a Papenmeier BRAILLEX EL 80c. Automated tests cover additional state,
Unicode, tab, viewport, and multi-session cases.

This proves one hardware and driver combination, not every display,
translation table, or input mapping. Braille planning expands tabs from
`tabstop` and text positions. A zero-width or double-width terminal character
can therefore change the number of visible blank cells relative to Neovim's
virtual screen column; UTF-8 routing remains correct.

## Build and documentation dependencies

MessagePack Python 1.1.1 is bundled into the add-on and Linux component
package. The Linux target therefore needs no separate MessagePack or pynvim
package.

Python 3, ConfigObj, and Pandoc are used only for tests or builds. ConfigObj
validates the add-on manifest with NVDA-compatible INI semantics; Pandoc
creates the standalone HTML documents. These tools are not included in the
installed plugin or add-on. See [dependencies](dependencies.md) and the [test
strategy](testing.md) for detail.

## Primary sources

- [Neovim API](https://neovim.io/doc/user/api/)
- [Neovim Lua Guide](https://neovim.io/doc/user/lua-guide/)
- [NVDA Developer Guide](https://download.nvaccess.org/documentation/developerGuide.html)
- [NVDA source](https://github.com/nvaccess/nvda)

Project-specific NVDA assumptions are recorded in the [NVDA API
boundaries](nvda-2026.1-api-notes.md).
