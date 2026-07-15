# Current status

Status: 2026-07-15, beta version 0.90.0; overall maturity remains between
alpha and beta.

The development branch requests correlated structured context from Neovim's
state cache when an authenticated registered WT control regains focus. File or
special-buffer identity, state, and mode are planned compactly for speech and
Braille. Unbound controls and late or mismatched replies have no effect.
Practical NVDA/WT testing confirmed the announcement when returning from
Explorer and the configured connection-name suffix. The result is still not
classified as stable.

The first `0.89.0-dev.1` practical test produced no filename announcement when
returning from Explorer to the same WT control. Diagnostics contained focus
loss, renewed focus, and suppression, but no focus-context request. An early
return had treated the deliberately retained authenticated binding as an
internal same-control focus event. `0.89.0-dev.2` distinguishes real focus
return; the correction was confirmed in practical testing.

Registry schema 3 validates local and remote sessions with a random RPC
endpoint nonce and, on Linux, process-start identity. Definitively dead private
entries and exact PID-plus-nonce plugin sockets are pruned; inherited and
user-defined socket paths are never unlinked.
Uncertainty remains non-destructive.
Closed individual WT tabs or whole windows require two negative five-minute sweeps,
detach fail-open, and stop their NVDA client
off the main thread without terminating Neovim or tmux. Isolated local and
`eh@tessa` SIGKILL tests left no visible session or owned nonce-qualified
registry/socket debris.
Focused tabs are never removed by UIA maintenance, and lifecycle validation
does not run from editor, connection-state, or terminal-action paths.
Discovery reads registry, process identity, and endpoint metadata passively.
The nonce is verified only on the permanent RPC channel, before plugin setup
or registration; inventory and polling never create throwaway channels.

Protocol v2, remote SSH stdio, local Windows loopback RPC, rootless component
installation and explicit per-target removal, F12 claims, multiple runtime instances, and explicit Windows
Terminal bindings are implemented. Local and SSH sessions can run in parallel
across tabs, windows, accounts, and tmux. The global service contains no global
input or focus hooks; Windows-specific behavior is confined to the Windows
Terminal AppModule and failures restore native terminal output.

Component removal runs outside NVDA's main thread for explicitly checked local
or SSH targets. It preserves saved connection profiles, user configuration,
SSH files, unrelated plugins, and running-session data, and reports every
result in a non-blocking summary.
Complete component removal was also confirmed with the installed test build.
An unchanged interactive mapping test with confirmed updated components showed
that F12 did not reach Neovim while NVDA support was active. Returning `True`
from `decide_handleRawKey` permits further NVDA processing but does not
guarantee OS delivery. Build 0.89.11 removes that observer, binds F12 locally
in the Windows Terminal AppModule, and explicitly forwards the original
gesture with `gesture.send()` before claim evaluation.
The interactive 0.89.11 test then confirmed `onKey`, the original mapping
callback, and a successful claim. Build 0.89.12 carries the monotonic timestamp
captured immediately before `gesture.send()` into automatic local evaluation,
so the exact fresh key press is recognized in addition to the activation
baseline.
Build 0.89.12 then confirmed local pairing and one Tessa SSH connection, but
the next F12 left both registries belonging to the actual running Tessa
Neovim processes at `claimSequence=0`. Build 0.89.13 therefore forwards F12
after a ten-millisecond GUI-loop delay, once NVDA's input-hook callback has
returned; evaluation still starts after 250 milliseconds.
Practical testing disproved that synthetic path as well. Manual selection
connected the same Tessa session, and a physical F12 control followed by
further presses advanced its registry to `claimSequence=3`. Build 0.89.14
therefore observes F12 through `decide_executeGesture` without binding an NVDA
script. NVDA's resulting `NoInputGestureAction` path passes the original key
directly, while only claim evaluation is queued to NVDA's event queue.
The 0.89.14 report then confirmed only automatic local pairing; its Tessa
connection was manual. An isolated Neovim 0.10.1 run consistently received
F12 as `typed=<F12>` but represented the internal key as a terminal code and
never resolved the `<F12>` mapping. Build 0.89.15 therefore evaluates `typed`
in the existing `vim.on_key` observer. The NVDA observer now ignores F12
completely while support is disabled.
Practical testing of 0.89.15 confirmed Tessa and the inactive observer while
support was disabled. Local Neovim 0.12.3 connected automatically but
immediately entered the `r?`/hit-enter state and then lost its RPC server.
Build 0.89.16 schedules the registry write with `vim.schedule()` outside
`vim.on_key`.
Final practical testing of 0.89.16 confirmed automatic binding for both local
Neovim 0.12.3 and Tessa with Neovim 0.10.1. Repeated physical F12 marks worked,
and with support disabled the observer remained completely inert and opened no
binding dialog. Marking, the transient registry claim, add-on binding, and the
transport connection are therefore distinct and practically confirmed stages.

Practical testing of 0.89.35 confirmed the correction for the later `r?`
regression. With a native swap-file confirmation active, the first F12 did not
create a claim (`changed=false`, no candidate). After the prompt was resolved
in Neovim, the next F12 connected with `keyModeAfterClaim=n`; the first `i`
entered Insert mode and subsequent text and newline input produced structured
`textChanged` events. Fresh local Windows Neovim and Tessa SSH sessions showed
the same normal-to-insert transition, and switching among remembered local and
remote terminal tabs returned a current `fullState`. No hidden `r?` state
recurred in this test. The first local editor's later exit disconnected its
client; bounded retries did not restore suppression, and disabling support
stopped the client. Subsequent local and SSH sessions used distinct connection
instances, so the original connection was not silently reused.

The main connection paths were tested with the reference environment, but the
overall maturity remains alpha to beta. Not every speech, menu, editor-mode,
file-manager, profile, reconnect, and error path has extensive practical
coverage. Braille has not been tested with physical hardware and very likely
contains bugs. Physical-display testing and correction are a priority.

Known limits include Windows Terminal as the only approved front end, no GUI
Neovim, no portable or automatic `NVIM_APPNAME` layout, an uninvestigated older
Rocky Linux 9/Neovim failure, limited long-duration and interruption testing,
and no broad Braille hardware matrix. In addition, complete non-interference
with unbound Windows Terminal panes is not yet proven. Remembered binding,
application-wide F12 observation, activity-confirmed rebind prompts, and the
Braille overlay require further isolation analysis and negative multi-pane
tests; uncertain state must remain fail-open.

The reproducible build produces separate German and English Quick Guide,
manual, and developer HTML files.
