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

That gate does not yet constitute a complete non-interference proof for every
unbound Windows Terminal pane. Remembered-binding activation, the application-
wide F12 observer, activity-confirmed rebind prompts, and overlay selection are
under an explicit continuing isolation audit. A `TerminalIdentity` proves the
focused UIA terminal control, not by itself that Neovim is still the foreground
application inside that control. Until fresh structured evidence and negative
pane tests close this gap, uncertain state must not gain suppression authority.
