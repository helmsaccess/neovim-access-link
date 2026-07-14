# Menus and completion

The plugin reports Neovim completion items, selection changes, confirmation,
closing, and available details as structured events. NVDA's own “Report
automatic suggestions with sound” setting under Object Presentation controls
the standard opening and closing cues.

Completion, command-line completion, LSP signature help, and supported menus
are announced from Neovim APIs or explicit adapters, not by reading screen
rows. Very custom floating interfaces require a supported public adapter and
are not automatically accessible.

Commands for opening, closing, moving within, confirming, and cancelling menus
can be assigned under `NVDA menu → Preferences → Input gestures... → Neovim
Access Link`. Normal Neovim keys continue to work; add-on commands are optional
accessible alternatives.

If a menu is silent, first verify that the editor tab is bound and that native
terminal fragments are not being mistaken for semantic output. Then copy the
redacted diagnostic report and note the menu or plugin involved.
