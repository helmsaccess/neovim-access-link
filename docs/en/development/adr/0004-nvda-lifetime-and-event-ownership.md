# ADR-0004: NVDA lifetime and application-event ownership

## Status

Accepted and implemented.

## Context

NVDA loads the Global Plugin once per NVDA process and creates one Windows
Terminal AppModule per application process. Settings, the top-level add-on
menu, and shared local and SSH connections need one lifetime with orderly
shutdown. Windows Terminal events, overlay selection, and `nextHandler` belong
to the AppModule.

NVDA extension points invoked process-wide may still be necessary. They must
not widen application scope: an operation is allowed only when the current
focus object, registered AppModule instance, concrete terminal control, and
confirmed connection state all match.

## Decision

The Global Plugin is only the process-wide lifetime adapter: it creates exactly
one runtime through `create_runtime()` and closes it on termination.
`composition.py` constructs shared services transactionally; `AddonRuntime`
registers settings and the menu, publishes the terminal facade only after
complete initialization, and shuts all owners down in a defined order.
Connection workflow, temporary-binding recovery, terminal actions, event
delivery, and domain assignment, gate, protocol, and presentation state reside
in ordinary services that do not inherit from `GlobalPlugin`.

The Windows Terminal AppModule owns:

- every application-specific NVDA event entry point;
- selection and removal of its overlays;
- metadata and dispatch for configurable terminal commands;
- every invocation of `nextHandler`, at most once per event;
- the fail-open decision for missing, stale, ambiguous, or faulty state.

The AppModule-managed `inputCore.decide_executeGesture` observer is registered
only while at least one Windows Terminal AppModule is alive. It considers only
the explicitly supported candidates: F12, contextual numbered choices, and
the exactly identified public NVDA Braille next-line command. Every other
gesture remains unchanged. Each match is revalidated against the focus object,
AppModule, control identity, service generation, and gate.

On termination or reload, the shared service is marked unavailable first.
Pending focus decisions are then discarded, suppression is disabled, and
connections are detached from canonical state. A fixed background pool owns
and stops every detached client without making NVDA's main thread wait; UI
registrations are removed symmetrically. AppModules do not use an unverified
stale service instance.

## Invariants

- Errors, disconnects, reload, and uncertain focus immediately fail open to
  NVDA's native terminal handling.
- Tabs, panes, windows, and Windows Terminal processes remain separated by
  concrete control identity.
- Local and SSH sessions never adopt one another's output, focus response, or
  assignment.
- Network I/O, reconnects, parsing, and logging never block NVDA's main thread.
- Native LiveText focus handling remains intact: prepare focus, invoke
  `nextHandler` exactly once, then complete speech suppression and any pending
  `fullState`.

## Consequences

Application events follow NVDA's AppModule model. Process-wide lifetime remains
where it prevents duplicate registration and competing connections. Further
extraction from the composition root is useful only when it clearly improves
ownership, testability, or fault isolation.

ADR-0002 remains authoritative for NVDA API exceptions. This ADR permits no
new private API use.
