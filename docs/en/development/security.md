# Security and privacy

## Transport and credentials

Remote connections use Windows OpenSSH standard input and output. SSH
authenticates host and user, and normal host-key checking remains active.
`ClearAllForwardings=yes` prevents inherited forwards. Keys and `ssh-agent`
are the recommended path.

Optional passwords are requested accessibly, kept only in memory, and exposed
only to the short-lived SSH process through Askpass. They never appear in
arguments, files, or logs and are discarded on deactivation or exit.

Local RPC connects only to a dynamic plugin-registered endpoint on
`127.0.0.1`. Users cannot configure another address.

## Session files and installation

The file-based session registry is in a private user directory. Records are
validated on Linux by directory and file owner, process start, PID, nonce, and
socket. On Windows, the add-on validates the schema, nonce-bound filename,
live PID, and IPv4-loopback-only endpoint. The records are not Windows
Registry keys.

Cleanup never terminates a process. A socket is removed only when the record
explicitly identifies it as plugin-owned and path, PID, and nonce agree.
Inherited or user-defined paths remain untouched. Timeout, SSH failure, focus
loss, or uncertain access falls back non-destructively.

Installation and removal use only fixed user paths and time-bounded commands.
Closing a Windows Terminal tab stops only its NVDA client, never Neovim or
tmux.

## Protocol and control messages

Protocol messages are size-bounded, schema-validated, and bound to session and
sequence. Incoming data is not executed and grants no general Neovim RPC
access.

The reverse direction has a fixed allowlist for state requests, cursor
routing, bounded Braille actions, read-only exploration, explicit clipboard
commands, Terminal-Normal mode, and contextual numbered choices. Every
state-changing command revalidates the applicable session, control, instance,
buffer, window, tab, changed tick, mode, cursor, and request ID.

- Routing and Braille actions contain fixed identifiers, not Lua, Ex, or key
  text. Write actions check modifiability and read-only state.
- Exploration moves only a bounded virtual position. It changes neither cursor
  nor buffer and is discarded on focus or context change.
- Spelling selection sends only the internally validated numeric index to a
  still-identical active prompt. Suggestion text is not executed or returned.
- Clipboard access starts only from assignable NVDA commands. Sources,
  registers, and target operations are fixed; paste is NUL-free and limited to
  256 KiB of UTF-8.

See [protocol](protocol.md) for complete payloads and bounds.

## Focus and suppression

A terminal path is suppressed only for an authenticated, active, focused,
exactly bound Neovim session. Error, timeout, disconnect, reload,
deactivation, or identity mismatch immediately fails open to NVDA's native
terminal handling.

One physical F12 press authorizes exactly one assignment attempt for the
currently focused `TerminalIdentity`. Focus object, registered AppModule
instance, complete control identity, and gate are checked before starting and
again on NVDA's main thread. Focus change or activity from another Neovim
instance cannot move a binding.

Configurable commands belong to the Windows Terminal AppModule. Even if
NVDA's user gesture map displays a saved assignment outside the application,
dispatch requires the same concrete AppModule and control identity. Focus
generations and adapter tokens reject late replies.

## Diagnostics and confidential text

Diagnostic reports redact text content, tokens, clipboard data, and other
potentially confidential payloads. Logs are diagnostic only and are not
required for correctness. Protocol errors record type and bound rather than
complete user text.

Agent-created reproductions, downloads, and reports live outside the
repository under `/nfs/src/nal-tmp/` and are never versioned. Project tools'
runtime or test output uses only its documented ignored paths.

## Remaining boundary

A confirmed RPC session alone does not prove that Neovim remains visible
inside an already bound `TermControl` if a shell or tmux client replaces it in
the foreground. This grants no authority to uncertain or unbound controls; a
solution must not depend on general terminal screen scraping. Compatibility
treats this as unapproved breadth.
