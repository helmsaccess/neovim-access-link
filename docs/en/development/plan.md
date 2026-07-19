# Active plan

Status date: July 19, 2026.

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

Phase 3 is partially implemented. An NVDA-independent
`ConnectionCoordinator` now owns the instance manager, active client, gate,
active speech planner, authentication, terminal bindings, correlated pending
requests, and isolated runtime state for connection instances. It also
allocates bounded, independent request IDs for the three allowlisted reverse
channels. For now, the `GlobalPlugin` class reaches that state through narrow
compatibility properties; event behavior and F12 assignment are unchanged. An
identity-checked `ServiceRegistrar` publishes only the fully initialized
service and prevents late termination of an old instance from removing a
newer registration. Further relocation of connection, gate, and presentation
behavior remains open, as do practical checks of the expanded coordinator
state. The preceding intermediate state with instance state and identity-safe
registration was confirmed in practice.

Placement of configurable commands is settled for a later, separate stage:
NVDA 2026.1.1 builds the Input Gestures dialog from the previous focus and its
AppModule. With Windows Terminal focused before opening the dialog, commands
on its AppModule are therefore visible and can be scoped more narrowly there.
The existing metadata remains unchanged until that relocation is implemented
and tested separately. After each stage, verify the built add-on, fail-open
behavior, and local and SSH sessions across multiple tabs, panes, and windows;
do not combine architectural relocation with behavior changes in one step.

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
