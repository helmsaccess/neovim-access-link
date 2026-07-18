# Current status

Status date: July 18, 2026. Version: 0.94.1.

Version 0.94.1 is currently published as a GitHub prerelease. Project-defined
maturity remains between alpha and beta. This documentation does not infer a
higher stability classification from test coverage, version number, or feature
count.

Verification is risk-based and best-effort, not exhaustive. Automated suites
and practical reference workflows cannot anticipate every combination of NVDA,
Windows Terminal, Neovim, SSH, plugins, and user data. Defect reports are
reproduced, prioritized, and corrected as promptly as circumstances allow;
this chapter promises neither defect-free operation nor fixed response times.

This chapter is a snapshot. See `changelog.md` for feature history and
`plan.md` for planned work. Old feature-branch reports and intermediate
development builds are not descriptions of the current product and are
therefore not repeated chronologically here.

## Reference environment

The main practical path has been exercised with:

- 64-bit Windows 11 25H2;
- NVDA 2026.1.1;
- Windows Terminal 1.24.x;
- `OpenSSH_for_Windows_9.5p2` with LibreSSL 3.8.2 and key authentication;
- Rocky Linux 10.2;
- Neovim 0.10.1 and Python 3.12.13 on Linux.

Local `nvim.exe` on Windows is tested automatically with Neovim 0.10.1. F12
assignment, concurrent local and SSH sessions, and Oil were also exercised
practically with Neovim 0.12.3. This does not make 0.12.3 the sole reference
version; optional newer APIs remain feature-tested.

See `compatibility.md` for complete platform boundaries.

## Implemented end-to-end path

### Installation and connections

- The `.nvda-addon` contains the NVDA add-on, the local Neovim plugin, and a
  rootless Linux user package containing plugin, bridge, protocol, and
  installer.
- The component dialog can install, update, and remove local and saved SSH
  targets. No runtime download is required on the target.
- Local Windows sessions use a dynamic Neovim RPC port bound only to
  `127.0.0.1`.
- Remote Linux sessions use protocol v2 over SSH stdin/stdout and a private
  Unix RPC socket on the target.
- The file-based session registry discovers running Neovim instances. It is
  not the Windows Registry.
- A physical F12 press assigns the focused Neovim session to the concrete
  Windows Terminal control. Tabs, panes, and windows can hold separate local
  or remote connections.
- Nonce, session identity, sequence numbers, heartbeats, resync, and the first
  valid `fullState` constrain and authenticate the persistent path.
- Focus loss, deactivation, protocol errors, and transport loss restore native
  terminal output fail-open.

### Editor output

The semantic path covers, among other features:

- Normal, Insert, Replace, Visual, command-line, and terminal modes;
- character, word, and line navigation plus file and line boundaries;
- typing, deletion, replacement, selection, and search matches;
- built-in completion, signature help, diagnostics, folds, and messages;
- typed command-line state and the correlated return message of an Ex command;
- configurable focus output: no announcement, current line, or context with
  mode and saved connection name;
- separate speech, sound, and persistent Braille planning.

See `accessibility.md` for the feature matrix and known differences.

### Terminal and file-manager paths

- Terminal Insert and `terminalNormal` are separate states. Direct terminal
  input enables passthrough; a user-assignable NVDA command can return through
  the fixed `stopinsert` path.
- Command-line text, return mode, messages, buffer changes, and window/tab
  changes are correlated structurally rather than guessed from visible
  terminal text.
- Oil, netrw, mini.files, nvim-tree, and Neo-tree have normalized file-manager
  entries and automated workflow coverage. Navigation, edited names, boundary
  sounds, and confirmation flows have so far been exercised practically only
  with Oil under Windows and NVDA.
- Oil is a useful practical foundation. Automated or isolated coverage for the
  other managers is not a practical recommendation for them.

### Clipboard

Four globally discoverable, user-assignable NVDA commands can:

- copy the active Visual selection to Windows;
- copy Neovim register 0 to Windows;
- paste Windows clipboard text through `nvim_paste`;
- or replace register 0 and point the unnamed register at it.

Local and SSH connections use the same correlated, size-bounded path. There is
no automatic synchronization or retry.

### Localization and documentation

- English is the source language for the project interface; a complete German
  NVDA gettext catalog is built with it.
- The manifest, settings, tool dialogs, messages, and Speech Planner strings
  pass translation checks.
- The quick guide, user manual, and developer documentation are each built as
  German and English HTML.

## Current verification evidence

Maintained automated checks cover:

- Lua specifications and real headless Neovim runs;
- protocol, local-client, SSH-stdio, and bridge tests;
- NVDA-independent state, speech, Braille, and gate tests;
- add-on integration and built-package tests;
- localization, manifest, archive, and documentation checks.

Tests include bounds, invalid UTF-8, sequence gaps, resync, late replies, focus
changes, concurrent instances, clipboard correlation, terminal return, and
file-manager workflows.

Automated tests do not replace checks in NVDA, Windows Terminal, real SSH, or
on Braille hardware. See `testing.md` for exact commands and the practical
acceptance matrix.

## Practically confirmed use

Without claiming a complete platform matrix, practical checks have confirmed:

- installation and update of local and remote components;
- local and SSH F12 assignment;
- concurrent local and remote sessions across multiple tabs, panes, and
  Windows Terminal windows;
- switching remembered connections without takeover by unrelated shell
  controls;
- existing SSH and tmux sessions without terminating or restructuring them;
- focus announcements and connection names locally and remotely;
- all four clipboard commands locally and over SSH;
- terminal mode, command-line return, and buffer switching;
- Oil navigation, rename preview, sounds, and confirmation flows.

## Known limits

- Windows Terminal is the only approved terminal frontend. Other terminals and
  Neovim GUIs have no validated focus, identity, and fail-open adapters.
- Only the normal `%LOCALAPPDATA%\nvim-data` layout is supported. Portable
  installations and `NVIM_APPNAME` are not approved.
- An older Neovim version on Rocky Linux 9 did not connect with a current
  build. The cause and exact version boundary are uninvestigated, so no
  compatibility claim follows.
- No physical Braille display has been tested. Automated Braille planning and
  routing cannot exclude hardware or driver issues.
- Oil is the only file manager practically tested under Windows and NVDA.
  netrw, mini.files, nvim-tree, and Neo-tree need incremental real-world
  acceptance.
- Representative negative isolation cases for shells, tabs, panes, windows,
  focus loss, and closed controls need broader practical coverage.
- Long runtimes, repeated reconnects, very high event load, and many concurrent
  sessions need more stress testing.
- Language profiles, Windows/NVDA versions, and real SSH configurations are
  not broad enough for a general compatibility claim.

## Where to go next

- Understand the design: `architecture.md`
- Check concrete limits: `compatibility.md`
- Prioritize open work: `plan.md`
- Run or extend tests: `testing.md`
- Follow historical changes: `changelog.md`
