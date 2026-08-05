# Architecture

This chapter expands the [overview for new developers](overview.md). It assumes
that basic model and follows the same order: participating processes and data
paths, terminology and connection lifecycle, responsibilities inside the
add-on, and specialized subsystems. New contributors should therefore begin
with the overview and then read this chapter before the protocol reference and
individual ADRs.

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

The semantic plugin-event decision is explained in
[ADR-0001](adr/0001-neovim-integration-point.md). The current local and remote
transport paths are defined by
[ADR-0006](adr/0006-local-tcp-and-ssh-stdio-transports.md).

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

Receiver threads never call NVDA directly. They queue validated events onto
NVDA's event queue with `queueHandler`; editor state and output plans are
updated there before speech, sounds, Braille, and UI are invoked.

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
| Neovim plugin | Editor semantics, buffer/window/tab identity, UTF-8 byte columns, menus, messages, file-manager state, and ephemeral read-only exploration position | Windows focus, speech, SSH lifecycle, or moving the real cursor for exploration |
| Bridge | Unix RPC connection, stdio framing, bounded forwarding | Arbitrary RPC or command execution, presentation |
| Protocol client | Size, type, session, sequence, heartbeat, and resync validation | Speech or terminal-focus decisions |
| `ConnectionInstanceManager` | Instances and binding a `TerminalIdentity` to an instance | Guessing bindings from titles or terminal text |
| `ConnectionCoordinator` | Instance manager, active client, gate, authentication, bindings, correlated requests, and mapping and lifetime of isolated runtime states | Domain mutation of editor state, NVDA events, `nextHandler`, dialogs, or concrete NVDA output |
| `service_registry.py` / `ServiceRegistrar` | Identity-checked process-wide publication of the fully initialized `TerminalIntegrationService` | A Global Plugin object, lifecycle decisions, or terminal events |
| `AddonRuntime` | Late service publication and the fixed, idempotent teardown order for composed process-wide services | Application events, editor planning, focus decisions, dialogs, or arbitrary service lookup |
| `TerminalIntegrationService` | Shared, explicitly bounded integration contract for focus, fixed terminal commands, F12 claims, speech exploration mode, developer contexts, and structured Braille interaction | A Global Plugin object, application events, `nextHandler`, dynamic method names, or access to private runtime state |
| `TerminalFocusService` | Concrete terminal identity, focus generation, AppModule/adapter correlation, focus completion, and conservative disposal of closed controls | A Global Plugin instance, network I/O, application events, or `nextHandler` |
| `SessionClaimService` | One-shot F12 authorization, claim generations, and claim inventory state | A Global Plugin instance, NVDA dialogs, synchronous discovery, or connection runtime copies |
| `EditorSessionController` | Domain mutation and reset of the active isolated per-instance editor state, runtime switching, mode/menu/transport/passthrough state, completion-documentation access, connection-label normalization, neutral typing actions, and validated outbound clipboard, terminal, and exploration plans with reply correlation | Concrete NVDA output, focus binding or authentication, the Windows clipboard, network I/O, or instance lifetime |
| `ControlDispatcher` | Bounded asynchronous sending of prepared control payloads | NVDA events, focus decisions, payload construction, or an unbounded queue |
| `SettingsService` | Loading, normalization, persistence, and profile switching for add-on settings plus immutable change reports | Dialog state, terminal events, focus, or connections |
| `SessionGate` | Whether native terminal output may be suppressed | Editor semantics and transport |
| Speech/Braille planning | Localized and prioritized presentation | Network, Neovim RPC, and focus binding |
| `NvdaPresentation` | NVDA-specific delivery of planned speech, Braille messages, tones, and add-on sounds | Speech planning, transport, focus binding, or dialogs |
| `nvda_braille.py` | NVDA Braille region, terminal overlay, Braille-position translation, and lookup of the published terminal service | A Global Plugin object, connection ownership, or focus decisions |
| Global Plugin | NVDA-process lifetime, composition and publication of shared services, and the current coordination of process-wide NVDA-edge workflows for connections, claims, clipboard, network events, dialogs, and presentation transitions | Application events, configurable terminal commands, `nextHandler`, overlay selection, configurable script metadata, or a second copy of domain runtime state |
| `NvdaUiManager` | One-time symmetrical settings and Tools registration, connection forms, component installation and removal | A Global Plugin instance, terminal events, focus binding, and suppression |
| Windows Terminal AppModule | UIA events, overlay selection, concrete terminal focus, configurable speech-exploration-mode gestures and their physical-key lifecycle, every invocation of `nextHandler`, and native-output delegation or suppression | General target selection, separate gesture resolution, or transport |

