# Neovim Access Link — User Manual

Neovim Access Link provides NVDA with structured state from Neovim instead of
scraping the changing terminal screen. It can report mode, cursor movement,
editing, selections, indentation, completion, diagnostics, and other semantic
editor events. A contextual exploration mode can read characters, words, and
lines temporarily without moving Neovim's real cursor.

Supported today are local Windows `nvim.exe` and Linux Neovim over SSH in
Windows Terminal, including multiple windows, tabs, split panes, mixed Neovim
and ordinary shell panes, accounts, and tmux sessions. PuTTY, graphical Neovim
front ends, portable layouts, and automatic `NVIM_APPNAME` layouts are not
supported.

## Maturity and important Braille warning

The add-on is in an alpha-to-beta state. The main local and SSH connection
paths have been tested in practice, but not every documented editor feature has
been exercised extensively in every mode and configuration. Bugs and missing
feedback should be expected.

Development aims to test important workflows, security boundaries, and known
defects carefully. This is not a claim that every combination of editor
feature, plugin, terminal layout, and environment has been covered. Reported
defects are investigated and corrected as promptly as circumstances allow;
no fixed response or resolution time is promised.

Braille has not been tested with a physical Braille display and very likely
contains bugs. Braille is important, not optional to the project; practical
hardware testing and corrections are priority follow-up work. The current
documentation must not be read as a claim of reliable Braille support.

## Core concepts

- The **NVDA add-on** manages settings, connections, speech, Braille, sounds,
  and safe suppression of native terminal output.
- The **Neovim plugin** reads editor APIs and emits semantic events.
- The Linux **bridge** connects one registered Neovim instance to NVDA over
  SSH stdin/stdout. Local Windows Neovim connects directly over `127.0.0.1`.
- A saved **connection** describes a Linux SSH account, not a running editor.
- A **session** is one running Neovim instance.
- A **terminal binding** links exactly one Windows Terminal control—depending
  on the layout, a tab or pane—to one session.

## Normal operating model

Install the add-on and components, activate discovery, focus the desired
Neovim, then press F12. Neovim records a short silent claim and the add-on binds
the one changed session to the current tab. F12 is not activation and is not an
SSH profile. It is handled only in Windows Terminal and remains untouched in
other applications.

If automatic claiming is unsuitable, assign a gesture to “Choose a server and
connect this terminal to a new Neovim session”. Accessible dialogs show names
and working directories; internal IDs are never required.

## Security and failure behavior

Local RPC is bound only to IPv4 loopback `127.0.0.1`. Remote communication uses
SSH stdin/stdout and opens no extra listener. Passwords are not stored in the
profile or diagnostic report. Native terminal output is suppressed only for a
focused, authenticated, explicitly bound Neovim session. Deactivation,
disconnect, invalid state, or an unknown window fails open to normal NVDA
terminal output.

## Manual chapters

1. [Settings and connection profiles](settings.md)
2. [Communication, connections, and session binding](communication.md)
3. [SSH, tmux, and Neovim](ssh-and-tmux.md)
4. [Menus and completion](menus-and-completion.md)
5. [Embedded terminal and file managers](terminals-and-file-managers.md)
6. [Sounds and earcons](sounds.md)
7. [Braille support](braille.md)
8. [Troubleshooting and diagnostic report](troubleshooting.md)

Begin with the separate [Quick Guide](neovim-access-link-quick-guide-en.html)
and test in a disposable buffer before important work. Include character,
word, and line exploration while holding NVDA and verify that the real cursor
does not move.
