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

Latency measurements must record platform, versions, transport, workload,
sample count, percentiles, and failures. Synthetic measurements do not replace
practical NVDA testing.
