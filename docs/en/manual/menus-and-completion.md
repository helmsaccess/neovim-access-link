# Menus and completion

The plugin reports Neovim completion items, selection changes, confirmation,
closing, and available details as structured events. NVDA's own “Report
automatic suggestions with sound” setting under Object Presentation controls
the standard opening and closing cues for Neovim's built-in menu, `nvim-cmp`,
and `blink.cmp`. Both plugin adapters tie the cue directly to the public open
or close event, even when candidates become available shortly afterwards.
A complete beginner-oriented setup with `init.lua`, a language server, and a
linter is provided in the previous chapter,
[Setting up LSP, auto-completion, and linters](language-tools.md).

Neovim's built-in popup menu is supported, including completion sources that
use `complete()`, `completefunc`, or `omnifunc`. Explicit adapters are included
for `nvim-cmp` and `blink.cmp`. Automated API-contract tests cover the current
`nvim-cmp` main branch, `blink.cmp` v1.10.2, and the provisional v2 branch.
`blink.cmp` v2 requires Neovim 0.12 and `blink.lib`; v1 remains the stable
recommendation. These checks do not replace practical acceptance of every
source, formatting, and key configuration.

The selected label, position, localized LSP kind, parameters, and source are
reported when available. Only the selected candidate is processed, including
selections beyond the first 200 list entries. Documentation resolved later
updates the documentation command silently instead of repeating the selection.
For built-in LSP completion, that documentation can arrive after the final
`CompleteChanged` event and remain available only in Neovim's internal preview
window. When the original LSP item has no documentation, Access Link therefore
resolves exactly the selected candidate through the public
`completionItem/resolve` method as well. A selection change or menu close
discards the stale request. Menu opening, selection, closing, and sounds remain
owned by Neovim's events. `nvim-cmp` exposes its resolved item directly.
`blink.cmp` currently does not expose its internally resolved copy through a
public API, so documentation present on the original item works while
resolve-only documentation may remain unavailable. Ghost text without a
visible completion menu is not reported as a selectable menu.

Neovim's built-in completion deliberately moves once to “no completion
selected” after the last candidate. That state preserves the originally typed
text; the next `Ctrl+N` selects the first candidate again. Access Link reports
this intermediate state explicitly in speech and Braille so it cannot look
like a lost key press. The menu remains open.

`:NvimNvdaLspStatus` reports the names of LSP clients attached to the current
buffer and explicitly reports when none is attached. Ongoing LSP progress is
not spoken continuously; errors and results remain available through
diagnostics and Neovim messages.

## Automatic parameter speech in Insert mode

Inside a function argument list, Access Link requests public LSP signature
help after a short quiet period. It speaks only the active parameter of the
signature selected by the server. Commas, cursor motion, and text changes
retrigger the request; a reply is used only while buffer, window, changed
text, mode, cursor, and associated call still match exactly. Stale replies
remain silent.

Entering a call speaks its first active parameter. Moving to another argument
speaks that parameter. Returning to an already filled earlier argument speaks
it again, while movement within the same argument is deduplicated and silent.
In nested expressions, the innermost enclosing call owns the cursor. Output is
speech-only and never covers source text in Braille. Without an unambiguous
structured server response, Access Link neither guesses from commas nor reads
unstructured hover text automatically.

Press `NVDA+Shift+P` to request callable information at the current cursor.
The cursor may be on the function name or on the call's immediately associated
opening or closing parenthesis. While at least one NVDA key remains held, the
result stays on the Braille display. `NVDA+h/l` cycles through parameters and
`NVDA+k/j` through multiple signatures without moving the real editor cursor.
Releasing the final NVDA key closes the view and restores the editor line.

In Normal mode, this manual query accepts the function name or its opening or
closing call parenthesis; the interior of a non-empty argument list is
deliberately excluded. In Insert mode, the name and both parentheses of an
empty call are unambiguous manual positions. Inside a non-empty argument list,
the automatic active-parameter speech above provides orientation.
Access Link prefers public LSP signature help and uses LSP hover as an
unstructured fallback. A reply is accepted only while instance, terminal,
buffer, window, tab, changed tick, and cursor position still match the request.

