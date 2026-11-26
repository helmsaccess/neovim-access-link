# Changelog

This changelog summarizes completed changes by product version. The
[detailed history](changelog-history.md) preserves earlier development and
test-build entries through August 5, 2026.

## Unreleased

- Bounds connection setup and reads in the shared Neovim RPC client. Invalid
  RPC messages cause a disconnect. Controls use the verified, registered
  channel.
- Exercises the local Python client against real Neovim, including session
  registration, full state, and cursor routing.
- Reaps the SSH process after protocol errors and cancellation during process
  startup before attempting another connection.
- Scales parallel test runs to the available logical processors. Up to twelve
  isolated shards speed up package tests on many-core machines. `-j` still
  sets the limit for each run.
- Enables local Windows development with Git fetches from `origin`. `build.cmd`
  uses a clean local branch. Python and Lua tests support native Windows paths
  and test processes. The Windows socket run checks the local TCP path.
  Unix socket and PTY tests run on Linux.

- Uses the current NVDA imports for Braille regions and retains the fallback
  for NVDA 2026.1. The built add-on starts on NVDA 2026.3.1. Lua and Windows
  TCP tests use Neovim 0.12.6.
- Builds the add-on and documentation ZIP through a shared isolated core.
  The Windows build recognizes official Pandoc 3.1.11.1 with Windows line
  endings. The Linux release build uses an approved clean `main` snapshot.
  The earlier Git-ref synchronizer was part of the Linux development workflow.
  MessagePack 1.1.2 provides official wheels for Python 3.14.
- Replaces the standalone generated-to-installed documentation sync with an
  internal layout library and removes the unused Windows NVDA log uploader.
- Fixes Lazy guided-test preparation on shared or mapped repository drives:
  the isolated Git configuration lists the concrete fixture repositories
  instead of a wildcard. Preparation stops at the first failed tool or profile
  check and shows its immediate reason. Existing Pyright installations are
  recognized from the package, server file, and a real CLI invocation and are
  started directly through Node. Preparation loads only plugins required by
  the selection, starts each linter exactly once, and evaluates its own
  diagnostic namespace. Saved state distinguishes which selected profiles
  already passed preflight. Specific reuse, update, and provider errors replace
  ambiguous aggregate messages.
- Starts the 0.99.0 development line with development build 1 after the 0.98.0
  beta pre-release.
- Simplifies Neovim-plugin runtime state: the public root facade now composes
  explicit owners for the event channel, input, completion, command line, UI
  prompts, Oil confirmations, and context changes. Public RPC/adapter
  functions and semantic events remain unchanged. A dedicated behavior test
  covers fail-open channel teardown, while the package test checks identical
  tested modules instead of internal source fragments. This installable state
  is development build 2.
- Stabilizes real-TUI regression tests by making one shared send helper drain
  pending PTY output before every physical-key step. A full test output buffer
  can therefore no longer stop Neovim from polling input.
- Completes the critical follow-up review of the Neovim-plugin refactoring. The
  event channel now protects invalid snapshots, payload failures, and
  publication failures. Input prefixes form one tagged state, so coupled `g`
  commands cannot be misclassified as independent macro, register, or edit
  commands; reconnects discard old scheduled input events. Regression tests
  cover these transitions, repeated setup, and bounded PTY draining. The test
  runner also bounds every isolated job. This installable state is development
  build 3.
- Corrects the remaining gaps found by an independent lifecycle review. Every
  internal publication failure now closes the real RPC transport as well. A
  connection generation discards scheduled UI, command-line, context,
  diagnostic, and file-manager events from the previous connection; transient
  menu, prompt, and controller state resets silently before the next
  `fullState`. A scheduled UI teardown can no longer remove a newer UI
  attachment. On timeout, the runner terminates the complete process group
  instead of only the direct test process. Real RPC, reconnect, menu-lifetime,
  and child-process regression tests cover these boundaries. This installable
  state is development build 4.
