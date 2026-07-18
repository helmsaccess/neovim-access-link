# Current status

Status: 2026-07-18, beta version 0.94.0; overall maturity remains between
alpha and beta.

Version `0.94.0` carries forward the practically confirmed cleanup branch and
uses the new internal NVDA ID
`NeovimAccessLink` throughout. This is an intentional clean
installation boundary with no import of former settings, profiles, or gesture
assignments. Obsolete configuration migration, AppModule script aliases, and
Python transition APIs for bridge, RPC, and connection instances are removed.
Product version, channel, and maturity classification are unchanged.
All 277 add-on/core/package tests, 42 protocol tests, 31 bridge tests, both
Neovim Lua suites, the final add-on archive, and six HTML builds pass. Practical
NVDA acceptance of the clean-install boundary remains open.

Test build `0.93.0-dev.7` sends Oil's public `parsed_name` to speech and
Braille while a file-manager row is edited but not yet written. The confirmed
old name remains the sole basis for path and public completion action until
`:w`. Existing `fileManagerEntryChanged` normalization now also retains the
fixed motion kind, so line/file boundary cues no longer disappear for `0`,
`$`, `gg`, `G`, or edge positions after line changes. Automated regressions
pass. This Oil path was practically confirmed with Windows/NVDA, Windows
Terminal, and Neovim 0.12; draft name and cues work. Oil is currently the only
file manager practically tested on Windows. netrw, mini.files, nvim-tree, and
Neo-tree have automated or isolated coverage and will be accepted practically
over time. Oil provides a solid foundation for that work.

Test build `0.93.0-dev.6` makes return from a message-producing Ex command
fully structured. The return mode is not inserted as an extra spoken fragment;
its mode cue plays on the immediate `messageReceived`, whose presentation
always keeps the message and, according to Session focus, appends nothing, the
current line, or context, mode, and connection name. Later asynchronous
messages do not carry that association. A new 118-assertion file-manager
workflow specification covers the public Oil, mini.files, nvim-tree, and
Neo-tree action matrices plus state changes, batches, failure/cancellation,
path minimization, Unicode, and spaces. The real-TUI prompt proves a selected
No answer; speech tests cover Yes, No, and
Cancel, and opening from a manager follows all three focus presentations.
Automated aggregate tests pass; practical acceptance of `dev.6` remains open.

Test build `0.93.0-dev.5` hardens Oil's real file-action dialog for
rename/move, copy/duplicate, delete, trash, purge, and restore. The strictly
bounded parser now accepts Oil's actual indentation, still transports neither
names nor paths, and marks destructive actions with a fixed class. Directly
typed Y/N is observed only; `promptClosed` distinguishes acceptance and
cancellation while Oil alone handles the key and filesystem action. Isolated
real-Oil runs prove cancelled rename, duplicate, and delete without filesystem
changes plus confirmed deletion. The 105 file-manager assertions and real-TUI
cancellation test pass. For complete confirmation coverage, Oil should keep
`skip_confirm_for_simple_edits = false`. Central prompt paths for nvim-tree,
Neo-tree, and mini.files remain documented; their complete real-plugin matrix
is still open. All 270 add-on/core/package tests, 41 protocol tests, 31
bridge/TUI tests on each of Neovim 0.10.1 and 0.12.3, and all Lua
specifications pass; the add-on and six HTML documents build reproducibly for
`dev.5`.

