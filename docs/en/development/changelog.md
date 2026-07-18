# Changelog

## 0.94.1

- The automatically and practically checked gettext feature-branch state is
  adopted as version `0.94.1`. Product channel and maturity classification
  remain unchanged.
- The German catalog covers all 310 extracted messages; MO, package, and
  completeness tests prevent empty or unnoticed English UI text.

## 0.94.0-dev.3+feature.gettext-translation (feature-branch test build)

- Native NVDA gettext catalogs use the public `nvda` domain; a German manifest
  and compiled German runtime catalog are shipped in the add-on.
- A standard-library tool reproducibly extracts POT/PO, preserves translations,
  validates catalog coverage and named format placeholders, and compiles
  deterministic MO files without an external gettext dependency.
- Speech planning remains NVDA-independent and receives the active translation
  as a callback. Mode, focus, navigation, selection, fold, register, and file
  manager text is localized through fixed templates. The German catalog covers
  all 310 currently extracted messages.
- Catalog, speech, and archive regressions pass. Practical acceptance with
  German NVDA remains open.
- Untranslated PO entries are omitted from the MO like `msgfmt` does, so
  gettext returns the English source rather than an empty string. Both Tools
  menu commands and their forms remain distinct and operable.

## 0.94.0 (prerelease)

- The product version was advanced to `0.94.0` at the user's explicit
  direction. The prerelease channel and between-alpha-and-beta maturity
  classification remain unchanged.

## 0.93.0-dev.1+feature.cleanup-0.94.0-prerelease (feature-branch test build)

- The internal NVDA add-on ID, Global Plugin package, native configuration
  section, and artifact prefix are consistently `NeovimAccessLink`. The former
  add-on must be uninstalled before testing; old settings and gesture
  assignments are intentionally not imported.
- JSON settings migration, native `schemaVersion`, old AppModule script IDs,
  and the unused example configuration are removed. A former
  `nvimNvdaAccess` section or JSON file remains unchanged and is never read.
- Bridge and connection management now accept only typed Neovim RPC endpoints
  and connection targets. Old Python re-exports and socket/remote-profile
  shorthand APIs are gone, while protocol, registry, and fail-open security
  checks remain.
- All 277 add-on/core/package tests, 42 protocol tests, 31 bridge tests, and
  Lua suites on Neovim 0.10.1 and 0.12.3 pass. The add-on contains only the new
  Global Plugin path; archive validation and all six HTML builds pass.

## 0.93.0-dev.7 (feature-branch test build)

- Oil's public `parsed_name` is now the semantic speech and Braille name while
  an edit has not yet been applied with `:w`. The path remains tied to
  `entry.name` until proven completion, so a draft name is not reported as an
  already completed rename.
- File-manager navigation retains its fixed motion kind alongside the
  decoration-free semantic entry. In particular, `0`, `$`, `gg`, and `G` once
  again play line/file boundary cues; line changes may retain their edge cues.
- Regression tests cover draft name versus confirmed path, plugin event wiring
  on Neovim 0.10/0.12, and speech planning without falling back to icons or
  extra columns. An isolated real-Oil run proves the draft name without a
  filesystem change.
- Practical Windows/NVDA acceptance with Neovim 0.12 confirms Oil including
  draft names and cues. Oil is currently the only file manager practically
  tested on Windows and provides a solid foundation; netrw, mini.files,
  nvim-tree, and Neo-tree will follow incrementally.

## 0.93.0-dev.6 (feature-branch test build)

- Message-producing Ex commands associate their immediate structured result
  with the mode they returned to. The matching mode cue plays exactly once;
  the message always remains, followed according to Session focus by nothing,
  the current line, or context, mode, and connection. Later asynchronous
  messages are not associated, and a command without output cannot suppress a
  later mode change.
- A new 118-assertion file-manager workflow specification covers create,
  rename, copy/duplicate, move, delete, restore, batches, same-entry state,
  failure/cancellation, path minimization, and writing-project names with
  spaces and Unicode.
- Real-TUI prompt coverage proves a selected No answer, while speech tests
  cover Yes, No, and Cancel. Canonical types such
  as `directory` survive nvim-tree action-result normalization. Opening a file
  from a manager follows all three configured focus presentations.
- Automated coverage is expanded; practical acceptance of this test build is
  explicitly still open.

## 0.93.0-dev.5 (feature-branch test build)

- The narrow Oil prompt parser accepts the real indented `MOVE`, `COPY`,
  `TRASH`, and `PURGE` rows plus `RESTORE`. It names rename and duplicate
  clearly, classifies delete/trash operations as destructive, and still
  transports no names or paths.
- Directly typed Y/N is observed but neither intercepted nor replaced. The
  event-driven close waits one Neovim scheduler cycle so `promptClosed`
  reliably carries acceptance or cancellation; Oil alone handles the key and
  filesystem operation. No timer or polling is added.
- Isolated real-Oil checks cover cancelled rename, duplicate, and delete plus
  confirmed deletion. The TUI regression explicitly requires
  `accepted=false`; all 105 file-manager assertions pass.
- The manual recommends `skip_confirm_for_simple_edits = false`, documents
  the central prompt options for nvim-tree and Neo-tree, and records
  mini.files' combined Yes/No/Cancel synchronization.

