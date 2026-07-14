# Neovim Access Link — Quick Guide

This guide covers the current alpha-to-beta build for NVDA 2026.1.x on Windows
11. Neovim is supported in Windows Terminal, either as local `nvim.exe` or on
Linux through SSH. Multiple tabs, windows, remote accounts, and tmux sessions
can be used.

> Not every feature has received extensive practical testing. Braille has not
> been tested with a physical Braille display and very likely contains bugs.
> Braille is important to the project and hardware testing and fixes are a
> priority, but reliable Braille support is not claimed yet.

## Requirements

- Windows 11, NVDA 2026.1.x, Windows Terminal, and Neovim 0.10.1 or newer.
- For Linux: Python 3, Windows OpenSSH, and a working SSH login. Keys,
  `ssh-agent`, or an SSH alias are recommended; an accessible password prompt
  is also available.

## Install the add-on and assign activation

1. Open `nvimNvdaAccess-<version>.nvda-addon`, confirm installation, and
   restart NVDA.
2. Open `NVDA menu → Preferences → Input gestures...`.
3. Under “Neovim Access Link”, assign a convenient gesture to “Turn Neovim
   accessibility on or off and discover configured connections”.

Do not use F12 as the activation gesture. F12 identifies the currently focused
Neovim session after activation. `Ctrl+Alt+N` may already start NVDA.

## Install or update components

Close running Neovim instances first, then:

1. Open `NVDA menu → Tools → Neovim Access Link: Install or update
   components...`.
2. Select “This computer” for local Windows Neovim and select any saved Linux
   connections that should be updated. Nothing is selected initially.
3. Press OK, review the success/failure summary, and restart Neovim.

The add-on contains the plugin, bridge, and configuration. Linux installation
uses `~/.local`, requires no root privileges, and downloads nothing at runtime.

## Add a Linux connection

This step is not needed for local Windows Neovim.

1. Open `NVDA menu → Preferences → Settings... → Neovim Access Link`.
2. On “Connections”, choose “Add connection”.
3. Enter a descriptive name, server or SSH alias, Linux user, and port.
4. Prefer “Use OpenSSH setup” for normal SSH configuration, keys, and
   `ssh-agent`. Alternatively choose “Ask for the SSH password”; the password
   is kept only for the current NVDA run.
5. Save the settings and install the Linux components as described above.

Verify the same login in Windows Terminal first, for example:

```text
ssh user@example.invalid
```

## Make the first connection

1. Start Neovim in Windows Terminal: local `nvim.exe`, or `nvim` inside the
   intended SSH/tmux session.
2. Press the activation gesture and wait for the ready message.
3. Focus the intended Neovim and press F12 once.
4. Wait up to two seconds for confirmation.

Repeat F12 in each additional tab that should be connected. F12 is forwarded
to Neovim first; it does not choose by title, terminal text, account, or current
directory. For special cases assign a gesture to “Choose a server and connect
this terminal to a new Neovim session”.

## First safety check

Use a disposable buffer. Check Insert, Normal, and Visual modes, navigation,
editing, tab switching, and deactivation. After deactivation or a disconnect,
normal NVDA terminal output must return. Do not begin important work until the
configuration has behaved correctly for you.

See the [full manual](neovim-access-link-handbook-en.html) for settings,
communication details, and troubleshooting.
