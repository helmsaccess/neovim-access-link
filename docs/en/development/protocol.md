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

`commandLineChanged.payload.commandLineType` carries Neovim's structured
command-line type, notably `:`, `/`, or `?`; `commandLine` carries its content
without that prefix. Consumers can therefore distinguish Ex commands from
identically named search patterns without inferring intent from text alone.

Byte, character, virtual, and visual columns are distinct. UTF-8, tabs,
combining characters, wide characters, and emoji must not be converted by
assuming one byte or code point equals one display cell.

File-manager state carries only bounded semantic values. Entry names are
limited to 512 UTF-8 bytes, paths and roots to 2048 bytes, and type or adapter
labels to 64 bytes. The plugin validates complete UTF-8 sequences and cuts
only before a code point; an invalid adapter value is discarded instead of
sending a malformed message.

A file-manager entry may carry `selectionState` with only `marked` or
`unmarked`, and `clipboardState` with only `copied`, `cut`, or `none`;
`expanded` remains Boolean. The legacy `marked` field is retained only for
compatibility and must not replace Copy-versus-Cut semantics.
`fileManagerEntryChanged` can originate from structured navigation or from a
public plugin event after the reread state actually changes. Inactive
buffers/windows and equal state produce no event; render bursts are coalesced
within one Neovim scheduler cycle rather than polled.
`fileManager.root` identifies the public manager or branch root;
`fileManager.currentDirectory` identifies the focused level. Both are optional,
UTF-8-validated, and limited to 2048 bytes. A missing value is not inferred
from `entry.path`.

`promptOpened` carries an intentional user-facing prompt bounded to 2048 bytes
and a fixed prompt kind. `promptClosed` distinguishes acceptance and
cancellation for `vim.ui.input/select`. For `vim.fn.confirm`, it carries
`answered=true`, a numeric selection index, and at most one visible selection
label bounded to 512 bytes; no file action is inferred from that label. Prompt
input itself is neither transferred nor retained. A blocking semantic mode
transition may prove closure when Neovim's external UI emits no `msg_clear`.
Oil's `oil_preview` confirmation fallback uses the same prompt contract but
only fixed action verbs, count, and Y/N. The rendered row, names, and paths are
cleared from `promptOpened` state; unknown verbs or a same-named non-float do
not produce a semantic prompt event. When `y` or `n` is typed directly, the
corresponding `promptClosed` carries `accepted=true` or `accepted=false`.
Other close paths omit `accepted` instead of guessing a choice.

`fileManagerActionResult.payload.fileManagerAction` contains only:

```text
manager     UTF-8-validated label, at most 64 bytes
action      add | change | copy | create | delete | move | multiple | rename | restore
result      success | cancelled | failed
count       integer from 1 through 10000
name        optional UTF-8-validated basename, at most 512 bytes
entryType   optional known semantic type
```

The adapter discards complete source/destination paths before sending.
Synchronous results in the same active buffer/window/tab are combined within
one scheduler cycle; an identity or manager change before output drops them.
The event confirms only what a public plugin API reports as completion.
Missing failure/cancellation events are not reconstructed from message text or
rendering.

Capabilities are fixed by v2. Protocol v1, generic TCP listeners, application
tokens, tunnel ports, and capability hello negotiation are intentionally not
supported.

`terminalControl` exposes one fixed control. `leaveTerminalInputRequest`
carries a correlated request ID, exact buffer/window/tab identity, and only
raw mode `t`; its sole operation is Neovim's `stopinsert`. No Lua or Ex text is
accepted. `leaveTerminalInputResult` returns the request ID, success flag, and
a fixed result code. Changed tick is intentionally absent because terminal
jobs update it asynchronously while this mode-only operation neither reads nor
changes text. The actual transition remains event-driven through
`ModeChanged`/`TermLeave`, with no polling.

`clipboardTransfer` exposes only three typed controls. `copyTextRequest` carries
a correlated request ID, expected buffer/window/tab, changed tick and raw mode,
plus exactly one source: `visualSelection` or `yankRegister` (register 0).
`pasteTextRequest` carries the same expected identity and at most 256 KiB of
valid, NUL-free UTF-8 text. No Lua, Ex command, or arbitrary register name is
accepted. `setRegisterRequest` carries the same expected identity and text
limit; its target is fixed to register 0 as the unnamed register's backing
store, and no register name crosses the protocol.

`copyTextResult`, `pasteTextResult`, and `setRegisterResult` return the same
request ID and a fixed result code. Only a copy result may carry one-shot
`clipboardText`. A response
that no longer matches focus, control, instance, or request is discarded. The
text is removed before the local client or bridge updates canonical state, so
it cannot appear in later `fullState` or `focusContext`. Paste invokes only
`nvim_paste(..., true, -1)` and stale or failed actions are never retried
automatically.
Register storage normalizes CRLF, chooses characterwise or linewise type from
the trailing newline, and invokes only fixed `setreg('0', ..., type .. '"')`.
This replaces register 0 and points the unnamed register to it without using a
named user register.

## File-based session-registry claim and explicit binding

These “registry” entries are short-lived JSON files owned by the Neovim
plugin, not Windows Registry data. The implementation reads or writes neither
`HKCU` nor `HKLM`. Windows normally uses
`%LOCALAPPDATA%\nvim-nvda\sessions`; Linux uses
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` or a private per-user `/tmp` fallback.

Schema 3 binds an entry to the actual Neovim RPC endpoint through a random
`sessionNonce`. On Linux, `processStartTicks` must also match `/proc/<pid>/stat`;
`ownsSocket` authorizes cleanup only for the exact plugin endpoint containing
the same PID and nonce; inherited or user-defined sockets are never unlinked.
A live PID or existing path alone is not an identity proof.
The private filename contains PID plus nonce; discovery may remove only that
uniquely owned record after proving it stale.
A scan processes at most 256 JSON session files and each file is limited to 65,536
bytes. Discovery and claim polling are passive and open no RPC channel. Once a
record is selected, its nonce is queried on the same permanent RPC channel
that will carry events, before plugin setup and channel registration. A
mismatch disconnects fail-open without reconnecting the rejected endpoint.

Local and remote session files contain a monotonically increasing
`claimSequence` and the corresponding `claimedMonotonic` timestamp. Neovim
recognizes the configured session-marking key from `vim.on_key`'s unchanged
`typed` value and schedules the session-file write outside the key callback. These
fields are only a transient claim: they are not protocol event sequencing,
authentication, a terminal binding, a connection, or Neovim editor marks, and
they do not survive a plugin restart.

Activation inventories eligible local and SSH sessions and records their
claim sequences as a baseline. After the physical F12 press, exactly one fresh
sequence increase may bind the focused terminal identity and start its typed
TCP or SSH connection. No match produces no guessed connection; multiple
matches require explicit selection. Manual target selection narrows the target
but still requires a fresh physical F12 claim before starting the same typed
connection path.

An authenticated remembered binding may send `requestFocusContext` with an
integer `requestId` from 0 through 2147483647. Local and SSH transports answer
once with `focusContext`, copying the latest canonical event state and adding
the matching `_focusRequestId`. The add-on discards a reply if request ID,
instance, exact terminal binding, authentication, or current focus no longer
matches. This focus-event-driven exchange performs no polling and no terminal
screen scraping.
