# Neovim Access Link — Quick Guide

This guide covers the current alpha-to-beta build for NVDA 2026.1.x on Windows
11. Neovim is supported in Windows Terminal, either as local `nvim.exe` or on
Linux through SSH. Multiple tabs, windows, remote accounts, and tmux sessions
can be used.

> Not every feature has received extensive practical testing. Braille has not
> been tested with a physical Braille display and very likely contains bugs.
> Braille is important to the project and hardware testing and fixes are a
> priority, but reliable Braille support is not claimed yet.

The documented reference workflows are checked on a best-effort basis; this
does not mean every possible configuration has already been covered. Report
defects with a reviewed, redacted diagnostic report so they can be investigated
as promptly as circumstances allow.

## Requirements

- Windows 11, NVDA 2026.1.x, Windows Terminal, and Neovim 0.10.1 or newer.
- For Linux: Python 3, Windows OpenSSH, and a working SSH login. Keys,
  `ssh-agent`, or an SSH alias are recommended; an accessible password prompt
  is also available.

## Install the add-on and assign activation

If upgrading from a build with the former internal ID `nvimNvdaAccess`, first
uninstall that old add-on and restart NVDA. Otherwise both Global Plugins may
load. Old settings and gesture assignments are not imported.

1. Open `NeovimAccessLink-<version>.nvda-addon`, confirm installation, and
   restart NVDA.
2. Focus any Windows Terminal control, then open
   `NVDA menu → Preferences → Input gestures...`.
3. Under “Neovim Access Link”, assign a convenient gesture to “Turn Neovim
   accessibility on or off and discover configured connections”.

NVDA initially lists the unassigned commands when Windows Terminal was focused
before the dialog opened. After a gesture has been assigned and Windows
Terminal's AppModule has loaded, NVDA may continue listing that saved mapping
from other applications until NVDA restarts. This is only how NVDA presents
its user gesture map: the command is resolved only while a Windows Terminal
control has focus, so it cannot displace another NVDA command in an unrelated
application. After upgrading from an earlier feature build that stored these
commands under the Global Plugin, assign the desired gestures once again.

Do not use F12 as the activation gesture. F12 identifies the currently focused
Neovim session after activation. `Ctrl+Alt+N` may already start NVDA.

The same input-gesture category contains four more commands without default
gestures: copy the active Neovim Visual selection, copy Neovim register 0 (the
last yank), paste Windows clipboard text into the active Neovim buffer, and
store Windows clipboard text in Neovim's current unnamed register for later
use with `p`.
Assign gestures only if needed. These commands affect only the explicitly bound
and currently focused Neovim session; normal Windows Terminal copy and paste is
unchanged.

## Install or update components

Close running Neovim instances first, then:

1. Open `NVDA menu → Tools → Neovim Access Link: Install or update
   components...`.
2. Select “This computer” for local Windows Neovim and select any saved Linux
   connections that should be updated. Nothing is selected initially.
3. Press OK, review the success/failure summary, and restart Neovim.

The add-on contains the plugin, bridge, and configuration. Linux installation
uses `~/.local`, requires no root privileges, and downloads nothing at runtime.

To remove the components completely, first close Neovim on the intended
targets and open `NVDA menu → Tools → Neovim Access Link: Remove
components...`. Explicitly select targets as for installation and review the
summary. Saved connections, Neovim and SSH configuration, and other plugins
remain intact.

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

For each additional window, tab, or pane, focus its Neovim and press F12 once
while the service remains enabled. Existing connections continue running. Each
physical F12 press authorizes one pairing attempt for exactly the focused
terminal control. F12 is forwarded to Neovim first; it does not choose by
title, terminal text, account, or current directory. Without a fresh Neovim
claim, the attempt stays silent and creates no binding, dialog, or suppression.
For special cases assign a gesture to “Choose a server and connect this terminal
to a new Neovim session”; after choosing the target, press F12 in Neovim.

Switching among already bound windows, tabs, and panes needs no new F12. Native
terminal output remains available until the matching authenticated connection
answers the newly focused control's context request.

The activation gesture turns the shared service on or off from any focused
Windows Terminal control.

To explore without moving Neovim's cursor, hold NVDA and use `h/l` for
characters, `k/j` for lines, or `Shift+h/l` for words. Releasing NVDA reads
the same unit at the real cursor. These fixed commands apply only in the exact
connected Neovim pane; NVDA remains unchanged in shells and other tabs or
panes.

## First safety check

Use a disposable buffer. Check Insert, Normal, and Visual modes, navigation,
editing, tab switching, and deactivation. After deactivation or a disconnect,
normal NVDA terminal output must return. Do not begin important work until the
configuration has behaved correctly for you.

See the [full manual](neovim-access-link-handbook-en.html) for settings,
communication details, and troubleshooting.
