# Embedded terminal and file managers

In Neovim's embedded terminal, Terminal mode and Terminal-Normal mode are
different. Direct terminal interaction must remain usable and native output is
allowed where the semantic editor gate does not apply. Returning to an editor
buffer restores structured Neovim reporting.

Entering direct terminal input uses the same focus cue as Insert mode. Leaving
it for Terminal-Normal mode uses the Normal-mode cue. Passthrough is switched
before either optional cue, so native terminal output remains fail open.
Because `Ctrl+\`, `Ctrl+N` can be awkward on some keyboard layouts, the Input
Gestures category also exposes “Leave direct input in the active Neovim
terminal”. It has no default gesture and targets only the authenticated
Neovim terminal bound to the focused Windows Terminal control. `i` returns to
direct input.

The assignable leave-input command stops only direct terminal input. It does
not terminate the shell process or delete the terminal buffer. Neovim rejects
`:bd` while the terminal job is running with `E89`; the add-on explains this
before Neovim's following hit-enter state. Only an intentional `:bd!`
terminates that job, so the add-on never invokes it automatically. `:bp` and
`:bn` can switch only to another existing listed buffer. If `:terminal`
replaced the sole empty buffer, the add-on reports that no other listed buffer
exists. Open a separate buffer, for example with `:new | terminal`, when a
reliable previous-buffer destination is wanted.

Opening Neovim's command line with `:` announces command-line mode and plays a
short mid-pitch tone. Returning from it in a terminal context uses the Normal
cue. For `:bp`, `:bn`, and their full forms, transient spoken return modes are
not added before the destination presentation selected under Session focus.
The cue remains; No announcement stays silent. Typed input, errors, and ordinary messages displayed after command execution are
reported structurally; messages are also shown briefly in Braille.
Neovim's structured `TermClose` reports the terminal process exit status;
shell output while it runs remains native terminal output.

`:terminal` creates a terminal buffer and uses the entry presentation selected
under Session focus. With Current line, the add-on waits event-first for the
first real terminal line; the following automatic cursor event is not repeated
as one initial character. `i` enters direct terminal input, presents the full
current cursor line, and then leaves native terminal output fail-open.

Windows Terminal is currently the only approved front end. The add-on's event
handlers and gestures live in its NVDA AppModule, so Notepad, PuTTY, and other
applications are not queried or modified.

The plugin contains adapters for netrw and the public APIs of Oil, nvim-tree,
Neo-tree, and mini.files. It can announce item type, name, state, and supported
actions. Supported public plugin events also report same-entry changes without
cursor movement: marked, unmarked, copied, cut, file-manager clipboard
cleared, expanded, or collapsed. Pure render bursts are coalesced; state is
not queried periodically. Confirmed actions are compactly reported as created,
added, renamed, copied, moved, deleted, changed, or restored. Immediate batches
produce one summary, and Access Link transfers at most a basename, never the
complete source or destination path. Oil can additionally report a completion
failure or some cancellations. For other plugins, their own failure/cancel
messages remain authoritative where the public API has no result event; Access
Link does not guess. Adapters load only for the active matching buffer. Unsupported custom
file-manager drawings do not fall back to terminal scraping.
Very long names and paths are byte-bounded for transport but never cut inside
a Unicode character. If a third-party adapter returns invalid UTF-8 text, an
optional field is ignored; an invalid required name suppresses only the
semantic entry. Normal Neovim navigation remains available in both cases.
netrw supports its thin, long, wide, and tree presentations. Banner lines are
manager context without an invented entry; spaces, tabs, and Unicode in names
are preserved. If an optional adapter repeatedly fails or stalls Neovim, it is
briefly suspended for the affected buffer while normal navigation remains
active. `:checkhealth nvim_nvda` reports counters without paths, file names,
or internal error text. External adapters must be synchronous and small and
must perform neither file/network I/O nor polling.
When no entry is temporarily selected, context output uses at most the final
name of the focused directory level. It does not speak a complete local,
remote, or virtual path.

The persistent Braille line presents a file-manager entry's name, type, and
state instead of the visible plugin row's icons, indentation decoration, and
extra columns. Routing is available only inside the name when that name occurs
exactly once in the real buffer row. Type and status text is synthetic
orientation and deliberately has no routing action.

For the most structured input and selection prompts, use
`select_prompts = true` with nvim-tree and `use_popups_for_input = false` with
Neo-tree. These public options use Neovim's central `vim.ui.select` and
`vim.ui.input` APIs, whose acceptance and cancellation Access Link observes.
Access Link never changes those plugin settings automatically. Lua
`confirm()` prompts also report the selected choice. Oil's custom confirmation
float has a deliberately narrow fallback: Access Link reports only the fixed
action, count, and Y/N, never the rendered raw row or complete paths. It applies
only to Oil's `oil_preview` in a real floating window; unknown or changed
rendering remains fail-open to normal structured buffer/window output. Other
plugin-specific popups still need separate verification.
