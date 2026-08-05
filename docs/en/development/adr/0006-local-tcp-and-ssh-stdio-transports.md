# ADR-0006: Local TCP and SSH standard streams as transports

## Status

Accepted.

Date: 2026-08-05.

Supersedes the transport portion of
[ADR-0001](0001-neovim-integration-point.md). That ADR's decision to produce semantic events
in a Lua plugin remains current.

## Context

Local Windows sessions and remote Linux sessions need different secure connection paths. Both
paths must associate multiple Windows Terminal windows, tabs, and panes precisely without
affecting NVDA through blocking network access or unconfirmed sessions. Fixed ports, general
Neovim RPC access over SSH, and port forwards inherited from user profiles increase the attack
and failure surface.

## Decision

- Local Neovim on Windows publishes a dynamic RPC endpoint on `127.0.0.1` only. The session
  registration contains a nonce and process data; NVDA validates them before connecting
  directly. No Python bridge runs on this path.
- Remote Neovim publishes RPC through a private Unix socket. NVDA starts the unprivileged Python
  bridge with `ssh.exe -T`; the restricted framed MessagePack protocol uses standard input and
  output. SSH authenticates the host and user. There is no port forward, fixed port, or shared
  application token.
- `ClearAllForwardings=yes` prevents configured SSH port forwards from being inherited by the
  bridge connection.
- Endpoints and discovered sessions remain untrusted until fully validated. Capabilities are
  negotiated, and control messages run only for the confirmed focused session. Native NVDA and
  terminal handling remains active on failure.

## Consequences

- Two transport adapters share protocol validation, canonical state, and presentation planning.
- The remote bridge provides a narrow trust and process boundary; local Windows does not need
  that extra process.
- Local TCP remains loopback-only, and remote RPC remains restricted to a private Unix socket.
- Capability or message changes require coordinated plugin, bridge, and add-on tests. Safe,
  SSH, and socket tests remain separate validation phases.
