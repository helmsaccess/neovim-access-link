# Manual: Communication, connections, and session binding

## Term: file-based session registry

“Registry” in this documentation never means the Windows Registry. Neovim
Access Link neither reads nor writes `HKCU` or `HKLM` and creates no Windows
Registry keys. It means only a plugin-managed directory of short-lived JSON
session records:

- on Windows, normally
  `%LOCALAPPDATA%\nvim-nvda\sessions\<PID>-<nonce>.json`;
- on Linux,
  `$XDG_RUNTIME_DIR/nvim-nvda/sessions/<PID>-<nonce>.json`, with a private
  per-user directory below `/tmp` as fallback.

These files contain only the session and endpoint metadata needed for
discovery and F12 binding. They do not store a Windows Terminal window, tab,
or pane mapping. The NVDA add-on keeps that binding only in memory for its
current runtime.

## What activation does

Activation turns the shared service on or off. When turning it on, it starts a bounded background inventory. It reads local registered
sessions and queries saved SSH targets that can be reached without opening a
password dialog. It does not immediately create permanent connections to every
target. Wait for the ready message before pressing F12. While the service is
enabled, each physical F12 press authorizes one pairing attempt for the exact
focused control's complete UIA identity. The activation command remains the
global off switch even when an unbound control has focus.

## What F12 does

The physical F12 press itself is the exact, one-shot authorization. In unbound
shells, file managers, and other controls, F12 remains an ordinary key. A
single claim check may run in response to that explicit action, but without a
fresh Neovim claim it remains silent and creates no dialog, binding, or
suppression. F12 is
forwarded to Windows Terminal and Neovim first. The plugin increments a
monotonic claim value in its private JSON session record without displaying a
message. The add-on compares that value with its activation baseline:

- one changed session is connected;
- multiple real changes produce an accessible choice;
- no change produces no guessed connection.

Titles, terminal text, current directory, user name, and wall-clock
synchronization are not used. Each additional window, tab, or pane is claimed
independently with its own physical F12 press.

## Local Windows path

The plugin starts a dynamic Neovim RPC endpoint bound exactly to `127.0.0.1`
and records it in a short-lived JSON session file below
`%LOCALAPPDATA%\nvim-nvda\sessions`. This does not use the Windows Registry.
After a claim, the add-on opens
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
binding. On window, tab, or pane changes, suppression is cleared immediately.
Only the instance bound to the focused control receives a correlated context
request; its matching authenticated response may restore speech, Braille,
sounds, and suppression. Stale, unbound, and previously focused instance events
are ignored.

Disconnect, timeout, invalid sequence, deactivation, or loss of focus clears
the gate and restores normal terminal output. The add-on never suppresses an
unknown application or an unbound tab.

## Explore text without moving Neovim's cursor

In a connected and confirmed Neovim control, hold the NVDA key and use these
fixed reading commands:

| Key | Virtual reading movement |
|---|---|
| `NVDA+h` / `NVDA+l` | previous / next character |
| `NVDA+k` / `NVDA+j` | previous / next line |
| `Shift+NVDA+h` / `Shift+NVDA+l` | previous / next word |

The first command starts at the real cursor. Further commands move only an
ephemeral reading position; the buffer, mode, view, and real cursor do not
change. Releasing NVDA reads the current character, or the current word or
line followed by its cursor character, according to the last-used unit. This
matches normal navigation feedback. During character exploration, a short
two-note cue marks a return to the real cursor position. The same cue marks a
return to the original word or line during word or line exploration. It
follows the configured line-boundary sound feedback.

The commands apply in Neovim's Normal, Insert, Visual, command-line, and
embedded-terminal contexts, but only in the exact focused, authenticated
Neovim pane. The same keys retain normal NVDA behavior in a shell, an unbound
pane, another tab, or another application. After installing a build that adds
this feature, update the Neovim components and restart running Neovim
instances.

## Manual selection

Focus Windows Terminal, then assign “Choose a server and connect this terminal
to a new Neovim session” in `NVDA menu → Preferences → Input gestures...`.
Use it for password profiles or
when automatic inventory cannot see the intended target. Choose the target,
focus the intended Neovim in the same control, and press F12. A session choice
appears only if multiple fresh matches genuinely remain.
