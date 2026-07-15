# Changelog

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
