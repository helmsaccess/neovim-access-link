# Architecture

The Lua plugin is authoritative for editor semantics. On Linux it exposes a
private Unix RPC socket; a Python bridge converts selected notifications to
bounded protocol-v2 frames over Windows OpenSSH stdin/stdout. On Windows the
same plugin starts a dynamic Neovim RPC endpoint bound only to `127.0.0.1`, and
the add-on uses a dedicated local client.

The NVDA-independent core validates sessions, sequences, Unicode positions,
and plans speech/Braille. The Windows Terminal AppModule owns focus, gestures,
terminal identity, overlays, and native-output suppression. The global plugin
owns only lifecycle, settings, installation, and connection services.

## Terms: marking, claim, binding, and connection

A **session mark** is the explicit user action in the focused Neovim,
normally one physical F12 press. It is distinct from Neovim editor **marks**
such as `ma` or `'a`.

A **claim** is only the transient, machine-readable evidence of that action in
the Neovim instance's private registry entry: `claimSequence` increases
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

Registry schema 3 binds discovery to a random RPC-confirmed `sessionNonce` and,
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