## 0.93.0-dev.4 (feature-branch test build)

- The netrw fallback handles banner lines and thin, long, wide, and tree list
  styles separately. Spaces, repeated spaces, tabs, Unicode, and symlink
  decoration are preserved or split deliberately, while the tree root is no
  longer appended to itself. Real isolated netrw views complement synthetic
  boundary cases.
- Built-in file-manager adapters are selected directly by `filetype`.
  Optional adapters have a fixed runtime budget: three repeated errors or
  calls over 5 ms trigger a five-second per-buffer cooldown. Buffer teardown
  releases that state and normal navigation remains fail-open.
- `:checkhealth nvim_nvda` exposes only fixed failure, slow-call, and cooldown
  counters—never error text, paths, or entry names. External adapters must be
  synchronous, bounded, and free of I/O and polling. Ninety-nine file-manager
  assertions cover the expanded path.
- `root` now identifies the public manager/branch root and `currentDirectory`
  the focused level. nvim-tree walks public parent nodes to its root, while
  mini.files separates branch start and focus. Without an entry, focus context
  speaks only the last directory name rather than a complete local, remote, or
  virtual path.
- Neovim 0.10 can deliver keys internally executed by an Ex command such as
  `:normal` to `vim.on_key` only after `CmdlineLeave`. Access Link now uses the
  empty `typed` value to distinguish them from direct input, so command text
  cannot impersonate semantic cursor motion on the reference version. The
  complete Lua suites pass with Neovim 0.10.1 and 0.12.3.
- File-manager buffers now keep a persistent semantic Braille row containing
  name, type, and state. Routing maps only to a name found exactly once in the
  real buffer row; status segments and ambiguous names are rejected safely.
- Real TUI tests cover `vim.ui.input` acceptance/cancellation,
  `vim.ui.select` choice, and a selected Lua `vim.fn.confirm` option on Neovim
  0.10.1 and 0.12.3. Blocking prompts close on mode exit even without
  `msg_clear`, while concurrent or late 0.12 external-UI and wrapper events are
  deduplicated. Prompt text and visible selection labels are UTF-8 safely bounded.
- Oil's custom confirmation float has no public prompt event. A narrow fallback
  accepts only `oil_preview` in a real float and fixed action verbs. It reports
  action/count plus Y/N, removes the raw row, name, and complete path from
  semantic prompt state, and suppresses competing generic float events. An
  isolated run with the real Oil main branch proves cancellation without a
  filesystem change.

## 0.93.0-dev.3 (feature-branch test build)

- The new `fileManagerActionResult` event carries only a fixed action, result,
  count, optional basename, and optional entry type. Complete local, SSH, or
  virtual paths never leave the plugin event layer. Successful actions come
  from public mini.files, nvim-tree, and Neo-tree events; Oil additionally
  exposes errors and detectable cancellations through `OilActionsPost`.
- Multiple synchronous actions in the same active buffer/window are combined
  within one scheduler cycle. A buffer, window, tab, or manager change before
  output drops the result. Missing error/cancellation events in other plugins
  are not inferred from rendering or text.
- Speech and Braille compactly report create, add, rename, copy, move, delete,
  change, or restore. Failures interrupt at critical priority while
  cancellation remains status output. Sixty-two Lua assertions and dedicated
  speech regressions cover success, failure, batching, path minimization, and
  focus changes.

## 0.93.0-dev.2 (feature-branch test build)

- A separate file-manager event layer subscribes to public state events from
  Oil, nvim-tree, Neo-tree, and mini.files. It then rereads only the active
  buffer or window through the existing semantic adapter API, coalesces rapid
  render bursts within one Neovim scheduler cycle, and sends only real state
  changes. It uses neither timer queries nor filesystem polling.
- Selection marks and the file-manager clipboard are distinct fixed states.
  Same-entry changes now report marked, unmarked, copied, cut, clipboard
  cleared, expanded, or collapsed; Neo-tree Copy/Cut is no longer spoken as
  the generic “marked”.
- Forty Lua assertions cover public event stubs, deduplication, coalescing, and
  inactive buffer/window rejection. Speech tests cover complete entries and
  state deltas.

## 0.93.0-dev.1 (feature-branch test build)

- Built-in and external file-manager adapters now centrally bound names to 512
  bytes and paths or roots to 2048 bytes only at valid UTF-8 code-point
  boundaries. Long Unicode names can no longer produce an invalid transport
  message; an invalid UTF-8 adapter value is discarded individually.
- Lua regressions cover exact and split two-, three-, and four-byte boundaries,
  long paths, and invalid byte sequences. Limits remain byte-based and add no
  polling or filesystem queries.

## 0.93.0 (prerelease)

- The product version was advanced to `0.93.0` at the user's explicit
  direction. The release channel remains `beta`; overall maturity remains
  between alpha and beta and is not classified as stable.
- Includes the practically confirmed terminal and buffer-switch hardening,
  structured command-line and process messages, semantic window/tab context,
  and corrected fresh F12 pairing from an ended local Neovim to an SSH
  session.

## 0.92.0-dev.11 (feature-branch test build)

- A disconnected but still remembered local connection no longer forces a new
  F12 pairing into local-only discovery. Only a still-authenticated binding may
  preserve its local or SSH target type. After local Neovim exits, the same WT
  control can therefore use a fresh F12 claim across every inventoried local
  and SSH session, replacing the stale instance in the normal controlled path.
