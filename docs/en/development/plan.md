# Active plan

Status date: July 28, 2026.

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
- incrementally align older English user-manual and developer chapters that
  are shorter than their German counterparts, starting with settings,
  communication, component installation, SSH/tmux, and security;
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

## 5. Broaden the Braille hardware matrix

- Beyond the already confirmed display, exercise more than one representative
  display or driver combination in practice.
- Check cursor, selection, Unicode, tabs, file-manager segments, and routing.
- Check standard horizontal panning plus Up/Down with retained columns across
  multiple drivers and display widths.
- Practically cover optional double/triple actions with all four commands,
  three line starts, timeout, position changes, and the safe disabled default.
- Ambiguous or synthetic cells must remain without invented routing targets.
- Add hardware-specific behavior to the planner only after reproducible
  evidence.

## 6. Practically accept the Braille navigation modes

- Exercise the implemented freely assignable `Cursor`/`Exploration` toggle
  with multiple Braille displays and drivers.
- Confirm that Up/Down changes only the ephemeral read position in exploration
  mode and that routing then moves the real cursor to the selected line.
- Practically check independence from speech exploration mode, separate mode
  selection across concurrent local and remote sessions, targeted reset of
  only the disconnected session, and rejection in command-line and
  direct-terminal modes.
- After edits on the explored line, confirm in practice that the virtual line
  and horizontal viewport stay in place, the content is refreshed completely,
  and a subsequent routing command uses the current mode and buffer state.
  After intervening changes while the real cursor is on another line, routing
  from a no-longer-proven line snapshot must be rejected and work again after
  that line has been fetched again.
- Mode selection is already retained independently for the lifetime of each
  connected session; new and disconnected sessions start safely in cursor
  mode. Decide on additional profile-aware persistence across connections or
  NVDA restarts only after hardware acceptance.

## 7. Increase robustness and compatibility breadth

- Test long runtimes, repeated SSH loss, and reconnects.
- Measure high event load, large files, and many concurrent sessions.
- Add more representative Windows, NVDA, Neovim, language, and SSH
  configurations to the practical matrix according to risk.
- Investigate the unresolved older Rocky Linux/Neovim combination only when a
  concrete support target is chosen.
- Plan portable layouts, `NVIM_APPNAME`, other terminal frontends, and Neovim
  GUIs only with their own identity, focus, security, and fail-open design.

## 8. Broaden diagnostic providers and languages according to risk

The shared `vim.diagnostic` layer, real nvim-lint/ALE contracts for C, Python,
Bash, Go, Rust, Ruby, and Markdown, and the real `none-ls.nvim` LSP-bridge
contract are implemented. Add combinations according to adoption and
reproducible defects without hard-coding languages into the add-on:

- in addition to the proven Staticcheck path, exercise Go through `gopls` in
  the combined practical LSP round; pin golangci-lint only for additional real
  demand;
- in addition to the proven Cargo/Clippy path, exercise Rust through
  `rust-analyzer` and its Clippy diagnostics in practice;
- add `ruby-lsp`, alternative Ruby analyzers, or other Markdown checkers only
  for demonstrated use; RuboCop and `markdownlint-cli2` are the automated
  baseline;
- pin extracted none-ls sources only with a concrete common tool and every
  commit they actually require;
- integrate navigation from Trouble, Telescope, ALE lists, or other diagnostic
  views only through public semantic APIs;
- consider a dedicated adapter only when a common provider demonstrably cannot
  mirror diagnostics to `vim.diagnostic`.

Every added combination still requires a real tool invocation, pinned
provider, correct UTF-8 byte ranges, source/code/message coverage, both
supported Neovim versions, and a clear distinction between automated and
practical acceptance.

## Priority for new work

Isolation failures, data loss, ambiguous reverse controls, main-thread stalls,
and output from the wrong session take priority over new feature breadth. New
integrations should use public semantic events. Polling is only a documented,
bounded last resort when no reliable event solution exists.
