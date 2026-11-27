# Current status

Status date: November 27, 2026. The source tree develops the 0.99.0 line.
`buildVars.py` derives the version identifier from the development build
number, branch, and commit and sets the manifest update channel to beta.
The latest published pre-release is 0.98.0.

Changes enter `main` through pull requests. The
[version and release guide](release-and-build.md) defines the release checks,
dated bilingual changelogs and separate GitHub and Store publication steps.
Pull requests include an English changelog covering the full diff.

This page is the compact snapshot of implemented and verified behavior. See
[architecture](architecture.md) and the [feature matrix](accessibility.md) for
detail, the [changelog](changelog.md) for completed changes, and the
[plan](plan.md) for future work.

The [guided workflow socket tests](testing.md#guided-workflows-over-real-neovim-rpc)
exercise Neovim mappings, real providers and the authenticated protocol with
Neovim 0.12.x. They verify the data delivered for held signatures and
diagnostics. The Python diagnostic tasks wait for results from Ruff and
Pyright. Windows focus and NVDA presentation have separate evidence.

## Reference environment

The earlier local and SSH reference run used Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x, local Neovim 0.12.3, and Neovim 0.10.1 and 0.12.3 on
Rocky Linux 10.2 through OpenSSH for Windows 9.5p2. Local Windows Neovim, Linux
Neovim over SSH, and tmux inside an SSH session are covered. The final field
test of development build 3 under NVDA 2026.2beta10 covered automatic F12
bindings, frequent switching between local and remote panes and another
Windows Terminal window, ending and restarting remote Neovim, and native typing
echo outside the active session. Bindings remained distinct and active, and
disconnected SSH snapshots caused no false reconnections.

On Windows, the packaged add-on started in an isolated NVDA 2026.3.1 profile.
The NVDA integration and Windows Terminal AppModule loaded successfully.
Neovim 0.12.6 passed the Lua and local TCP tests. The packaged NVDA client
received an authenticated full state. An automated run on an active Windows 11
guest desktop with NVDA 2026.3.1, Windows Terminal 1.25, and Neovim 0.12.6
confirmed F12, editing, separate panes, tab and window switching, and focus
recovery after an editor exited. The same scenario passed with NVDA 2026.1.1
and Neovim 0.10.1. Digital speech, Braille cells, and tone
requests were captured in NVDA 2026.1.1 and 2026.3.1.
The manifest lists NVDA 2026.3.1 as last tested and retains 2026.1 as its minimum.
See [compatibility](compatibility.md) for details.

## Implemented end-to-end path

The Windows development build and Linux release builder use SCons for the
add-on. The base manifest, localized manifests, and gettext sources follow the
NVDA AddonTemplate layout. Documentation and Linux component builds remain
separate steps.
Package metadata and bundled Python line endings are platform independent.

The shared Neovim RPC client validates message structures and bounds setup,
its receive buffer, and pending notifications. Controls use the verified and
registered channel.
Failed SSH attempts reap their own process before a retry.

### Installation, connections, and ownership boundaries

- The `.nvda-addon` contains the NVDA integration, Neovim plugin, and a
  rootless Linux user package with bridge, protocol, and installer. The
  top-level `Neovim Access Link` menu opens settings, component management,
  and four localized installed HTML documents.
- Component installation can install a small basic configuration with Lazy
  and Oil through a choice that remains unchanged by default. Existing regular
  `init.lua` and `init.vim` files are first moved to unique backup paths; the
  results dialog names the installation and backups. The basic configuration
  uses actual tab characters on two-column tab stops even after
  filetype-specific defaults, no line numbers, and leader commands for
  Oil and Lazy. An isolated headless startup with real local Access Link,
  Lazy, and Oil directories is checked under Neovim 0.10.1. Alternatively, it
  copies the complete local Windows configuration to selected Linux
  connections after bounding and validating links, file types, paths, and
  sizes. An existing Linux configuration is atomically backed up as a complete
  directory. The
  add-on does not rewrite Windows-specific content; Lazy must explicitly load
  the installed Access Link copy as a local plugin. Automated tests cover
  archiving, local and rootless Linux package paths, SSH transfer, and rollback.
  The basic configuration has practical local Windows acceptance; practical
  acceptance of copying configuration to Linux over SSH remains pending.
- Component removal requires explicit, default-declined confirmation after
  target selection. It removes only the installed plugin locally and also the
  bridge and related component paths on Linux. Neovim configuration and backups
  remain unchanged; explicit plugin load entries remain owned by user
  configuration.
- The manifest follows the NVDA template with the project URL, default help
  file, update channel, and localized changelog. Development builds on the
  0.99.0 line use the `Unreleased` section; the Store comparison version
  remains 0.96.0 until an actual Store publication. The package build
  rejects missing, empty, unknown, or malformed template fields and verifies
  the default English help plus the German localization manifest.
- The documentation job and Linux release build use the respective official
  Pandoc 3.1.11.1 binary from an archive with a verified digest. The Windows
  development build accepts an installed Pandoc 3.1.11.1 and
  otherwise uses the verified binary temporarily. CI and normal Linux
  development validate in temporary directories only. `build.cmd` creates
  development artifacts in the local Windows checkout;
  `tools/build_release.py` creates the later
  published assets only from clean Linux `main` with approved release
  metadata.
- `NVDA+Alt+N` is the default activation gesture and remains reassignable in
  Input Gestures. It continues to belong to the Windows Terminal AppModule;
  outside a matching focused control, the native keyboard path remains intact.
- Local sessions use dynamic TCP bound only to `127.0.0.1`; remote sessions use
  SSH stdin/stdout and a private Unix RPC socket. Short-lived JSON files, not
  the Windows Registry, provide session discovery.
- A physical F12 press assigns the running Neovim instance to the exact focused
  Windows Terminal control. Multiple windows, tabs, and panes retain
  independent local, remote, or ordinary shell sessions.
- A successful F12 association is remembered automatically without a question
  for the concrete control until NVDA or Windows Terminal exits. It remains
  runtime-only; there is no profile decision or related setting. After a focus
  switch, the running session activates only after the foreground context is
  correlated and confirmed again. Native terminal output, including typing
  echo, remains fail-open until then.
- Authentication, sequences, heartbeats, resync, and focus correlation bound
  the persistent path. Disconnects, invalid state, or uncertain focus identity
  restore NVDA's native terminal behavior fail-open.
  A new transport session is adopted only through `fullState` at sequence 0;
  Boolean or negative envelope sequences and timestamps are rejected. After a
  sequence gap, only a newer snapshot from the same session leaves the resync
  state.
  When a remote Neovim instance ends, the SSH client immediately translates
  the bridge lifecycle state to the same fail-open path as a local RPC
  disconnect, even while the SSH process and bridge remain alive. State
  snapshots requested during that disconnect cannot authenticate the instance
  again; only a `fullState` reporting a connected Neovim may create another
  connection transition. An automated boundary test reproduces a mixed
  local/SSH pane scenario with an ended remote instance and repeated focus
  changes.
- The AppModule owns Windows Terminal events and `nextHandler`. Dedicated
  services own focus, session assignment, connections, editor state, settings,
  presentation, and runtime. The Global Plugin now only creates and closes the
  transactionally composed runtime. Connection workflow, runtime maintenance
  of temporary bindings, terminal actions, and event delivery have dedicated
  owners; the
  AppModule and Braille adapter see only their static ports. Outbound controls
  use a bounded queue and remain ordered per client, while a fixed worker pool
  isolates independent clients. A second fixed pool owns every already-detached
  client until it is stopped. Disabling and teardown therefore do not wait for
  transport I/O. [Architecture](architecture.md) describes the
  current boundary; the dated Appendix C only preserves the review basis at
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
  buffer. A native Neovim test checks that F3 in L4 opens the Quickfix list
  on the first result. Practical acceptance of L4 and L6 under Windows/NVDA
  is pending.
- Diagnostics from `vim.diagnostic` can be read at the current, previous, next,
  first, and last position. Held diagnostic views and error, warning, and
  empty-result cues use the same validated data path.
- Neovim's native `z=` suggestions are accessible through speech, Braille, and
  contextual NVDA commands. Spelling feedback follows NVDA's separate document
  formatting settings.
- Neovim's built-in `:Tutor` remains entirely owned by Neovim. Access Link
  reads only its unambiguous native extmarks in Tutor buffers on Neovim 0.12
  and later, speaks status transitions only while the buffer, window, and line
  context remain unchanged, includes the assessment when the line is read
  again, and persistently shows a non-routable `✓` or `✗` after the
  Braille line text. A buffer-local text observer is created only inside a
  Tutor buffer; there is no polling or additional control traffic. Values of
  other types or outside this context are rejected before canonical state. On
  Neovim 0.10, Tutor remains unchanged with Neovim and Access Link registers no
  Tutor observers. Both boundaries and the 0.12 path have headless coverage; the
  0.12 path also has an isolated real-TUI test. A dedicated GitHub Actions job
  runs the native Lua contract and this current socket/TUI test under the pinned
  Neovim 0.12.3.

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
  and Braille. Plugin rows, virtual progress, and success are not inferred.
  Guided P1 through P4 were practically confirmed in the Windows/NVDA
  reference path.
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
language, title, and description metadata. GitHub Actions runs this temporary
validation as a dedicated job. Development uses a local Windows checkout
and normal Git fetches. `build.cmd` checks the branch, commit, and cleanliness
of tracked files before and after building. The same isolated core builds
Linux release artifacts and places the add-on and documentation ZIP in `dist`.

## Verification evidence

Automated suites cover protocol and bounds, bridge, local and SSH clients,
multiple instances, focus and fail-open behavior, editor and presentation
planning, Lua with real headless Neovim processes, package contents,
localization, and documentation links. The test runner uses the logical
processors available to Python and distributes package tests across up to
twelve isolated shards. Pinned runs use Neovim 0.10.1 or 0.12.3
according to their purpose and exercise real completion, LSP, diagnostic, and
linter paths. The Clang-Tidy profile invokes the pinned binary directly, fixes
the language mode and supplied test configuration explicitly, and merges
standard and error output. The
markdownlint profile checks the absolute fixture instead of relying on a cold
stdin run; both parsers retain complete Windows drive and UNC paths.
The public Neovim-plugin facade composes separate owners for the channel,
input, completion, command line, UI prompts, Oil confirmations, and context
changes. The channel treats state capture, payload decoration, and RPC
publication as one fail-open boundary. Input prefixes are one tagged state. On
an internal publication failure, the channel also closes the real RPC
transport. A connection change discards old scheduled controller events and
silently resets transient menu, prompt, and runtime state before the next
`fullState`.
Semantic Lua tests cover real RPC serialization failures, fast reconnects,
menu lifetimes, coupled prefix commands, repeated setup, completion, and
command-line transitions; the add-on test checks that these tested modules are
bundled identically instead of inspecting their internal source shape.
Real-TUI tests use one shared send helper to drain a time- and byte-bounded
amount of pending PTY output before every physical-key step. Every isolated
runner job also has a fixed timeout whose failure terminates its complete
process group, including Neovim and helper processes it started.
The completed unit-test review exercises the extracted NVDA runtime owners
directly while complete composition contracts remain in the reduced package
fixture. Mock-isolated bridge contracts and real TUI/socket scenarios are
separate, file-classified suites. Four targeted protocol mutations must fail
at the Boolean/integer distinction, exact field set, size boundary, and
session-sequence rule. The runner also reports skip reasons and Python
warnings for successful jobs.
Preflight and test helpers use one bounded 60-second wait for real providers.
This permits cold Windows and network-drive starts without waiting forever for
a stalled provider.
Listener-free, SSH, and real socket tests run separately. See the
[test strategy](testing.md) for commands and detail.
`guided-desktop` and `guided-audio` exercise the 18 guided cases and their
mechanically verifiable expectations in an isolated Windows guest. They
observe actual focus, NVDA speech output, digital Braille cells, and rendered
audio at their respective interfaces. Both groups run on explicit request.
All 18 cases have complete guest evidence, including controls. The local VM
reference profile used NVDA 2026.3.1, Neovim 0.12.6, and Windows Terminal 1.25.3131.0.
The [result audit](testing.md#guided-windows-and-audio-checks) verifies the guest
logs, package hash, and PCM recordings.
The GitHub-hosted S1 check has also verified native focus and keyboard input.
The private lab keeps the independent WASAPI and QEMU checks for C1, audits
any replay caused by a missing QEMU start marker, and runs independent cases
even if an earlier case fails.
The QEMU calibration verifier for C1 and D1 checks disjoint waveform segments when
timing slips affect a calibration signal. Application cues and the separate
WASAPI capture are checked against complete waveforms.
The managed test guest starts fresh for the second P2 fixture.
Guided practical tests isolate the remaining perceptual checks for speech,
Braille, sounds, focus, and response time. Their technical preflight confirms
real provider data and task-specific isolated key control. The compatibility
suite also includes four lazy.nvim tasks with fully local Git fixtures for its
window, installation, update, and synchronization; the individual selector
groups them under plugin management. The headless preflight does not require
Lazy's deliberately suppressed UI; it verifies the public command and
isolated fixture configuration. When Lazy redraws the same plugin row, the
speech planner suppresses an extra character announcement from the restored
cursor column. Explicit character and word navigation remain audible.
Fixture repositories disable line-ending
conversion and irrelevant Git output. On shared or mapped drives, the isolated
Git configuration permits only the concrete fixture repositories. Preparation
stops at the first failed tool or profile check and names its immediate reason.
It verifies and reuses matching pinned tools and only the plugin revisions
required by the selection. Saved state records the profiles that passed
preflight, so a new selection is not skipped because other profiles passed.
Pyright runs directly through Node. Direct tool failures include tool output;
linter failures name the configured provider and whether its process is still
running.
Structure and safe key choices are
documented in [guided practical tests](human-testing.md).
Optional empty path lists remain real JSON arrays in the PowerShell runner;
the Lua verifier additionally normalizes older or external JSON `null` before
F5 checks the actual Git states. Its confirmation names only targets proven to
be at the expected revision and, where applicable, the target proven absent.
For a real Lazy buffer the plugin also carries the first contiguous text block,
bounded to 2,048 UTF-8 bytes. Rendering makes it available only after the
initial context transition; Access Link then speaks it exactly once as the
complete command bar despite the layout-only blank line and width-dependent
wrapping. Line navigation suppresses visual-only edge and padding spaces. In a
buffer identified exactly as `nofile`/`lazy`, speech planning removes
private-use Unicode characters from every spoken part, including speech
exploration. Unmodified source text remains the basis for Braille, the cursor,
and routing. The current plugin row is recognized only from Lazy's documented
icon highlights. An immediately following `dir` property with the documented
`LazyProp` extmark marks it as expanded. Speech uses NVDA's localized
`collapsed` and `expanded` states; Braille appends `+` or `-` as NVDA tree views
do. A state change sends
no transient Braille message, so it cannot obscure the updated marker. The
existing NVDA line exploration can read the command bar again after opening.
Access Link remains silent for unknown or ambiguous rendering.

Practical confirmation includes:

- local and remote component installation and updates;
- concurrent local and SSH sessions across multiple windows, tabs, and panes;
- focus transitions between connected Neovim and ordinary shell controls;
- navigation, speech exploration, mode, buffer, and terminal transitions;
- Braille routing, both Braille modes, and spelling suggestions with a
  Papenmeier BRAILLEX EL 80c;
- the lazy.nvim window, speech exploration, Braille markers, and install,
  update, and synchronization with isolated local test plugins;
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