- Diagnostics now distinguish `selected` from `selectedAuthenticated`, so an
  existing mapping is not confused with a live Neovim connection. A transient
  transport disconnect still fails open and never causes automatic rebinding
  without the user's physical F12 action.
- Practical acceptance confirmed rebinding from an ended local Neovim to the
  SSH session in the same WT control without further issues.

## 0.92.0-dev.10 (feature-branch test build)

- For the Context choice, switches among Neovim windows and tabs now combine
  destination position, file or special context, modified/read-only state,
  mode, and connection name in exactly one announcement. A preceding mode
  event stays silent in speech while its independent cue remains. No
  announcement and Current line keep their existing behavior.
- Short file names are made explicit with `file`, for example `file T,
  modified, normal mode`. Terminal buffers report only their semantic mode,
  `terminal mode` or `terminal-normal mode`, instead of `terminal, terminal
  mode`. An existing terminal window is no longer mistaken for a buffer newly
  created through `:terminal`.

## 0.92.0-dev.9 (feature-branch test build)

- The Context choice for `:terminal` entry now remains exactly once even when
  `contextChanged` arrives before the final `terminalNormal` mode event.
  Initial terminal text and its automatic cursor event can no longer append a
  single “T”, “M”, or other character from that line.
- Neovim's key observer no longer treats command-line or direct-terminal text
  as a possible Normal-mode motion. The final `l` in `:terminal`, for example,
  cannot misclassify a later cursor update as explicit character navigation.

## 0.92.0-dev.8 (feature-branch test build)

- A terminal buffer created with `:terminal` now uses the same profile-aware
  entry choice as other buffer switches. No announcement stays silent,
  Current line waits event-first for the first real terminal line, and Context
  reports Terminal-Normal plus the connection. A following automatic cursor
  event can no longer replace that line with its first character.
- Entering direct terminal input with `i` then presents the complete line at
  the terminal cursor once. It replaces competing spoken mode output at this
  boundary; the Insert/focus cue and fail-open passthrough remain intact.

## 0.92.0-dev.7 (feature-branch test build)

- For `:bp`, `:bn`, and their full buffer-command forms, transient spoken
  return modes are no longer placed before the configured destination output.
  No announcement remains silent after the command, Current line speaks only
  the complete destination line, and Context speaks destination, mode, and
  connection once. The independent mode cue and command-line entry
  announcement remain intact.
- `commandLineType` distinguishes Ex commands from identically named search
  patterns, so `/bn` does not trigger buffer-switch suppression. A no-op
  buffer command in the sole terminal buffer still speaks its structured
  guidance without a clipped “terminal-normal mode”.

## 0.92.0-dev.6 (feature-branch test build)

- An automatic `cursorMoved` following `BufEnter`/`BufWinEnter` can no longer
  replace the configured destination line with the single character at the
  destination column. Output is therefore independent of the source buffer's
  cursor position.
- `textChanged` no longer compares lines belonging to different buffers. A
  change event arriving as the destination becomes visible is not presented as
  typed or replaced source text.

## 0.92.0-dev.5 (feature-branch test build)

- Successful buffer switches within the same tab and window, such as `:bp` or
  `:bn`, now use the profile-aware focus choice too: silent, current
  destination line, or destination context with mode and saved connection
  name. The source remains `BufEnter`/`contextChanged`; no polling is added.
- Tab and window changes retain their own context announcements. Mode cues
  remain independent of the selected focus/buffer-switch output.

## 0.92.0-dev.4 (feature-branch test build)

- UI-protocol messages on Neovim 0.12 are processed only after returning from
  the `vim.ui_attach` fast-event callback. State queries therefore no longer
  raise `E5560` or leave a hidden hit-enter prompt; commands, search, and
  following messages remain usable.
- The long real-TUI test drains its PTY output before sending further physical
  keys. Neovim 0.12 can no longer block on test output; this hardens the test
  driver and adds no product delay.

## 0.92.0-dev.3 (feature-branch test build)

- Entering Neovim's command line has a distinct short 600 Hz tone. Returning
  from it in a terminal context uses the Normal cue, while the transient state
  used to create a terminal buffer still produces no duplicate cue.
- Exact `:bd` on a running terminal job reports structured `E89` guidance
  before Neovim's blocking hit-enter state. Destructive `:bd!` remains an
  explicit user decision and is never invoked automatically.
- Buffer-navigation commands such as `:bp` or `:bn` explain when no other
  listed buffer exists in the terminal context. A real switch continues to use
  event-driven `BufEnter` for the destination announcement; no polling or
  terminal screen scraping is introduced.

## 0.92.0-dev.2 (feature-branch test build)

- Raw `nt` is now canonical `terminalNormal`, distinct from a file buffer's
  Normal mode, spoken explicitly, and confirmed by one Normal cue.
- Command-line character echo uses its own UTF-8 byte position rather than the
  unchanged editor cursor, preserving NVDA character/word echo after the first
  character and for Unicode.
- A freely assignable command with no default gesture leaves direct terminal
  input through the fixed Neovim `stopinsert` operation. Local and SSH paths
  validate request, instance, focused control binding, buffer, window, tab,
  and exact mode; no arbitrary Lua or Ex crosses the protocol. Changed tick is
  intentionally omitted because terminal jobs change it asynchronously and
  this operation neither reads nor changes text.
