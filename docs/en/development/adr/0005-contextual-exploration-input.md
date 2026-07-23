# ADR-0005: Contextual input for exploration mode

## Status

Implemented. Automated confirmation is complete; practical acceptance is
still pending.

## Context

Exploration mode uses `NVDA+h/j/k/l` and `Shift+NVDA+h/l` as read-only
navigation inside a confirmed Neovim pane. The same Windows Terminal process
may simultaneously contain other tabs and panes running PowerShell, an
ordinary SSH shell, or another Neovim session. NVDA's unchanged input
resolution must therefore apply outside the exact assigned Neovim
`TermControl`.

NVDA already resolves keyboard gestures through `scriptHandler.findScript`.
GlobalPlugins are checked before the focused object's AppModule, followed by
NVDA's built-in `globalCommands`. A separate gesture dispatcher would
duplicate that priority and bypass input help and user assignments. Normal
NVDA scripts do not, however, receive the modifier's later key-up.

## Decision

The Windows Terminal AppModule owns selection, execution, and lifecycle of the
six exploration actions. It overrides `getScript` only for their normalized
identifiers and a narrowly bounded autorepeat barrier.

- When the exact focused control has a locally confirmed, connected, and
  authenticated assignment, `getScript` returns the exploration script.
- When authorization is absent or uncertain, it delegates to normal AppModule
  resolution. NVDA continues its normal search itself; the add-on neither calls
  `gesture.send()` nor emulates the displaced NVDA command.
- Every other identifier delegates unchanged to
  `super().getScript(gesture)`.
- The queued script revalidates the control, instance, service generation,
  capability, and canonical editor state before requesting a fixed
  exploration action.
- If this second check fails after script selection, the chord is consumed
  silently. It is not forwarded as a bare `h/j/k/l` that could move the real
  Neovim cursor.

Exploration registers no handler with `inputCore.decide_executeGesture`. Its
existing use remains limited to the F12 assignment described by ADR-0004.

The AppModule symmetrically registers the public
`inputCore.decide_handleRawKey` extension point while at least one of its
instances exists. The callback:

- always returns `True`, so it never changes NVDA's raw-key processing;
- records physical NVDA-key down and up so a release that arrived before the
  queued script runs cannot be missed;
- recognizes physical NVDA- or direction-key release during active exploration;
- queues completion on NVDA's main thread and clears bounded autorepeat state.

Bare repeats from a direction key still held when NVDA is released are
consumed through a temporary no-op AppModule script, and only in the same
still-confirmed Neovim control. The barrier does not apply in another pane.

Exploration itself is semantic and transport-neutral. A strictly read-only
Lua component holds an ephemeral virtual cursor and returns only the selected
character, word, or line through fixed validated controls. It never moves the
real Neovim cursor. Outbound controls are sent outside NVDA's main thread.

## Priority and user assignments

In a confirmed Neovim control, normal NVDA ordering places the AppModule ahead
of built-in commands such as `NVDA+k` and laptop `NVDA+l`. Other GlobalPlugins
retain NVDA's defined higher priority. Explicit user assignments and removals
remain governed by NVDA's Gesture Map. Forcing precedence over GlobalPlugins
or user rules is outside this decision.

## Consequences

The feature uses NVDA's existing gesture recognition, input help, script
queue, and conflict resolution. The only process-wide callback added is a
passive public raw-key observer. Structural and runtime tests must prove its
fast return, constant `True`, symmetric reload, exact pane isolation, and
fail-open behavior.

Focus changes, disconnect, resync, stale state, or a late reply end
exploration without guessed text or editor operations. Practical acceptance
follows tests with mixed local, SSH, Neovim, and non-Neovim panes.
