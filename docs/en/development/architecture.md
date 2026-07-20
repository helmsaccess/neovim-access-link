# Architecture

This chapter starts with the overall model and then follows a connection from
startup to output. Special cases deliberately come last. New contributors
should read this chapter before the protocol reference and the individual
ADRs.

## Goals and design principles

Neovim Access Link does not make the visible terminal surface accessible.
Instead, the Neovim plugin describes editor state through semantic events:
mode, cursor, current line, menu selection, message, or file-manager entry.
The NVDA add-on turns that data into speech, sounds, and Braille.

Five rules follow from this approach:

1. Neovim is the source of editor semantics. Screen scraping is only a narrow
   fallback when no reliable API or event source exists.
2. Transport, protocol validation, canonical state, presentation, and focus
   remain separate layers.
3. Network, SSH, reconnect, parsing, and installation work never blocks NVDA's
   main thread.
4. Output or suppression applies only to the assigned Neovim session and the
   bound Windows Terminal control.
5. Errors restore NVDA's normal terminal path: the system fails open rather
   than silent.

The integration decision is explained in
`adr/0001-neovim-integration-point.md`.

## Runtime model: three processes

At most three processes participate at runtime:

| Process | Location | Responsibility |
|---|---|---|
| Neovim with the Lua plugin | locally on Windows or remotely on Linux | Produces semantic state and registers the session. |
| Python bridge | only on Linux for a remote SSH connection | Connects the private Neovim RPC socket to a bounded protocol over SSH stdin/stdout. |
| NVDA with the add-on | Windows | Manages connections and focus, validates events, and plans speech, sounds, and Braille. |

`protocol/python/` and `nvda-addon/core/` are not additional processes. They
are library layers imported by the bridge or add-on. See
`repository-layout.md` for source directories and entry points.

## Two data paths

### Local Neovim on Windows

```text
Neovim + Lua plugin
  │ semantic nvim_nvda_event RPC notifications
  │ dynamic listener restricted to 127.0.0.1
  ▼
local protocol client inside the NVDA add-on
  │ validated protocol-v2 messages
  ▼
canonical state → speech/sound/Braille planning
```

The plugin starts the listener with the fixed address `127.0.0.1:0` and lets
Neovim select a free port. The client maps RPC notifications to the same
bounded message contract used over SSH, without a bridge process or stdio
framing.

### Remote Neovim on Linux

```text
Neovim + Lua plugin
  │ private Unix RPC socket
  ▼
Python bridge
  │ protocol v2 framed over SSH stdin/stdout
  ▼
SSH client inside the NVDA add-on
  │ validated messages
  ▼
canonical state → speech/sound/Braille planning
```

The add-on starts Windows OpenSSH with `-T`. The bridge connects to the private
Unix socket of the selected Neovim session. It does not expose Neovim's general
RPC interface; it exposes only the events and controls documented in
`protocol.md`. There is no tunnel port, general TCP listener, or runtime
download.

## Core terms

These terms describe different stages and must not be treated as synonyms:

| Term | Meaning |
|---|---|
| Session | One running Neovim instance with the plugin loaded and its own registry record. |
| Session registry | Private directory containing JSON session files. It is explicitly not the Windows Registry. |
| Connection profile | Saved details for an SSH destination; local Windows is a separate fixed target type. |
| Session mark | Explicit physical key press in focused Neovim, F12 by default. |
| Claim | Monotonic counter and timestamp in the session record that proves the mark to software. |
| Assignment or binding | In-memory association of one concrete Windows Terminal identity with a connection instance. |
| Connection | Persistent local RPC or SSH-stdio transport to exactly one Neovim session. |

