# Manual: Communication, connections, and session binding

## What activation does

Activation starts a bounded background inventory. It reads local registered
sessions and queries saved SSH targets that can be reached without opening a
password dialog. It does not immediately create permanent connections to every
target. Wait for the ready message before pressing F12.

## What F12 does

F12 is forwarded to Windows Terminal and Neovim first. The plugin increments a
monotonic claim value in its private session registry without displaying a
message. The add-on compares that value with its activation baseline:

- one changed session is connected;
- multiple real changes produce an accessible choice;
- no change produces no guessed connection.

Titles, terminal text, current directory, user name, and wall-clock
synchronization are not used. Each additional tab is claimed independently.

## Local Windows path

The plugin starts a dynamic Neovim RPC endpoint bound exactly to `127.0.0.1`
and records it under `%LOCALAPPDATA%\nvim-nvda`. After a claim, the add-on opens
a dedicated background RPC client for that one session. No fixed port,
`nvim --listen`, wrapper, SSH process, or administrator privilege is required.

## Remote Linux path

The interactive SSH window is the user's visible terminal session and may
contain tmux and Neovim. After a claim, the add-on starts a separate hidden
Windows OpenSSH process running `nvim-nvda-bridge --session ...`. The bridge
connects to the selected private Unix RPC socket and sends bounded protocol-v2
events over SSH stdout; control travels over stdin. Closing the interactive SSH
window and stopping the bridge connection are separate operations.

## Switching and failure

Each runtime connection has its own client, state, sequence, and terminal
binding. On tab changes, only the instance bound to the focused tab may reach
speech, Braille, sounds, or terminal suppression. Stale and unbound events are
ignored and a fresh full state is requested when required.

Disconnect, timeout, invalid sequence, deactivation, or loss of focus clears
the gate and restores normal terminal output. The add-on never suppresses an
unknown application or an unbound tab.

## Manual selection

Assign “Choose a server and connect this terminal to a new Neovim session” in
`NVDA menu → Preferences → Input gestures...`. Use it for password profiles or
when automatic inventory cannot see the intended target. Choose the target and
then, if necessary, the session by name and working directory.