- Simplifies the NVDA add-on's Python runtime after a complete architecture
  audit. The Global Plugin shrinks from more than 3,200 lines to a few dozen
  and now owns only the lifetime of a transactionally constructed runtime. Connection workflow,
  terminal actions, event delivery, presentation, and deferred work have
  explicit owners; the AppModule and Braille adapter use narrow public
  contracts instead of private Global Plugin details. One dispatcher
  serializes outbound control data, while a bounded background worker stops
  clients without making NVDA's main thread wait for transport shutdown.
  Architecture, rollback, concurrency, and ownership tests protect these
  boundaries, and Python style validation now covers every add-on test. This
  first installable state on the new development branch is development build
  1.
- Hardens the Python runtime refactoring after an independent senior review.
  `ControlDispatcher` preserves per-client order, isolates independent clients
  with a fixed worker pool, and lets local RPC shutdown interrupt a blocked
  socket send. `ClientStopper` owns every accepted detached client instead of
  leaving one unowned when a queue is full. Selection and password dialogs use
  NVDA's public modal-lifetime tracking, and stale passwords are discarded. The
  lifecycle delegates complete connection retirement to one workflow, while
  the state machine for temporarily remembered bindings has its own controller.
  Direct queue, ordering, isolation, cancellation, dialog, and ownership tests
  cover the new boundaries. This installable state is development build 2.
- Improves the question about a temporary F12 tab association: `Yes` again has
  the default focus. A new checkbox stores the explicitly selected answer in
  the active NVDA configuration profile; the `Temporary terminal connections`
  setting can then switch between asking again, remembering automatically, and
  not remembering automatically. Package tests cover profile switches, `Yes`
  and `No` decisions, cancellation, dialog focus, and prompt-free reuse. This
  installable state is development build 3.
- Fixes a focus race in the F12 remember question. Dialog-decision
  authorization and one-shot focus recovery now have separate lifetimes. A
  focus return consumed while the question is open no longer discards a later
  `Yes`; suppression and structured typing echo remain disabled until the
  correlated foreground context is confirmed again, preserving native typing
  echo in other Windows Terminal windows. Regression tests cover repeated
  focus changes while the question is open. The practical run under NVDA
  2026.2beta10 exposed the defect and exercised the surrounding focus path, so
  the manifest sets the last tested NVDA version to 2026.2. The corrected build
  still needs the final manual repetition test. This installable state is
  development build 1.
- Prevents false SSH reconnections after the bound remote Neovim instance
  exits. A surviving bridge can still answer focus-triggered state requests,
  but a `fullState` with `connection.neovim=disconnected` can no longer
  authenticate the transport instance. Focus changes between a local pane and
  the ended SSH pane therefore cannot cause repeated connection and
  disconnection cues. Direct protocol tests cover repeated disconnected
  snapshots, an initially disconnected state, and a genuine later reconnect.
  The practical two-pane run under NVDA 2026.2beta10 exposed the defect; the
  corrected build still needs manual repetition. This installable state is
  development build 2.
- Removes the error-prone question about remembering a new F12 association,
  including its checkbox, profile value, and setting. A successful,
  still-exactly-focused association is now remembered automatically only for
  the running NVDA/Windows Terminal session; the existing forget command still
  removes it early. The same WT pane also remains associated when its UIA
  provider changes between the runtime-ID forms observed under NVDA
  2026.2beta10. This normalization jointly requires the same process, window
  handle, allowed class, and pane-tail components plus NVDA's positive UIA
  element equality; different panes remain separate. Direct and package
  regression tests cover automatic retention, focus races, alias changes, and
  distinct panes. Manual repetition of the corrected build under NVDA
  2026.2beta10 confirmed stable, distinct bindings during frequent switching
  between a local pane, an SSH pane, and another WT window, native typing echo
  outside the active session, and no false reconnections after remote Neovim
  ended. This installable state is development build 3.
