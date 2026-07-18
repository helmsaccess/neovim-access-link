# Architecture

The Lua plugin is authoritative for editor semantics. On Linux it exposes a
private Unix RPC socket; a Python bridge converts selected notifications to
bounded protocol-v2 frames over Windows OpenSSH stdin/stdout. On Windows the
same plugin starts a dynamic Neovim RPC endpoint bound only to `127.0.0.1`, and
the add-on uses a dedicated local client.

The NVDA-independent core validates sessions, sequences, Unicode positions,
and plans speech/Braille. The Windows Terminal AppModule owns focus events,
F12 observation, terminal identity, overlays, native-output suppression, and
the default-bound diagnostic command. The global plugin owns lifecycle,
settings, installation, connection services, and unbound script metadata for
freely configurable commands.

The add-on registers only the validated `NeovimAccessLink` section in NVDA's
`config.conf`. NVDA's aggregation layer handles profile inheritance and writes;
profile switches reload effective values without stopping an authenticated
connection. Former add-on IDs, separate JSON settings files, and configuration
schema versions are intentionally neither read nor converted.

## Explicit clipboard path

NVDA owns the Windows clipboard. Four freely assignable, globally discoverable
NVDA scripts read or write it through NVDA's public `api.copyToClip` and
`api.getClipData`; the bridge and Neovim receive no general Windows clipboard
access. Neovim exposes only the active Visual selection, register 0, a fixed
`nvim_paste` entry point, and register 0 as the fixed backing store for the
unnamed paste register. Writing changes no buffer and no named user register.

Every action carries a request ID and expected buffer, window, tab, changed
tick, and raw mode. NVDA accepts the result only for the still-focused,
authenticated, and bound instance. One-shot copied text is removed before the
client or bridge updates canonical state. The path is event driven and uses no
polling, automatic clipboard synchronization, or automatic retry.

## Returning from the command line

`CmdlineLeave` creates a one-shot result association for a non-empty Ex
command. Only the immediate `messageReceived` proven by `msg_show` or
`v:statusmsg` receives `commandLineReturn=true`; the association is then
discarded. NVDA uses it to play the already reached return mode's cue and
combine the message with the selected focus presentation. No timing heuristic
or delayed mode event is involved, and later asynchronous messages remain
ordinary messages.

## Event-driven file-manager adapters

`file_manager.lua` obtains and normalizes the current semantic entry. The
separate `file_manager_events.lua` layer subscribes only to public supported
plugin events: Oil mutation and `OilActionsPost` events, mini.files
buffer/action events, nvim-tree render/file/folder events, and Neo-tree
render/clipboard/file-action events. A callback
rereads only the still-active buffer or window through the adapter. One
central comparison drops equal state, while callbacks in one Neovim scheduler
cycle cause at most one reread. Missing or incompatible plugin APIs fail open
to existing navigation. There are no timer queries or filesystem polling.

The only narrow exception to purely semantic plugin APIs is Oil's own
confirmation float. Because Oil exposes no public pre-action event,
`file_manager_prompt.lua` recognizes only a real float whose exact `filetype`
is `oil_preview`. The event-driven parser examines at most 200 lines, accepts
fixed action words after optional indentation, and reports only action, count,
and the Y/N choice. Names, paths, and raw lines never leave Neovim; unknown
rendering fails open. Direct Y/N is observed in the existing key-input event.
Buffer closure is published one scheduler cycle later so the choice is present
without a timer or polling. There is no general popup parser. Risk, tests, and replacement are recorded in
`adr/0003-oil-confirmation-fallback.md`.

State distinguishes selection marks, the plugin clipboard's Copy/Cut state,
and expansion. The plugin sends only fixed values; NVDA plans same-entry
deltas as one compact speech and Braille message. This layer changes neither
terminal binding, gating, nor native output.
`root` and `currentDirectory` remain separate UTF-8-validated values: the
manager/branch root versus its focused level. If a public API reliably exposes
only one of them, nothing is inferred from the entry path. Focus context
without an entry locally reduces the level to its final name and does not
speak a complete path.
Oil additionally separates the edited display name from confirmed filesystem
identity: `parsed_name` immediately drives the semantic name, while `name`
continues to drive the path until `:w` and public action completion. Generic
cursor events remain normalized as `fileManagerEntryChanged`, but retain their
allowlisted motion kind for edge cues. The semantic row therefore displaces
neither edit state nor navigation cues.

