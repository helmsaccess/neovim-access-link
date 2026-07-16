# Feature and accessibility matrix

This matrix describes implemented, primarily automated behavior in an
alpha-to-beta build. It does not imply exhaustive practical verification.

Implemented areas include mode reporting; character/word/line navigation;
editing and deletion; Visual character/line/block selection; indentation;
completion and signature help; search, pairs, diagnostics and spelling; folds,
marks, registers and macros; command line; embedded terminal transitions; and
adapters for common file managers.

Speech and sounds are configurable where NVDA has no better native setting.
Confirmed session-focus presentation is profile-selectable as silent, current
structured line, or existing file/special context with mode and connection
name. Insert/Normal sounds remain independently governed by their existing
feedback settings.
Explicit copy/paste uses four freely assignable NVDA commands and correlated
Neovim controls for the Visual selection, register 0, `nvim_paste`, and fixed
register 0 as the unnamed paste register's backing store.
Protocol, Lua, bridge, and built-add-on coverage exists; practical local/SSH
acceptance of the extended register command remains pending.
Multiple bound sessions are isolated by process, window handle, complete UIA
runtime identity, session, sequence, and structured focus validation. Exact
one-shot, control-specific physical F12 proofs and switching between
independently bound windows, tabs, and panes have automated negative coverage. Unknown controls and failures remain
fail open. Local/SSH tabs and horizontal/vertical split panes are practically
confirmed; separate windows and the complete unbound-shell-pane negative matrix
remain pending.

Braille state, indentation, selection dots 7/8, and routing are implemented in
the model and automated tests, but no physical display has been tested. Bugs
are very likely. Hardware coverage and fixes are explicitly important priority
work before reliable Braille support can be claimed.