- Event-driven `TermClose` reports the terminal process exit status without
  polling or terminal screen scraping.
- The real-TUI regression uses isolated XDG and runtime paths so an installed
  older plugin cannot shadow the branch under test.

Terminology note: “registry” in every historical entry means Neovim's
file-based session registry of short-lived JSON records, never the Windows
Registry. The product uses no `HKCU` or `HKLM` keys.

## 0.92.0-dev.1 feature-branch test build

- Direct embedded-terminal input now uses the Insert/focus cue and the
  transition to Terminal-Normal uses the Normal cue. The passthrough gate is
  changed before optional feedback so failures remain open to native output.
- Command-line mode remains audible independently of Insert/Normal speech.
  Non-empty `msg_show` results with an empty or future UI classification are
  reported as ordinary speech and Braille messages; search counts retain their
  dedicated structured path.

## 0.92.0 beta pre-release

- The product version was advanced to `0.92.0` at the user's explicit
  direction. The GitHub entry is published as a pre-release.
- The release channel remains `beta`; overall maturity remains between alpha
  and beta and is not classified as stable.
- Includes configurable focus output for bound Neovim sessions,
  control-specific Windows Terminal isolation, and explicitly invoked
  clipboard commands for local and SSH connections.

## 0.91.0-dev.4 unreleased feature-branch test build

- Adds four freely assignable NVDA commands without default gestures: copy
  the current Visual selection, copy Neovim register 0, and paste Windows
  clipboard text through `nvim_paste` or store it in register 0 and point
  Neovim's unnamed register to it for normal `p`.
- Local and SSH paths use the same fixed correlated controls. Focus, control
  binding, instance, request ID, buffer, window, tab, changed tick, and mode
  are validated; text is NUL-free and limited to 256 KiB of UTF-8. There is no
  polling, automatic synchronization, or automatic retry.
- Paste is limited to normal modifiable editor buffers. One-shot copied text is
  removed from caches and redacted diagnostics. Success feedback is profile-
  aware as Off/Speech/Sounds/Both; failures remain audible. Pending requests
  are bounded.
- All four commands were practically confirmed without problems in the
  supplied `dev.4` build.
- Freely assignable commands are now visible in Input Gestures regardless of
  the previously focused application. Outside an exactly recognized Windows
  Terminal control, an assigned gesture is passed through unchanged; events,
  F12, overlays, and default gestures remain in the WT AppModule. Undocumented
  compatibility aliases retain assignments saved by earlier feature builds.
- The `dev.4` practical test confirmed the product category when opening Input
  Gestures from an unrelated application, unchanged gesture pass-through
  outside WT, and correct execution in the bound Neovim control.
- All 38 protocol, 28 bridge, 244 add-on/core/package tests and all Lua
  specifications, including 28 clipboard assertions, pass; the add-on and six
  HTML documents build successfully.

## 0.91.0-dev.1 unreleased feature-branch test build

- Adds a profile-aware focus choice: no announcement, current structured line,
  or the existing file/special context with mode and connection name. Existing
  behavior remains the default.
- Confirmed Insert/Normal session focus plays the sound permitted by existing
  mode-sound settings independently of the focus choice.
- Focus correlation, gating, structured Braille, and fail-open behavior always
  remain active. Automated coverage includes every choice, Unicode/blank
  lines, Braille, independent sound gating, NVDA profiles, and safe schema-5
  migration without re-importing a legacy backup.
- Practical NVDA/Windows Terminal testing confirmed all three choices and mode
  sounds with local and remote SSH sessions without problems.

## 0.91.0 beta release

- Includes control-specific Windows Terminal isolation with fail-open focus
  switching and no activity-based rebinding.
- The activation command remains the global toggle everywhere; each physical
  F12 authorizes exactly one pairing attempt for the focused terminal control.
- Local and remote connections across multiple tabs plus horizontal and
  vertical split panes were practically confirmed without errors.
- Overall maturity remains between alpha and beta; this is not classified as
  stable.

## 0.90.0-dev.3 unreleased feature-branch test build

- Practical `dev.1` testing exposed two linked regressions: F12 did nothing in
  a second WT tab, and the activation command could no longer turn the service
  off there. The separate pre-arm has been removed.
- The activation command is again the global toggle in every control. While
  enabled, each physical F12 authorizes one pairing attempt for exactly the
  focused control.
- Without a fresh Neovim claim, that explicit attempt remains silent and
  creates no choice, binding, or suppression. Regression coverage includes the
  second tab, global deactivation, and silent shell case.
- Practical `dev.3` testing fully confirmed local pairing in the first tab,
  remote F12 pairing in a second tab without reactivation, and global
  deactivation from that second tab.
- Horizontal and vertical WT split panes subsequently worked without errors or
  cross-binding while local and SSH connections remained active in other tabs.

## 0.90.0-dev.1 supplied feature-branch test build

- F12 pairing is a 60-second, one-shot permission for the exact focused Windows
  Terminal control. Unarmed shells, file managers, tabs, panes, and windows are
  inert at the add-on level.
- Events from another connection can no longer move or offer to move a binding.
- Switching among explicitly remembered controls clears suppression first and
  restores only the instance whose correlated focus-context response matches
  the still-focused control.
