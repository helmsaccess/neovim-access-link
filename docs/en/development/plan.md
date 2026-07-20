# Active plan

Status date: July 20, 2026.

This chapter contains only open or active work. See `current-status.md` for
implemented features and `changelog.md` for completed steps and former feature
branches. An item in this plan is not a claim that the feature is already
available or practically confirmed.

Order and test depth depend on risk, available test environments, and defects
that are actually reported. The plan promises neither coverage of every
possible combination nor fixed response or resolution times. Reproducible
defects are investigated as promptly as circumstances allow; security,
isolation, and data-loss risks take priority.

## 1. Make documentation understandable and verifiable

In progress:

- start developer documentation with architecture and terminology before
  protocol details and special cases;
- separate durable reference, current status, active plan, and history;
- keep German and English core chapters structurally parallel;
- verify claims about processes, session registry, assignment, gate, reverse
  controls, polling, and fallbacks against current code;
- validate the HTML build, internal links, and published sources.

## 2. Narrow NVDA responsibility boundaries

Implement [ADR-0004](adr/0004-nvda-lifetime-and-event-ownership.md) in
independently verifiable steps:

- separate UI registration and component management from the terminal path;
- move shared connections and state from the Global Plugin class into ordinary
  services;
- make the AppModule fully own Windows Terminal events, overlays, and
  `nextHandler`;
- narrow F12 focus checks without impairing tab, pane, or window transitions.

Phase 1 is implemented under automated coverage: window identity and process
liveness use `winUser`, `winBindings`, and `winKernel`, while the neutral
session lister receives the process probe by injection. Adapter, registry,
claim, lifecycle, and complete built-add-on tests pass. Practical Windows/NVDA
checks of process exit, closed tabs/panes, and plugin reload remain open; the
phase is not treated as practically accepted until they pass.

Phase 2 is implemented under automated coverage: `NvdaUiManager` owns
symmetrical settings and Tools-menu registration, connection forms, and
Neovim component installation and removal. The `GlobalPlugin` class creates
and terminates this manager but no longer contains its implementation.
Structure, localization, dialog, installer, and built-add-on tests pass;
settings, Tools dialogs, and German UI text were then confirmed in practice.

Phase 3 is implemented under automated coverage. An NVDA-independent
`ConnectionCoordinator` owns the instance manager, active client, gate, active
speech planner, authentication, terminal bindings, bounded correlated
requests, isolated runtime states, and instance selection, focus confirmation,
and complete state disposal. `NvdaPresentation` owns NVDA-specific delivery of
planned speech, Braille messages, and sounds, while `NvdaUiManager` continues
to own settings, Tools commands, and component forms. An identity-checked
`ServiceRegistrar` publishes only the fully initialized service and protects
add-on reloads from late termination of an older instance. Narrow
compatibility properties keep the existing event path stable during the
refactor. F12 assignment was not changed; its hardening belongs explicitly to
phase 5. The completed phase-3 state was subsequently confirmed in practice
with local and remote connections across multiple Windows Terminal windows,
tabs, and panes.

Phase 4 is implemented under automated coverage and confirmed in practical
testing. The Windows Terminal AppModule now owns all terminal events,
overlay selection, and every invocation of `nextHandler`. An opaque token
prevents a late `loseFocus` from an old WT process from clearing newer focus.
`gainFocus` uses a two-phase contract: the shared service only prepares the
focus decision, the AppModule invokes NVDA's native handler exactly once so
Terminal LiveText is initialized, and it completes structured focus handling
afterwards. Generation and token reject late completions without losing a
pending `fullState`. Early and late failures fail open without a second native
call. Local and remote connections, multiple WT windows, tabs and panes, focus
changes, native shell output, speech, and sounds showed no problems in the
subsequent practical test. Braille could not be tested in practice because no
hardware was available. F12 and configurable commands remain unchanged in
this phase.

Phase 5 is implemented under automated coverage and practically confirmed.
The F12 decider queries NVDA's current focus object only after the
claim gesture matches. It authorizes only the concrete still-registered
Windows Terminal AppModule instance when the complete `TermControl` identity
derived from that object matches the gate. The former single-adapter fallback
is gone; a focus change before queued main-thread evaluation still rejects the
one-shot generation. In Insert mode the physical key remains observable as a
claim but is no longer inserted as `<F12>`: Neovim 0.11 and later use the
`vim.on_key` return contract, while Neovim 0.10 receives an Insert-mode
`<Ignore>` mapping only when F12 was otherwise unbound. Other modes and
existing user mappings remain unchanged. Automated negative cases cover
unrelated applications, stale controls, multiple WT AppModules, and rapid
focus changes. The subsequent practical test of Normal- and Insert-mode claims
plus focus and control isolation found no errors.

Phase 6 is implemented under automated and practical coverage. The ten freely
assignable terminal commands have moved from the Global Plugin to the Windows
Terminal AppModule. NVDA 2026.1.1 initially lists unassigned commands when Windows
Terminal was focused before opening Input Gestures and no longer resolves
their assignments in unrelated applications. A saved assignment may remain
listed elsewhere after the AppModule class has loaded; this is NVDA's user-map
presentation, not global execution. Dispatch revalidates the exact AppModule
instance and control;
focus races and an unavailable shared service pass the original gesture
through. Assignments stored for the former GlobalPlugin scripts must be
assigned again. Visibility, reassignment, local and SSH commands, and multiple
windows, tabs, and panes are practically confirmed; no fault was found. After
each stage, verify the built add-on, fail-open behavior, and local and SSH
sessions across multiple tabs, panes, and windows.

