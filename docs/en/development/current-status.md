# Current status

Status date: August 5, 2026. The source tree belongs to the 0.97.0 development
line; `buildVars.py` generates the exact development build number and Git
metadata. The current published beta pre-release is 0.96.0. The project does
not infer a higher stability classification from test coverage or feature
count.

This page is the compact snapshot of implemented and verified behavior. See
[architecture](architecture.md) and the [feature matrix](accessibility.md) for
detail, the [changelog](changelog.md) for completed changes, and the
[plan](plan.md) for future work.

## Reference environment

The main practical path has been exercised with Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x, OpenSSH for Windows 9.5p2, Rocky Linux 10.2, and
Neovim 0.10.1 or 0.12.3. Local Windows Neovim, Linux Neovim over SSH, and tmux
inside an SSH session are covered. See [compatibility](compatibility.md) for
complete platform and version boundaries.

## Implemented end-to-end path

### Installation, connections, and ownership boundaries

- The `.nvda-addon` contains the NVDA integration, Neovim plugin, and a
  rootless Linux user package with bridge, protocol, and installer. The Tools
  dialog installs, updates, or removes local and saved SSH targets.
- Local sessions use dynamic TCP bound only to `127.0.0.1`; remote sessions use
  SSH stdin/stdout and a private Unix RPC socket. Short-lived JSON files, not
  the Windows Registry, provide session discovery.
- A physical F12 press assigns the running Neovim instance to the exact focused
  Windows Terminal control. Multiple windows, tabs, and panes retain
  independent local, remote, or ordinary shell sessions.
- Authentication, sequences, heartbeats, resync, and focus correlation bound
  the persistent path. Disconnects, invalid state, or uncertain focus identity
  restore NVDA's native terminal behavior fail-open.
- The AppModule owns Windows Terminal events and `nextHandler`. Dedicated
  services own focus, session assignment, connections, editor state, settings,
  presentation, and runtime. The Global Plugin remains the process-wide NVDA
  edge and composition root; [architecture](architecture.md) and
  [Appendix C](global-plugin-appmodule-audit-2026-08-04.md) describe the current
  boundary.

### Editor and presentation

The semantic path handles Normal, Insert, Replace, Visual, Select,
Operator-pending, Command-line, and terminal modes. It covers navigation,
typing, deletion, replacement, selection, search, folds, buffer, window, and
tab changes, plus structured Neovim messages.

- Speech and cues report mode, characters, words, lines, indentation,
  boundaries, and configurable focus context.
- Speech exploration reads characters, words, and lines without moving the
  real cursor. Structured Braille supports routing, standard navigation,
  repeated-routing actions, and a per-session Braille exploration mode.
- Neovim built-in completion, `nvim-cmp`, and `blink.cmp` provide selection,
  type, source, and available documentation. LSP hover, signature help,
  automatic active parameters, and held parameter views are correlated and do
  not move the editor cursor.
- Diagnostics from `vim.diagnostic` can be read at the current, previous, next,
  first, and last position. Held diagnostic views and error, warning, and
  empty-result cues use the same validated data path.
- Neovim's native `z=` suggestions are accessible through speech, Braille, and
  contextual NVDA commands. Spelling feedback follows NVDA's separate document
  formatting settings.

### Development tools, terminal, and files

- LSP data and diagnostics remain provider-neutral. Automated contracts cover
  native LSP completion, `nvim-cmp`, `blink.cmp`, `nvim-lint`, ALE, and
  `none-ls.nvim`; users install the applicable external language servers and
  linters themselves.
- Direct input in a Neovim terminal buffer uses native terminal pass-through.
  Terminal-Normal mode, command-line return, process exit, and buffer changes
  remain structured.
- Oil, netrw, mini.files, nvim-tree, and Neo-tree have normalized adapters and
  automated basic workflows. Oil is the only file manager practically tested
  under Windows/NVDA.
- Four assignable commands transfer a Visual selection, register 0, or Windows
  clipboard text explicitly and with correlation. There is no automatic
  clipboard synchronization.

### Localization and documentation

English is the UI source language; the complete German gettext catalog is
verified and packaged. The Quick Guide, user manual, developer documentation,
and guided practical-test guide are built in German and English as eight
validated HTML files. The copyable Neovim example comes from one real tested
Lua file and is synchronized identically into both manuals.

## Verification evidence

Automated suites cover protocol and bounds, bridge, local and SSH clients,
multiple instances, focus and fail-open behavior, editor and presentation
planning, Lua with real headless Neovim processes, package contents,
localization, and documentation links. Pinned matrices cover Neovim 0.10.1 and
0.12.3 plus real completion, LSP, diagnostic, and linter paths. Listener-free,
SSH, and real socket tests run separately. See the [test
strategy](testing.md) for commands and detail.

Practical confirmation includes:

- local and remote component installation and updates;
- concurrent local and SSH sessions across multiple windows, tabs, and panes;
- focus transitions between connected Neovim and ordinary shell controls;
- navigation, speech exploration, mode, buffer, and terminal transitions;
- Braille routing, both Braille modes, and spelling suggestions with a
  Papenmeier BRAILLEX EL 80c;
- all four clipboard paths locally and over SSH, plus Oil navigation, rename,
  and confirmation workflows.

Verification is risk-based and best-effort, not exhaustive. Automated and
practical reference workflows do not replace acceptance of every combination
of NVDA, Braille hardware, Neovim, plugins, and user data.

## Known limits

- Windows Terminal is the only supported frontend. Other terminals and
  graphical Neovim frontends have no approved adapter.
- Windows expects the normal `%LOCALAPPDATA%\nvim-data` layout; portable
  installations and data paths separated with `NVIM_APPNAME` are not approved.
- Only Oil has practical Windows/NVDA file-manager confirmation. The other
  adapters have automated, not practical, coverage.
- The practical Braille result covers one hardware and driver combination,
  not every display, translation table, or input mapping.
- External completion plugins, language servers, and linters are supported
  through their documented public contracts; no exhaustive plugin and version
  matrix is promised.

## Further references

- [Compatibility](compatibility.md) for platforms, versions, and evidence level;
- [feature matrix](accessibility.md) for individual accessible workflows;
- [test strategy](testing.md) and [guided practical tests](human-testing.md)
  for evidence;
- [changelog](changelog.md) for completed work and [plan](plan.md) for intended
  work.
