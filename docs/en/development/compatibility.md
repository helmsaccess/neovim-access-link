# Compatibility

## Confirmed reference platform

- Windows 11 25H2, 64-bit; NVDA 2026.1.1; Windows Terminal 1.24.x.
- `OpenSSH_for_Windows_9.5p2`, `LibreSSL 3.8.2`, key-based login.
- Rocky Linux 10.2, kernel 6.12.0-211.28.1.el10_2.
- Neovim 0.10.1 (`neovim-0.10.1-4.el10_0.x86_64`) with LuaJIT.
- Python 3.12.13 for the bundled Linux bridge.

Neovim 0.10.1 is the provisional minimum. Newer optional APIs require feature
tests. NVDA manifest values are minimum 2026.1 and last tested 2026.1.1; this
boundary intentionally follows NVDA's 64-bit Python 3.13 transition.
Configurable terminal scripts reside in the Windows Terminal AppModule. NVDA
2026.1.1 initially lists them after Windows Terminal was focused before opening
Input Gestures and does not resolve them in unrelated applications. Its user
map may still display a saved assignment elsewhere after the class has loaded;
dispatch also revalidates the concrete AppModule and control identity.

Completion API-contract tests use `nvim-cmp`
`2ffe79f1f021def8dd1fcd81deb16f1bb0d989f3` and `blink.cmp` v1.10.2 on
Neovim 0.10.1 and 0.12.3. Provisional `blink.cmp` v2 commit
`d33327a0ed7bfe3cd5dfa2fdd2738ad74f9e0ea3` is tested with `blink.lib`
`5876dd95deeb70aadbe9f1c0b7117a135061cdac` only on Neovim 0.12.3. The
checkouts are not bundled. This proves module/API attachment with injected
selection values, not every practical rendering or NVDA configuration.

Diagnostic-provider contract tests use `nvim-lint`
`a219b2c9e5b4765e5c845aba119dad55806fcaf1` and ALE
`9e2efaa4d348b1f93200b24e5540c670eb6fdd3f`, plus `none-ls.nvim`
`01f8e62ea11603e59ad9ff7afcfa94fd183f76d6` with `plenary.nvim`
`74b06c6c75e4eeb3108ec01852001636d85a932b`, on Neovim 0.10.1 and 0.12.3.
They actually run Clang-Tidy 22.1.8 for C, Ruff 0.15.4 for Python, ShellCheck
0.11.0 for Bash, Staticcheck 2026.1 for Go, Clippy from Rust 1.97.1, RuboCop
1.88.2 for Ruby, and `markdownlint-cli2` 0.23.2 for Markdown and publish
through `vim.diagnostic`. The checkouts, runtimes, and tools are test-only
dependencies and are not bundled. A built-in none-ls source additionally
confirms the LSP bridge without an external tool. This proves the semantic
Linux contract, not installation, project configuration, or practical
Windows/NVDA output.

Languages are not hard-coded into the add-on. The standalone Go and Rust
linters are now covered by automation; `gopls` and `rust-analyzer`, reserved
for the later combined practical LSP round, use the same contract. Another
combination is described as covered by real automation only after a pinned
contract test exists.

The local Windows CLI and parallel local/SSH tabs were tested. Automatic F12
binding and the following RPC connection were also confirmed practically with
Neovim 0.12.3 on Windows. Windows Terminal is the only approved front end.
PuTTY or another terminal requires a dedicated
identity, focus, output, suppression, and fail-open adapter.

File-manager support uses the public APIs of the Oil, nvim-tree, Neo-tree, and
mini.files main branches checked on July 12, 2026. The event layer was checked
again on July 18 and uses `OilMutationComplete`, mini.files User autocmds,
nvim-tree public `api.events`, and Neo-tree's public event module. If an event
is absent or a public API changes incompatibly, cursor-driven adapter output
continues fail-open; polling is not started as a replacement.
Only Oil with Neovim 0.12 has so far been practically tested under
Windows/NVDA. Its navigation, edited name, cues, and confirmation work and
provide a solid foundation. netrw, mini.files, nvim-tree, and Neo-tree have not
yet received practical Windows acceptance and will follow incrementally. Their
evidence below is automated or isolated unless explicitly stated otherwise.
The netrw fallback is automated against version 184 from Neovim 0.12.3 and
version 173 from the Neovim 0.10.1 reference version in thin, long, wide, and
tree presentation. A broader practical matrix has not yet been confirmed under
Windows/NVDA.
The public nvim-tree option `select_prompts = true` and Neo-tree option
`use_popups_for_input = false` route their dialogs through
`vim.ui.select/input`; Access Link never changes them automatically. Oil keeps
its custom confirmation float without a public prompt source. A narrow
`oil_preview` real-float fallback is verified against the real Oil main branch
on Neovim 0.12.3 for rename, duplicate, delete, and Y/N; it carries only fixed
action and count, never rendered paths. mini.files and other Lua calls to
`vim.fn.confirm` are captured semantically on both Neovim reference versions.
Public action forms, including long type names such as `directory` and
`symbolicLink`, are normalized; a complete practical operation matrix remains
open.

The `z=` suggestion path, including restoration of the editor line, was
successfully tested with one physical Braille display. Automated Braille tests
cover further state and planning cases, but hardware-specific defects outside
the practically tested path may remain undiscovered. The neutral Braille
planner expands tabs from `tabstop` and the preceding Unicode code-point
position. If a zero-width or double-width terminal character precedes a tab,
the number of blank Braille cells can therefore differ from Neovim's virtual
screen column; routing still resolves to the correct UTF-8 text position. A
future exact display-width mapping must come from semantic Neovim state, not
screen scraping or a second Unicode-width table in the add-on. Other
Windows/NVDA/Neovim versions, SSH variants, languages, and many add-on features
also lack exhaustive practical coverage. The supported state is beta.

An older Neovim on Rocky Linux 9 did not connect with the current build; no
compatibility promise is made for it. GUI front ends, portable Windows layouts,
and `NVIM_APPNAME` are unsupported.
Because only Neovim 0.11 and later can consume a key through the return value
of `vim.on_key`, the plugin installs a silent `<Ignore>` mapping on 0.10 only
for an otherwise-unbound F12 in Insert mode. This keeps the physical claim
observable without inserting `<F12>` into the buffer and preserves existing
user mappings.
