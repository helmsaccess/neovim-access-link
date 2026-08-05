# Use SSH and tmux

The remote Access Link path connects Windows Terminal to Neovim on a Linux
target. The practically confirmed target is Rocky Linux 10.2 with Python 3 and
OpenSSH.

## Prerequisites

First test a normal login in Windows Terminal:

```text
ssh user@example.invalid
```

Confirm host keys and configure keys, `ssh-agent`, OpenSSH configuration, or
permitted password login before enabling Access Link. The add-on changes
neither Windows OpenSSH configuration nor `sshd_config` on the Linux target.

## Configure a Linux connection

1. Open `NVDA menu > Preferences > Settings... > Neovim Access Link`.
2. Open `Connections` and select `Add connection...`.
3. Enter the SSH target, account, port, and sign-in method.
4. Confirm the settings dialog.
5. Close running Neovim instances on that target.
6. Open `NVDA menu > Tools > Neovim Access Link: Install or update
   components...`.
7. Select the saved connection and check the result.

Installation places the plugin and bridge in the Linux account's home
directory and requires no root privileges.

## Connect a remote session

1. Sign in over SSH in the intended Windows Terminal tab or pane.
2. Start `nvim` on the Linux target.
3. Press the assigned Access Link activation gesture.
4. Wait for the ready message.
5. Focus Neovim and press F12 once.
6. Wait for connection confirmation.

The visible SSH session carries your shell and keyboard input. Separately,
Access Link opens its own SSH connection to the bridge for accessibility data.
The Linux computer opens no additional network port for this connection.

## Use tmux

Start tmux in the visible SSH session and then start Neovim:

```text
tmux new -s work
nvim
```

Access Link associates the concrete Neovim instance, not the tmux window. A
Neovim session inside tmux remains active when the visible SSH session ends.
After attaching again, focus its pane; Access Link restores a remembered
association after focus is confirmed. Press F12 again when no remembered
association exists.

Several Neovim instances inside tmux are separate Access Link sessions. Use
descriptive session names for similar working directories:

```text
NVIM_NVDA_SESSION_NAME=Backend nvim
NVIM_NVDA_SESSION_NAME=Documentation nvim
```

## Connection loss

When the background connection ends, Access Link releases native Windows
Terminal output. The visible SSH session and Neovim in tmux do not end as a
result.

Restore normal SSH access first. Then enable Access Link again and press F12 in
the intended Neovim pane. See [Troubleshooting](troubleshooting.md) for more
checks.
