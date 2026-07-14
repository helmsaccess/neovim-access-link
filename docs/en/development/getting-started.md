# Development and test onboarding

Neovim Access Link separates the Lua plugin, Linux Python bridge, shared
protocol/core, and NVDA integration. Read [Architecture](architecture.md)
before changing a boundary.

Windows runtime requirements are Windows 11, NVDA 2026.1.x, Windows Terminal,
and either local Neovim or Windows OpenSSH. A remote Linux target needs Neovim
0.10.1 or a verified compatible version, Python 3, SSH, and writable `~/.local`.
The package bundles MessagePack; target-side `python3-msgpack`, `pynvim`, root,
and runtime downloads are not required.

The confirmed reference environment is Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x, `OpenSSH_for_Windows_9.5p2` with `LibreSSL 3.8.2`,
and Rocky Linux 10.2 with Neovim 0.10.1 and Python 3.12.13.

```bash
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
python3 -m unittest discover -s nvda-addon/tests
python3 -m unittest discover -s protocol/python/tests
python3 -m unittest discover -s bridge/python/tests
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
git diff --check
```

This is alpha-to-beta software. Not every add-on feature has extensive manual
coverage. Braille has no physical-display test coverage and very likely has
bugs; this is important priority work, not a dismissed feature.