- Automated multi-control and multi-window coverage is included; practical
  split-pane acceptance remains pending. Product maturity remains between alpha
  and beta.

## 0.90.0 beta release

- Includes the practically confirmed focus-context announcement with filename,
  mode, and configured connection name.
- Overall maturity remains between alpha and beta; this is not classified as
  stable.

## 0.89.0-dev.3 unreleased feature-branch test build

- Focus announcements additionally name the user-configured connection, for
  example “on Example”. Local Windows sessions use “on local”; technical host
  names are not exposed separately.

## 0.89.0-dev.2 unreleased feature-branch test build

- Returning from another application to the same registered WT control now
  actually requests focus context. The previous early return mistook the
  deliberately retained authenticated binding for an internal focus event in
  the same control.

## 0.89.0-dev.1 unreleased feature-branch test build

- A refocused authenticated registered WT control can announce its file or
  special buffer, state, and mode compactly.
- The request is event-driven and correlated. Unbound controls and late or
  mismatched replies have no effect; neither polling nor terminal screen
  scraping is used.
- Practical NVDA/WT testing remains pending. This is not a stable build and
  remains between alpha and beta.

## 0.89.35 beta release

- Registry lifecycle hardening and Windows Terminal binding maintenance are
  published as a prerelease after practical local Windows and an SSH test target
  verification. Overall product maturity remains between alpha and beta.
- Complete non-interference with unbound Windows Terminal panes remains a
  documented follow-up; uncertain suppression state continues to fail open.

- The 0.89.34 trace identifies the apparent F12 failure as an already-active
  swap-file confirmation (`r?`, confirm, swap), not an input or RPC failure.
- `ext_messages` and `ext_popupmenu` are no longer attached at Neovim startup.
  They transfer UI ownership only after an authenticated channel is registered
  and detach again on unregister, snapshot failure, or RPC failure. Native swap
  recovery and other pre-connection prompts therefore remain visible and the
  terminal path fails open.
- F12 observed in hit-enter, pager, or confirmation mode does not write a
  session claim. The user must answer the native prompt first and then press
  F12 from an editor mode; the add-on never chooses a destructive swap action.
- Practical testing confirmed the complete path locally and over an SSH test target:
  F12 during the swap confirmation produced no candidate, the next F12 after
  resolving it connected in Normal mode, the first `i` entered Insert mode,
  and structured text input continued normally. Closing the first editor
  disconnected its client; retries remained fail-open and disabling support
  stopped that client before later sessions received distinct instances.

## 0.89.34 diagnostic test build, superseded by 0.89.35

- Practical 0.89.33 testing proved that the visible F12 mapping is not applied
  to Windows Neovim's internal function-key form. The mapping is removed.
- Neovim documents raw mode `r?` specifically as a `:confirm` query. The UI
  message observer now retains only bounded pre-connection metadata for that
  prompt: active state, message kind, byte length, and a fixed category such as
  swap, overwrite, unsaved changes, quit, delete, or other. Prompt text and
  paths are never retained or reported.

## 0.89.33 failed corrective test build

- The 0.89.32 trace isolates the Windows failure: both key values are exactly
  `<F12>`, the observer and claim have no error, and Neovim nevertheless ends
  normal processing of that reserved key in non-blocking `r?` mode.
- The configured claim key now has a silent, immediate no-op mapping in each
  Neovim input mode. `vim.on_key` still observes and records the claim first;
  the mapping only consumes subsequent default processing. Existing user
  mappings are detected and never overwritten.
- No Escape or other synthetic input is injected. A real Neovim 0.12.3 PTY
  regression sends F12, observes the claim, and requires Normal mode afterward.

## 0.89.32 failed diagnostic test build

- Practical 0.89.31 testing still entered the blocking `r?`/hit-enter mode.
  The observer metadata was present on the wire but omitted by the add-on's
  explicit diagnostic field filter.
- Event diagnostics now expose only bounded fields needed to locate the
  failure: blocking state, fixed current-error code/category, translated F12
  forms and byte lengths, observer/claim error categories, and mode after the
  scheduled claim. No error message or editor text is added.
- State snapshots now distinguish Neovim's blocking flag from its raw mode.

## 0.89.31 diagnostic and corrective test build

- The complete `vim.on_key` observer is now contained by `pcall`, and the
  scheduled registry claim cannot propagate a Lua exception into Neovim's
  input loop. Failures neither disable nor consume a key.
- The first `fullState` carries bounded, non-sensitive metadata only for a
  recognized F12 claim: function-key translation, byte lengths, fixed error
  categories, and mode after the scheduled claim. Normal keys, message text,
  and editor content are never recorded.
- A regression forces a `keytrans` failure and requires it not to escape into
  Neovim input. A real PTY test sends the complete F12 CSI sequence to Neovim
  0.12.3 and verifies both claim and Normal mode.

## 0.89.30 failed beta test build

- Registry inventory is passive again and no longer opens short-lived Neovim
  RPC channels while polling. The previous 1.5-second wait could issue roughly
  30 identity requests per candidate and disturb Neovim channel/UI state. This
  is the strongest concrete difference from the practically verified 0.89.16
  path and the most likely cause of the `r?` regression.