These boundaries are intentionally redundant. A valid message is not enough;
the instance, focus, and gate must also match.

The application boundary is therefore cleanly implemented: terminal events,
overlay selection, `nextHandler`, configurable NVDA scripts, and input
observers live in the Windows Terminal AppModule. The Global Plugin is the
process-wide composition root and joins shared services to NVDA's process
boundary; it owns no application events.
[ADR-0004](adr/0004-nvda-lifetime-and-event-ownership.md) records the rationale
for this boundary.

`AddonRuntime.start()` first registers the profile callback, then Settings and
Tools, and publishes the terminal service last. If any step fails, the runtime
immediately uses its complete idempotent teardown: unpublish, close the
published service, cancel delayed main-thread calls, open the gate, unregister
the profile callback, stop connections exactly once through their coordinator
owner, clear its runtime/focus/request state exactly once, then close UI and
presentation. Claim and terminal-focus generations are invalidated before
clients stop. Each step fails independently so one cleanup error cannot leave
later resources active. The callback that clears session passwords held only
by the Global Plugin remains as a narrow ownership-specific shutdown boundary.

A closed `TerminalIntegrationService` is a fail-open fence for retained
references: it suppresses no native event or Braille output, authorizes no
gesture, and produces no diagnostic effect. Claim, managed-connection,
network, Braille, and delayed main-thread callbacks additionally pass through
a runtime check that covers unpublication between queueing and execution.

Editor state, mode, completion documentation, transport capabilities,
connection instances, and pending requests belong exclusively to
`EditorSessionController` and `ConnectionCoordinator`. Claim and inventory
state belongs exclusively to `SessionClaimService`; focus and UIA lifetime
state belongs to `TerminalFocusService`; concrete output and sound caches
belong to `NvdaPresentation`. The Global Plugin exposes no second writable
interface for these states.

The AppModule and Braille overlay receive only the
`TerminalIntegrationService`; the concrete Global Plugin remains hidden behind
that contract. Terminal commands use a fixed enum instead of freely resolved
method names, while focus decisions and F12 authorizations are immutable
values. If the service is absent, has been replaced during add-on reload, or
violates the contract, the AppModule passes the original gesture or native
NVDA event through fail-open.

“Bounded” describes the trust and ownership boundary: the service exposes only
the typed operations required by the AppModule, the Braille module, and
inbound developer contexts.

The process-wide service instance lives in neutral `service_registry.py`. The
Global Plugin publishes and removes the service through the same
identity-checked `ServiceRegistrar` that the AppModule and Braille module only
read. `nvda_braille.py` owns the region and overlay and imports no Global
Plugin; `__init__.py` merely re-exports their class names for the Windows
Terminal AppModule.

The service holds no broad `_runtime` reference. The composition root supplies
exactly one handler for every `TerminalCommand` plus separate callbacks for
diagnostics, fail-open handling, F12 completion, and Braille presentation. The
constructor copies the command map and rejects missing, additional, or
non-callable entries. The public service therefore cannot reach other Global
Plugin methods or state.

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
reactivation. If Windows Terminal emits no new focus event after the question
closes, a short bounded main-thread sequence checks NVDA's current focus and
starts the normal focus-context handshake only for the same control, AppModule,
adapter token, and instance selection. A different terminal focus discards the
reactivation; missing or uncertain focus keeps native output open.

