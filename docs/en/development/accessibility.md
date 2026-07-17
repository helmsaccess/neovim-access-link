# Feature and accessibility matrix

This matrix describes implemented, primarily automated behavior in an
alpha-to-beta build. It does not imply exhaustive practical verification.

Implemented areas include mode reporting; character/word/line navigation;
editing and deletion; Visual character/line/block selection; indentation;
completion and signature help; search, pairs, diagnostics and spelling; folds,
marks, registers and macros; command line; embedded terminal transitions; and
adapters for common file managers.

Speech and sounds are configurable where NVDA has no better native setting.
Confirmed session-focus presentation and an event-driven in-place buffer
switch are profile-selectable as silent, current structured line, or existing
file/special context with mode and connection name. Tab and window changes
retain their own announcements. Automatic destination cursor events cannot
replace the selected line with one character, and text changes are never
diffed across buffers. Insert/Normal sounds remain independently
governed by their existing feedback settings; direct terminal input uses the Insert cue and the return to
canonical `terminalNormal` uses one Normal cue. A freely assignable fixed,
correlated command leaves direct terminal input, while event-driven
`TermClose` reports process status. Command-line entry has a distinct short
600 Hz tone and return from it in a terminal context uses the Normal cue.
Creating a buffer with `:terminal` uses the configured focus presentation and
coalesces its asynchronous first line with the automatic cursor event. Direct
terminal entry presents the complete cursor line and retains the Insert cue.
Exact `:bd` on a running terminal job reports `E89` guidance without forcing
`:bd!`; no-op navigation reports that no other listed buffer exists.
Command-line echo uses its own UTF-8 byte position, and command-line mode plus
non-empty ordinary messages following a command are covered by built-add-on
and real-TUI tests. Structured command-line type distinguishes Ex commands
from search; recognized buffer-command return speech is coalesced into the
configured destination presentation while its cue remains independent. Pager variants and
practical Windows/NVDA acceptance remain open.
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