Phase 7 is mechanically implemented. Python modules loaded directly by NVDA
under `nvda-addon/addon/` now follow NVDA's Ruff format with tabs, LF, and a
110-character line length. Core, bridge, protocol, and test code retain their
already consistent component styles. Ruff 0.14.5 checks only this explicit
NVDA style zone locally and in GitHub Actions; the Global Plugin's dynamically
required imports now carry individual, justified `E402` exceptions. The
subsequently detected loss of Braille overlay selection is corrected by a
direct `controlTypes` import in the AppModule and tests of the actual overlay
hook.

The follow-up V2 slimming work is again divided into small phases protected by
automated tests. V2-1 through V2-3 are implemented under automated coverage. The
registrar publishes only a narrow `TerminalIntegrationService` for the
AppModule and Braille overlay. A dedicated `SettingsService` owns loading,
normalization, persistence, and profile switching. Presentation and
`NvdaUiManager` use its snapshots and domain operations; the UI manager knows
neither the Global Plugin nor its state. A dedicated `TerminalFocusService`
owns identity, focus correlation, and the lifecycle sweep. Duplicate
registration, partial failure, invalid configuration, and connection changes
have direct coverage.
Process-wide availability of Settings and Tools is unchanged. No separate
practical check is planned for these internal phases; it will be combined with
later user-visible V2 stages. V2-4 is complete under automated coverage:
`SessionClaimService` owns F12
authorization, inventory state, scanning, candidate evaluation, and the
immutable transition decision. Discovery lifetime and session-list workers
plus domain selection of their results also live there. The service now plans
reuse or start of a local or remote instance, applies a current reuse plan to
neutral bindings, and reports displaced terminal identities to the NVDA
boundary. Start, binding, and runtime selection of new instances are also
service transitions; rollback and replaced clients are handled without a
blocking stop on NVDA's main thread. Explicit selection and disconnect are
transactional service transitions, with client stops scheduled only after
fail-open state teardown. Fail-open activation of a remembered instance and
the correlated choice between focus context and full state are also owned by
the service. It additionally owns pending offers for temporary terminal
bindings and revalidates focus, control, and instance after the modal dialog;
dialogs, diagnostics, and transport calls remain at the NVDA boundary. An
injected factory encapsulates local and remote client construction plus
instance-correlated callbacks, and the claim service joins it to the
existing start transition. The completion audit removed unnecessary forwarding
methods and direct production access to mutable claim containers. The
composition root retains only NVDA's main-thread, dialog, message, and
transport boundaries. The combined practical milestone is now complete across
multiple windows, tabs, and panes, local and remote sessions, and clipboard
operations. The first V2-5 slice introduces `EditorSessionController`. It owns
mutation and switching of isolated per-instance editor state, including mode,
menu documentation, transport capabilities, connection state, and structured
typing echo. Concrete NVDA delivery and focus/gate decisions remain outside.
The second slice moves bounded request ownership and reply correlation for the
clipboard, register, and embedded-terminal control into the same controller.
Network calls, the Windows clipboard, diagnostics, and translated feedback
remain in the NVDA composition root.

## 3. Broaden practical isolation coverage

- Record the most important negative Windows Terminal cases incrementally for
  unbound shell tabs and panes, separate windows, rapid focus changes, closed
  controls, and RPC connections that remain alive. Add real defect cases to
  the matrix.
- For tested and newly discovered uncertain states, ensure that native
  terminal output remains available and that neither a binding nor a focus
  announcement is created.
- Investigate the open case where a shell or tmux visibly replaces Neovim
  inside an already bound `TermControl` while Neovim's RPC channel stays live.
  Screen scraping is not an acceptable shortcut.

## 4. Accept file managers practically

Oil is practically confirmed under Windows and NVDA. Next, accept netrw,
mini.files, nvim-tree, and Neo-tree incrementally, both locally and over SSH:

- navigation and opening files;
- create, rename, copy, move, and delete;
- Yes/No/Cancel, conflicts, and read-only targets;
- multi-selection and manager clipboard;
- Unicode, spaces, and long names;
- transitions to files, terminals, tabs, panes, and windows;
- speech, sounds, and Braille without stale manager state.

Missing public plugin events must not be replaced with unbounded polling or
general popup scraping.

## 5. Test Braille on physical hardware

- When hardware is available, exercise more than one representative display
  or driver combination in practice.
- Check cursor, selection, Unicode, tabs, file-manager segments, and routing.
- Ambiguous or synthetic cells must remain without invented routing targets.
- Add hardware-specific behavior to the planner only after reproducible
  evidence.

## 6. Increase robustness and compatibility breadth

- Test long runtimes, repeated SSH loss, and reconnects.
- Measure high event load, large files, and many concurrent sessions.
- Add more representative Windows, NVDA, Neovim, language, and SSH
  configurations to the practical matrix according to risk.
- Investigate the unresolved older Rocky Linux/Neovim combination only when a
  concrete support target is chosen.
- Plan portable layouts, `NVIM_APPNAME`, other terminal frontends, and Neovim
  GUIs only with their own identity, focus, security, and fail-open design.

## Priority for new work

Isolation failures, data loss, ambiguous reverse controls, main-thread stalls,
and output from the wrong session take priority over new feature breadth. New
integrations should use public semantic events. Polling is only a documented,
bounded last resort when no reliable event solution exists.