The `EditorSessionController` uses the active runtime managed by
`ConnectionCoordinator` but is solely responsible for its domain mutation. It
owns state and mode transitions, transport capabilities, menu documentation,
connection state, per-instance terminal passthrough, and isolated typing echo.
For an already validated focus/context event, it adds the saved connection
label to a copy before state and speech planning; it does not decide whether
that event belongs to the focused terminal. Its ordered neutral typing actions
become speech only at the NVDA boundary. Protocol-envelope
validation and network callbacks remain separate. For each validated event,
an immutable plan combines the state transition, domain terminal passthrough,
at most one mode cue, and the ordered neutral speech actions. The Global
Plugin applies passthrough to the gate and hands the cue and speech plan to
`NvdaPresentation`. The controller also
allocates bounded request IDs for clipboard,
register, and terminal control, binds them to an instance and
`TerminalIdentity`, and rejects foreign or late replies. One-shot clipboard
text is exposed only as a validated result to the NVDA boundary and is removed
from the safe follow-up event. Before sending, the same controller validates
the negotiated capability and canonical buffer/mode state and returns either
an immutable allowlisted outbound plan or one bounded rejection reason. It
allocates a pending request only for a valid action. Exact focus/gate
validation, transport calls, the Windows clipboard, diagnostics, and concrete
presentation remain separate. Semantic planner reset and access to the active
instance's completion documentation use the same controller boundary. NVDA's
own typed-word buffer and speech delivery remain at the NVDA boundary.

Each managed Neovim instance runtime also owns its own Braille exploration
controller, its own controller for numbered native choices, and a
`HeldContextController` for read-only callable and diagnostic queries. A tab
or pane therefore cannot display or mutate another local or remote session's
selected Braille mode, suggestion state, or held developer context. A runtime
switch activates only the state
owned by the assigned session. Its virtual line, reading column, and NVDA's
public `windowStartPos` remain in that runtime. Repeated-routing sequences and
focus messages are discarded when the control changes. Disconnect resets
only the affected runtime.

For Braille, the controller copies the active canonical state into a
`BrailleSessionPlan`; later editor events cannot mutate that plan. A
`BrailleRoutePlan` contains either a fully validated fixed `routeCursor`
payload with target kind, exact raw mode, and UTF-8-safe source character, or
one bounded rejection reason. In command-line mode, only content cells and
one virtual end cell map to byte columns; the prompt is non-routable. Insert
mode likewise provides one virtual blank after unchanged line text. An empty
Normal-mode line provides one cursor-bearing blank because NVDA cannot focus a
region with a cursor but no cells. Non-empty Normal-mode lines have no extra
end cell. `focusToHardLeft` and `hidePreviousRegions` ensure that the
structured line replaces preceding Windows Terminal context labels.

The public terminal service first confirms the exact terminal and records the
result. The overlay maps only NVDA's translated Braille position to the
semantic byte column. The service places the immutable fixed payload in the
same bounded `ControlDispatcher` used by exploration and numbered choices.
Its worker calls the local or SSH transport; a full queue or closed dispatcher
drops the optional action fail-open. Neither a routing key nor an NVDA region
callback can therefore perform socket, SSH, or `stdin.flush()` I/O on NVDA's
main thread. Only after successful queueing does `NvdaPresentation` announce
the source character, if NVDA's public `braille.speakOnRouting` setting is
enabled, through public `speech.speakSpelling`. It does not call the private
`braille._speakOnRouting` helper.

Optional repeated presses remain within the same layers. The pure
`BrailleRoutingRepeatController` recognizes only identical target signatures
and uses NVDA's public `keyboard.multiPressTimeout` setting. The first press
still emits `routeCursor` immediately; only the double-press word action is
delayed when a third press could replace it with a line action.
`core.callLater` schedules only this local main-thread callback and performs
no transport I/O. A `BrailleRoutingActionPlan` permits only Normal and Insert
modes and four fixed actions. The immutable `brailleRouteAction` payload uses
the same bounded dispatcher. The Neovim plugin revalidates buffer, window,
line, byte column, `changedtick`, raw mode, modifiability, and UTF-8 boundary,
then maps the action identifier to `cw`, `dw`, `c$`, or `d$` with one fixed
line start. No Lua, Ex, or Normal-command text crosses the transport.