- The selected registry record carries its `sessionNonce` to the real,
  permanent RPC channel. Identity is checked there before `setup()` and
  `register_channel()`; mismatch disconnects fail-open without retrying the
  rejected endpoint. Authentication and TOCTOU resistance remain without a
  second channel.
- The experimental delayed Escape from 0.89.29 is removed, restoring the
  practically verified F12/input path.
- The automated matrix ran with the official Neovim 0.12.3 Linux build. The
  runner explicitly loads its optional `netrw` package; version-specific
  default-dialog details are not treated as protocol.

## 0.89.29 beta test build

- Empty `preConnectErrorCode` and `preConnectErrorKind` in 0.89.28 proved that
  `r?` is not caused by Lua, snapshot, registry, or textlock failure. It is the
  mode left by full normal processing of the physical F12 terminal sequence.
- The proven claim path remains unchanged. Only 100 ms after persisting the
  claim, once remaining terminal-sequence bytes have drained, the plugin feeds
  one Escape. This remains well before NVDA evaluates the claim at 250 ms and,
  unlike 0.89.26, cannot run ahead of queued F12 bytes.
- A regression requires the delayed claim and subsequent Normal mode while F12
  remains unbound.

## 0.89.28 diagnostic test build, superseded by 0.89.29

- Adds only privacy-preserving fields to the first `fullState` for a Neovim
  error already present before connection: `preConnectErrorCode` and a fixed
  error category, never message text, paths, or editor content. This locates
  the persistent pre-input `r?` state without changing the proven input path
  again.

## 0.89.27 failed beta test build

- Restored the `main` input path, but practical testing still found the first
  `fullState` already in `r?`. The cause therefore precedes ordinary input and
  is likely in claim, registry identity probing, or connection setup; 0.89.28
  instruments that boundary.

- Precisely removes the experimental `vim.on_key` changes introduced after
  0.89.22: there is no F12 no-op mapping, raw-termcode special path, general
  callback wrapper, or injected Escape. Input and claim handling now match the
  practically verified 0.89.16 implementation on `main` again.
- Independent work remains intact: registry schema 3, process/nonce
  validation, robust WT lifecycle handling, the required Neovim 0.12
  `vim.str_utfindex` signature fix, and fail-open handling of an actual
  snapshot failure.
- The comparison regression again requires F12 to remain unbound and the
  proven `typed` observer to persist exactly one delayed claim.

## 0.89.26 failed beta test build

- Initially restored Normal mode after F12 but produced `r?` again on the first
  ordinary key. The injected Escape and all other experimental input changes
  were therefore removed from the registry branch.

- After a recognized F12 claim, the plugin executes Escape in the scheduled
  normal event cycle to establish a harmless Normal-mode baseline. This is
  necessary because `vim.on_key` is observational and cannot consume Windows
  Terminal's internal function-key sequence; in practical 0.89.25 testing its
  tail was processed as `v`, leaving Neovim in characterwise Visual mode as
  soon as the connection opened.
- A regression starts deliberately in Visual mode and requires the delayed
  claim to persist exactly once and subsequently restore Normal mode.

## 0.89.25 failed beta test build

- Recognized and persisted F12 again but allowed the observed internal key
  sequence to continue through normal processing. Its first `fullState`
  therefore reported `modeRaw=v`, making subsequent operation appear stuck.

- F12 recognition now performs only raw string comparisons against a termcode
  resolved during plugin setup. It invokes neither `keytrans()` nor another
  Vim function before recognizing the claim inside `vim.on_key`, preserving
  claims when Neovim 0.12 rejects such calls under textlock.
- The regression test deliberately makes `keytrans()` fail during F12 and
  still requires exactly one asynchronously persisted claim sequence.

## 0.89.24 failed beta test build

- Contained visible failures from the input observer, but still kept the
  `keytrans()` call that ran before F12 comparison. Neovim 0.12 therefore hid
  the contained error and silently lost the claim.

- UIA lifecycle validation now runs only in the periodic maintenance sweep.
  It was removed from editor events, connection-state handling, and terminal
  actions after 0.89.23 falsely pruned the active focused tab.
- A focused tab is always considered alive. Inactive tabs require two
  consecutive negative checks five minutes apart before detachment, making a
  single transient UIA gap non-destructive.
- The complete `vim.on_key` handler is now a fail-safe observer: API-version or
  textlock errors cannot reject the actual key or open an `r?`/hit-enter
  prompt. Scheduled claims and spelling checks likewise contain their errors.
  A regression test simulates an API rejection.

## 0.89.23 failed beta test build

- The claim key remains version-independently detected through `vim.on_key`
  and its unchanged `typed` value. When Neovim resolves `<F12>` as a normal
  mapping, an additional silent no-op mapping now consumes it after
  observation. Practical testing still produced `r?`/hit-enter prompts because
  failures in the remaining input observer could still escape into Neovim's
  input loop.

- Snapshots use the new `vim.str_utfindex(text, encoding, index, strict)`
  signature on Neovim 0.11 and newer while retaining the old signature on
  Neovim 0.10. Local Neovim 0.12 therefore no longer enters a Lua/hit-enter
  error on the first mode change.
- Unexpected snapshot failures close the plugin RPC channel without a visible
  Neovim error prompt, making NVDA disconnect fail-open to native WT output.

