# Feature and accessibility matrix

This matrix describes implemented, primarily automated behavior in an
beta build. It does not imply exhaustive practical verification.

Implemented areas include mode reporting; character/word/line navigation;
editing and deletion; Visual character/line/block selection; indentation;
completion and signature help; search, pairs, diagnostics and spelling; folds,
marks, registers and macros; command line; embedded terminal transitions; and
adapters for common file managers.

Repeated presses of one Braille routing key have an optional, fixed editing
path. The first press routes immediately. A double press may run `cw` or `dw`;
a triple press may run `c$` or `d$` from the routed position, first non-blank
character, or absolute line beginning. All actions default to “Route only”
and are restricted to Normal and Insert modes. The recognizer requires the
same target signature within NVDA's multiple-press timeout. Controller,
settings, protocol, local/SSH transport, built-add-on, Lua, and real
Insert-mode RPC tests cover the path. The reference workflow has been
confirmed on the BRAILLEX EL 80c; the complete command, line-start, timeout,
and multi-driver matrix remains open.

Speech exploration mode uses six fixed Windows Terminal AppModule chords to
read characters, lines, or words through an ephemeral Lua position. Exact
control binding, authenticated instance, capability, editor origin, and reply
correlation are required. The real cursor, buffer, mode, changed tick, and
view remain unchanged; releasing NVDA reads the character or the word/line
with separately configurable current-word and cursor-character details at the
real cursor. Ordinary word and line navigation has an independent copy of
those detail choices. Protocol, Lua, controller, dispatcher, and built-package
tests cover the path; the base exploration path has been practically confirmed
under NVDA. Both word-detail choices and all four line-detail choices were also
practically exercised independently for normal navigation and exploration
release without an observed defect. This is evidence for the tested Windows
and NVDA path, not an exhaustive claim across every environment.

The built-in `z=` spelling list has a separate bounded path. A proven direct
command and a consecutively numbered native UI event open transient local
selection. `NVDA+j/k` cycles through labels without exposing numbers in speech
or Braille, `NVDA+Enter` accepts only the internally validated index, and
releasing NVDA discards only the local selection. Exact control, instance,
prompt, capability, and editor identity are required. Parser, protocol,
transport, controller, AppModule, Braille, built-package, and real Neovim RPC
tests cover positive and negative paths. Practical Windows/NVDA acceptance,
including one physical Braille display, succeeded; a broader hardware matrix
remains pending. A profile-aware one-based setting shifts only the transient
suggestion to an existing later Braille cell; a position beyond
`braille.handler.displaySize` is ignored and cell 1 is used. If the translated
suggestion does not fit to the right, its start moves left to the last cell
where the complete result fits.

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
confirmed deletion. Oil is the only file manager practically tested under
Windows/NVDA so far, using Neovim 0.12; it provides a solid foundation. netrw,
mini.files, nvim-tree, and Neo-tree currently have automated or isolated
coverage and will be accepted practically over time. Further real
plugin/prompt versions and physical Braille remain open.
The persistent semantic file-manager Braille region localizes typed kind and
state labels at the NVDA boundary. Navigation and same-entry state speech no
longer create a transient Braille message that covers this region.

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
configured destination presentation while its cue remains independent. Core
terminal and buffer transitions are practically confirmed under Windows/NVDA;
pager variants remain open.
Explicit copy/paste uses four freely assignable NVDA commands and correlated
Neovim controls for the Visual selection, register 0, `nvim_paste`, and fixed
register 0 as the unnamed paste register's backing store.
Protocol, Lua, bridge, and built-add-on coverage exists; all four commands are
practically confirmed locally and over SSH.
Multiple bound sessions are isolated by process, window handle, complete UIA
runtime identity, session, sequence, and structured focus validation. Exact
one-shot, control-specific physical F12 proofs and switching between
independently bound windows, tabs, and panes have automated negative coverage. Unknown controls and failures remain
fail open. Local/SSH tabs, horizontal/vertical split panes, and multiple
windows are practically confirmed; the complete unbound-shell-pane negative
matrix remains pending.

File-manager output uses semantic name, type, and state instead of decoration.

