# Bridge instructions

- Keep network, stdio, reconnect, parsing, and subprocess work off NVDA's main thread.
- Use bounded framing, queues, timeouts, and reconnect behavior; never make correctness depend on
  logs.
- Accept only authenticated, validated sessions and fixed protocol controls.
- Use SSH stdio, private Unix sockets, or loopback-only local TCP. Never bind to a non-loopback
  interface or execute received data.
- Keep bridge transport and lifecycle code separate from canonical editor and presentation state.
- Fail closed for invalid protocol data and fail open toward native NVDA/terminal behavior.
- Use isolated temporary runtime directories and never attach tests to a user's Neovim or tmux
  session.
- Run bridge unit tests through `python3 tools/run_tests.py quick` or `all-safe`.
- Run `python3 tools/run_tests.py ssh` separately for mocked SSH and Askpass behavior.
- Run `python3 tools/run_tests.py socket` separately for real disposable TUI/RPC/socket behavior.
