# Latency

Interactive editor feedback must remain immediate and must never wait for SSH,
DNS, reconnection, installation, or logging on NVDA's main thread. Neovim
callbacks create small snapshots; background clients perform transport I/O;
NVDA output is queued back to the event thread.

Messages, queues, scans, retries, joins, and diagnostic records are bounded.
High-frequency cursor and text events may be coalesced only when ordering,
session identity, and the latest semantic state remain correct. A gap requests
resynchronization and `fullState` rather than speaking stale data.

File-manager render events are coalesced without a wait timer within exactly
one Neovim scheduler cycle. The active adapter state is then read once and
sent only for a real semantic change. Inactive targets are rejected before and
after scheduling. There is no periodic adapter or filesystem query.
Synchronous action results for the same active target use that same scheduler
cycle for batching. This is not a wait window: exactly one typed summary is
planned immediately after the cycle.

Built-in file-manager adapters are selected directly by `filetype`. An
external detector or provider has a 5-ms budget. Three repeated overruns or
errors cause a five-second per-buffer fail-open cooldown. The deadline is
checked only on existing events and uses no timer or background query.

The Oil confirmation fallback likewise runs only on an existing buffer or
window event. It reads at most 200 buffer lines and abandons recognition on an
unknown format; it creates neither a timer nor a periodic check.

An exploration gesture prepares only a bounded control payload on NVDA's main
thread. A bounded worker sends it, so the gesture script performs no socket or
SSH I/O. One result contains at most 16 KiB of text; word scanning is limited
to 256 lines or 64 KiB, and repetition to 64 steps. Modifier release reads
from existing canonical state and waits for no round trip.

Braille routing uses the same bounded control dispatcher. Region and routing
callbacks only map the translated cell to an already validated fixed payload
and place an immutable copy in the queue without waiting. The worker alone
calls `send_control`. This is especially required for SSH because its stdio
client acquires a pipe lock, writes, and calls `flush()` inside
`send_control`. A full or closed queue drops the optional routing action
fail-open; it must never block NVDA.

The first routing-key press remains immediate even when repeated actions are
enabled. If word and line actions are both configured, `core.callLater` holds
only the already planned local word action until NVDA's multiple-press
timeout expires. The callback neither waits nor sleeps nor performs I/O; a
third press invalidates it by token. Only the resulting fixed
`brailleRouteAction` control is then placed non-blockingly in the same
dispatcher as other routing.

`moveBrailleLine` uses the same dispatcher and non-blocking rules. The NVDA
region callback only validates and queues the small fixed payload.
Virtual-to-byte column mapping, cursor movement, and the resulting state event
occur in the Neovim process.

In Braille exploration mode, an equally bounded
`brailleExploreLineRequest` replaces that cursor control. NVDA's main thread
changes only local planning state and does not wait for the virtual line.
Results are limited to 16 KiB, correlated, and trigger only a public Braille
refresh. A full queue, stale reply, or focus change drops the optional step
fail-open.

Latency measurements must record platform, versions, transport, workload,
sample count, percentiles, and failures. Synthetic measurements do not replace
practical NVDA testing.
