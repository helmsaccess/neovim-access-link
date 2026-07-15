# Changelog

## 0.89.35 beta release

- Registry lifecycle hardening and Windows Terminal binding maintenance are
  published as a prerelease after practical local Windows and Tessa SSH
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
- Practical testing confirmed the complete path locally and over Tessa SSH:
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
- Multi-tab/window regressions and isolated SIGKILL tests cover local and Tessa
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
  local Neovim 0.12.3 and Neovim 0.10.1 on Tessa. With support disabled, the
  observer remained inert and opened no binding dialog.

## 0.89.15 failed beta test build

- The Neovim plugin now recognizes the configured claim key from the unchanged
  `typed` value supplied to its existing `vim.on_key` observer. It no longer
  depends on Neovim 0.10.1 resolving its internal terminal code as an `<F12>`
  mapping.
- An isolated Tessa test proved the distinction: Neovim twice reported
  `typed=<F12>` but an internal `key=<t_…>`; the `<F12>` mapping never ran and
  the test timed out.
- The NVDA observer is completely inert while support is disabled. F12 then
  remains an ordinary key and cannot open an add-on dialog.
- Practical testing confirmed automatic Tessa connection and an inert observer
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
  claims in the same Tessa session.
- Practical testing confirmed automatic local pairing, but Tessa still
  produced no claim. The successful connection in the report came from manual
  profile and session selection. The isolated follow-up located the remaining
  defect in Neovim's terminal-code-to-mapping resolution.

## 0.89.13 failed beta test build

- Windows Terminal now receives F12 after a short GUI-loop delay, once NVDA's
  input-hook callback has returned. This lets the terminal process the
  function key outside the still-running NVDA script while bounded claim
  discovery continues to start afterwards.
- A practical 0.89.12 run confirmed local claims and one SSH connection to
  Tessa. On the subsequent failure, both registries belonging to the actual
  running Tessa Neovim processes remained at `claimSequence=0`; activation and
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