Spelling and grammar presentation follows NVDA's document-formatting bitmask:
Speech is `1`, Sound is `2`, and Braille is `4`. Navigation and exploration
share one presentation path for all values from `0` through `7`. Character
movement reports entering and leaving an error. Each semantic word motion and
word-exploration result carries only the error kind at the reached word,
allowing NVDA's configured localized label and error sound without exposing
diagnostic text. Label and word form one interruption-safe presentation.
Opening a proven non-empty native spelling list produces one brief spoken
availability message.

General diagnostics use Neovim's public `vim.diagnostic` API as the sole
provider boundary. Access Link neither reads private nvim-lint/ALE tables nor
starts their processes. It validates types and ranges, applies UTF-8-safe
bounds, orders all namespaces deterministically, and selects overlapping
ranges by severity, smallest containing range, then a stable provider-neutral
key. A missing source falls back to the bounded Neovim namespace name. The
ordered list is retained per buffer and discarded on `DiagnosticChanged` or
`BufWipeout`, so ordinary cursor movement does not repeatedly sort large
diagnostic sets.

Pinned real-provider contracts run Clang-Tidy, Ruff, ShellCheck, Staticcheck,
Clippy, RuboCop, and `markdownlint-cli2` through both `nvim-lint` and ALE on
Neovim 0.10.1 and 0.12.3, and additionally exercise the real `none-ls.nvim`
LSP bridge with a built-in source. All three plugins publish to
`vim.diagnostic`, so no plugin-specific diagnostic adapter is needed. ALE
selects `markdownlint-cli2` through its public executable configuration
because the existing Markdownlint handler understands its output. The same
contract can later consume `gopls`, `rust-analyzer`, `ruby-lsp`, or other
linters through an appropriate diagnostic provider. A language alone does not
require an Access Link change; only a relevant provider without semantic
mirroring would justify evaluating an adapter.

`DiagnosticChanged` refreshes state without automatic speech flooding. Five
commands provide previous, next, first, last, and current diagnostic output
without changing user mappings. Neovim 0.12 native jumps are observed through
the public `jump.on_jump` hook; the 0.10 path uses compatible
`goto_prev()`/`goto_next()` calls and observes its native previous/next
navigation.

The `nvim-cmp` and `blink.cmp` adapters are one documented polling exception.
Public plugin events start and stop the accessible-menu lifetime, but neither
plugin currently provides a reliable event for every selection change. A
35 ms timer therefore queries the public selection API only while that plugin
menu is open and stops on the public close event. The accessible lifetime and
standard opening/closing cues do not depend on the first successful tick, so a
briefly empty or invisible item view while the plugin populates its menu does
not produce a false close/open pair. Each tick normalizes only the selected
candidate. `nvim-cmp` still needs two public calls wrapped in
`cmp.sync()`, so content-free diagnostics expose errors, slow ticks, maximum
duration, and the active API variant in the diagnostic report and
`:checkhealth`. Built-in Neovim completion remains fully event-driven. This
fallback should be removed when a reliable public selection event becomes
available.

All 25 LSP completion kinds, sources, UTF-8-safe limits, selections beyond item
200, and silent resolved-documentation updates have automated coverage.
`nvim-cmp` exposes its mutable `entry.completion_item`, allowing resolve results
to update the documentation command without another announcement. `blink.cmp`
does not expose its internally resolved copy through the public item API;
original documentation works, while resolve-only documentation remains an
upstream dependency. Ghost-text-only configurations without an open menu are
outside the adapter contract.

Real-module contract tests cover current `nvim-cmp` and `blink.cmp` v1.10.2 on
Neovim 0.10.1 and 0.12.3, plus the provisional `blink.cmp` v2 branch with
`blink.lib` on 0.12.3. They exercise the actual modules and event registration
with injected selection data; complete TUI and Windows/NVDA acceptance remains
open.

Signature help observes Neovim 0.10's handler path and only the
`textDocument/signatureHelp` callback through `buf_request_all` on 0.11/0.12.
It supports UTF-16 parameter ranges, multiple-client alternatives,
deduplication, and a silent close state. Listener-free tests pass on Neovim
0.10.1 and 0.12.3; a real language server and Windows/NVDA remain practical
acceptance work.

LSP hover follows the same version split while observing only
`textDocument/hover`. It normalizes MarkupContent and MarkedString forms,
deduplicates multiple clients, speaks and Brailles the first meaningful line,
and stores bounded complete documentation per instance for the existing
documentation command. Cursor, Insert, or buffer context changes close it
silently. Listener-free parser and compatibility tests pass on Neovim 0.10.1
and 0.12.3; a real language server and Windows/NVDA remain practical
acceptance work.

