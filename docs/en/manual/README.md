# Neovim Access Link — User Manual

Neovim Access Link provides NVDA with structured state from Neovim instead of
scraping the changing terminal screen. It can report mode, cursor movement,
editing, selections, indentation, completion, diagnostics, and other semantic
editor events. Speech exploration mode can read characters, words, and lines
temporarily without moving Neovim's real cursor.

Supported today are local Windows `nvim.exe` and Linux Neovim over SSH in
Windows Terminal, including multiple windows, tabs, split panes, mixed Neovim
and ordinary shell panes, accounts, and tmux sessions. PuTTY, graphical Neovim
front ends, portable layouts, and automatic `NVIM_APPNAME` layouts are not
supported.

Advanced [Braille support](braille.md) presents structured editor lines
instead of terminal fragments. It includes routing in Normal, Insert, and
command-line modes, the insertion position after the final character,
automatic following on long lines, Braille display navigation controls, and
an independent Braille exploration mode.

## Maturity

The add-on is beta software. Defects, incomplete feedback, and changes to its
operation remain possible. Keep normal backups and introduce the add-on
gradually with your own NVDA, Neovim, and terminal configuration before
relying on it for important work.

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
2. [Speech exploration mode](speech-exploration.md)
3. [Communication, connections, and session binding](communication.md)
4. [SSH, tmux, and Neovim](ssh-and-tmux.md)
5. [Setting up LSP, auto-completion, and linters](language-tools.md)
6. [Small Python configuration with Lazy and Oil](example-configuration.md)
7. [Menus and completion](menus-and-completion.md)
8. [Embedded terminal and file managers](terminals-and-file-managers.md)
9. [Sounds and earcons](sounds.md)
10. [Braille support](braille.md)
11. [Troubleshooting and diagnostic report](troubleshooting.md)

Begin with the separate [Quick Guide](neovim-access-link-quick-guide-en.html)
and use a disposable buffer before important work. Include character, word,
and line speech exploration while holding NVDA and verify that the real cursor
does not move.
