# Compatibility

## Confirmed reference platform

- Windows 11 25H2, 64-bit; NVDA 2026.1.1; Windows Terminal 1.24.x.
- `OpenSSH_for_Windows_9.5p2`, `LibreSSL 3.8.2`, key-based login.
- Rocky Linux 10.2, kernel 6.12.0-211.28.1.el10_2.
- Neovim 0.10.1 (`neovim-0.10.1-4.el10_0.x86_64`) with LuaJIT.
- Python 3.12.13 for the bundled Linux bridge.

Neovim 0.10.1 is the provisional minimum. Newer optional APIs require feature
tests. NVDA manifest values are minimum 2026.1 and last tested 2026.1.1; this
boundary intentionally follows NVDA's 64-bit Python 3.13 transition.

The local Windows CLI and parallel local/SSH tabs were tested. Windows Terminal
is the only approved front end. PuTTY or another terminal requires a dedicated
identity, focus, output, suppression, and fail-open adapter.

No physical Braille display has been tested. Automated Braille tests cover only
state and planning, so hardware bugs are very likely. Other Windows/NVDA/
Neovim versions, SSH variants, languages, and many add-on features also lack
exhaustive practical coverage. The supported state is alpha to beta.

An older Neovim on Rocky Linux 9 did not connect with the current build; no
compatibility promise is made for it. GUI front ends, portable Windows layouts,
and `NVIM_APPNAME` are unsupported.