- Periodic cleanup of closed WT bindings now runs every five minutes instead
  of every two seconds. Immediate disconnect fail-open and registry validation
  during discovery remain unchanged.

- The `registry_probe.py` module required by local registry validation is now
  included in the NVDA add-on. A packaging regression checks the file and its
  relative import in the extracted installation archive.

- Every unexpected add-on exception in a delegated Windows Terminal event now
  falls back to NVDA's native handler exactly once and immediately drops
  session-scoped suppression.
- Registry lifecycle pruning no longer runs synchronously before
  `Terminal.event_gainFocus`, so an add-on management failure cannot prevent
  NVDA from starting native LiveText monitoring.
- An unexpected periodic lifecycle failure now drops suppression fail-open and
  does not reschedule itself.

- Registry schema 3 combines process identity with a random RPC-confirmed
  session nonce against PID, port, and socket reuse.
- Older registry schemas without complete identity proof remain hidden and
  require restarting Neovim after the component update.
- Registry files and nonce RPC responses have absolute time and size bounds;
  permission failures are never treated as proof of process death.
- Only definitively dead private entries and exact nonce-qualified owned plugin
  sockets are pruned. Inherited or user-defined paths remain untouched;
  timeout and access uncertainty are non-destructive.
- A five-minute safety sweep makes closed WT tabs and whole windows detach fail-open;
  their NVDA clients stop off the main
  thread. Neovim and tmux processes are never terminated.
- Multi-tab/window regressions and isolated SIGKILL tests cover local and remote
  paths. Inactive open tabs remain valid through their directly checked UIA
  element; uncertain UIA errors are non-destructive.

## 0.89.22 beta test build, superseded by 0.89.23

- Corrected the Neovim 0.12 snapshot signature but did not prevent normal
  processing of the observed, otherwise unbound F12 key.

## 0.89.21 beta test build, superseded by 0.89.22

- Changed WT binding cleanup to five minutes but still contained the old
  `vim.str_utfindex` call that is incompatible with Neovim 0.12.

## 0.89.20 beta test build, superseded by 0.89.21

- Already contained the packaging and fail-open corrections, but still used an
  unnecessarily short two-second interval for WT binding cleanup.

## 0.89.18 failed beta test build

- The add-on could not import because packaged `registry_probe.py` was missing.
  Settings, Tools menu integration, suppression, and the periodic lifecycle
  sweep therefore never started in this build.

## 0.89.17 failed beta test build

- Material registry changes were mistakenly rebuilt under the same version.
  This ambiguous build must no longer be installed.
- Practical testing found that merely loading the add-on could prevent native
  Windows Terminal output. 0.89.23 replaces it with an explicit fail-open
  barrier.

## 0.89.16 beta test build

- A claim recognized through `typed` is now moved to Neovim's normal event
  cycle with `vim.schedule()`. The `vim.on_key` callback therefore performs no
  registry, filesystem, or regular Vim-function work.
- The regression test explicitly verifies that the claim sequence remains
  unchanged inside the key callback and advances only in the scheduled
  callback.
- Final practical testing confirmed repeated automatic F12 binding with both
  local Neovim 0.12.3 and Neovim 0.10.1 on an SSH test target. With support disabled, the
  observer remained inert and opened no binding dialog.

## 0.89.15 failed beta test build

- The Neovim plugin now recognizes the configured claim key from the unchanged
  `typed` value supplied to its existing `vim.on_key` observer. It no longer
  depends on Neovim 0.10.1 resolving its internal terminal code as an `<F12>`
  mapping.
- An isolated test on that SSH target proved the distinction: Neovim twice reported
  `typed=<F12>` but an internal `key=<t_…>`; the `<F12>` mapping never ran and
  the test timed out.
- The NVDA observer is completely inert while support is disabled. F12 then
  remains an ordinary key and cannot open an add-on dialog.
- Practical testing confirmed automatic connection to the SSH test target and an inert observer
  while support was disabled. Local Neovim 0.12.3 was also found and briefly
  connected automatically, but immediately entered the `r?`/hit-enter state
  and then lost its RPC server. Build 0.89.16 moves the registry write out of
  `vim.on_key`.

## 0.89.14 failed beta test build

- F12 is no longer bound as an NVDA script or synthetically reinjected. The
  Windows-Terminal-only AppModule observes it at the public
  `decide_executeGesture` extension point, allows normal NVDA resolution to
  continue unchanged, and starts claim discovery separately through NVDA's
  event queue.
- With no bound script, NVDA ends F12 resolution with
  `NoInputGestureAction`, so the keyboard hook passes the original physical
  key directly to the operating system. A control test confirmed three real
  claims in the same remote session.
- Practical testing confirmed automatic local pairing, but the SSH test target still
  produced no claim. The successful connection in the report came from manual
  profile and session selection. The isolated follow-up located the remaining
  defect in Neovim's terminal-code-to-mapping resolution.

## 0.89.13 failed beta test build

- Windows Terminal now receives F12 after a short GUI-loop delay, once NVDA's
  input-hook callback has returned. This lets the terminal process the
  function key outside the still-running NVDA script while bounded claim
  discovery continues to start afterwards.
