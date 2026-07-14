# Embedded terminal and file managers

In Neovim's embedded terminal, Terminal mode and Terminal-Normal mode are
different. Direct terminal interaction must remain usable and native output is
allowed where the semantic editor gate does not apply. Returning to an editor
buffer restores structured Neovim reporting.

Windows Terminal is currently the only approved front end. The add-on's event
handlers and gestures live in its NVDA AppModule, so Notepad, PuTTY, and other
applications are not queried or modified.

The plugin contains adapters for netrw and the public APIs of Oil, nvim-tree,
Neo-tree, and mini.files. It can announce item type, name, state, and supported
actions. Adapters load only for the active matching buffer. Unsupported custom
file-manager drawings do not fall back to terminal scraping.
