# Protocol v2

Protocol v2 is the only supported semantic interface between Neovim and the
NVDA add-on. It is a bounded application protocol, not a transparent Neovim
RPC tunnel. Read `architecture.md` first for the process and lifecycle model.

## Transports

### SSH stdio

For Linux, the add-on starts one Windows OpenSSH process per connection. Its
remote command starts `~/.local/bin/nvim-nvda-bridge`; application frames use
SSH stdin and stdout only. Before the first frame the bridge writes exactly:

```text
NVIM-NVDA-STDIO/2
```

The client discards at most 64 KiB of shell startup output before this marker.
After it, stdout is reserved for protocol frames and diagnostics use stderr.
There is no TCP listener, port forwarding, application token, or `hello`
negotiation.

### Local Windows RPC

For local Windows Neovim, `LocalTcpClient` connects directly to Neovim's
dynamic MessagePack-RPC port on exactly `127.0.0.1`. The SSH marker and stdio
length framing do not exist on this segment. Notifications are still converted
to the same protocol-v2 envelope and validated with the same event types and
1 MiB limit before NVDA receives them. Users cannot configure a host or port.

## Framing and envelope

An SSH message is a four-byte unsigned big-endian length followed by one
MessagePack object. A frame is at most 1 MiB.

Every framed protocol message has:

```text
protocolVersion      exactly 2
sessionId            non-empty transport-session identifier
sequence             monotonic integer starting at 0
timestampMonotonic   non-negative monotonic timestamp
type                  non-empty event or control type
payload               map
```

Wrong versions, missing fields, invalid types, malformed MessagePack, and
oversized frames terminate the affected transport instance. Unknown optional
payload fields may be ignored. State fields such as mode, buffer, cursor, and
changed tick belong to semantic event payloads; they are not present on every
transport message such as a heartbeat.

## Session start, ordering, and resync

The first accepted message in each transport session is `fullState` with
sequence 0. Earlier or foreign session identities are not adopted.

- Duplicate or decreasing sequences are discarded.
- A sequence gap enters “resync required”.
- The client sends `requestFullState`.
- Only a new valid `fullState` leaves that state.
- An SSH reconnect creates a new `sessionId` and restarts at sequence 0.

The bridge normally sends one `heartbeat` per second. OpenSSH also uses
`ServerAliveInterval=5` and `ServerAliveCountMax=2`; the client reconnects with
bounded exponential backoff. The local client has no separate heartbeat: a
closed RPC socket produces `disconnected`, followed by bounded reconnect.

For both transports, the first valid `fullState` is the add-on's accessibility
authentication point.

## Fixed capabilities

There is no open-ended capability-negotiation handshake.
`fullState.payload._transport` describes the v2 transport that actually
started. SSH stdio has these fixed base capabilities:

```text
heartbeat, resync, semanticEvents, cursorRouting, accessibleMenus,
focusContext, clipboardTransfer, terminalControl
```

Local `windows-loopback-tcp` supports the same list without `heartbeat`.
The transport adds `exploration` only when the connected Neovim plugin reports
it in the fixed `pluginCapabilities` field. This prevents an updated add-on
from capturing exploration gestures while an older plugin is still installed
or running.
Protocol v1, generic listeners, tokens, tunnel ports, and compatibility mode
are not supported.

## File-based session registry and explicit assignment

