# Active plan

Status date: July 23, 2026.

This chapter contains only open or active work. See `current-status.md` for
implemented features and `changelog.md` for completed steps and former feature
branches. An item in this plan is not a claim that the feature is already
available or practically confirmed.

Order and test depth depend on risk, available test environments, and defects
that are actually reported. The plan promises neither coverage of every
possible combination nor fixed response or resolution times. Reproducible
defects are investigated as promptly as possible; security, isolation, and
data-loss risks take priority.

## 1. Keep documentation understandable and verifiable

Ongoing:

- start developer documentation with architecture and terminology before
  protocol details and special cases;
- keep durable reference, current status, active plan, changelog, and dated
  reports clearly separated;
- keep German and English core chapters structurally parallel;
- verify claims about processes, session registry, assignment, gate, reverse
  controls, polling, and fallbacks against the current code;
- validate the HTML build, internal links, and published sources
  automatically.

## 2. Change architecture boundaries only for demonstrated benefit

The slimming decided in
[ADR-0004](adr/0004-nvda-lifetime-and-event-ownership.md) is implemented and
has been exercised practically across multiple windows, tabs, and panes with
local and remote sessions. `current-status.md` describes the current design;
the changelog and Appendices A and B preserve its development and metrics.

No further split is planned merely because of file size or LOC. Reopen this
work only if it creates one unambiguous state owner, a smaller public
contract, a failure path testable without NVDA, or a demonstrated robustness
gain. AppModule event ownership, fail-open behavior, F12 isolation,
asynchronous transport, and separation of windows, tabs, and panes remain
mandatory invariants.

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
