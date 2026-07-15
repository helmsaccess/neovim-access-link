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
**binding** from the focused Windows Terminal tab's stable `TerminalIdentity`
to a new `ConnectionInstance`. Only a successful TCP or SSH handshake by that
instance creates a **connection** and permits structured output or native
terminal suppression. Manual profile/session selection bypasses marking and
claim resolution, then enters the same typed connection and binding path.

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

## Open Windows Terminal isolation audit

The strict session gate limits native-output suppression, but it does not yet
prove that an unbound Windows Terminal control is completely unaffected by an
enabled add-on. Windows Terminal distinguishes windows, tabs, and panes; the
current `TerminalIdentity` identifies a UI Automation `TermControl` by process,
window handle, and runtime ID. Until this is verified against every supported
Windows Terminal layout, documentation and code should call that object a
terminal control or pane rather than assume that it always represents a tab.

The following paths remain explicitly open for further investigation and
hardening:

- the F12 observer sees gestures in every focused eligible Windows Terminal
  control while support is enabled and may start discovery or show feedback,
  even when that control is not bound;
- an event from another connected Neovim instance can offer an
  activity-confirmed rebind while focus is in an unbound terminal control;
- focusing a remembered identity reactivates suppression immediately from the
  existing authenticated connection before a newly requested `fullState`
  arrives, although the same pane may meanwhile display a shell while the
  remote Neovim RPC channel remains alive; and
- the Braille overlay class is considered for every eligible Windows Terminal
  control and relies on fallback behavior when no bound structured state is
  available.

These paths are not evidence that ordinary shell text is currently lost in
every case, but they mean that complete non-interference has not been
established. Future work must prefer per-control explicit activation, require
fresh structured Neovim evidence before suppression or rebinding, keep F12 and
dialogs inert outside that scope, and prove native speech, Braille, and input
behavior with negative multi-window, multi-tab, and split-pane tests. Terminal
screen text or titles must not be scraped to close this evidence gap; uncertain
state must remain fail-open.
