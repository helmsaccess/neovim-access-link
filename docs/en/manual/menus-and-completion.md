# Menus and completion

The plugin reports Neovim completion items, selection changes, confirmation,
closing, and available details as structured events. NVDA's own “Report
automatic suggestions with sound” setting under Object Presentation controls
the standard opening and closing cues.

Neovim's built-in popup menu is supported, including completion sources that
use `complete()`, `completefunc`, or `omnifunc`. Explicit adapters are included
for `nvim-cmp` and `blink.cmp`; test them with the installed plugin version and
configuration. Completion, command-line completion, LSP signature help, and
supported menus are announced from Neovim APIs or explicit adapters, not by
reading screen rows. Very custom floating interfaces require a supported
public adapter and are not automatically accessible.

Open, move through, confirm, and close a menu with the keys configured in
Neovim or the completion plugin; Access Link does not replace those mappings.
Under `NVDA menu → Preferences → Input gestures... → Neovim Access Link`, a
gesture can be assigned only to read the longer documentation for the currently
selected completion item. It works while a selected item provides such
documentation.

If a menu is silent, first verify that the editor tab is bound and that native
terminal fragments are not being mistaken for semantic output. Then copy the
redacted diagnostic report and note the menu or plugin involved.

Command-line wildmenu, `vim.ui.select`, and custom floating menus have not been
practically covered in every configuration.
