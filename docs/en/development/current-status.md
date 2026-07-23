# Current status

Status date: July 21, 2026. Product version in the source tree: 0.95.1.

The source tree is prepared for version 0.95.1. Its corresponding GitHub
release link is kept prominently in `README.md`. Project-defined maturity
remains between alpha and beta. This documentation does not infer a higher
stability classification from test coverage, version number, or feature count.

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
- The Windows Terminal AppModule and structured Braille overlay reach the
  shared service through a narrow `TerminalIntegrationService`. Fixed command
  values and immutable focus and claim results prevent private or dynamic
  calls across the AppModule boundary.
- A dedicated `SettingsService` owns loading, normalization, persistence, and
  NVDA profile switching. Presentation and Tools dialogs receive only
  snapshots or narrow operations; `NvdaUiManager` has no Global Plugin
  instance.
- `TerminalFocusService` owns terminal identity, focus generation,
  AppModule/adapter correlation, and the periodic lifecycle sweep. Uncertain
  UIA results fail open; closed, unfocused controls are disposed only after two
  conclusive negative checks.
- The completed V2-4 extraction gives `SessionClaimService` sole ownership of
  one-shot F12 authorization, claim generations, and claim inventory state. Local and
  SSH inventory and session-list workers, discovery generation, and candidate
  evaluation run behind that service. It also returns an immutable decision
  between local, remote, and automatic resolution and for each session-list
  result. It plans reuse or start of local and remote sessions, including an
  instance that may need replacement. The service applies a current reuse
  plan to instance bindings and returns displaced terminal identities for
  separate NVDA-side focus cleanup. Starting, binding, and runtime selection
  of new instances form another service transition; rollback and replacement
  stop clients asynchronously. NVDA messages, dialogs, and focus-related side
  effects retain their established main-thread
  boundaries. Explicit instance selection and disconnect are neutral service
  transitions as well: failed selection restores the previous binding, while
  disconnect removes runtime state and bindings before asynchronous client
  stop. Restoration of remembered bindings is prepared fail-open and creates
  a correlated focus-context or full-state request according to authentication
  state. Delay and transport calls remain at the NVDA boundary. The service
  also owns pending offers to remember temporary terminal bindings and
  revalidates focus, control, instance, and selection after the modal question.
  Dialogs, messages, and diagnostics remain NVDA-side. A one-shot correlated
  reactivation bridges only this question's focus loss; declining does not
  create a persistent binding. An injected
  `ManagedClientFactory` constructs local TCP and remote SSH clients with
  instance-correlated callbacks. The claim service connects this construction
  to its transactional start transition; profiles, passwords, and translated
  output remain at the NVDA boundary. The Global Plugin now uses claim targets,
  eligibility, and baselines only through narrow service operations; no
  writable state copy is shared.
- The following practical milestone is complete across multiple windows,
  tabs, and panes, mixed local and remote sessions, and the clipboard paths.
  V2-5 has therefore started: `EditorSessionController` mutates the active
  isolated per-instance editor state, switches its runtime, processes mode,
  menu, transport, and connection state, and creates ordered neutral actions
  for structured typing echo. It also owns the bounded clipboard, register,
  and terminal-control requests, correlates their replies to instance and
  terminal identity, and removes one-shot clipboard text before further state
  processing. Transport calls, focus/gate validation, the Windows clipboard,
  and concrete output remain at the NVDA boundary. The controller combines
  state transition, terminal passthrough, mode-cue decision, and neutral
  speech actions in one immutable event plan. It also records the resulting
  passthrough state for the active instance and adds the saved connection
  label to an isolated copy of an already validated focus/context event. The
  Global Plugin applies the gate decision and delivers the plan through
  `NvdaPresentation`. The Braille path receives an isolated line plan from the
  controller; semantic cursor routing is validated there against capability,
  active client, and complete editor state. Terminal confirmation, instance
  authentication, the NVDA overlay, and concrete transport remain outside.
  Clipboard, register, and embedded-terminal actions likewise receive an
  immutable allowlisted outbound plan only after capability, mode, buffer, and
  canonical state validation. Rejection allocates no pending request; exact
  terminal checks, Windows clipboard access, feedback, and sending stay at the
  NVDA boundary. The final audit also routes semantic planner reset and
  per-instance completion-documentation access through the controller. V2-5
  is complete under automated coverage. Its seven temporary Global Plugin
  compatibility properties have since been removed in V2-6.
