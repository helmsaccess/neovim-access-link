# Connection, first editing session, and session switching

Installation, activation, and connection are separate steps:

1. The component command installs the Neovim plugin and, for Linux, the bridge.
2. `NVDA+Alt+N` enables the Access Link service and finds reachable sessions.
3. F12 associates the focused Windows Terminal control with the currently
   focused Neovim session.

An installed component is therefore not yet a running connection.

## Activation and F12

The default `NVDA+Alt+N` gesture is an NVDA command. NVDA runs it while Windows
Terminal is focused. You can assign a different gesture in NVDA's Input
Gestures dialog.

F12 belongs to the normal Windows Terminal and Neovim keyboard path. Access
Link does not block it: Neovim receives the key and briefly marks the current
session. Access Link then connects exactly that new match to the focused
control. F12 does not turn the add-on on or off.

Press F12 once and wait for confirmation. Several rapid presses start several
separate selection attempts.

## Complete the first editing session

After connection, Neovim supplies the current buffer, mode, cursor, and other
semantic state. Begin in an unimportant buffer:

1. Press `i`, type text, and press `Escape`.
2. Navigate in Normal mode with `h`, `j`, `k`, and `l`.
3. Save with `:w` or `:w filename`.
4. Test a selection with `v` and movement commands.
5. Switch to another shell pane and back.
6. Press the activation gesture again to disable Access Link.

`i`, `Escape`, `h`, `j`, `k`, `l`, `v`, and `:w` are Neovim commands. Neovim
changes the mode, cursor, selection, or file. Access Link makes those changes
accessible.

Key combinations containing the NVDA key belong to the screen-reader layer.
Examples are `NVDA+h` for speech exploration and `NVDA+Alt+D` for the
diagnostic report. Access Link takes over these commands only in the documented
exact connected Neovim context.

## Transfer text between Neovim and Windows

The Access Link clipboard commands have no default gestures. First focus
Windows Terminal, then assign your own gestures to the required commands under
`NVDA menu > Preferences > Input gestures... > Neovim Access Link`. Four paths
are then available in a connected local or remote Neovim session:

- Start a Visual selection with `v`, then use
  `Copy the active Neovim Visual selection to the Windows clipboard`.
- Yank text with Neovim's `y`, then use
  `Copy Neovim's last yank to the Windows clipboard`.
- Use `Paste Windows clipboard text into the active Neovim buffer` to insert
  text directly into an editable ordinary buffer in Normal or Insert mode.
- Use `Store Windows clipboard text in Neovim's unnamed register`, followed by
  Neovim's `p`, when Neovim should perform the insertion as an ordinary
  register command.

Before every execution, Access Link checks the focused pane and its active
Neovim association again. Copy and paste feedback follows the
[output settings](settings.md#feedback).

## Switch between tabs and panes

A Windows Terminal pane is a separate terminal control. Access Link keeps a
separate association for each control:

- A connected Neovim pane receives structured output.
- An unconnected Neovim pane keeps NVDA's native terminal output until you
  press F12 there.
- A shell pane remains entirely on NVDA's native terminal output.
- An embedded Neovim terminal buffer also uses native terminal output during
  direct input.

After focus changes, Access Link restores an existing association only after a
matching response from its Neovim session. Native terminal output remains
active until that confirmation. State from the previously focused pane is
therefore not presented in the new pane.

## Connect more sessions

Start Neovim in another window, tab, or pane and press F12 there. Existing
connected controls remain active. Local and remote sessions can be mixed in
the same Windows Terminal window.

When several sessions have similar names, the manual connection dialog shows
the connection name, working directory, and existing association. For more
orientation, set a session name before starting Neovim:

```text
NVIM_NVDA_SESSION_NAME=Documentation nvim
```

In PowerShell:

```powershell
$env:NVIM_NVDA_SESSION_NAME = "Documentation"
nvim.exe
```

The name is only an aid for selection and does not change Neovim's working
directory.

## Remember or manually select an association

Access Link automatically remembers a successful F12 association for the
concrete Windows Terminal control until NVDA or Windows Terminal exits. The
association remains runtime-only and is not stored in the NVDA profile. On a
later tab or pane switch, Access Link restores the matching running session
only after focus is confirmed.

The following assignable commands are available under
`NVDA menu > Preferences > Input gestures... > Neovim Access Link`:

- `Choose a server and connect this terminal to a new Neovim session`;
- `Disconnect the selected Neovim connection instance`;
- `Forget the temporary Neovim connection for the focused terminal`.

The first command opens the accessible selection dialog when F12 does not
produce one exact match. Disconnect ends the selected Access Link connection,
not Neovim or SSH. Forget removes only the remembered tab association for the
current NVDA process.

## Local and remote connections

Local Windows Neovim connects only through the local computer. Remote Neovim
uses two independent SSH connections:

- The visible Windows Terminal session remains your ordinary shell and carries
  your keyboard input.
- Access Link opens a separate background SSH connection to the installed
  bridge and transfers only bounded accessibility data through it.

The bridge opens no additional network service on Linux. Access Link stores no
passwords. A password profile keeps the password in memory only for the
current NVDA process.

## Disconnection and error behavior

Access Link suppresses native terminal output only for an active,
authenticated, and focused Neovim association. When support is disabled, the
transport ends, data is invalid, focus is uncertain, or the control is
unknown, NVDA's native terminal output remains or becomes active.

Suppression never applies to an entire Windows Terminal window. A failure in
one session does not change any other pane association.

See [Troubleshooting](troubleshooting.md) for symptoms and checks. See the
[Command reference](commands.md) for the complete command list.
