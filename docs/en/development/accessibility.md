# Feature and accessibility matrix

This matrix describes implemented, primarily automated behavior in an
alpha-to-beta build. It does not imply exhaustive practical verification.

Implemented areas include mode reporting; character/word/line navigation;
editing and deletion; Visual character/line/block selection; indentation;
completion and signature help; search, pairs, diagnostics and spelling; folds,
marks, registers and macros; command line; embedded terminal transitions; and
adapters for common file managers.

File-manager adapter names, paths, roots, and types are byte-bounded only at
validated UTF-8 code-point boundaries. Public plugin events now report real
same-entry state changes with distinct mark, Copy, Cut, expansion, and clear
semantics; equal state, inactive targets, and render bursts are suppressed or
coalesced without polling. Typed action results use proven public completion
events, basename-only minimization, target revalidation, and synchronous batch
coalescing. Automated netrw/API/event-stub coverage includes
two-, three-, and four-byte boundary cases and invalid adapter bytes. Action
results are covered with public stubs. Oil's real custom confirmation float is
also path-free tested for cancelled rename, duplicate, and delete plus
confirmed deletion. Further real plugin/prompt versions and physical Braille
remain open.

Message-producing Ex commands carry a one-shot semantic return marker on their
immediate structured result. The matching mode cue plays once before that
result; the message always remains and Session focus appends either nothing,
the current line, or context, mode, and connection. A later asynchronous
message has no marker and cannot inherit this return presentation.

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

File-manager output uses semantic name, type, and state instead of decoration.
When no entry exists, focus context outputs at most the final name from
`currentDirectory` or `root`; complete local, remote, or virtual paths are not
spoken.
The persistent Braille region uses the same semantic entry instead of the raw
decorated manager row. Routing is available only within an entry name found
exactly once in that real row; status segments and ambiguous names are
deliberately not routable.

Real-TUI tests cover accepting and cancelling `vim.ui.input`, choosing from
`vim.ui.select`, and the selected choice from Lua `vim.fn.confirm()` calls on
Neovim 0.10.1 and 0.12.3. Custom plugin floats and pager variants remain
separate practical work.

Braille state, indentation, selection dots 7/8, and routing are implemented in
the model and automated tests, but no physical display has been tested. Bugs
are very likely. Hardware coverage and fixes are explicitly important priority
work before reliable Braille support can be claimed.