- Hardens protocol boundaries after the complete unit-test review. Boolean and
  negative sequences or timestamps are rejected in the message envelope. A new
  transport session starts exclusively with `fullState` at sequence 0, while
  resync accepts neither old snapshots nor foreign sessions with a continued
  sequence. Direct boundary and negative tests also cover MessagePack
  fragmentation, text columns, cursor routing, and removal of transient result
  fields. This first installable state on the test-review branch is development
  build 1.
- Completes the structural actions from the unit-test review. Direct tests
  exercise the extracted NVDA runtime owners without constructing the complete
  `GlobalPlugin`; redundant package cases were removed while real composition,
  persistence, and focus contracts remain. Architecture rules use syntax-tree
  invariants instead of fragile source-text matches, and concurrency tests use
  events instead of short wall-time thresholds. Mock and real-TUI bridge tests
  are separated by file, the runner reports skip reasons and warnings, and
  four targeted mutations provide evidence for critical protocol contracts.
- Corrects the dedicated GitHub Actions job for Neovim 0.12 Tutor semantics
  after the mock and socket tests were split. The job again invokes the
  existing real-TUI test through its current module and class names instead of
  failing at a stale import path after the Lua test succeeds.

## 0.98.0

- Pins the official Pandoc 3.1.11.1 binary for local reference and CI
  documentation builds. CI verifies the archive by SHA-256, while the build
  script rejects differently packaged builds of the same version so they
  cannot generate different checked-in installed HTML.
- Assigns `NVDA+Alt+N` to the contextual activation command by default. The
  gesture remains reassignable in NVDA's Input Gestures dialog and continues
  to pass through outside a matching focused Windows Terminal control.
- Makes Neovim's built-in `:Tutor` specifically more accessible without adding
  separate tutorial logic. From Neovim 0.12, recognized, unambiguous native
  Tutor extmarks provide localized announcements when an assessment changes,
  the assessment when its line is read again, and persistent non-routable
  Braille markers. Other buffers and extmarks remain untouched. Invalid
  transitions, including structurally invalid JSON values, are rejected before
  canonical state, while
  existing Braille routing and source mappings are preserved. On Neovim 0.10
  the Tutor path is fully inactive and registers no observers. Transition
  announcements remain bound to the same buffer, window, and line context.
  Isolated headless boundary tests and a real 0.12.3
  TUI contract test cover the scope; the Tutor was also sampled practically
  under Windows/NVDA with speech and a physical Braille display.
- Restores NVDA's normal terminal behavior immediately after a remote Neovim
  instance exits. The SSH client now treats the authenticated bridge
  `disconnected` state as connection lifecycle rather than an ordinary editor
  event, even while SSH and the bridge remain alive. Invalid state values are
  rejected, and a later reconnect again requires a valid `fullState`.
- Adds a component-dialog configuration choice that remains unchanged by
  default and can install a basic configuration with Lazy, Oil, the bundled
  Access Link copy, actual tab characters on two-column tab stops, disabled
  line numbers, and leader commands for Oil and Lazy. The indentation
  remains fixed after filetype-specific Neovim defaults are applied. An
  isolated headless startup with local Access Link, Lazy, and Oil directories
  is checked under Neovim 0.10.1.
  Existing regular `init.lua` and `init.vim` files move to unique backup paths
  named in the results dialog before atomic replacement; failures restore the
  originals from the retained backups. Symbolic links and unusual targets
  remain unchanged, and component removal deletes neither configuration nor
  backups. The local Windows basic configuration has practical acceptance.
- Adds a second configuration path that safely copies the complete local
  Windows configuration directory to selected Linux connections. A bounded,
  link-free snapshot is transferred separately from the component package over
  SSH and validated again on the target; existing configurations are backed up
  as complete directories before atomic replacement. Windows-specific content
  and execute permissions are neither guessed nor rewritten. Lazy must still
  list the installed Access Link copy explicitly as a local plugin.
