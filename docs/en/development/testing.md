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
binding. NVDA observes an otherwise unbound gesture only while support is
active and does not synthesize or consume the key. Neovim matches the
unchanged `typed` value and schedules the registry write outside `vim.on_key`.
Manual selection bypasses claim resolution but uses the same connection path.

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