Vertical Braille-display navigation follows the same boundary. NVDA's public
region methods plan only a direction. An immutable
`BrailleLineNavigationPlan` binds it to the negotiated capability, active
client, buffer, window, changed tick, raw mode, origin line, and Neovim's
preferred virtual column. The dispatcher sends the fixed `moveBrailleLine`
control. The fixed `preferred`, `start`, or `end` target rule distinguishes
direct up/down from horizontal panning across a line boundary. Only the
Neovim plugin maps that rule and virtual column to a valid byte
column on the adjacent line through public `winsaveview()`, `virtcol2col()`,
and `winrestview()`. With `preferred`, retaining `curswant` prevents a short
intermediate line from losing the desired horizontal position. `start`
resets both cursor and desired columns to zero; `end` selects the last
character in Normal mode and the insertion point after it in Insert mode.
Command-line mode and direct terminal input are excluded. Horizontal panning
within a line remains entirely in NVDA; only crossing a line boundary sends a
semantic transport control.

The region deliberately passes only the semantic direction and one of the
three fixed target rules. NVDA's `start` parameter distinguishes direct up
from backward panning; for the parameterless down callback the Windows
Terminal AppModule supplies an exactly bound marker for the public global
Braille command that expires after one input turn. Behind the
service/controller boundary, the independent `BrailleExplorationController`
selects one of two strategies. Cursor mode produces the `moveBrailleLine`
control described above. Braille exploration mode instead produces a
correlated `brailleExploreLineRequest`. Its `desiredVirtualColumn`,
`targetColumn`, and complete canonical origin identity are mapped by the
Neovim plugin to an ephemeral line position; neither the buffer nor the real
cursor changes. The first request must match the real cursor and mode exactly.
After that, real-cursor, mode, and text changes do not replace the virtual
position. When `changedtick` advances, the controller copies the new line
text and its derived presentation fields into the derived view only when the
real cursor line currently matches the explored line. The virtual line,
reading column, and Braille viewport remain unchanged. Changes on other lines
advance correlation only and do not refresh the displayed exploration.
Every follow-up request must still carry the original identity,
exploration ID, and next action number, while buffer, window, and tab remain
unchanged. `changedtick` may only advance to the currently validated value of
that same buffer. The result updates
only a derived Braille view in `EditorSessionController`, never canonical
connection state. Routing then plans from that view and deliberately moves the
real cursor to the explored line without toggling the still-selected Braille
exploration mode. The target line and byte column come from that derived view,
but buffer/window identity, mode, transport capabilities, and `changedtick`
come from the current canonical state. Routing is available only when the
derived line content belongs to that same `changedtick`. This keeps a manually
panned NVDA viewport stable while preventing an edit or mode transition from
turning an old display snapshot into an apparently successful routing request.

The derived view owns no visible Braille cursor. `EditorSessionController`
copies the real cursor into the Braille plan only when the real and explored
line and their text match.
The targeted content refresh restores that match after an edit on the
displayed line without introducing a second, virtual cursor. It replaces the
complete line-derived snapshot, not only its text, while retaining the virtual
line, preferred reading column, and NVDA viewport. A return from Insert to
Normal mode therefore updates routing authorization without re-anchoring the
Braille view.
`BrailleSessionPlan` additionally marks this derived view with
`preserve_viewport`. In that case, `StructuredLineRegion.update()` clears
NVDA's public `TextInfoRegion.pendingCaretUpdate` marker after calculating
the new region. A native terminal caret event arriving in the same NVDA cycle
therefore cannot scroll to the real cursor after `handleUpdate()` has restored
the Braille window as designed. The region is still processed fully through
NVDA's public update path, so changes inside the existing viewport appear
without allowing changes or the cursor outside it to take over its position.