- Hardens component removal with an explicit warning that defaults to
  declining and a repeated results notice. The plugin and Linux bridge are
  removed; Neovim configuration and backups remain unchanged, including any
  explicit plugin load instruction that the user must remove when appropriate.
- Adds robust baseline support for `lazy.nvim`: Access Link gives the real
  Lazy buffer an unambiguous context name and speaks the complete command bar
  regardless of its initial blank line or width-dependent wrapping. Line
  navigation omits visual-only edge and padding spaces. Graphical private-use
  Unicode characters remain silent throughout the Lazy buffer, including
  speech exploration, while Braille retains the unmodified text. Only documented
  lifecycle events produce neutral start/end reports through speech and
  Braille. Plugin rows identified unambiguously through public icon highlights
  report NVDA's localized `collapsed` or `expanded` state when entered or
  toggled; Braille shows the corresponding tree-view markers `+` and `-`.
  Toggling does not obscure them with a transient Braille message, and existing
  NVDA line exploration reads the command bar again when needed. Unclear
  rendering remains silent. Synchronization collapses child operations
  without guessing progress, result, or success from Lazy's rendering.
- Adds four guided lazy.nvim practical tests for window operation, install,
  update, and synchronization. Isolated local Git fixtures and pinned headless
  contract tests verify actual end states without changing user configuration
  or installed plugins. The individual selector lists these tasks under
  plugin management. Technical preflight accounts for Lazy deliberately not
  opening its UI in headless mode; local fixture repositories run without
  line-ending conversion or distracting Git progress output.
  The F5 final-state check treats an empty optional path list consistently as
  an array instead of Lua `vim.NIL` and names the revisions and removals it
  actually confirmed. All four guided workflows were practically confirmed in
  the Windows/NVDA reference path; their completion reports remain explicitly
  neutral until F5 proves the Git end state.
- Integrates all eight German and English HTML documents into the add-on. A
  top-level `Neovim Access Link` menu opens settings, component management,
  and installed help selected for NVDA's language.
- Documents the separate, assignable commands for copying a Visual selection
  or register 0 to the Windows clipboard and inserting Windows clipboard text
  into Neovim.
- Adds the default help file and a change log generated from the current
  German or English changelog section to the manifest.
  Development builds use the unreleased section; releases curate it into the
  version section and then reset it.
- Strictly validates built base and localization manifests against the official
  NVDA AddonTemplate field set. Missing, empty, unknown, or malformed metadata
  and missing default English help stop the package build.
## 0.97.0

- Adds the HTTPS project URL to the add-on manifest.
- Adds an optional parameterless Windows build from source. A temporary Python
  environment leaves the system installation unchanged, while the embedded
  Linux package receives portable Python modules and reproducible Unix
  metadata.
- Adds Insert-mode LSP active-parameter speech and held, read-only signature,
  parameter, and diagnostic views with correlated speech and Braille.
- Hardens native completion, `nvim-cmp`, and `blink.cmp`, including
  documentation resolution, menu cues, and the no-selected-candidate state.
  It also fixes the practical-test preflight incorrectly rejecting Blink's
  intentionally disabled automatic menu display.
- Makes native incremental search, `inccommand` replacement previews, Quickfix
  and location lists, replacement prompts, multi-buffer replacement, and LSP
  rename completion accessible. Neovim and the language server retain
  execution; Access Link coalesces internal buffer, cursor, and context changes
  into one evidence-based completion report. Automated multi-file tests cover
  Quickfix files, listed buffers, and argument files; guided L4 through L6
  isolate the remaining practical NVDA checks.
