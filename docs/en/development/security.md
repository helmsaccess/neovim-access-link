# Security and privacy

Remote transport is Windows OpenSSH stdin/stdout. SSH authenticates host and
account and normal host-key checking remains active. `ClearAllForwardings=yes`
prevents inherited forwards. Keys and `ssh-agent` are recommended.

Optional passwords are requested accessibly, kept only in memory, exposed only
to the short-lived SSH process through askpass, and erased on deactivation or
exit. They are never persisted, logged, or placed in arguments.

Local Windows RPC accepts only an endpoint registered by the plugin and bound
exactly to `127.0.0.1`; users cannot configure another address. The registry is
private to the user and stale PID/endpoint entries are rejected.

Registry cleanup never terminates a process. It removes only a definitively
dead or process-start-mismatched private entry. Nonce verification happens on
the selected permanent RPC channel and never deletes anything on mismatch. A socket is removed only
when `ownsSocket=true` and its plugin path exactly contains the same PID and
nonce; inherited and user-defined paths are never removed.
Timeouts, SSH failure, focus loss, or access uncertainty are non-destructive.
Closing a WT tab or whole window stops only its NVDA client, never remote Neovim/tmux.

Protocol messages are size-bounded, schema-validated, session- and sequence-
checked. Untrusted messages cannot request arbitrary code or general Neovim
RPC. Cursor routing is the only state-changing reverse action and is validated
against current state. Diagnostic editor text and secrets are redacted.

Terminal suppression requires an authenticated, active, focused, exact binding
and always fails open on error, timeout, disconnect, or deactivation.

Each physical F12 press authorizes one claim attempt for the exact focused
`TerminalIdentity`. Any intervening focus change rejects it; without a fresh
Neovim claim, the check creates no binding, dialog, output, or suppression.
Activity from another Neovim instance cannot move a binding. On focus loss
or a control change, suppression is cleared before a request-ID-correlated
focus-context response may reactivate the exact remembered connection.

This still does not independently prove that Neovim remains the visible
foreground program inside an already bound `TermControl` when a shell or tmux
client replaces it while RPC stays alive. That residual limit remains under
investigation; it grants no authority to uncertain or unbound controls and may
not be closed with terminal screen scraping.
