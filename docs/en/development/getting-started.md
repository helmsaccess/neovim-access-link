# Development and test onboarding

This page takes a new checkout to its first meaningful verification. Begin
with the [overview](overview.md) if the project is new to you, and read
[architecture](architecture.md) before changing an architectural boundary.
See the [user manual](../manual/README.md) for operation of the installed
add-on.

## What actually runs

Runtime involves at most three processes:

1. Neovim loads the Lua plugin.
2. For a remote Linux session, a Python bridge connects exactly that Neovim
   instance to SSH stdin/stdout. Local Windows operation has no bridge.
3. NVDA loads the Global Plugin and, only for Windows Terminal, the AppModule.

Protocol, connection models, and speech/Braille planning are libraries inside
these processes, not additional services. [Repository layout](repository-layout.md)
maps them to source paths.

## Runtime prerequisites

Windows operation requires Windows 11, NVDA 2026.1.x, Windows Terminal, and
either local Neovim or Windows OpenSSH.

A remote Linux target needs Neovim 0.10.1 or a verified compatible later
version, `python3`, a reachable SSH service, and writable `~/.local`. The
installed package bundles MessagePack, so target-side `python3-msgpack`,
`pynvim`, root access, and runtime downloads are not required.

The currently confirmed environment is listed in
[compatibility.md](compatibility.md). It is test evidence, not a blanket claim
about every newer or similar platform.

## Development tools

Complete local verification requires:

- Python 3;
- `msgpack` exactly 1.1.1 for protocol tests and package builds;
- ConfigObj 5.0.8 for NVDA-compatible manifest validation during the add-on
  build;
- Pexpect 4.9.0 for bridge and TUI integration tests;
- Ruff 0.14.5, matching NVDA 2026.1;
- Neovim for real Lua suites;
- Pandoc for HTML builds; 3.1.11.1 is confirmed;
- Git for diff and whitespace checks.

The Python dependencies used by the GitHub test workflow are version-pinned
in `tools/requirements-ci.txt`.

Pure Python and Lua tests do not import NVDA. NVDA-facing tests use controlled
test doubles and additionally inspect the built add-on.

## First checkout verification

For fast feedback without package builds or real listeners:

```bash
tools/run_tests.py quick
```

The normal complete sandbox-compatible workflow is:

```bash
ruff check .
ruff format --check .
tools/run_tests.py all-safe
tools/run_tests.py ssh
python3 tools/build_nvda_addon.py
python3 tools/gettext_catalog.py check
tools/build_documentation.sh
git diff --check
```

Real local listeners and Unix sockets require a suitable environment and
therefore run separately:

```bash
tools/run_tests.py socket
```

`tools/run_tests.py all` runs the sandbox-compatible, mocked SSH, and socket
phases sequentially. With no group argument, the runner uses the `safe`
preset. Use `-j N` to limit parallel processes and `--list` to inspect
selection without running it.

| Group or preset | Compact purpose |
| --- | --- |
| `unit` | pure and mock-isolated Python tests |
| `package` | built add-on, package contents, and NVDA integration doubles |
| `lua` | headless-Neovim specifications without listeners |
| `ssh` | mocked SSH command, Askpass, and failure paths, without a real connection |
| `socket` | real disposable TUI, RPC, TCP, and Unix-socket cases |
| `quick` | fast feedback; equivalent to `unit` |
| `safe` | default without arguments: `quick`, `package`, and `lua` |
| `all-safe` | complete listener-free suite; an alias of `safe` |
| `all` | every group in separate `all-safe`, `ssh`, and `socket` phases |

The add-on build is itself part of verification: package tests inspect the
actual generated archive rather than only the source tree. See
[testing.md](testing.md) for isolation, sandbox boundaries, and the properties
proved by each suite.

## Where a change starts

| Task | Inspect first | Minimum relevant verification |
| --- | --- | --- |
| Neovim event or mode recognition | `neovim-plugin/lua/nvim_nvda/init.lua`, `state.lua` | affected Lua specification and speech regression |
| Message field or control | `protocol/python/nvim_nvda_protocol/`, `protocol.md` | protocol, bridge, and add-on tests |
| SSH discovery or bridge | `bridge/python/nvim_nvda_bridge/`, `ssh_sessions.py` | bridge, protocol, and security tests |
| Local Windows session | `session.lua`, `local_sessions.py`, `local_client.py` | local Lua, protocol, and add-on tests |
| Focus, WT binding, or suppression | `appModules/windowsterminal.py`, `gate.py`, Global Plugin | gate, isolation, package, and practical WT negative tests |
| Speech, Braille, or sounds | `speech.py`, `braille.py`, `globalPlugins/NeovimAccessLink/nvda_presentation.py` | planner, Unicode, package, and practical NVDA tests |
| Settings or Tools dialogs | `globalPlugins/NeovimAccessLink/nvda_ui.py` and `settings-reference.md` | settings, localization, and package tests |
| Installation or build | `tools/`, `packaging/`, installer classes | built add-on, installation, and archive tests |

[testing.md](testing.md) also contains the complete mapping. One passing test
does not approve unrelated components or platforms.

## Safe practical testing

- Begin with a test buffer and a disposable test file.
- Never terminate or modify existing tmux or Neovim sessions for destructive
  testing.
- Fully update local and remote components before a test and restart Neovim.
- Alongside the success path, verify that an unbound Windows Terminal control
  retains normal NVDA output and that disconnect restores fail-open behavior.
- Never copy real hostnames, accounts, domains, key paths, passwords, or editor
  content into tests or versioned diagnostic examples.

Before implementing a change, read [current status](current-status.md), the
affected reference page, and relevant ADRs. The plan and changelog provide
context but do not replace current code and tests.