- V2-6 is complete and began with a normal `AddonRuntime`. It publishes the
  completed terminal service only after process-wide registration and owns one fixed,
  idempotent shutdown sequence. Unpublication and fail-open gate reset precede
  connection and state cleanup; UI and presentation close last. Individual
  cleanup failures are diagnosed without stopping later steps, and a late
  initialization failure rolls registrations back.
- The second V2-6 slice removes the former Global Plugin views of editor
  planner, state, mode, typing, completion documentation, and transport
  capabilities. Tests now use the actual coordinator/controller ownership
  boundary.
- The third V2-6 slice likewise removes the former Global Plugin views of
  pending claims, inventory generation and readiness, baselines, eligible
  targets, inventory errors, and discovery generation. Tests now use the
  owning `SessionClaimService`; remaining compatibility views concern later
  connection or focus migration and are audited separately before removal.
- The fourth V2-6 slice removes eleven more passive views with no production
  callers. Sound-cache tests use `NvdaPresentation`; binding, runtime, and
  request tests use `ConnectionCoordinator`; AppModule and adapter focus data
  remain owned by `TerminalFocusService`. Active connection, gate, focused
  object, and lifecycle views still require a separate production audit.
- The fifth V2-6 slice completes the focus/lifecycle compatibility cleanup.
  Braille refresh reads the focused terminal object from
  `TerminalFocusService`, and lifecycle tests adjust that service's timestamp
  directly. Active connection and gate views remain for their own audit.
- The sixth V2-6 slice removes seven active-client and connection-state views.
  Production and tests now use `ConnectionCoordinator` directly for the active
  client and instance, connection status, authenticated instances, terminal
  passthrough, and deferred full states.
- The seventh V2-6 slice closes the public terminal service immediately after
  unpublication and rechecks queued runtime callbacks when they execute. Stale
  service references and late claim, network, Braille, or scheduler calls are
  therefore inert and fail open. The gate and instance manager remain after a
  separate audit as frequently used composition dependencies; another layer
  of indirection would not create a clearer ownership boundary.
- The eighth V2-6 slice also centralizes activation in `AddonRuntime`. The
  profile callback, UI, and publication run exactly once in that order;
  failure at each boundary triggers the same complete teardown. The Global
  Plugin no longer marks registration and publication through separate
  transitional calls.
- The ninth V2-6 slice removes duplicate connection cleanup from teardown.
  `AddonRuntime` invalidates claim and focus state, stops clients once through
  the coordinator owner, and then clears its runtime tracking once.
  `_stopClient()` remains only for active user and profile-switch paths.
- The tenth V2-6 slice removes the public `TerminalIntegrationService`'s broad
  Global Plugin back-reference. A complete fixed command map and narrow
  callbacks replace unrestricted access to the composition root; focus, F12,
  and Braille services remain separate.
- The eleventh V2-6 slice moves the Braille region and terminal overlay into
  `nvda_braille.py`. Neutral `service_registry.py` owns process-wide service
  publication; neither that registry module nor the Braille module imports the
  Global Plugin.
- The final V2-6 structural audit removes the remaining test-only runtime
  factory and adds package-level dependency checks. The composition root is
  2,499 lines with 112 methods and exactly two properties: the frequently used
  gate and instance-manager composition views. No AppModule event entry point
  remains there, and none of the extracted runtime or NVDA-edge services
  depends on the `GlobalPlugin` class. Further extraction is deliberately
  stopped without a demonstrated ownership, reliability, or testability gain.
  Automated V2-6 work and practical milestone 2 are complete without a newly
  reported error. Practical Braille hardware remains unavailable.

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

The feature branch also implements contextual exploration:
`NVDA+h/j/k/l` and `Shift+NVDA+h/l` read characters, lines, or words at an
ephemeral position without moving the real cursor. AppModule, protocol,
controller, dispatcher, and Lua tests cover the path; practical NVDA
acceptance is still pending.

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

Four user-assignable Windows Terminal AppModule commands can:

- copy the active Visual selection to Windows;
- copy Neovim register 0 to Windows;
- paste Windows clipboard text through `nvim_paste`;
- or replace register 0 and point the unnamed register at it.

Local and SSH connections use the same correlated, size-bounded path. There is
no automatic synchronization or retry. These and the other configurable
terminal commands initially appear in Input Gestures after Windows Terminal
was focused before opening the dialog; they are not resolved in unrelated
applications. Once the AppModule class has loaded, NVDA may continue listing a
saved mapping elsewhere for that run without making its execution global.

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