On opening, Access Link speaks and shows only the selected signature and its
available documentation. `NVDA+h/l` speaks and shows only the previous or next
parameter of that signature; `NVDA+k/j` speaks and shows only the previous or
next signature with its documentation. Each signature has an independent
parameter selection that starts at parameter 1 and is never mixed with another
signature when switching. Speech and Braille therefore expose the same current
navigation axis. Because the signature view exposes no parameter, the first
`NVDA+h` or `NVDA+l` press reveals the parameter selected for that signature;
only subsequent presses move backward or forward. Speech keeps the full
labels. On Braille, `S 1 of 2`, `P 1 of 3`, and `D:` shorten only the structural
prefixes for signature, parameter, and documentation; function names,
parameter names, and content remain complete. If the content does not fit
on the display, both the normal
pan controls and the next/previous Braille-line
commands page only within this information. The view remains at its first or
last page instead of returning to source text; releasing NVDA restores the
editor line.

Access Link consumes diagnostics through Neovim's public `vim.diagnostic`
API, whether an LSP server, `nvim-lint`, ALE, `none-ls.nvim`, or another
provider produced them. It does not install or start linters. Real automated
runs currently cover Clang-Tidy for C, Ruff for Python, ShellCheck for Bash,
Staticcheck for Go, Clippy for Rust, RuboCop for Ruby, and
`markdownlint-cli2` for Markdown through both `nvim-lint` and ALE on Neovim
0.10.1 and 0.12.3. A built-in diagnostic source additionally exercises the
`none-ls.nvim` LSP bridge on both versions. Background lint updates stay
silent; an explicit diagnostic jump reports source, severity, optional code,
message, and position together in speech and Braille.

Press `NVDA+Shift+E` to inspect diagnostics under the cursor followed by the
remaining diagnostics on the current line. While NVDA remains held,
`NVDA+k/j` cycles through the entries without moving the editor cursor.
Errors and warnings can also produce a short cue when explicit navigation
enters an affected line and at every reached cursor position within an exact
diagnostic range. Typing and background diagnostic refreshes remain silent.
When an explicit query at the current position or line finds no entry, NVDA
reports “no diagnostic” and confirms the empty result with its own short cue.
Mere cursor movement on a clean line never triggers that cue. Information and
hint diagnostics continue to have no diagnostic sound.

The commands `:NvimNvdaDiagnosticPrevious`, `:NvimNvdaDiagnosticNext`,
`:NvimNvdaDiagnosticFirst`, `:NvimNvdaDiagnosticLast`, and
`:NvimNvdaDiagnosticCurrent` can be used in custom Neovim mappings without
replacing existing mappings. Newer Neovim versions also expose native
diagnostic jumps through their public hook. Directly typed `[d`/`]d` jumps
remain observable when the mapping supplies a per-call callback. The Access
Link commands visit every individual diagnostic in the announced order. If
several providers publish diagnostics at the same position, each remains
reachable with its source, index, and total. Navigation wraps from the last
entry to the first and vice versa. A provider
that keeps results only in a private list or screen decoration must mirror
them to `vim.diagnostic` before Access Link can consume them.

Completion, command-line completion, LSP signature help, and supported menus
are announced from Neovim APIs or explicit adapters, not by reading screen
rows. Very custom floating interfaces require a supported public adapter and
are not automatically accessible.

Open, move through, confirm, and close a menu with the keys configured in
Neovim or the completion plugin; Access Link does not replace those mappings.
Under `NVDA menu → Preferences → Input gestures... → Neovim Access Link`, a
gesture can be assigned to read the longer documentation for the currently
selected completion item or LSP hover. Hover reports only its first meaningful
line automatically in speech and Braille; the command reads the full content.
It works while either source provides documentation.

If a menu is silent, first verify that the editor tab is bound and that native
terminal fragments are not being mistaken for semantic output. Then copy the
redacted diagnostic report and note the menu or plugin involved.

Command-line wildmenu, `vim.ui.select`, and custom floating menus have not been
practically covered in every configuration.
