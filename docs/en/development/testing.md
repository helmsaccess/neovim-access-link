# Test strategy

Python protocol, bridge, and NVDA-independent core tests run separately. Lua
specifications use real `nvim --headless`; TUI tests use disposable Neovim and
pseudoterminals and never attach to a user's tmux or editor session. Packaging
tests extract and import the actual built add-on and embedded Linux package.

```bash
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
python3 -m unittest discover -s protocol/python/tests -v
python3 -m unittest discover -s bridge/python/tests -v
python3 -m unittest discover -s nvda-addon/tests -v
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
git diff --check
```

Regression coverage includes framing, resync, Unicode, empty buffers, modes,
editing, completion, menus, settings profiles, installation, multiple local
and SSH sessions, focus/runtime IDs, F12 claims, delayed callbacks, redaction,
and fail-open suppression.

The F12 path distinguishes four stages: physical session marking, the
transient registry claim, unique claim resolution, and terminal-to-connection
binding. While support is enabled, NVDA treats each physical F12 as one
authorization for the exact focused control and does not synthesize or consume
the key. Neovim matches the
unchanged `typed` value and schedules the registry write outside `vim.on_key`.
Manual target selection prepares the same physical F12 proof before using the
typed connection path.

Lifecycle regressions cover graceful exit, SIGKILL, PID/endpoint nonce reuse,
legacy schemas, passive bounded inventory, permission uncertainty,
bounded entry counts, UTF-8-safe names, uncertain process checks,
nonce-owned versus inherited socket handling, one closed WT
window beside a live window, individual tabs sharing one HWND, the periodic
idle-tab sweep, off-main-thread client shutdown, and fail-open suppression.
Socket tests prove that cleanup removes only an exact nonce-owned plugin path.
Real RPC tests prove that the permanent channel verifies the nonce before
setup and that mismatch disconnects without a reconnect loop.
Isolated local and Tessa SIGKILL tests must leave discovery empty
without touching existing user Neovim or tmux sessions.

## Required Windows Terminal isolation tests

For focus-context output, alternate focus between a bound Neovim control, an
unbound shell-only tab, and, where possible, two split panes. Expect exactly
one compact file/special-buffer and mode announcement only for the bound
control. Rapid switching must never announce stale context. After disconnect,
native WT output must remain immediately available. Record the request ID,
result, and actual output in the redacted test report.

Automated tests establish the intended gating behavior, but complete practical
non-interference across Windows Terminal layouts remains an open acceptance
area. Practical tests must cover all of these negative cases:

- unbound PowerShell, Command Prompt, and WSL panes retain native focus, text,
  input, speech, LiveText, and Braille behavior while add-on support is active;
- F12 in an unbound shell may perform one bounded claim check as an explicit
  user action, but without a fresh claim it does not announce, bind, suppress,
  or open a dialog;
- events from another connected Neovim never offer or perform a rebind in an
  unrelated shell pane;
- a remembered identity cannot suppress native output before fresh structured
  state, including when a shell replaces Neovim in the pane while its RPC
  channel remains alive;
- separate Windows Terminal processes, windows, tabs, and split panes neither
  cross-bind nor register duplicate gesture observers; and
- the add-on overlay does not change unbound Braille or LiveText fallback.

Tests must record the focused UIA class and runtime identity so pane-level and
tab-level behavior are not conflated. Any uncertain result is a fail-open
defect and remains documented until practically reproduced and corrected.

Practical regression test on 16 July 2026 with NVDA 2026.1.1 and
`0.90.0-dev.3`: local `nvim test.txt` was started in the first WT tab, support
was enabled, F12 was pressed, and the control binding was remembered. A second
tab opened `ssh user@example.invalid` and remote `nvim test.txt`; F12 connected
it without another activation command. Deactivation was then invoked from the
second tab. Expected and actual results matched: independent second-tab pairing
worked and the global off command worked from that tab. Result: passed. Split
panes were then tested in both horizontal and vertical orientations while
local and SSH connections remained active in other tabs. Both orientations
worked without errors or crossed connections. Result: passed. Separate WT
windows, tmux, and the complete unbound-shell-pane negative matrix remain
practically unverified.

Manual tests must record prerequisites, exact actions, expected and actual
results, and avoid confidential text. Confirmed tests used Windows 11 25H2,
NVDA 2026.1.1, Windows Terminal 1.24.x, OpenSSH 9.5p2/LibreSSL 3.8.2, Rocky
Linux 10.2, Python 3.12.13, and Neovim 0.10.1.

Automated coverage is not a stable-release claim. Many add-on features still
need deeper practical tests. No physical Braille display has been tested;
Braille hardware testing, routing, selection dots, translation tables, and
bug fixing are priority TODO work.

The documentation build must produce six independent HTML files: German and
English Quick Guide, manual, and developer documentation. Every published
source is assigned explicitly; private ignored material is excluded.
