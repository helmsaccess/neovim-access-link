# Command reference

This reference separates NVDA commands from Neovim commands. For assignable
NVDA commands, first focus Windows Terminal and then open
`NVDA menu > Preferences > Input gestures... > Neovim Access Link`.

## NVDA commands with fixed gestures

These combinations contain the NVDA key. Access Link takes them over only in
the stated connected Neovim context. In other applications, shells, and
unconnected panes, NVDA's normal commands apply.

| Gesture | Context | Function |
| --- | --- | --- |
| `NVDA+Alt+D` | Windows Terminal | copy the redacted diagnostic report |
| `NVDA+h` / `NVDA+l` | connected Neovim pane | explore previous / next character |
| `Shift+NVDA+h` / `Shift+NVDA+l` | connected Neovim pane | explore previous / next word |
| `NVDA+k` / `NVDA+j` | connected Neovim pane | explore previous / next line |
| `NVDA+Space`, continue holding NVDA | position with signature help | show signatures and parameters |
| `NVDA+Shift+Space`, continue holding NVDA | position or line with diagnostics | show diagnostics |
| `NVDA+j` / `NVDA+k` while a `z=` list is open | spelling suggestions | show next / previous suggestion |
| `NVDA+Enter` with a selected suggestion | spelling suggestions | accept the suggestion |

In a held signature view, `NVDA+h` and `NVDA+l` move between parameters, while
`NVDA+k` and `NVDA+j` move between signatures. In a held diagnostic view,
`NVDA+k` and `NVDA+j` move between diagnostics. Releasing the NVDA key closes
the temporary view.

## Assignable NVDA commands

These commands have no default gesture:

| UI name | Function |
| --- | --- |
| `Turn Neovim accessibility on or off and discover configured connections` | enable or disable the service |
| `Toggle Braille navigation between Braille cursor mode and Braille exploration mode` | change the Braille mode for the current session |
| `Read documentation for the selected Neovim completion item or LSP hover` | present available completion or hover documentation |
| `Copy the active Neovim Visual selection to the Windows clipboard` | copy the current Visual selection |
| `Copy Neovim's last yank to the Windows clipboard` | copy Neovim register 0 |
| `Paste Windows clipboard text into the active Neovim buffer` | insert text at the Neovim position |
| `Store Windows clipboard text in Neovim's unnamed register` | make text available to Neovim's `p` command |
| `Leave direct input in the active Neovim terminal` | change from direct terminal input to Terminal-Normal mode |
| `Choose a server and connect this terminal to a new Neovim session` | open the accessible session dialog |
| `Disconnect the selected Neovim connection instance` | end the Access Link connection |
| `Forget the temporary Neovim connection for the focused terminal` | remove the remembered tab association |

Before every execution, Access Link checks an assignable command against the
focused Windows Terminal application, exact control, and active Neovim
association.

## F12 association

F12 is not an NVDA command and is not the activation gesture. Windows Terminal
and Neovim receive the key normally. The Neovim plugin marks the current
session; the enabled Access Link service then uses this fresh match for the
association.

## Common Neovim commands

These inputs do not contain the NVDA key. Neovim executes them; Access Link
presents their semantic effect.

| Input | Neovim function |
| --- | --- |
| `i` | enter Insert mode |
| `Escape` | return to Normal mode or cancel a Neovim prompt |
| `h`, `j`, `k`, `l` | move left, down, up, right |
| `w` / `b` | move to the next / previous word |
| `0` / `$` | move to the beginning / end of the line |
| `gg` / `G` | move to the beginning / end of the file |
| `v` | begin a Visual selection |
| `y` | yank a selection in Neovim |
| `p` | paste a Neovim register |
| `z=` | open spelling suggestions for the current word |
| `:w` | save the buffer |
| `:q` | close the Neovim window when no unsaved changes remain |
| `:terminal` | open a terminal buffer |
| `Ctrl+\`, then `Ctrl+n` | leave direct terminal input |

See `:Tutor`, `:help quickref`, and the
[official Neovim help](https://neovim.io/doc/user/) for more Neovim commands.
