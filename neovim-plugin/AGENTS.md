# Neovim plugin instructions

- Follow the existing Lua and Neovim conventions in this component.
- Use semantic Neovim APIs and events. Screen scraping is a documented fallback only.
- Distinguish byte, Unicode character, virtual, and visual columns at every boundary.
- Keep controls capability-gated, bounded, and limited to fixed validated entry points.
- Exploration and presentation-only operations must not mutate canonical editor state.
- Never attach tests to or otherwise disturb existing Neovim or tmux sessions.
- Prefer disposable headless instances with isolated runtime, state, and `packpath`.
- Run listener-free Lua specifications through `python3 tools/run_tests.py lua`.
- Run `python3 tools/run_tests.py socket` separately for real TUI, RPC, TCP, or Unix-socket cases
  in an environment that permits local listeners.
- Use `tools/test_neovim_plugin.sh` for the serial compatibility run when version boundaries or
  Neovim compatibility are affected.
