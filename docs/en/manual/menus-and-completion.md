# Menus and completion

The plugin reports Neovim completion items, selection changes, confirmation,
closing, and available details as structured events. NVDA's own “Report
automatic suggestions with sound” setting under Object Presentation controls
the standard opening and closing cues.

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
`nvim-cmp` exposes that resolved item. `blink.cmp` currently does not expose its
internally resolved copy through a public API, so documentation present on the
original item works while resolve-only documentation may remain unavailable.
Ghost text without a visible completion menu is not reported as a selectable
menu.

`:NvimNvdaLspStatus` reports the names of LSP clients attached to the current
buffer and explicitly reports when none is attached. Ongoing LSP progress is
not spoken continuously; errors and results remain available through
diagnostics and Neovim messages.

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
