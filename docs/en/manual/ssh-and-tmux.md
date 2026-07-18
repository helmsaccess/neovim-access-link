# Using SSH, tmux, and Neovim

The add-on does not drive the visible shell. Open Windows Terminal, log in with
SSH normally, enter the desired tmux window or pane, and start `nvim`.
Activation first uses short, bounded OpenSSH calls to inventory reachable
sessions. A persistent hidden bridge connection is created only after F12 or
the manual workflow confirms one specific Neovim session.

Create profiles under `NVDA menu → Preferences → Settings... → Neovim Access
Link → Connections`, then install components with `NVDA menu → Tools → Neovim
Access Link: Install or update components...`.

Keys, `ssh-agent`, or an OpenSSH alias are recommended. Confirm host keys and
test the login visibly before relying on the add-on. Password mode is available
only when the server permits it; the password remains in memory and is passed
through the bundled askpass helper, not the command line.

The Linux plugin registers each Neovim independently. Multiple instances under
the same account, even in the same directory, remain distinct. An optional
`NVIM_NVDA_SESSION_NAME` environment variable or `:NvimNvdaSessionName` command
can provide a human-readable label. F12 remains the authoritative binding
signal.

Shell startup output before the bridge marker is discarded. After the marker,
stdout belongs exclusively to the protocol and diagnostics use stderr. SSH
forwardings are explicitly disabled for the bridge process.
