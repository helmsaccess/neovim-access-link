# Neovim Access Link — Quick Guide

This Quick Guide takes experienced NVDA users with limited Neovim experience
from installation to a confirmed first connection. See the
[User Manual](README.md) for complete operation.

Access Link supports Neovim in Windows Terminal, locally on Windows and
remotely on Linux over SSH. Multiple windows, tabs, and split panes can mix
local Neovim sessions, remote Neovim sessions, and ordinary shells. Other
terminal applications and graphical Neovim frontends are not supported.

The remote path uses Linux, Python 3, and OpenSSH. Rocky Linux 10.2 is
practically confirmed; other Linux systems are not practically confirmed.

## 1. Check the prerequisites

You need:

- Windows 11;
- NVDA 2026.1.x;
- Windows Terminal;
- Neovim 0.10.1 or later.

Open Windows Terminal and check the local installation:

```text
nvim.exe --version
```

For Neovim on Linux, you also need Python 3 on the Linux target, the Windows
OpenSSH client, and a working SSH login. Test that login before configuring
Access Link:

```text
ssh user@example.invalid
```

Keys, `ssh-agent`, an OpenSSH configuration, or a password requested by the
add-on are supported.

## 2. Install the add-on

1. Open `NeovimAccessLink-<version>.nvda-addon` on Windows.
2. Confirm installation in NVDA.
3. Restart NVDA.

After the restart, `NVDA menu > Preferences > Settings...` contains the
`Neovim Access Link` category.

## 3. Assign the activation gesture

1. Focus Windows Terminal.
2. Open `NVDA menu > Preferences > Input gestures...`.
3. Open the `Neovim Access Link` category.
4. Assign a convenient gesture to `Turn Neovim accessibility on or off and
   discover configured connections`.

Do not use `Ctrl+Alt+N` when that combination restarts NVDA in your
installation.

The assigned gesture is an **NVDA command**: NVDA processes it while Windows
Terminal is focused. `F12` is not the activation gesture. Access
Link passes F12 to Neovim and then uses the key press to identify the focused
Neovim session exactly.

## 4. Install the components

Close all affected Neovim instances before installation or update.

1. Open `NVDA menu > Tools > Neovim Access Link: Install or update
   components...`.
2. Select `This computer - local Neovim` for local Windows Neovim.
3. Select saved Linux connections for remote sessions.
4. Confirm with `OK`.
5. Check every selected target in the result dialog.

Access Link installs its bundled plugin copy in Neovim's standard data
directory. A simple Neovim configuration loads this start plugin on the next
Neovim start. A plugin manager that replaces Neovim's `packpath` or start
plugins must explicitly load the existing local copy. Do not install a second
Access Link copy from a plugin repository. The optional
[Lazy example](example-configuration.md) shows the required setup.

## 5. Optional: Save a Linux connection

Skip this section for local Windows Neovim.

1. Open `NVDA menu > Preferences > Settings... > Neovim Access Link`.
2. Open the `Connections` tab.
3. Select `Add connection...`.
4. Enter a connection name, server or SSH alias, and SSH port.
5. Enter the Linux username unless OpenSSH configuration supplies it.
6. Choose the sign-in method.
7. Confirm the form and then the NVDA settings dialog.
8. Install components for this connection as described in section 4.

`Use OpenSSH setup (recommended: keys, ssh-agent or SSH config)` uses your
normal Windows OpenSSH setup. `Ask for the SSH password when connecting
(password is not saved)` keeps the password in memory only until the current
NVDA process ends.

## 6. Connect the first session

### Local Windows session

1. Start `nvim.exe` in Windows Terminal.
2. Press the activation gesture assigned in section 3.
3. Wait for the message that local and saved connections are being checked or
   are ready.
4. Focus the intended Neovim and press F12 once.
5. Wait for the connection confirmation.

### Linux session over SSH

1. Sign in over SSH in the intended Windows Terminal tab or pane.
2. Start `nvim` on the Linux target.
3. Press the activation gesture and wait for the ready message.
4. Focus the intended Neovim and press F12 once.
5. Wait for the connection confirmation.

## 7. Confirm the connection in practice

Use an unimportant buffer:

1. Press `i`. Access Link reports Insert mode according to your settings.
2. Type a short line.
3. Press `Escape`. Access Link reports Normal mode.
4. Navigate by character with `h` and `l`, and by line with `j` and `k`.
   Neovim moves the cursor; Access Link speaks the semantic position and plays
   configured boundary sounds.
5. Hold the NVDA key and press `h` or `l`. Access Link reads characters without
   moving the real Neovim cursor. Releasing the NVDA key returns output to the
   real cursor.

The last two steps show the input layers: `h`, `j`, `k`, and `l` without the
NVDA key are normal Neovim commands. Access Link makes their effect accessible.
`NVDA+h`, `NVDA+j`, `NVDA+k`, and `NVDA+l` are contextual NVDA commands for
speech exploration.

## 8. Check tabs and panes

A Windows Terminal tab contains one terminal. A split tab contains several
panes and therefore several separate terminals.

1. Switch to another pane containing an ordinary shell. NVDA uses its normal
   terminal output there; Access Link does not take over Neovim key commands.
2. Switch back to the connected Neovim pane. Access Link restores structured
   output after the focus response is confirmed.
3. If needed, start Neovim in another tab or pane and press F12 there. The
   first association remains active.

## 9. If no connection is established

Check in this order:

1. Is Neovim running in Windows Terminal?
2. Is the activation gesture assigned, and did you press it before F12?
3. Did you fully restart Neovim after installing the components?
4. Does the Neovim configuration load the installed Access Link plugin?
5. For Linux, does the normal SSH login work outside the add-on?

Check the plugin inside Neovim:

```vim
:echo exists(':NvimNvdaSessionName')
```

Output `2` confirms that Neovim loaded the plugin. For any other result, close
all affected Neovim instances, update the components, and check the plugin
manager configuration.

`NVDA+Alt+D` copies the redacted diagnostic report. Before sharing it, still
check it for local paths, profile names, and SSH targets.

The first connection is now configured. The [User Manual](README.md) explains
Neovim basics, daily operation, Braille, completion, diagnostics, file
management, and all settings.
