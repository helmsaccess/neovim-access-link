# ADR-0001: Hybrid Neovim integration point

## Status

Partly superseded by
[ADR-0006](0006-local-tcp-and-ssh-stdio-transports.md). The decision to obtain semantic events
from a Lua plugin remains current. ADR-0006 replaces the loopback-listener and SSH-forwarding
transport described here.

Date: 2026-07-11.

## Context and measurement

| Model | n | p50 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|---:|
| A: Lua state capture | 10,001 | 1.19 µs | 4.63 µs | 8.68 µs | 70.95 µs |
| B: external snapshot, 6 RPC requests | 10,000 | 193.25 µs | 281.80 µs | 456.42 µs | 3.88 ms |
| C: Lua snapshot, 1 RPC transition | 10,000 | 68.92 µs | 103.92 µs | 135.36 µs | 951.29 µs |

Model C was measured conservatively as a synchronous request. Production notifications avoid
the request portion; integration testing verifies that assumption.

## Decision

The project selected model C:

1. A small Lua plugin registers autocommands and buffer callbacks, reads consistent semantic
   state, and sends grouped RPC notifications.
2. An external Linux bridge registers its RPC channel with the plugin, receives pushed events,
   and may use `nvim_ui_attach()` for command-line, message, and completion events.
3. The bridge handles sequencing, session identity, queuing, heartbeat, framing, and
   resynchronization. This ADR originally placed the restricted protocol on a loopback listener.
4. This ADR originally connected NVDA as a client through an SSH local forward.

Items 3 and 4 describe the historical transport decision and are replaced by ADR-0006.

## Rationale

Structured semantics must come from a Lua plugin using Neovim APIs. A separate
bridge isolates Linux RPC and SSH lifecycle, while NVDA remains responsible for
focus and accessible output. Terminal scraping cannot reliably represent mode,
selection, completion, diagnostics, Unicode columns, or multiple sessions and
is rejected as the primary data source.

This split keeps the protocol narrow, allows core tests without NVDA, and
ensures transport errors cannot silently turn terminal pixels into editor
truth.

## Consequences

External message and popup-menu UI capabilities attach only while an
authenticated bridge channel is registered. Before connection and after
disconnect, native TUI ownership is preserved so recovery and confirmation
prompts remain visible fail-open.
