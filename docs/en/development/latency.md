# Latency

## Measurement model and target

Measurements separate Neovim callback to send, transport, parsing and
dispatch, invocation of the NVDA output queue, and the complete pipeline. They
use monotonic high-resolution clocks. Timestamps from different computers are
not subtracted directly without a synchronization model.

The target from a Neovim event to the speech call is a median below 20 ms, p95
below 40 ms, and p99 below 75 ms. A synthetic measurement proves only its
measured section; practical perception under NVDA remains a separate check.

## Non-blocking NVDA path

NVDA's main thread never waits for SSH, socket I/O, DNS, reconnect,
installation, parsing, or logging. Input and region callbacks validate small
immutable payloads and place them into bounded queues without waiting. Workers
perform transport access; results return through NVDA's event queue for
presentation.

A full or closed queue, stale result, or focus change drops an optional control
action fail-open. Releasing an exploration key uses existing canonical state
and waits for no round trip.

## Bounded high-frequency paths

- Cursor, text, and UI events may be coalesced only when ordering, session
  identity, and the latest semantic state remain correct. A sequence gap
  requests `fullState`.
- File-manager render events and synchronous action results are coalesced
  within exactly one Neovim scheduler cycle. There is no periodic filesystem
  or adapter query.
- External file-manager detectors have a 5 ms budget. Repeated errors or
  overruns activate a per-buffer event-driven cooldown.
- The Oil confirmation fallback reads only on existing events and at most 200
  buffer lines.
- Speech exploration limits replies to 16 KiB, word scanning to 256 lines or
  64 KiB, and repetition to 64 steps.
- Braille routing, Braille-line navigation, and Braille exploration use the
  same bounded control dispatcher. Translation and planning on NVDA's main
  thread perform no transport I/O.

The first routing press remains immediate. Only when configured double and
triple actions must be distinguished does `core.callLater` retain an already
planned local action until NVDA's multiple-press timeout expires. The callback
does not sleep or perform I/O.

## Reproducible measurements

`tools/latency/serialization_benchmark.py` compares MessagePack and compact
JSON with a representative state event:

```bash
python3 tools/latency/serialization_benchmark.py
```

Results are interpreted only with platform, versions, transport, workload,
sample count, percentiles, and failures. The microbenchmarks that informed the
original semantic Lua-path decision remain as decision context in
[ADR-0001](adr/0001-neovim-integration-point.md).

## Practical acceptance

Before publication, perceived navigation, completion, diagnostic output,
local connections, and SSH connections are checked under NVDA. Automated
tests enforce non-blocking behavior, bounds, correlation, and fallback paths;
they do not replace practical speech-synthesizer, Braille-hardware, or real
network-latency checks.
