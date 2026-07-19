# Repository layout

Directories follow runtime and trust boundaries. They are not all separate
programs: runtime consists of a Neovim process, an additional bridge process
for SSH, and the NVDA process on Windows. `protocol/python/` and
`nvda-addon/core/` are shared library layers.

## Source areas and entry points

| Path | Responsibility | Important entry points |
| --- | --- | --- |
| `neovim-plugin/` | Neovim state, semantic events, session files, and plugin adapters | `plugin/nvim_nvda.lua`, `lua/nvim_nvda/init.lua`, `lua/nvim_nvda/session.lua`, `lua/nvim_nvda/state.lua` |
| `bridge/python/` | Connect exactly one remote Linux Neovim session to SSH stdin/stdout | `nvim_nvda_bridge/__main__.py`, `bridge.py`, `session_registry.py`, `stdio.py` |
| `protocol/python/` | MessagePack framing, message validation, sequencing, and local/SSH clients | `codec.py`, `messages.py`, `session.py`, `nvim_rpc.py`, `local_client.py`, `stdio_client.py` |
| `nvda-addon/core/` | NVDA-independent connection models and coordination, service publication, gate, discovery, and speech/Braille planning | `connection_coordinator.py`, `service_registrar.py`, `gate.py`, `connection_instances.py`, `speech.py`, `braille.py` |
| `nvda-addon/addon/` | NVDA Global Plugin, Windows Terminal AppModule, dialogs, resources, and locale catalogs | `globalPlugins/NeovimAccessLink/__init__.py`, `appModules/windowsterminal.py` |
| `packaging/` | Rootless installation of Linux user components | `install_user.py` |
| `tools/` | Reproducible package, documentation, catalog, and test tools | `build_nvda_addon.py`, `build_user_package.py`, `build_documentation.sh`, `test_neovim_plugin.sh` |
| `docs/de/` | Maintained German user and developer documentation | `README.md` |
| `docs/en/manual/` | English user documentation | `README.md`, `quick-guide.md` |
| `docs/en/development/` | English developer explanation, reference, and evidence | this file and `README.md` |

[Architecture](architecture.md) explains how these areas relate. In
particular, NVDA-specific code must not move into the speech planner or
transport protocol.

## Sources, package layout, and generated output

`buildVars.py` is the single maintained source for product identity, numeric
Store version, branch-local development build number, author, and supported
NVDA versions.

The add-on build copies maintained Python modules from `protocol/python/` and
`nvda-addon/core/` below the Global Plugin. A built `.nvda-addon` therefore has
a deliberately different layout from the development repository. The Linux
user package is also built from bridge, protocol, plugin, and installer sources
and then embedded as an add-on resource. Changes belong in the source areas
listed above, never in an unpacked build.

Generated or private files have fixed locations:

- `dist/`: installable, uniquely versioned packages;
- `build/`: generated HTML documentation and other reproducible output;
- `tmp/`: local, private, and short-lived investigations.

These directories are not alternative sources of truth.

## Test locations

- `neovim-plugin/tests/` covers Lua state and real headless-Neovim flows.
- `protocol/python/tests/` covers messages, framing, sequences, and clients.
- `bridge/python/tests/` covers discovery, the RPC bridge, and stdio transport.
- `nvda-addon/tests/` covers core, speech/Braille, package contents, and
  NVDA-facing adapters through test doubles.

See [testing.md](testing.md) for suite selection and commands.

## Names and documentation locations

Public community files use GitHub-recognized root names `README.md`, `LICENSE`,
`CONTRIBUTING.md`, and `SECURITY.md`; templates live below `.github/`. New
Python and Lua files normally use `snake_case`, while documentation uses
`lowercase-kebab-case`. `buildVars.py` deliberately retains the official NVDA
Add-on Template filename and is the documented exception.

Durable decisions belong in the matching language tree under
`docs/de/development/adr/` or `docs/en/development/adr/`. Verified current
state belongs in `current-status.md`, reproducible evidence in `testing.md`,
and historical changes in `changelog.md`.