Test build `0.93.0-dev.4` implements file-manager findings F6, F7, and F9 from the
analysis. The netrw fallback distinguishes banners and thin, long, wide, and
tree lists while preserving spaces, tabs, and Unicode; tree roots and symlink
targets are handled explicitly. Built-in adapters are selected directly by
the active `filetype`. Optional adapters have 5 ms per synchronous call;
three repeated errors or overruns activate a five-second cooldown only for the
affected buffer. The deadline is checked on normal events and is neither a
timer nor polling. Buffer teardown releases runtime state, and
`:checkhealth nvim_nvda` exposes fixed counters without error text, paths, or
names. `root` and `currentDirectory` are distinct; nvim-tree walks its public
parent nodes to the tree root, while mini.files distinguishes branch start and
focused level. Empty-manager context speaks only the last directory name, not
the complete path. Ninety-nine file-manager assertions pass. An ordering of
`CmdlineLeave` and internally executed `:normal` keys found by the full Neovim
0.10.1 run is now distinguished from direct navigation through the empty
`typed` value. File-manager buffers now keep a persistent semantic Braille
plan containing name, type, and state instead of the decorated raw row.
Routing is allowed only inside a name found unambiguously in the real buffer
line; synthetic status segments and ambiguous names cannot move the cursor.
Real-TUI coverage accepts and cancels `vim.ui.input` and selects an item from
`vim.ui.select`. Lua calls to `vim.fn.confirm` report the prompt and selected
choice on Neovim 0.10.1 as well; the semantic mode transition closes stale
prompt state when no `msg_clear` arrives, while concurrent and late Neovim
0.12.3 UI output is deduplicated. Oil's custom confirmation float has no public
prompt source. A narrow fallback therefore recognizes only its dedicated
`oil_preview` float and fixed action verbs, reports count plus Y/N, and
suppresses rendered names and complete paths. Cancellation and path
suppression are verified in an isolated run of the real Oil main branch.
Further real-plugin prompt matrices and physical Braille hardware remain open.
All 270 add-on/core/package tests, 41 protocol tests, 31 bridge/TUI tests, and all Lua specifications pass; the add-on
and six HTML documents build reproducibly for `dev.4`.

Test build `0.93.0-dev.3` implements the first four file-manager items left
open by the terminal-analysis comparison. Names, paths, roots, types, and external
adapter labels remain bounded in bytes for the protocol budget, but only at
validated UTF-8 code-point boundaries. Invalid adapter output is discarded per
field. A separate event-only layer subscribes to public Oil, nvim-tree,
Neo-tree, and mini.files events, rereads only the active semantic state, and
deduplicates it while coalescing render bursts in one scheduler cycle. Marks,
Copy, and Cut are distinct fixed values; same-entry changes including unmark
and clipboard clear are explicit in speech and planned Braille messages.
Typed action results complement file-manager state. mini.files, nvim-tree, and
Neo-tree provide confirmed successes; Oil also exposes public completion
errors and detectable cancellations. Only basenames, fixed values, and a
coalesced count are sent, while an intervening buffer/window/tab/manager change
drops output. Sixty-two file-manager assertions and speech regressions pass.
Plugin paths without public failure/cancellation events are not guessed. Real
plugin versions, prompt/cancellation matrices, and hardware Braille remain the
next phases; the new path adds no polling and awaits the later grouped
practical test.
All 267 add-on/core/package tests, 41 protocol tests, 31 bridge/TUI tests, and
all Lua specifications pass; the add-on and six HTML documents build
reproducibly for `dev.3`.

