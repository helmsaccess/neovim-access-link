# Neovim and Windows Terminal basics

This chapter explains only the terms and Neovim commands required by the
remaining Access Link workflows. It does not replace a general Neovim course.

## Understand Windows Terminal

Windows Terminal arranges terminals at three levels:

- A **window** is the complete Windows Terminal window.
- A **tab** is a tab inside that window.
- A **pane** is one split area inside a tab. Each pane is a separate terminal
  with its own content and focus.

An unsplit tab contains one terminal control. A split tab contains several
terminal controls, one per pane. Access Link stores the Neovim association for
each control separately. One pane can contain local Neovim, another can contain
Neovim over SSH, and a third can contain an ordinary shell.

When focus changes, Access Link checks the exact focused control. Only a
connected Neovim control receives structured output. A shell or unconnected
pane behaves like Windows Terminal without the add-on.

## Understand Neovim content

Neovim has its own structures inside one terminal control:

- A **buffer** contains text. It can belong to a file or have no filename yet.
- A **Neovim window** displays a buffer. Several Neovim windows can be visible
  in the same terminal control.
- A **Neovim tab** groups a layout of Neovim windows.

A Windows Terminal tab and a Neovim tab are therefore different things. This
manual uses the complete term whenever confusion is possible.

## Essential modes

Neovim responds differently according to its current mode:

| Mode | Purpose | Enter or return |
| --- | --- | --- |
| Normal mode | navigate and run commands | Neovim starts here; `Escape` returns here |
| Insert mode | enter text | `i` starts text input |
| Replace mode | overwrite existing text | `R` starts replacement |
| Visual mode | select text | `v` starts a characterwise selection |
| Select mode | replace a selection with subsequent input | normally entered by a mapping or plugin |
| Command-line mode | enter Ex commands | `:` opens the command line |
| Operator-pending mode | wait for the target of a command | for example after `d` or `c` |
| Terminal-Normal mode | navigate a terminal buffer with Neovim | `Ctrl+\`, then `Ctrl+n` |

Access Link presents supported mode changes semantically. The mode commands
themselves belong to Neovim.

## Complete a first safe edit

Start Neovim with an unimportant test file or without a filename:

1. Press `i`. Neovim enters Insert mode.
2. Type a short line.
3. Press `Escape`. Neovim returns to Normal mode.
4. Navigate by character with `h` and `l`, or by line with `j` and `k`.
5. Type `:w filename.txt` and press `Enter` to save a buffer that has no name.
6. Type `:q` and press `Enter` to exit Neovim.

For an existing file, `:w` saves under its current name. Neovim prevents `:q`
when unsaved changes remain.

## Key combination or key sequence

A plus sign means keys held together. `NVDA+Alt+D` is an NVDA command;
`Ctrl+w` is interpreted by Neovim or Windows Terminal according to context.

Commas or a directly written Neovim sequence mean keys pressed one after
another. `z=` opens Neovim spelling suggestions. `Space`, `l`, `s` requests LSP
status in the example configuration.

The NVDA key identifies the screen-reader layer. Without the NVDA key, input
remains with Neovim or Windows Terminal. Access Link observes Neovim's semantic
result and makes it accessible; it does not invent a second editor interface.

## Continue learning Neovim

Type `:Tutor` and press `Enter` to start Neovim's interactive course. Use
`:help nvim-intro` for Neovim's introduction. The
[official online help](https://neovim.io/doc/user/) contains the same basics
and further chapters.
