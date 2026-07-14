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

Protocol messages are size-bounded, schema-validated, session- and sequence-
checked. Untrusted messages cannot request arbitrary code or general Neovim
RPC. Cursor routing is the only state-changing reverse action and is validated
against current state. Diagnostic editor text and secrets are redacted.

Terminal suppression requires an authenticated, active, focused, exact binding
and always fails open on error, timeout, disconnect, or deactivation.
