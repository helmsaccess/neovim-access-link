# ADR-0003: Narrow fallback for Oil confirmations

## Status

Accepted for development after 0.93.0. Recheck it against supported Oil
versions before every release.

## Context

Oil publishes completion events for file actions but no public semantic event
before executing its custom confirmation float. The float contains complete
paths. Speaking its raw rendering would disclose unnecessary data and would
not identify the confirmation reliably.

## Decision

The Neovim plugin may recognize only a real float whose exact `filetype` is
`oil_preview` as an Oil confirmation. On an existing event it reads at most
200 rendered lines, accepts only the fixed actions `CHANGE`, `COPY`, `CREATE`,
`DELETE`, and `MOVE`, and publishes only action, count, and “Y yes, N no” as
`promptOpened`. It transports no file name, path, or raw line. Leaving or
closing the float produces `promptClosed`.

Unknown rendering, another file type, a normal window, or a parser failure
fails open to general behavior. There is no timer query, filesystem read, or
general popup parser. Public Oil completion events remain authoritative for
the action result.

## Consequences

- Benefit: the confirmation is understandable and path-free before execution.
- Risk: `oil_preview` and the rendered action format are private plugin details
  and may change.
- Mitigation: before release, an isolated real-Oil test must prove opening,
  cancellation, exactly one open/close pair, absence of raw competing events,
  and an unchanged fixture.
- Replacement: remove this fallback as soon as Oil offers a suitable public
  pre-action event.
