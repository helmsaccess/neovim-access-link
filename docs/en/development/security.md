# Security and privacy

## Transport and credentials

Remote transport is Windows OpenSSH stdin/stdout. SSH authenticates host and
account and normal host-key checking remains active. `ClearAllForwardings=yes`
prevents inherited forwards. Keys and `ssh-agent` are recommended.

Optional passwords are requested accessibly, kept only in memory, exposed only
to the short-lived SSH process through askpass, and erased on deactivation or
exit. They are never persisted, logged, or placed in arguments.

## Local RPC and session files

Local Windows RPC accepts only an endpoint registered by the plugin and bound
exactly to `127.0.0.1`; users cannot configure another address. The file-based
session registry is private to the user and stale PID/endpoint entries are
rejected. It consists of short-lived JSON files, not Windows Registry keys;
the implementation uses neither `HKCU` nor `HKLM`.

Session-file cleanup never terminates a process. It removes only a definitively
dead or process-start-mismatched private entry. Nonce verification happens on
the selected permanent RPC channel and never deletes anything on mismatch. A socket is removed only
when `ownsSocket=true` and its plugin path exactly contains the same PID and
nonce; inherited and user-defined paths are never removed.
Timeouts, SSH failure, focus loss, or access uncertainty are non-destructive.
Closing a WT tab or whole window stops only its NVDA client, never remote Neovim/tmux.

## Protocol and reverse controls

Protocol messages are size-bounded, schema-validated, session- and sequence-
checked. Untrusted messages cannot request arbitrary code or general Neovim
RPC. The reverse direction is a fixed allowlist: `requestFullState` and
`requestFocusContext` request state; validated `routeCursor` performs Braille
routing; the explicit clipboard requests below perform fixed copy, paste, and
register operations; `leaveTerminalInputRequest` can perform only
`stopinsert`; and exploration controls can perform only six read-only virtual
movements or discard their ephemeral state. State-changing controls are correlated with current session,
control, instance, editor identity, and mode as applicable. Diagnostic editor
text and secrets are redacted.

Exploration validates the complete editor origin and never moves the real
cursor or mutates a buffer. Result size, repeats, and word scanning are
bounded; a focus or context change invalidates the ephemeral position.

The clipboard path runs only from explicit, freely assignable NVDA commands.
It accepts no arbitrary Lua, Ex, or register name: copy reads only the current
Visual selection or register 0, paste uses only Neovim's paste API, and
register storage uses only fixed register 0 while pointing the unnamed
register to it. Every direction validates
request ID, active control binding, instance, buffer,
window, tab, changed tick, and mode. Paste is limited to normal modifiable
editor buffers; text must be NUL-free and at most 256 KiB in UTF-8. Focus loss,
disconnect, or state mismatch discards the pending result without retry. A
paste already sent to the previously and explicitly focused session cannot be
retracted, but it must never affect the new session or run more than once.
Copied text is not retained in bridge/client state and is redacted from
diagnostics.

## Terminal focus and suppression

Terminal suppression requires an authenticated, active, focused, exact binding
and always fails open on error, timeout, disconnect, or deactivation.

Freely configurable commands belong to the Windows Terminal AppModule. NVDA
initially lists their unassigned metadata after Windows Terminal was focused
before opening Input Gestures. Once that module is loaded, NVDA's global user
gesture map may list a saved assignment from another application, but runtime
resolution still does not select it in that application's script chain.
Invocation additionally requires that exact AppModule instance and a complete,
allowed Windows Terminal control identity; a focus race passes the original
gesture through and leaves gate, bindings, and suppression untouched. Focus
events, overlays, F12, and the default-bound diagnostic command remain
Windows-Terminal-AppModule-only.
An opaque per-AppModule token rejects late focus-loss notifications from an
old WT process. Two-phase focus completion is also bound to that token, its
generation, and the concrete terminal identity.

Each physical F12 press authorizes one claim attempt for the exact focused
`TerminalIdentity`. Any intervening focus change rejects it; without a fresh
Neovim claim, the check creates no binding, dialog, output, or suppression.
After an F12 match, the shared observer accepts only NVDA's current focus
object, its exact still-registered AppModule instance, and the same complete
control identity in the gate; there is no single-adapter fallback. In Insert
mode the plugin consumes only an otherwise-unbound claim F12 after observing
it and never replaces an existing user mapping. Before the first connection,
Neovim cannot know NVDA's authorization state, so this reservation applies to
every configured, unbound Insert claim F12 inside Neovim, but to no other key
or mode; NVDA itself never consumes the physical key. Activity from another
Neovim instance cannot move a binding. On focus loss or a control change, suppression
is cleared before a request-ID-correlated focus-context response may reactivate
the exact remembered connection.

This still does not independently prove that Neovim remains the visible
foreground program inside an already bound `TermControl` when a shell or tmux
client replaces it while RPC stays alive. That residual limit remains under
investigation; it grants no authority to uncertain or unbound controls and may
not be closed with terminal screen scraping.
