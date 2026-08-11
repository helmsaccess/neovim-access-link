# Current status

Status date: August 11, 2026. The source tree belongs to the 0.98.0 development
line; `buildVars.py` generates development builds with Git metadata and sets
the release channel to beta. The current published pre-release is 0.97.0. The
project does not infer a higher stability classification from test coverage or
feature count.

This page is the compact snapshot of implemented and verified behavior. See
[architecture](architecture.md) and the [feature matrix](accessibility.md) for
detail, the [changelog](changelog.md) for completed changes, and the
[plan](plan.md) for future work.

## Reference environment

The main practical path has been exercised with Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x, local Neovim 0.12.3, and Neovim 0.10.1 and 0.12.3 on
Rocky Linux 10.2 through OpenSSH for Windows 9.5p2. Local Windows Neovim, Linux
Neovim over SSH, and tmux inside an SSH session are covered. See
[compatibility](compatibility.md) for complete platform and version boundaries.

## Implemented end-to-end path

### Installation, connections, and ownership boundaries

- The `.nvda-addon` contains the NVDA integration, Neovim plugin, and a
  rootless Linux user package with bridge, protocol, and installer. The
  top-level `Neovim Access Link` menu opens settings, component management,
  and four localized installed HTML documents.
- The manifest provides the project URL and default help file. Development
  builds use the matching German or English unreleased changelog section;
  releases use their version section.
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
  edge and composition root; [architecture](architecture.md) describes the
  current boundary. The dated Appendix C only preserves the review basis at
  that time.

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
- Native incremental search reports preview matches, bounded match counts,
  wrapping at buffer boundaries, and visible search highlighting. Direct
  `inccommand` replacement in the current buffer reports the previewed line
  and bounded affected-line count for both `nosplit` and `split`.
- Quickfix and location lists report count, position, and the complete selected
  result row. Native replacement prompts present the row and position before
  Neovim processes the answer.
- Buffer-local replacement uses Neovim's result or falls back to the observed
  changed-line count. Multi-buffer replacement receives one summary of
  observed changed and unsaved buffers; Neovim's internal buffer visits do not
  appear as focus changes. Automated tests cover Quickfix files, listed
  buffers, and argument files, including an initially unloaded argument
  buffer. Guided L4 and L6 have not yet received complete practical acceptance
  under Windows/NVDA.
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
- Lazy's public `nofile`/`lazy` buffer receives an unambiguous focus context.
  Access Link speaks the current command row when the window opens; line
  navigation omits visual-only trailing spaces from speech. Documented
  lifecycle events neutrally report the start and end of install,
  update, cleanup, checking, log display, and synchronization through speech
  and Braille. Plugin rows, virtual progress, and success are not inferred;
  practical NVDA acceptance remains open.
- Native LSP rename remains entirely owned by Neovim and the language server.
  Access Link observes `LspRequest` and actual buffer changes, then reports one
  evidence-based completion instead of internal text, cursor, and context
  updates. The guided L5 test reports both references that were actually
  renamed without an extra buffer or focus transition. This workflow is
  automated but not yet practically accepted under Windows/NVDA.
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
The documentation build also checks complete German and English source sets,
parallel heading structures, Markdown links, generated HTML targets, and
language, title, and description metadata. GitHub Actions runs this build as a
dedicated job.
Windows users can additionally run parameterless `build.cmd` to build the
current development state. The wrapper uses only a temporary Python environment
and leaves the regular build and CI path unchanged.

## Verification evidence

Automated suites cover protocol and bounds, bridge, local and SSH clients,
multiple instances, focus and fail-open behavior, editor and presentation
planning, Lua with real headless Neovim processes, package contents,
localization, and documentation links. Pinned runs use Neovim 0.10.1 or 0.12.3
according to their purpose and exercise real completion, LSP, diagnostic, and
linter paths. The Clang-Tidy profile invokes the pinned binary directly, fixes
the language mode and supplied test configuration explicitly, and merges
standard and error output. The
markdownlint profile checks the absolute fixture instead of relying on a cold
stdin run; both parsers retain complete Windows drive and UNC paths.
Preflight and test helpers use one bounded 60-second wait for real providers.
This permits cold Windows and network-drive starts without waiting forever for
a stalled provider.
Listener-free, SSH, and real socket tests run separately. See the
[test strategy](testing.md) for commands and detail.
Guided practical tests isolate the remaining perceptual checks for speech,
Braille, sounds, focus, and response time. Their technical preflight confirms
real provider data and task-specific isolated key control. The compatibility
suite also includes four lazy.nvim tasks with fully local Git fixtures for its
window, installation, update, and synchronization; the individual selector
groups them under plugin management. The headless preflight does not require
Lazy's deliberately suppressed UI; it verifies the public command and
isolated fixture configuration. Fixture repositories disable line-ending
conversion and irrelevant Git output. Structure and safe key choices are
documented in [guided practical tests](human-testing.md).
For a real Lazy buffer the plugin also carries the first contiguous text block,
bounded to 2,048 UTF-8 bytes. Access Link therefore speaks the complete command
bar despite the initial layout-only blank line and width-dependent wrapping;
line navigation suppresses visual-only edge and padding spaces.

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
