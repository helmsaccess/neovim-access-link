# Latency

Interactive editor feedback must remain immediate and must never wait for SSH,
DNS, reconnection, installation, or logging on NVDA's main thread. Neovim
callbacks create small snapshots; background clients perform transport I/O;
NVDA output is queued back to the event thread.

Messages, queues, scans, retries, joins, and diagnostic records are bounded.
High-frequency cursor and text events may be coalesced only when ordering,
session identity, and the latest semantic state remain correct. A gap requests
resynchronization and `fullState` rather than speaking stale data.

Latency measurements must record platform, versions, transport, workload,
sample count, percentiles, and failures. Synthetic measurements do not replace
practical NVDA testing.