`:NvimNvdaLspStatus` reports up to 32 unique bounded names from public
`vim.lsp.get_clients()` for the current buffer. It explicitly reports an empty
state in speech and Braille. Continuous `LspProgress` events are deliberately
not announced because routine indexing would create an unbounded speech stream;
errors and results remain covered by diagnostics and Neovim messages.
When no entry exists, focus context outputs at most the final name from
`currentDirectory` or `root`; complete local, remote, or virtual paths are not
spoken.
An editable Oil entry uses its current public `parsed_name`; line and file
boundary motions retain their cues without speaking icons or extra columns.
The confirmed path changes only with Oil's own written action. This Oil path
is practically confirmed under Windows/NVDA with Neovim 0.12; netrw,
mini.files, nvim-tree, and Neo-tree do not yet have practical Windows
acceptance.
The persistent Braille region uses the same semantic entry instead of the raw
decorated manager row. Routing is available only within an entry name found
exactly once in that real row; status segments and ambiguous names are
deliberately not routable.

Real-TUI tests cover accepting and cancelling `vim.ui.input`, choosing from
`vim.ui.select`, and the selected choice from Lua `vim.fn.confirm()` calls on
Neovim 0.10.1 and 0.12.3. Custom plugin floats and pager variants remain
separate practical work.

Braille state, indentation, selection dots 7/8, virtual end cells, and routing
are implemented in the model and automated tests. The persistent editor path
and cursor routing were practically confirmed with one physical Braille
display in Normal, Insert, and command-line modes, including Unicode, tabs, an
empty line, and the position after the final character. The transient spelling
suggestion was checked on the same display. This acceptance confirms the
NVDA 2026.1.1 path in use; it does not replace a broader matrix of displays,
drivers, translation tables, and NVDA major versions.

Braille-display navigation now uses NVDA's standard scroll-back,
scroll-forward, previous-line, and next-line commands. Horizontal movement
stays inside NVDA's viewport until a line boundary: back then selects the
previous line end and forward selects the next line start. Direct Up/Down
instead changes the real Neovim cursor by exactly one line and retains
Neovim's preferred virtual column across short lines. Protocol, local and SSH
transport, controller, built-add-on, Lua, and real Insert-mode RPC coverage is
automated, including empty lines, tabs, UTF-8/wide characters, and the
one-shot direct-down marker. The correction has been confirmed practically
with a BRAILLEX EL 80c. A separate freely assignable toggle now selects
Braille cursor mode or Braille exploration mode. In Braille exploration mode,
Up/Down changes only a virtual buffer line while routing commits the chosen
position. The selected mode is stored in the individual Neovim-instance
runtime, so concurrent local and remote sessions can choose independently.
Changing controls or applications preserves that session's virtual position
and horizontal NVDA viewport; returning restores both without adopting
another session's view. Disconnect resets only the affected runtime. Later
real-cursor and mode changes, as well as edits on other lines, do not replace
this virtual position. An edit on the explored real-cursor line
refreshes its complete content and current mode without re-anchoring the
virtual line, reading column, or viewport. The structured region also clears
NVDA's public pending caret-update marker in this mode, preventing a
concurrent native terminal caret event from moving the selected viewport. The
virtual position is not rendered as an apparent second Braille cursor. The
initial request requires the complete real origin; continuation keeps its own
exploration ID and action sequence while buffer, window, and tab remain
unchanged and `changedtick` advances only to the validated current snapshot.
Routing is accepted only when the displayed line snapshot matches the current
buffer tick, and delayed multi-press actions revalidate immediately before
dispatch. This state and its controls are independent of speech exploration
mode. Automated coverage includes per-instance modes, targeted disconnect
reset, transient focus-sequence cleanup, focus and instance correlation,
UTF-8, Insert line ends, an unchanged real cursor, cursor and text-input
decoupling, complete line refresh after edits and mode changes, viewport
retention, rejection of stale routing, deferred revalidation, and cursor
visibility. The principal hardware path has been confirmed with a BRAILLEX EL
80c; the latest edit/routing edge cases, multi-session mode isolation, and a
broader hardware matrix remain to be exercised practically.