The persistent file-manager Braille plan uses the same typed name, type, and
state. It creates a routing map only when the name occurs exactly once in the
real `lineText`; synthetic type/status cells and ambiguous names have no route
target. The unchanged control path still validates session, buffer, window,
line, and `changedtick`.

Public completion events are normalized separately as
`fileManagerActionResult`. Source and destination paths are reduced to an
optional basename before transport, while action, result, and type come from
small allowlists. Synchronous bulk actions in one target are combined within
one scheduler cycle. Buffer, window, tab, and manager are checked again before
output. Of the currently checked APIs, only Oil also exposes completion errors
and some detectable cancellations; a missing failure event in another plugin
is not guessed.
The action matrix includes create, add, change, copy, rename, move, delete, and
restore wherever the plugin exposes a public completion event. Opening a file
remains a normal `contextChanged` buffer transition and therefore uses the
same profile-selected focus presentation as other buffer changes.

Built-in adapters are selected solely from the active `filetype` before they
are called. External adapters remain optional synchronous extensions. Their
detector and provider calls are measured; three repeated errors or calls over
5 ms activate a five-second cooldown for the affected buffer. The deadline is
checked only on an event that already occurred and creates neither a timer nor
polling. `BufWipeout` removes the state. Checkhealth output contains only the
adapter name and fixed counters, never error text, paths, or file names.

NVDA therefore lists configurable commands even when Input Gestures is opened
from another application. On invocation, the global adapter reads focus once
and delegates only for a complete, allowed Windows Terminal `TermControl`
identity. Otherwise it sends the original user-assigned gesture unchanged and
does not alter the gate, bindings, or suppression. This discoverability layer
does not move focus events, F12, overlays, or terminal suppression out of the
Windows Terminal AppModule. Undocumented AppModule aliases preserve gesture
assignments saved before this move without creating a second configuration
surface.

## Localization boundary

Only the NVDA side selects the human output language. The Global Plugin
initializes NVDA's public gettext domain `nvda` and passes its translation
callable to the otherwise NVDA-independent `SpeechPlanner`. The bridge,
protocol, and Neovim plugin continue to transport typed state, document
content, and third-party messages unchanged; they know neither the active NVDA
language nor any catalog. Language selection therefore remains at the final
trusted presentation boundary and cannot affect transport or session state.

PO/POT files are versioned development sources outside the add-on staging
tree. The deterministic builder validates and compiles them into
`locale/<language>/LC_MESSAGES/nvda.mo`; only MO files and optional translated
manifest fields are shipped. Missing entries use gettext's English fallback
and must never block activation, connection, or fail-open behavior.

## Terms: marking, claim, binding, and connection

“Registry” below means a file-based Neovim session registry, never the Windows
Registry. The implementation creates no `HKCU` or `HKLM` keys. Records are
short-lived JSON files below `%LOCALAPPDATA%\nvim-nvda\sessions` on Windows and
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` (or a private per-user `/tmp` fallback)
on Linux. These files register Neovim sessions, not Windows Terminal windows,
tabs, or panes. Their concrete connection binding exists only in the NVDA
add-on's memory.

A **session mark** is the explicit user action in the focused Neovim,
normally one physical F12 press. It is distinct from Neovim editor **marks**
such as `ma` or `'a`.

A **claim** is only the transient, machine-readable evidence of that action in
the Neovim instance's private JSON session record: `claimSequence` increases
monotonically and `claimedMonotonic` is updated. A claim does not open a
transport, authenticate a peer, permanently select a terminal tab, or survive
a plugin restart.

**Claim resolution** compares values read after the key press with the
activation inventory baseline. Exactly one fresh result may create a
**binding** from the focused Windows Terminal control's stable `TerminalIdentity`
to a new `ConnectionInstance`. Only a successful TCP or SSH handshake by that
instance creates a **connection** and permits structured output or native
terminal suppression. Manual target selection narrows discovery to the chosen
profile but still requires the same physical mark and fresh claim resolution
before entering the typed connection and binding path.

For F12 pairing, the Windows Terminal AppModule observes the gesture through
the public `decide_executeGesture` extension point without binding a script.
Normal NVDA resolution therefore reaches `NoInputGestureAction` and lets the
keyboard hook pass the original physical key directly to Windows Terminal and
Neovim. The observer queues bounded claim evaluation separately and remains
inert while support is disabled. Neovim recognizes the configured claim key
from `vim.on_key`'s unchanged `typed` value rather than a terminal-code-sensitive
mapping. It schedules the registry write into the normal event cycle so the
input callback remains free of filesystem and regular Vim-function work, then
atomically increments its registry claim sequence. The add-on
then compares current sequences with the inventory baseline and binds only the
freshly changed session. Local pairing also carries a monotonic timestamp
captured for the observed key press, identifying the registry claim
from that exact F12 press. It never guesses from terminal text or titles.