Test build `0.92.0-dev.11` on branch `feature/terminal-file-manager-hardening`
implements eleven focused hardening steps. Successful `:bp`/`:bn` buffer
switches within the same tab and window now use the profile-aware session-focus
choice: silent, current destination line, or destination context with mode and
saved connection name. Processing remains driven by `BufEnter`-based
`contextChanged`; an earlier mode event cannot swallow the announcement.
Tab/window destination positions remain present and mode cues stay independent.
Transient spoken return
modes are coalesced into that configured destination presentation,
so No announcement stays silent and neither a clipped mode fragment nor a
duplicate mode overwrites the line. Structured command-line type keeps Ex
commands distinct from search. Automatic destination
cursor/change events neither overwrite the destination line nor compare its
text with the source buffer. The same entry policy now covers a terminal
buffer created by `:terminal`: the focus choice controls its presentation,
Current line waits for the first real terminal line, and the automatic cursor
event stays silent. Reversed terminal-context/final-mode ordering is coalesced
as well, and command-line text cannot leak into the new buffer as a Normal-mode
motion. Entering direct terminal input presents the complete
cursor line while retaining the Insert cue. Raw `nt` is canonical
`terminalNormal`; command-line echo uses its UTF-8 byte position; a freely
assignable fixed, validated local/SSH `stopinsert` command can replace the
layout-dependent `Ctrl+\`, `Ctrl+N`; and `TermClose` reports process status.
Passthrough changes fail open before feedback and duplicate terminal context
events do not replay the cue. Command-line entry now has a distinct tone;
return, no-op buffer navigation, and Neovim's `E89` for `:bd` on a running
terminal job are explicit without ever invoking `:bd!`. UI messages on Neovim
0.12 are processed outside the `vim.ui_attach` fast-event context and no longer
create an `E5560` hit-enter state. For window and tab changes, the Context
choice now combines destination position, explicit file or special context,
state, mode, and connection in one announcement. A short name is therefore
reported as `file T`, while terminal modes no longer duplicate “terminal”;
mode cues remain separate. A disconnected but still remembered local instance
no longer blocks fresh SSH pairing: only authenticated bindings constrain F12
to their prior target kind; otherwise the physical gesture is resolved again
across the complete inventoried target set. All 265 add-on/core/package tests, 41 protocol
tests, 31 bridge/TUI tests, and all Lua specifications pass; the add-on and six
HTML documents build successfully. Practical acceptance confirmed the
implemented terminal, buffer, window/tab, and fresh SSH-pairing paths without
further issues. Pager variants and the complete negative Windows Terminal
matrix remain open.

Branch `feature/copy-paste` implements four freely assignable, explicitly
invoked NVDA commands: copy the Visual selection, copy register 0, paste
Windows clipboard text through Neovim's paste API, or store it in register 0
and point the unnamed register to it for normal `p`. Local and SSH use the same
correlated protocol path. It validates focus, control binding, instance,
request ID, buffer, window, tab, changed tick, and mode; limits text to 256 KiB
of UTF-8; and keeps copied text out of canonical state and diagnostics. Paste
is limited to normal modifiable editor buffers. All 38 protocol, 28 bridge,
244 add-on/core/package tests and all Lua specifications, including 28
clipboard assertions, pass; the add-on and six HTML documents build
successfully. All four commands were practically confirmed without problems
in the supplied `dev.4` build.

The first build registered freely assignable commands only in the Windows
Terminal AppModule. NVDA's applicability filtering therefore hid the entire
product category when Input Gestures was opened from Explorer or another
application. The correction adds unbound global metadata, revalidates the
exact WT `TermControl` identity on invocation, and passes the gesture unchanged
in every other application. `dev.4` practical acceptance fully confirmed the
category from an unrelated application, unchanged pass-through there, and
correct execution in the bound Neovim control.

The released control-isolation path still treats each physical F12 press as one
authorization for exactly the focused Windows Terminal control. Activity from
another Neovim cannot rebind it. Local/SSH tabs and horizontal/vertical split
panes were practically confirmed; separate windows, tmux, and the complete
unbound-shell-pane negative matrix remain pending.

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

The project historically calls its short-lived JSON session files a
“registry”; this is not the Windows Registry, and neither `HKCU` nor `HKLM` is
used. File-based session-registry schema 3 validates local and remote sessions with a random RPC
endpoint nonce and, on Linux, process-start identity. Definitively dead private
entries and exact PID-plus-nonce plugin sockets are pruned; inherited and
user-defined socket paths are never unlinked.
Uncertainty remains non-destructive.
Closed individual WT tabs or whole windows require two negative five-minute sweeps,
detach fail-open, and stop their NVDA client
off the main thread without terminating Neovim or tmux. Isolated local and
`user@example.invalid` SIGKILL tests left no visible session or owned nonce-qualified
session-file/socket debris.
Focused tabs are never removed by UIA maintenance, and lifecycle validation
does not run from editor, connection-state, or terminal-action paths.
Discovery reads session files, process identity, and endpoint metadata passively.
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
further presses advanced its session record to `claimSequence=3`. Build 0.89.14
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
Build 0.89.16 schedules the session-file write with `vim.schedule()` outside
`vim.on_key`.
Final practical testing of 0.89.16 confirmed automatic binding for both local
Neovim 0.12.3 and Tessa with Neovim 0.10.1. Repeated physical F12 marks worked,
and with support disabled the observer remained completely inert and opened no
binding dialog. Marking, the transient session-file claim, add-on binding, and the
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
and no broad Braille hardware matrix. Exact one-shot F12 gating and removal of
activity-based rebinding now have automated negative coverage, but practical
multi-pane non-interference and the Braille overlay fallback still require
acceptance testing; uncertain state must remain fail-open.

The reproducible build produces separate German and English Quick Guide,
manual, and developer HTML files.
