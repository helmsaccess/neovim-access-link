# Protocol v2

Linux uses a fixed ASCII start marker followed by length-prefixed MessagePack
frames on SSH stdout; control frames use stdin. Output before the marker is
discarded as shell startup noise. Local Windows uses Neovim MessagePack RPC
directly and shares the same validated semantic event model.

Every event carries protocol/schema identity, session ID, monotonic sequence,
type, mode, buffer/window identity, changed tick, cursor positions, and only
the bounded semantic payload needed for the event. `fullState` establishes or
repairs state. Sequence gaps, session changes, invalid sizes/types, or stale
ticks trigger rejection and resync rather than speech.

Byte, character, virtual, and visual columns are distinct. UTF-8, tabs,
combining characters, wide characters, and emoji must not be converted by
assuming one byte or code point equals one display cell.

Capabilities are fixed by v2. Protocol v1, generic TCP listeners, application
tokens, tunnel ports, and capability hello negotiation are intentionally not
supported.

## Registry claim and explicit binding

Local and remote registry entries contain a monotonically increasing
`claimSequence` and the corresponding `claimedMonotonic` timestamp. Neovim
recognizes the configured session-marking key from `vim.on_key`'s unchanged
`typed` value and schedules the registry write outside the key callback. These
fields are only a transient claim: they are not protocol event sequencing,
authentication, a terminal binding, a connection, or Neovim editor marks, and
they do not survive a plugin restart.

Activation inventories eligible local and SSH sessions and records their
claim sequences as a baseline. After the physical F12 press, exactly one fresh
sequence increase may bind the focused terminal identity and start its typed
TCP or SSH connection. No match produces no guessed connection; multiple
matches require explicit selection. Manual profile/session selection bypasses
the claim but starts the same connection path.