The file-based session registry registers Neovim sessions, not Windows
Terminal windows, tabs, or panes. On Windows it normally lives under
`%LOCALAPPDATA%\nvim-nvda\sessions`; on Linux it uses
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` or a private per-user fallback under
`/tmp`. It does not use `HKCU` or `HKLM` keys.

A `TerminalIdentity` identifies the concrete terminal control discovered
through UI Automation. In Windows Terminal that control may be the content of
a tab or of one pane. A window handle alone would not be precise enough.

## Connection lifecycle

### 1. The plugin registers the Neovim session

At startup, `plugin/nvim_nvda.lua` loads the Lua module. `session.lua`
atomically creates a schema-3 JSON record containing the session identifier,
nonce, process details, RPC endpoint, and claim counter. On Linux, the current
user owns the socket and record. On Windows, the RPC endpoint is fixed to IPv4
loopback.

The record is discovery metadata, not a trust decision. A stale or foreign
record alone must never enable output or bind a terminal.

### 2. Activation only builds an inventory

On manual activation, the add-on reads local session files and scans configured
SSH destinations in the background. It stores existing claim counters as a
baseline. This inventory neither creates a persistent connection nor assigns a
terminal automatically.

Password profiles that cannot be scanned automatically remain available
through manual target selection. The physical session mark is still required.

### 3. F12 associates the focused terminal with a session

The F12 mechanism combines two independent observations:

1. After the claim gesture matches, the Windows Terminal AppModule queries
   NVDA's current focus object at the public `decide_executeGesture` boundary.
   Only that concrete registered AppModule instance may authorize the complete
   `TermControl` identity against the gate. The physical key continues
   unchanged to the application.
2. The Neovim plugin observes the unchanged key through `vim.on_key`. Outside
   the input callback it atomically increments `claimSequence` and updates the
   monotonic timestamp in its session file. Only in Insert mode, an otherwise
   unbound F12 is consumed after that observation so `<F12>` cannot enter the
   buffer; Neovim 0.10 requires a narrow Insert-mode mapping for this.
3. The add-on reads the candidates again. Only one fresh claim relative to the
   baseline may trigger assignment. No match has no effect; multiple matches
   require a choice.

The claim does not open a transport or authenticate a session. It proves only
which Neovim instance observed the key. The actual assignment exists only in
the add-on's memory and can be separate for multiple tabs, panes, and windows.

### 4. The persistent transport is authenticated

After assignment, exactly one `ConnectionInstance` starts a local RPC or
SSH-stdio transport. The session-record nonce is verified on the persistent
Neovim RPC channel before the plugin registers that channel and sends semantic
events. Discovery does not open short-lived editor RPC connections.

The first valid `fullState` is the authentication point on the add-on side.
Only then may the instance take over structured output. SSH additionally
provides host and user authentication, a fixed protocol-v2 marker, sequence
validation, and heartbeats.

### 5. Events become output

The plugin publishes small typed events. The protocol client and bridge bound
and validate them before updating a canonical state cache. `SpeechPlanner` and
the persistent Braille plan consume that state without making network or
Neovim calls.

Receiver threads never call NVDA directly. They queue completed results onto
NVDA's event queue with `queueHandler`; speech, sounds, Braille, and UI are
updated there.

### 6. Focus changes request confirmed context

When focus moves between Windows Terminal controls,
`ConnectionInstanceManager` checks the exact `TerminalIdentity`. A remembered
binding does not immediately allow suppression. The gate first closes and the
bound, already authenticated instance receives a `requestFocusContext`
request.

Only a reply with the matching request ID, instance, binding, and still-current
focus reopens the gate. Another tab, pane, or shell control in the same window
therefore cannot inherit state from an earlier Neovim session accidentally.

### 7. Disconnect and deactivation fail open

Protocol errors, sequence gaps, invalid state, transport loss, focus loss, or
manual deactivation remove authentication from the affected instance. The gate
restores native terminal output. Reconnects use bounded background backoff and
must not close output again before state is confirmed.

## Layer responsibilities

| Layer | Owns | Explicitly does not own |
|---|---|---|
| Neovim plugin | Editor semantics, buffer/window/tab identity, UTF-8 byte columns, menus, messages, file-manager state | Windows focus, speech, SSH lifecycle |
| Bridge | Unix RPC connection, stdio framing, bounded forwarding | Arbitrary RPC or command execution, presentation |
| Protocol client | Size, type, session, sequence, heartbeat, and resync validation | Speech or terminal-focus decisions |
| `ConnectionInstanceManager` | Instances and binding a `TerminalIdentity` to an instance | Guessing bindings from titles or terminal text |
| `ConnectionCoordinator` | Instance manager, active client, gate, authentication, bindings, correlated requests, and mapping and lifetime of isolated runtime states | Domain mutation of editor state, NVDA events, `nextHandler`, dialogs, or concrete NVDA output |
| `ServiceRegistrar` | Identity-checked publication of the fully initialized `TerminalIntegrationService` | Lifecycle decisions or terminal events |
| `TerminalIntegrationService` | Narrow public contract for focus, fixed terminal commands, F12 claims, and structured Braille interaction | Application events, `nextHandler`, dynamic method names, or access to private runtime state |
| `TerminalFocusService` | Concrete terminal identity, focus generation, AppModule/adapter correlation, focus completion, and conservative disposal of closed controls | A Global Plugin instance, network I/O, application events, or `nextHandler` |
| `SessionClaimService` | One-shot F12 authorization, claim generations, and claim inventory state | A Global Plugin instance, NVDA dialogs, synchronous discovery, or connection runtime copies |
| `EditorSessionController` | Domain mutation of the active isolated per-instance editor state, runtime switching, mode/menu/transport state, connection transitions, neutral typing actions, and bounded clipboard/terminal-control requests with reply correlation | Concrete NVDA output, focus binding, the Windows clipboard, network I/O, or instance lifetime |
| `SettingsService` | Loading, normalization, persistence, and profile switching for add-on settings plus immutable change reports | Dialog state, terminal events, focus, or connections |
| `SessionGate` | Whether native terminal output may be suppressed | Editor semantics and transport |
| Speech/Braille planning | Localized and prioritized presentation | Network, Neovim RPC, and focus binding |
| `NvdaPresentation` | NVDA-specific delivery of planned speech, Braille messages, tones, and add-on sounds | Speech planning, transport, focus binding, or dialogs |
| Global Plugin | NVDA-process lifetime plus shared-service composition and teardown | Application events, configurable terminal commands, `nextHandler`, overlay selection, or implementation of Settings, Tools, and presentation delivery |
| `NvdaUiManager` | One-time symmetrical settings and Tools registration, connection forms, component installation and removal | A Global Plugin instance, terminal events, focus binding, and suppression |
| Windows Terminal AppModule | UIA events, overlay selection, concrete terminal focus, configurable terminal commands, every invocation of `nextHandler`, and native-output delegation or suppression | General target selection or transport |

These boundaries are intentionally redundant. A valid message is not enough;
the instance, focus, and gate must also match.

The AppModule and Braille overlay receive only the
`TerminalIntegrationService`; the concrete Global Plugin remains hidden behind
that contract. Terminal commands use a fixed enum instead of freely resolved
method names, while focus decisions and F12 authorizations are immutable
values. If the service is absent, has been replaced during add-on reload, or
violates the contract, the AppModule passes the original gesture or native
NVDA event through fail-open.

`TerminalIntegrationService` delegates focus operations directly to
`TerminalFocusService`. Identity construction, UIA lifetime validation, the
main-thread scheduler, and a few domain callbacks are injected explicitly. A
closed, unfocused control is removed only after two conclusive negative checks;
an uncertain UIA failure is not treated as closure.

`TerminalIntegrationService` also authorizes and cancels physical F12 claims
directly through `SessionClaimService`. That service owns the mutable claim and
inventory state, local/SSH inventory workers, and candidate evaluation.
It also owns discovery, selection, reuse, connection start, disconnect, and
remembered bindings. The Global Plugin only joins its immutable results to
NVDA's main-thread, dialog, message, and transport boundaries; it keeps no
writable copy of claim state. Focus loss caused by the optional modal remember
question is bridged by exactly one terminal- and instance-correlated
reactivation; a different terminal focus discards it.

The V2-5 `EditorSessionController` uses the active runtime managed by
`ConnectionCoordinator` but is solely responsible for its domain mutation. It
owns state and mode transitions, transport capabilities, menu documentation,
connection state, and isolated per-instance typing echo. Its ordered neutral
typing actions become speech only at the NVDA boundary. Protocol-envelope
validation and network callbacks remain separate. The controller also
allocates bounded request IDs for clipboard,
register, and terminal control, binds them to an instance and
`TerminalIdentity`, and rejects foreign or late replies. One-shot clipboard
text is exposed only as a validated result to the NVDA boundary and is removed
from the safe follow-up event. Focus/gate validation, transport calls, the
Windows clipboard, diagnostics, and concrete presentation remain separate.

The settings panel, presentation adapter, and profile-switch path use snapshots
or domain operations supplied by `SettingsService`; no dialog mutates a freely
accessible plugin dictionary. `NvdaUiManager` receives only that service, a
diagnostic recorder, and the small password and component-operation callbacks
it needs. Its Tools entries and Settings category nevertheless remain registered
exactly once for the Global Plugin's process lifetime.

## The fail-open gate

`SessionGate.suppression_active` is true only when all of these conditions hold:

- the feature is manually enabled;
- the instance is authenticated;
- Neovim is active;
- terminal passthrough is not active for direct terminal input;
- a supported terminal control is focused;
- and its full identity exactly equals the bound identity.

If any condition is missing, NVDA handles the terminal normally. The add-on is
therefore not enabled wholesale for a Windows Terminal window or all its tabs.

## State, ordering, and columns

Every event belongs to one session and carries a monotonic sequence number.
Gaps trigger resynchronization; `fullState` restores a complete validated
starting point. State from different connection instances is not mixed.

Cursor positions distinguish:

- line;
- UTF-8 byte column for Neovim APIs and the protocol;
- Unicode character position for human-facing output;
- virtual column for tabs and display alignment;
- visual column or selection boundaries where the mode requires them.

A number must never cross these layers without its column type. See
`protocol.md` for field definitions and limits.

## Reverse direction: a small allowlisted control channel

The reverse channel is a fixed allowlist, not general remote control:

- `requestFullState` and `requestFocusContext` request state;
- `routeCursor` sets a validated cursor after a Braille routing action;
- `copyTextRequest`, `pasteTextRequest`, and `setRegisterRequest` mediate
  explicit clipboard actions;
- `leaveTerminalInputRequest` performs only Neovim's fixed `stopinsert`.

State-changing requests carry the expected session, buffer, window, tab, mode,
and, where needed, `changedtick` identity. Text is never executed as Lua or Ex
code. See `protocol.md` for complete payloads and `security.md` for trust
assumptions.

## Events, polling, and fallbacks

Normal editor, focus, transport, and file-manager paths are event-driven.
Polling is permitted only as a bounded last resort where no reliable event
structure exists. Current code has two such exceptions:

1. After an explicit local F12 mark, a worker reads session files every 50 ms
   for at most 1.5 seconds because the atomic file update has no reliable event
   path into NVDA. The loop is user-triggered, bounded, and opens no RPC
   connection.
2. The `nvim-cmp` and `blink.cmp` adapters query their public selection API at
   35 ms intervals, but only while the plugin has reported its menu open. The
   plugins currently expose no reliable event for every selection change.
   Closing the menu stops the timer.

The five-minute terminal lifecycle sweep is different. It is slow maintenance
for closed Windows Terminal controls, not a source of editor state or focus
actions. Two negative liveness observations are required before detaching a
binding, and errors open the gate.

File managers use plugin events. Only Oil's confirmation float needs the
narrow parser documented in `adr/0003-oil-confirmation-fallback.md`. Buffer and
window events trigger it; it polls neither the screen nor the filesystem.

## Specialized subsystems

### Command line, terminal, and messages

Neovim provides command-line type and content as structured data. A
`CmdlineLeave` correlation associates only the immediately proven message from
an Ex command with the already-reached return mode. Time intervals are not
treated as semantics. Terminal insert, `terminalNormal`, and normal file-buffer
mode remain distinct states; passthrough opens the gate during direct terminal
input.

### Clipboard

The Windows clipboard remains owned by NVDA. User-assignable NVDA commands
explicitly transfer a Visual selection or register 0 to Windows, Windows text
through `nvim_paste`, or Windows text into fixed register 0. A request ID and
expected editor/focus state prevent late replies from affecting another
session. There is no automatic synchronization or retry.

### File managers

`file_manager.lua` normalizes the active entry. Separate adapters subscribe to
public events from Oil, netrw, mini.files, nvim-tree, and Neo-tree where
available. They transport typed names, kinds, states, and action results rather
than decorated screen lines. Missing plugin APIs fall back to existing
navigation. See `accessibility.md` and `current-status.md` for the feature
matrix and practical test status.

### Localization and packaging

Only the NVDA side localizes user-facing text. The bridge, protocol, and plugin
carry typed values and document content without knowing the active language.
The build compiles PO files into NVDA's gettext domain and also embeds bridge,
protocol, plugin, and installer as a rootless Linux user package. Remote
installation uses that embedded package and performs no runtime download.

## Rules for extensions

Design new features in this order:

1. find reliable public Neovim or plugin events;
2. produce a small typed state in the plugin;
3. define and test protocol bounds and correlation;
4. keep transport as transparent bounded forwarding;
5. model output in the NVDA-independent planner;
6. validate focus and fail-open conditions in the add-on;
7. add a narrow fallback or bounded polling only for a proven event gap, with
   its replacement path documented.

Private APIs require an ADR before release. Raw-text heuristics, general RPC
forwarding, and automatic assignment from window titles are not acceptable
shortcuts.

## Related chapters

- `protocol.md`: messages, fields, limits, sequences, and controls
- `security.md`: trust boundaries and threat model
- `latency.md`: threading, budgets, and measurement
- `accessibility.md`: feature matrix and fallbacks
- `testing.md`: automated and practical evidence
- `adr/`: recorded architecture decisions