The “registry” consists of short-lived JSON files owned by the Neovim plugin,
not Windows Registry data. The implementation reads or writes neither `HKCU`
nor `HKLM`. Windows normally uses
`%LOCALAPPDATA%\nvim-nvda\sessions`; Linux uses
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` or a private per-user `/tmp` fallback.

Schema 3 binds a record to the actual Neovim RPC endpoint with a random
`sessionNonce`. On Linux, `processStartTicks` must also match
`/proc/<pid>/stat`. `ownsSocket` authorizes cleanup only for the exact plugin
endpoint containing the same PID and nonce; inherited or user-defined sockets
are never unlinked. A live PID or an existing path alone is not identity
proof.

A scan considers at most 256 JSON files, each at most 65,536 bytes. Discovery
and claim reads are passive and open no RPC channel. After unique selection,
the nonce is queried on the same persistent RPC channel that will carry
events, before plugin setup and channel registration. Mismatch disconnects
fail-open and does not reconnect to the rejected endpoint.

Each record contains a monotonic `claimSequence` and its
`claimedMonotonic` timestamp. Neovim recognizes the configured marking key
from `vim.on_key`'s unchanged `typed` value and schedules the file update
outside the key callback. These fields are only a transient claim; they are not
event sequencing, authentication, terminal binding, a connection, or Neovim
editor marks.

Activation inventories eligible local and SSH sessions and stores their claim
sequences as a baseline. After physical F12, exactly one fresh increase may
bind the focused terminal identity and start its typed local or SSH connection.
No match produces no guessed connection; multiple matches require explicit
selection. Manual target selection narrows the target but still requires a
fresh physical F12 claim.

## Event direction

Neovim pushes semantic events. The bridge keeps only the latest confirmed
canonical state and does not queue events for later replay while no stdio
client exists.

Important types include `fullState`, `modeChanged`, `characterMoved`,
`wordMoved`, `lineChanged`, `selectionChanged`, `textChanged`, `textDeleted`,
`textReplaced`, `searchMatchChanged`, `menuOpened`,
`menuSelectionChanged`, `menuClosed`, `signatureChanged`,
`diagnosticChanged`, `foldChanged`, `commandLineChanged`, `messageReceived`,
`errorReceived`, `fileManagerEntryChanged`, `fileManagerActionResult`,
`leaveTerminalInputResult`, `exploreTextResult`, and `connectionStateChanged`.

Canonical `terminalNormal` represents raw Neovim mode `nt` and remains
distinct from Normal mode in a file buffer.
`commandLineChanged.payload.commandLineType` carries structured `:`, `/`, or
`?`, while `commandLine` excludes that prefix. Ex commands are therefore not
guessed from text. `messageReceived.payload.commandLineReturn=true` marks only
the immediate proven output of the non-empty Ex command that just ended; a
later asynchronous message does not inherit it.

`focusContext` is a correlated snapshot of the canonical state.
`_focusRequestId` links it to the triggering focus request; it is not a
free-running editor stream.

Buffer text is not transferred wholesale. See `accessibility.md` for the
semantic feature matrix.

### File-manager payloads

File-manager state carries bounded semantic values. Entry names are at most
512 UTF-8 bytes, paths and roots at most 2048 bytes, and type or adapter labels
at most 64 bytes. Truncation occurs only before a complete code point; invalid
optional adapter text is discarded.

An entry may carry `selectionState` as `marked` or `unmarked`,
`clipboardState` as `copied`, `cut`, or `none`, and Boolean `expanded`.
`fileManagerMotion` is restricted to fixed motions such as `lineStart`,
`lineEnd`, `fileStart`, `fileEnd`, or `lineChanged`. It preserves navigation
cues without making a decorated manager row the speech source.

`fileManagerActionResult.payload.fileManagerAction` is restricted to:

```text
manager     UTF-8 label, at most 64 bytes
action      add | change | copy | create | delete | move | multiple | rename | restore
result      success | cancelled | failed
count       integer from 1 through 10000
name        optional basename, at most 512 UTF-8 bytes
entryType   optional known semantic type
```

Complete source and destination paths are removed before sending. Synchronous
results in the same active buffer/window/tab may be combined within one
scheduler cycle. A changed identity or manager drops the output. Missing
failure or cancellation events are not reconstructed from rendering or text.

`promptOpened` carries a deliberate user-facing prompt at most 2048 bytes and
a fixed prompt kind. `promptClosed` distinguishes acceptance and cancellation
where Neovim proves it. Oil's narrow `oil_preview` fallback uses only fixed
action verbs, count, and Y/N; rendered names and paths are cleared.

## Control direction

Only these add-on-to-Neovim controls are permitted:

- `requestFullState` with no content payload;
- `requestFocusContext` with an integer `requestId` from 0 through
  2,147,483,647;
- `routeCursor` with buffer, window, line, UTF-8 byte column, and changed tick;
- `copyTextRequest` with correlated request ID, expected buffer/window/tab,
  changed tick and raw mode, plus exactly `visualSelection` or `yankRegister`;
- `pasteTextRequest` with the same expected identity and at most 256 KiB of
  valid NUL-free UTF-8 text;
- `setRegisterRequest` with the same identity and text limit, fixed to register
  0 as backing storage for the unnamed register;
- `leaveTerminalInputRequest` with correlated request ID, exact
  buffer/window/tab identity, and raw mode `t`, fixed to `stopinsert`.
- `exploreTextRequest` with positive request, exploration, and action indices;
  one of six fixed movements; a repeat count from 1 through 64; and exact
  buffer/window/tab, changed-tick, raw-mode, and real-cursor identity;
- `endExplorationRequest` with request and exploration IDs to discard
  ephemeral Lua state.

`requestFocusContext` is sent only to an authenticated instance bound exactly
to the focused terminal control. A mismatched request ID, instance, binding, or
focus discards its response.

`routeCursor` validates current buffer, window, changed tick, line, UTF-8 byte
column, and character boundary before calling Neovim's cursor API.

Clipboard results return the same request ID and a fixed result code. Only
`copyTextResult` may contain one-shot `clipboardText`; it is removed before
updating canonical state. Paste invokes only `nvim_paste(..., true, -1)`.
Register storage normalizes CRLF, derives characterwise or linewise type from
the trailing newline, and invokes only fixed register 0. Stale or failed
actions are not retried.

`leaveTerminalInputResult` returns the request ID, success flag, and fixed
code. Changed tick is intentionally absent because a terminal job changes it
asynchronously while `stopinsert` neither reads nor changes text. The actual
mode transition remains event-driven through `ModeChanged` or `TermLeave`.

`exploreTextResult` correlates request, exploration, action index, and fixed
action. A successful result contains exactly a character, word, or line unit,
a bounded virtual position, and at most 16 KiB of text. One word scan reads at
most 256 lines or 64 KiB. The Lua engine uses no cursor, feedkeys, Normal,
search, or buffer-mutation operation. The receiver rejects a result after any
focus, binding, context, or identifier change.

No received text is ever executed as Lua or Ex code.

## Security boundary

For Linux, SSH provides host/account authentication, confidentiality, and
integrity. The bridge prevents Neovim's powerful general MessagePack-RPC API
from reaching Windows. Locally, that API remains restricted to IPv4 loopback
inside the signed-in Windows user context and is not exposed as a configurable
remote endpoint. See `security.md` for the complete trust model.
