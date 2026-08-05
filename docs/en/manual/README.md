# Neovim Access Link — User Manual

Neovim Access Link connects Neovim in Windows Terminal to NVDA. The add-on
receives structured information directly from Neovim and presents modes,
cursor movement, text changes, selections, indentation, completion, and
diagnostics through speech, sounds, and Braille.

This manual is for experienced NVDA users who are learning Neovim or want to
use Access Link productively. Use the [Quick Guide](quick-guide.md) for the
first installation and connection.

## Supported workflow

Access Link currently supports:

- local `nvim.exe` in Windows Terminal;
- Neovim on Linux over SSH;
- Normal, Insert, Replace, Visual, Select, Operator-pending, and Command-line
  modes;
- Neovim Terminal-Normal mode and native terminal output during direct
  terminal input;
- multiple Windows Terminal windows, tabs, and split panes;
- parallel local and remote Neovim sessions alongside ordinary shell panes;
- tmux inside an SSH session;
- structured speech and Braille, speech exploration, completion, LSP,
  diagnostics, and Neovim spelling suggestions;
- file management with Oil; other file managers have automatically tested
  adapters.

The practically confirmed reference environment uses Windows 11 25H2,
NVDA 2026.1.1, Windows Terminal 1.24.x, and Neovim 0.10.1 or 0.12.3. The
remote path is confirmed on Rocky Linux 10.2. See the
[compatibility overview](../development/compatibility.md) for the complete
evidence and remaining test coverage.

Other terminal applications, graphical Neovim frontends, portable Windows
installations, and data directories separated with `NVIM_APPNAME` are not
supported.

## Maturity

The add-on is beta. The documented reference workflows have practical or
automated coverage, but the combinations of NVDA configuration, Braille
hardware, Neovim versions, and plugins are not exhaustively covered. Use
normal version control or backups for important files.

## How Access Link works

The NVDA add-on runs on Windows. A Neovim plugin supplies semantic editor
state. For a remote session, a small bridge carries that state through a
separate SSH connection.

An Access Link session is one running Neovim instance. Access Link associates
exactly one focused Windows Terminal control with exactly one session. A
control is the content of a tab or one pane. Connected Neovim panes and normal
shell panes in the same Windows Terminal window therefore remain independent.

This is a central strength of the add-on: one Windows Terminal tab can contain
several panes, and each pane behaves like a separate terminal. You can switch
between local Neovim sessions, remote SSH sessions, and ordinary shells.
Access Link takes over only the exact connected and focused Neovim pane. Every
other pane keeps NVDA's normal terminal behavior.

When support is disabled, the connection ends, data is invalid, or the
association cannot be confirmed exactly, Access Link does not suppress
terminal output. NVDA fails open to its normal terminal behavior.

## Two kinds of keyboard input

This manual distinguishes two separate input layers:

- **NVDA key combinations** include the NVDA key, such as `NVDA+Alt+D` or
  `NVDA+h`. NVDA resolves these combinations. Access Link takes them over only
  in the documented connected Neovim context. Outside that context, NVDA's
  normal commands apply.
- **Neovim commands** do not contain the NVDA key, such as `i`, `Escape`, `w`,
  `z=`, or `:w`. Neovim executes these inputs. Access Link does not replace
  their function; it makes their result, mode, and cursor movement accessible.

A plus sign means that keys are held together: `NVDA+Alt+D`. A sequence
separated by commas means that keys are pressed one after another: `Space`,
`l`, `s`. Neovim's `z=` also means two keys pressed in sequence.

## Recommended reading order

1. [Neovim and Windows Terminal basics](basics.md)
2. [Connection, first editing session, and session switching](communication.md)
3. [Speech exploration mode](speech-exploration.md)
4. [Braille support](braille.md)
5. [Menus, completion, and diagnostics](menus-and-completion.md)
6. [Embedded terminal and file managers](terminals-and-file-managers.md)
7. [SSH and tmux](ssh-and-tmux.md)
8. [Set up LSP, completion, and linters](language-tools.md)
9. [Optional example configuration with Lazy and Oil](example-configuration.md)
10. [Command reference](commands.md)
11. [Settings reference](settings.md)
12. [Sounds and earcons](sounds.md)
13. [Troubleshooting](troubleshooting.md)

Learn general Neovim operation with `:Tutor`. Neovim's
[official help](https://neovim.io/doc/user/) also provides `nvim-intro`, its
task-oriented user manual, and the complete command reference.