- Unifies diagnostics from LSP, `nvim-lint`, ALE, and `none-ls.nvim`, extends
  navigation commands, and adds distinct error, warning, and empty-result
  cues. On Windows, the Clang-Tidy practical test launches the pinned binary
  directly, uses an explicit C mode and supplied test configuration, and
  consumes both output streams. One bounded wait allowance accommodates cold
  provider starts on Windows and network drives.
  Markdownlint checks the absolute fixture instead of relying on an unreliable
  cold stdin run. Setup probes real linter output first and collects failures
  from all selected profiles in one run.
- Fixes Linux session discovery across differing runtime environments and
  without `XDG_RUNTIME_DIR`, plus focus and remembered-binding paths after the
  optional F12 question.
- Separates safe, SSH, and socket verification into independent test phases
  and expands reproducible completion, LSP, linter, and guided practical tests.
  Compact task cards state purpose, numbered steps, and pass condition; F2
  repeats the task while F1 and F11 remain free because of Neovim and Windows
  Terminal default bindings.
- Updates selection and LSP test APIs for Neovim 0.12 while retaining Neovim
  0.10 compatibility.
- Restructures the Quick Guide and manual around reader tasks. One real,
  tested Lua example generates identical code blocks for GitHub and the German
  and English HTML manuals.
- Clarifies the Global Plugin's remaining process-wide role after a renewed
  architecture audit without broadening the AppModule-owned event path.
- Reorganizes developer documentation around onboarding, current explanation,
  tasks, references, and decisions; removes stale transport claims and adds a
  dedicated CI build with automated German/English structure and HTML metadata
  validation.

## 0.96.0

- Adds structured Braille, cursor routing, standard navigation, and a
  per-session Braille exploration mode.
- Makes Neovim's built-in `z=` spelling suggestions accessible through speech,
  Braille, and contextual NVDA commands.
- Aligns spelling feedback with NVDA document formatting and stabilizes
  Braille viewports across focus, session, and text changes.

## 0.95.2

- Introduces speech exploration by character, word, and line without moving
  the real Neovim cursor.
- Adds origin cues and separate detail settings for normal navigation and
  exploration release.

## 0.95.1

- Slims the Global Plugin into a composition root with dedicated services for
  focus, assignment, editor state, connections, settings, Braille, and runtime
  ownership.
- Preserves local and SSH sessions across multiple Windows Terminal windows,
  tabs, and panes, including clipboard and component management.

## 0.95.0 (beta)

- Moves Windows Terminal events, overlay selection, `nextHandler`, and
  assignable terminal commands into the AppModule.
- Restricts F12 to the concrete AppModule and `TermControl` identity and
  prevents an inserted `<F12>` during an Insert-mode assignment.
- Uses NVDA's Windows bindings and coding conventions in NVDA-side code.

## 0.94.2

- Structures user and developer documentation from basic concepts through
  architecture, current status, plan, and history.
- Aligns UI labels with the gettext catalog and NVDA source and describes
  testing and support as a risk-based best-effort process.

## 0.94.1

- Ships the complete German gettext catalog with reproducible catalog, MO, and
  package verification.

## 0.94.0 (prerelease)

- Unifies the product ID, package names, configuration section, and artifact
  prefix under `NeovimAccessLink`.

## 0.93.0 (prerelease)

- Hardens terminal and buffer switching, structured command-line and process
  messages, and window and tab context output.
- Fixes reassignment from a terminated local session to an SSH Neovim session.

## 0.92.0 beta pre-release

- Adds configurable focus presentation, control-specific Windows Terminal
  isolation, and explicit clipboard commands for local and SSH connections.

## 0.91.0 beta release

- Introduces control-specific Windows Terminal assignment with fail-open focus
  transitions and one-shot F12 authorization.
- Practically confirms local and remote connections across multiple tabs and
  split panes.

## 0.90.0 beta release

- Adds practically confirmed focus context with file, mode, and configured
  connection name.

## 0.89.35 beta release

- Hardens session registration and Windows Terminal bindings for local and
  remote Neovim sessions.
- Takes over Neovim's external UI only after authenticated registration and
  returns it fail-open to the native TUI on errors.
