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
