# Component installation and SSH stdio

## Runtime model

Users install the Linux components without root under `~/.local` and then
start normal Neovim. For remote activation, the add-on starts a noninteractive
SSH process itself:

```text
ssh.exe -T -o BatchMode=yes <ssh-alias> nvim-nvda-bridge
```

Framed MessagePack uses standard output and controls use standard input. The
SSH process ends on deactivation or NVDA shutdown. There is no port forward,
fixed port, or shared application token.

## Rootless user package

`tools/build_user_package.py` creates a `tar.gz` from the versioned bridge,
protocol, and plugin sources with:

```text
bin/nvim-nvda-bridge
config/linux-components.json
share/nvim/site/pack/nvim-nvda/start/nvim-nvda/
install.py
```

The bridge is a Python zipapp with the protocol codec and portable MessagePack.
The archive is stored in the add-on as
`globalPlugins/NeovimAccessLink/resources/server-user.tar.gz`. The menu
installer transfers those exact bytes through SSH stdin; the target needs
Python 3 but no repository access, external download, RPM, or `sudo`.

`linux-components.json` keeps Neovim's session marker and NVDA's observed F12
gesture consistent. Changes are made in source, after which the add-on and
target components are rebuilt or updated together. Editing one installed copy
in isolation is unsupported.

## Session registry

The plugin starts a private Unix RPC socket with `serverstart()` and writes one
short-lived JSON record per Neovim instance in the private user runtime
directory. It contains only the process, time, endpoint, and session data
needed for discovery and validation. These files are unrelated to the Windows
Registry.

Interactive Neovim and a later noninteractive SSH process can see different
`XDG_RUNTIME_DIR` values. The bridge therefore checks the configured runtime
directory, user-owned `/run/user/UID`, and the private `/tmp` fallback. It
reads only private directories owned by the current user, deduplicates
identical records, and validates process, nonce, endpoint, owner, and protocol
before use.

## SSH stream and security

The bridge sends a fixed ASCII marker before the binary protocol. The Windows
client discards shell startup output before that marker; after it, stdout is
reserved for the protocol and diagnostics go to stderr.

- SSH authenticates host and user. Keys, an agent, or saved OpenSSH
  configuration are the standard path.
- `BatchMode=yes` prevents invisible password prompts in the NVDA process.
  For explicitly configured password authentication, the add-on uses an
  accessible dialog and does not store the password.
- `ClearAllForwardings=yes` prevents configured port forwards from being
  inherited.
- Installation, connection, and removal run outside NVDA's main thread and
  have time bounds.

## Installation and update

Connections are managed under “NVDA menu → Preferences → Settings… → Neovim
Access Link → Connections.” “Add connection…” records name, host or OpenSSH
alias, Linux user, port, optional key file, and authentication method.

“NVDA menu → Tools → Neovim Access Link: Install or update components…” offers
“This computer” and every saved Linux connection as an initially clear
multi-selection. Selected targets run in the background; a results summary
reports every success and failure. Locally, the plugin is replaced atomically
under `%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda`. Neovim
must be restarted after installation or update.

## Removal

“NVDA menu → Tools → Neovim Access Link: Remove components…” uses the same
multi-selection. Neovim must be closed on the selected targets; the add-on does
not stop a Neovim or tmux session.

Local removal deletes only the installed plugin directory. Over SSH, one
time-bounded user command removes only:

```text
~/.local/bin/nvim-nvda-bridge
~/.local/share/nvim/site/pack/nvim-nvda
~/.local/share/nvim-nvda
~/.cache/nvim-nvda-install
```

Removal is idempotent. Saved connections, SSH and Neovim configuration,
unrelated plugins, and runtime session data remain intact.

## Owning code and tests

Package construction and installation live in `tools/build_user_package.py`,
`packaging/install_user.py`, and the add-on installation services. Bridge entry
points live under `bridge/`, and session registration lives in the Neovim
plugin. Package, SSH, and socket tests run separately; see the [test
strategy](testing.md) for commands.