- A practical 0.89.12 run confirmed local claims and one SSH connection to
  the SSH test target. On the subsequent failure, both registries belonging to the actual
  running remote Neovim processes remained at `claimSequence=0`; activation and
  deactivation had correctly stopped and rediscovered their clients.
- Delayed synthetic forwarding still failed in practical testing. Manual
  selection connected the same session, while a physical key allowed through
  with support disabled and subsequent attempts advanced that registry to
  `claimSequence=3`. Build 0.89.14 therefore removes synthetic forwarding.

## 0.89.12 beta test build

- Automatic local pairing now carries a monotonic timestamp captured
  immediately before forwarding F12, matching the manual path. A claim is
  fresh when either its sequence increased from the activation baseline or it
  was written after that exact key press.
- An interactive 0.89.11 test confirmed the complete key path through a
  successful registry claim, isolating the remaining defect to add-on
  evaluation.

## 0.89.11 failed beta test build

- An unchanged interactive check of the original product mapping proved that
  F12 did not reach Neovim at all while NVDA support was active. The raw-key
  decider has therefore been removed.
- F12 is again bound only in the Windows Terminal AppModule. Its script first
  forwards the original gesture through NVDA's public `gesture.send()` method,
  then starts bounded claim evaluation.
- The Neovim mapping changes tried in 0.89.9 and 0.89.10 were reverted after
  being disproved as the cause.
- Forwarding and the Neovim claim worked in practice, but automatic local
  evaluation still failed to recognize the claim reliably from its sequence
  baseline alone. Build 0.89.12 adds a key-press-bound timestamp.

## 0.89.10 failed beta test build

- The F12 claim is now registered separately for every Neovim mode, exactly as
  in the successful interactive probe. On the tested Windows Terminal path,
  the previous combined multi-mode mapping was visible through `maparg()` but
  did not react to the function key represented internally as a terminal code.
- Regression tests verify description, `nowait`, and a callable callback
  separately for Normal, Insert, Visual, Select, Operator-pending, command-line,
  and terminal modes.
- Practical testing with confirmed updated components still failed. An
  unchanged mapping probe then showed that F12 never reached Neovim, so the
  mapping change was not causal.

## 0.89.9 failed beta test build

- Neovim's session-claim mapping is now resolved explicitly without waiting
  for another mapping key. An interactive test proved that Windows Terminal
  delivered F12 and that claiming itself worked, while the previous permanent
  mapping could remain pending in Neovim's mapping resolution.
- The regression test now verifies both repeated claims and the `nowait`
  property required for reliable terminal function-key handling.
- Practical testing showed that `nowait` alone was insufficient. Build 0.89.10
  additionally adopts per-mode registration from the successful interactive
  probe.

## 0.89.8 failed beta test build

- The F12 script binding and synthetic key reinjection were removed. The
  Windows Terminal app module observes the unchanged physical key through
  NVDA's public `decide_handleRawKey` extension point and always allows normal
  delivery to Neovim.
- Claim evaluation runs only while support is active and Windows Terminal is
  focused. Other applications and other keys trigger no add-on action.
- A subsequent interactive probe proved that the unchanged key reached
  Neovim, but the permanent Neovim mapping did not run. Build 0.89.9 corrects
  this final mapping stage.

## 0.89.7 failed beta test build

- Re-injected F12 before refreshing focus. Practical tests still showed
  state-dependent unchanged claim counters; 0.89.8 removes reinjection
  completely.
- The aggressive Neovim mapping refresh tried in 0.89.6 was removed. Practical
  testing showed unchanged claim counters, locating the defect before the
  Neovim mapping; user mappings are therefore not overwritten repeatedly.

## 0.89.6 failed beta test build

- Tried refreshing the F12 mapping repeatedly. Practical testing disproved the
  assumed cause, and 0.89.7 removes this approach.

## 0.89.5 beta test build

- `NVDA menu → Tools → Neovim Access Link: Remove components...` can completely
  remove the bundled components from this Windows computer and from explicitly
  selected saved Linux connections.
- The accessible multi-target checklist, background work, and compact results
  summary match the installation workflow. Saved connections, Neovim and SSH
  configuration, and unrelated plugins are preserved.

## 0.89.4 beta test build

- Complete German and English Markdown sources and separate HTML outputs for
  the Quick Guide, manual, and developer documentation.
- Project licensing is GPL-2.0-only. The unmodified license is included in both
  installable packages; contribution and additional relicensing terms are
  documented separately.
- Standard GitHub community files were added and private product requirements
  removed from the public source tree.

## 0.89.3 beta test build

- Separate German and English Quick Guide, user manual, and developer HTML
  documents with validated links.
- Bounded local F12 follow-up handles delayed atomic registry updates.
- Diagnostics distinguish local/remote inventory and claim resolution without
  exposing editor text.

## 0.89.2 beta test build

- A unique local F12 claim is resolved immediately without waiting for slower
  SSH inventory work.

## 0.89.1 first beta preparation

- Centralized product metadata and the visible “Neovim Access Link” name.
- Stable internal add-on ID retained for upgrades and profile settings.
- NVDA private API exceptions documented in ADR-0002.

Earlier development established protocol v2, SSH stdio, local loopback RPC,
rootless embedded components, multiple explicitly bound runtime sessions,
Windows Terminal AppModule isolation, fail-open terminal behavior, and
structured speech/Braille planning. Git retains the detailed experimental
history.