Braille exploration mode and speech exploration mode own separate controllers, request-ID channels,
exploration IDs, Lua state, and cleanup controls. Interleaving therefore
cannot consume the other mode's action sequence. A profile-aware option may
also project the speech-exploration-mode controller's already validated virtual
state as a derived Braille view. It does not merge the state machines:
canonical editor state remains unchanged, the separate Braille exploration
controller takes priority, and release or cancellation restores the canonical
Braille view. The freely assignable toggle
remains a contextual script in the Windows Terminal AppModule.
`TerminalIntegrationService` owns the controller toggle and any asynchronously
queued remote cleanup; the Global Plugin process action only delivers the NVDA
message and requests a Braille refresh. Instance changes discard the transient
virtual position and in-flight requests, but returning activates that
session's independently selected Braille mode again. Disconnect and teardown
symmetrically reset only the affected runtime or all owned runtimes,
respectively. Command-line and direct-terminal modes are excluded.

`StructuredLineRegion` is not a parallel Braille implementation. It subclasses
NVDA's public `braille.TextInfoRegion` extension point so
`braille.handler.handleCaretMove` can trigger normal caret following and
`scrollToCursorOrSelection`. Because its text comes semantically from Neovim,
its update calls the public `braille.Region.update()` base method directly. It
sets only documented raw text, cursor, selection, and region fields and leaves translation, Unicode
normalization, cursor shape, selection dots, viewport, and display driver to
NVDA. Public `brailleToRawPos` maps a physical routing cell back into the
neutral plan. For review tether the overlay raises `NotImplementedError` as
handled by `braille.getFocusRegions`, so NVDA uses its native fallback.

The successful asynchronous `focusContext` confirmation rebuilds the native
focus region through public `handleGainFocus(..., shouldAutoTether=False)`;
incremental `handleUpdate` is used only when the correct region already
exists. Overlay composition belongs to the Windows Terminal AppModule and is
based on the terminal class NVDA has already selected. It is inert without the
published service or an exact authenticated binding and delegates fail-open.
Persistent regions and routing read no private NVDA buffer or gesture state.
Only the separate transient spelling suggestion identity-checks and dismisses
the private message buffer created by its own public
`braille.handler.message()` call. [ADR-0002](adr/0002-nvda-api-boundaries.md)
documents and justifies every private touchpoint.

The settings panel, presentation adapter, and profile-switch path use snapshots
or domain operations supplied by `SettingsService`; no dialog mutates a freely
accessible plugin dictionary. `NvdaUiManager` receives only that service, a
diagnostic recorder, and the small password and component-operation callbacks
it needs. Its Tools entries and Settings category nevertheless remain registered
exactly once for the Global Plugin's process lifetime.
Navigation-detail indices are resolved by the service into booleans before
they cross the editor or exploration interfaces. The shared speech planner
therefore remains independent of NVDA configuration and produces the same
line-word-character ordering for normal navigation and exploration release.
The exploration-release values affect only output at the real cursor when
NVDA is released; virtual exploration steps and character exploration remain
independent of them.

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
- `brailleRouteAction` performs only one of four fixed word or line actions at
  a previously and exactly bound routing position;
- `moveBrailleLine` moves the editor cursor to the immediately previous or
  next line while retaining the preferred virtual column;
- `copyTextRequest`, `pasteTextRequest`, and `setRegisterRequest` mediate
  explicit clipboard actions;
- `leaveTerminalInputRequest` performs only Neovim's fixed `stopinsert`.
- `exploreTextRequest` moves only an ephemeral reading position, while
  `endExplorationRequest` discards it; neither moves the real cursor.
- `acceptNumberedChoiceRequest` confirms only the already validated index of
  an active native choice list.

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

### Numbered native choices

A neutral `NumberedChoiceController` stored in each instance runtime owns only
transient local selection state. Its first strict adapter covers Neovim's
built-in `z=` spelling list:
the Lua plugin proves the immediately typed command and parses only a
consecutively numbered, bounded list from Neovim's UI event. Items enter
neither canonical editor state nor diagnostics.

Neovim 0.12 permits full context validation on the scheduled UI-event path.
Neovim 0.10 is already blocked inside the native prompt, so the plugin captures
the bounded editor snapshot at the proven `z=` input and publishes only its
corresponding native list through a fast-callback-safe RPC notification. The
additional native input instruction at the end of that list is accepted only
in its narrow form.

