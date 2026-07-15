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

Network, SSH, DNS, socket reads, reconnects, installation, and substantial
parsing never run on NVDA's main thread. Results return through NVDA's event
queue. Queues and waits are bounded, delayed actions are owned until execution,
and shutdown uses stop events and bounded joins.

The session gate suppresses native terminal output only when activation,
authenticated full state, a Neovim context, focus, and exact binding all hold.
Any failure clears the gate and fails open.
