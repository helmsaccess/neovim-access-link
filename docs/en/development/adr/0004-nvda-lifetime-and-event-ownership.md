# ADR-0004: NVDA lifetime and application-event ownership

## Status

Accepted as the target architecture for an incremental migration. This ADR
alone does not change runtime behavior. Registration of configurable commands
and the concrete mechanism for locating the shared service remain open until
the NVDA community confirms suitable patterns.

## Context

NVDA loads the Global Plugin once per NVDA process, while it creates a Windows
Terminal AppModule for the corresponding application process. Settings, tools,
and shared local and SSH connections therefore need one lifetime with orderly
shutdown. Windows Terminal events, overlay selection, and `nextHandler` belong
to the AppModule instead.

The current implementation already places public event entry points in the
AppModule, but delegates decisions and `nextHandler` to a large Global Plugin
instance. This works, but obscures the boundary between application-specific
NVDA integration and shared state.

## Decision

A minimal Global Plugin remains as the process-wide composition and lifetime
root. It may only:

- register settings and tools once and remove them symmetrically;
- construct, expose, and shut down shared services in an orderly manner;
- provisionally provide metadata for configurable commands until their final
  scope is resolved.

Connections, assignments, the gate, protocol state, and presentation planning
reside in ordinary services that do not inherit from `GlobalPlugin`. Their
contract accepts concrete terminal identities and domain data and returns
decisions or output plans. It owns neither public AppModule events nor
`nextHandler` or the overlay list.

The Windows Terminal AppModule owns:

- every application-specific NVDA event entry point;
- selection and removal of its overlays;
- every invocation of `nextHandler`, at most once per event;
- the fail-open decision when the service, identity, or state is missing,
  stale, ambiguous, or faulty.

During startup, a shared service is exposed only after complete
initialization. During reload or termination, it is first marked unavailable;
pending focus decisions are then discarded, suppression is disabled,
connections are stopped, and UI registrations are removed symmetrically.
AppModules must not continue using an unverified stale service instance. This
ADR deliberately does not decide whether the current instance is found through
a registrar, module-level access, or another established public NVDA pattern.

## F12 exception

F12 remains the explicit assignment signal, but is neither a global input hook
nor an NVDA script. Only the Windows Terminal AppModule observes the physical
key. Assignment may start only when the same concrete focused Windows Terminal
control is confirmed both during capture and again on NVDA's main thread. Any
mismatch falls back to native processing without an assignment.

## Non-negotiable invariants

- Errors, disconnects, reload, and uncertain focus immediately fail open to
  NVDA's native terminal handling.
- Tabs, split panes, windows, and multiple Windows Terminal processes remain
  separated by concrete control identity.
- Local and SSH sessions may share a lifetime but must never adopt one
  another's output, focus response, or assignment.
- Network I/O, reconnects, parsing, and logging never block NVDA's main thread.
- Native focus handling required by LiveText remains intact; regression tests
  will define its exact ordering before event migration.

## Open command decision

The existing globally visible, unbound script metadata remains during the
migration. No new global default gestures will be introduced. Final placement
will be decided only after determining how commands can remain discoverable in
the Input Gestures dialog while being reliably restricted to the active
Windows Terminal AppModule.

## Consequences

Global lifetime remains where it prevents duplicate registrations and
connections. Application events move closer to NVDA's AppModule model. The
migration proceeds in phases; a phase is retained only when automated and
practical checks demonstrate at least the existing multi-window, focus, and
fail-open reliability.

ADR-0002 remains authoritative for private NVDA API exceptions. This ADR
clarifies ownership without permitting additional private API use.