The Windows Terminal AppModule uses NVDA's normal contextual gesture
resolution for `NVDA+j/k/Enter`. The service and controller revalidate focus,
control, instance, capability, and editor identity. Only the internal
zero-based index is confirmed; displayed text is never sent back as input.
Releasing NVDA discards the local selection, not Neovim's prompt. Each future
prompt type requires its own strict adapter.

### Automatic active parameter

`call_context.lua` resolves call boundaries independently of rendering or the
completion plugin. When available, Tree-sitter marks strings, comments, and
language-specific text nodes; a bounded lexer supplements incomplete code and
provides a conservative fallback. Scanning is limited to 512 lines, 128 KiB,
and 20,000 tree nodes. Ambiguous or oversized contexts produce no result.
Paired parentheses resolve nesting, so Insert mode selects the innermost
enclosing call. The manual query reuses this resolver with stricter position
rules.

In Insert mode, `signature_help.lua` observes `InsertEnter`, `CursorMovedI`,
`TextChangedI`, and `CompleteDone`, debounces for 120 ms, and requests Neovim's
public `textDocument/signatureHelp` interface. Trigger and retrigger characters
and bounded prior `activeSignatureHelp` follow the LSP contract. Every request
carries a generation and an exact buffer, window, changed-text, mode, cursor,
and call-identity snapshot; a later change cancels the request or rejects its
reply. With multiple clients, the first valid bounded result is selected
deterministically.

Server-provided `activeSignature` and `activeParameter` are authoritative; the
implementation deliberately does not count commas. Identity is deduplicated
by call, signature, and parameter. Movement within one argument is therefore
silent, while returning to an already filled earlier parameter speaks it
again. A signature change uses only that signature's parameter list. The
validated `activeParameterChanged` event is speech-only, leaving canonical
Braille on source text. Neither transport nor NVDA's main thread performs LSP
requests.

### Held developer contexts

The Windows Terminal AppModule owns the physical NVDA-key lifetime and
captures only the fixed parameter or diagnostic navigation gestures. The
per-instance `HeldContextController` correlates each read-only query with
focus, terminal control, instance, buffer, window, tab, changed tick, line,
and UTF-8 byte column. The Lua plugin reads signature help, hover, or
`vim.diagnostic` without moving the cursor or changing the buffer. When the
real cursor is on a callable name immediately followed by `(` or on that
opening parenthesis, the plugin places only the LSP query position after the
delimiter. On the associated closing parenthesis, the unchanged LSP position
already denotes the inside of the argument list. Servers such as Pyright can
therefore return structured parameters rather than only hover text. Any mismatch
before the reply or during presentation discards the state and restores the
ordinary Braille line. Transport I/O remains in the bounded
`ControlDispatcher`.

For Braille, the NVDA adapter uses NVDA's transient message buffer. NVDA's own
source uses the same public path for suggestion and selection feedback, and it
writes the display immediately rather than waiting for a focus event. A normal
NVDA region first measures the suggestion with the active translation table,
then limits the configured start to the last position where the complete result
fits. On release, only the proven add-on-owned message region is dismissed and
the preserved editor buffer is refreshed. The narrowly scoped private
counterpart required for that dismissal is documented in
[ADR-0002](adr/0002-nvda-api-boundaries.md).

### File managers

`file_manager.lua` normalizes the active entry. Separate adapters subscribe to
public events from Oil, netrw, mini.files, nvim-tree, and Neo-tree where
available. They transport typed names, kinds, states, and action results rather
than decorated screen lines. Missing plugin APIs fall back to existing
navigation. See `accessibility.md` and `current-status.md` for the feature
matrix and practical test status.

The Braille planner represents canonical file-manager state as a persistent
region. Navigation and state announcements remain speech-only actions and do
not create a second NVDA Braille message that would cover this region until a
message timeout. The controller passes only the translation function into the
NVDA-independent Braille planner: names and routing positions remain
unchanged, while typed kinds and states are localized only at the NVDA
boundary.

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