Each `ConnectionInstance` has its own target, transport, session, client, and
state. A stable UI Automation runtime ID binds one instance to one tab. Only
the focused bound instance can produce output. Switching clears planners and
may request `fullState`; stale or unbound events are ignored.

File-based session-registry schema 3 binds discovery to a random RPC-confirmed `sessionNonce` and,
on Linux, `/proc/<pid>/stat` process-start ticks. Definitively stale private
records and plugin-owned socket paths both use PID plus nonce, so exactly stale
owned pairs can be pruned without touching a reused PID's new session.
Inherited and user-defined socket paths are never unlinked.
Timeouts, access failures, and other uncertainty retain the record but hide it
from selection.
Older registry schemas are hidden because they cannot prove process and
endpoint identity; Neovim instances running an older component must be
restarted after updating.
Inventory validates registry structure and process identity passively. Only
the selected permanent RPC channel queries the nonce, before plugin setup and
registration. A mismatch disconnects fail-open and is not retried.

While connections exist, a five-minute main-loop lifecycle sweep validates the
exact WT tab by HWND, process ID, and UIA runtime ID. It is maintenance only
and never runs from editor-event, connection-state, focus, or action paths.
The focused identity is positive proof of life; an inactive identity must be
absent in two consecutive sweeps before detachment. Closing one tab therefore
detaches only its instance after confirmation; closing a whole WT window
detaches every confirmed-absent instance in that window. Client shutdown is
moved off NVDA's main thread. A directly live hidden tab is retained, and any
UIA uncertainty fails open without deleting a binding.

Network, SSH, DNS, socket reads, reconnects, installation, and substantial
parsing never run on NVDA's main thread. Results return through NVDA's event
queue. Queues and waits are bounded, delayed actions are owned until execution,
and shutdown uses stop events and bounded joins.

The session gate suppresses native terminal output only when activation,
authenticated full state, a Neovim context, focus, and exact binding all hold.
Any failure clears the gate and fails open.

## Focus context for registered terminal controls

When an already authenticated remembered Windows Terminal control regains
focus, the add-on requests its current structured context once. The local
client or SSH bridge answers from the canonical state cache maintained by
Neovim events. A request ID binds the reply to that focus event. Current focus
identity, instance, exact binding, and authentication are checked again before
output; focus loss invalidates pending requests. Unbound controls send no
request and receive no add-on output. This path is event-driven and explicitly
uses neither polling nor terminal screen scraping.
Presentation of the confirmed response is profile-selectable: silent, current
structured line, or the existing file/special context with mode and the
user-configured connection name. This selection changes neither the request
nor its gating effect. Insert/Normal sounds are offered only after the same
successful correlation and independently of the announcement choice; existing
sound settings remain authoritative. Technical SSH target addresses are not
inserted into semantic editor state.

## Control-specific Windows Terminal pairing

Windows Terminal distinguishes windows, tabs, and panes. `TerminalIdentity`
therefore names the actual UI Automation `TermControl` by process, window
handle, and complete runtime ID instead of assuming that every control is a
tab.

- The activation command is always the global on/off toggle. While enabled,
  the physical F12 press itself authorizes one pairing attempt for exactly the
  focused control. Delayed main-thread handling rejects it after any intervening
  identity change. The observer is shared by all Windows Terminal AppModules.
- In an unbound control, explicit F12 may run one bounded registry/target
  check. Without a fresh Neovim claim it remains silent and creates no choice,
  binding, feedback, or suppression.
- Events from a different connected Neovim instance never offer or perform an
  activity-based rebind.
- Focus loss and every control change clear suppression immediately. A
  remembered authenticated control only becomes active again after its bound
  client answers a request-ID-correlated focus-context request while the exact
  control remains focused.
- Multiple explicitly bound controls may coexist in the same window or in
  separate Windows Terminal windows. Switching selects only the corresponding
  client; late replies and unbound controls remain native.

The remaining structural limit is that a Neovim focus-context response proves
the bound authenticated RPC state, but not independently that a shell or tmux
program has not replaced Neovim inside the same `TermControl`. A future
Neovim-to-add-on `FocusGained`/`FocusLost` prototype should investigate this
without screen scraping. The Braille overlay is still considered for eligible
terminal controls and must continue to fall back when the gate is inactive.
