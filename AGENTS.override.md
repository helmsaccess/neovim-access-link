# Repository-specific instructions

## Project

- Build a low-latency, reliable Neovim integration for NVDA 2026.1.x on Windows and Neovim on Rocky Linux 10.
- Use Neovim APIs and semantic events. Screen scraping is fallback only.
- Keep transport, protocol, state, speech/Braille planning and focus logic separated.
- Never block NVDA's main thread with network I/O, reconnects, parsing or logging.
- Fail open on disconnects or errors.
- Distinguish byte, Unicode, virtual and visual columns.
- Validate sessions, sequence numbers, heartbeat, resync and `fullState`.
- Use SSH and private local sockets. Never expose listeners or execute untrusted protocol data.

## Sources of truth

- `docs/de/development/current-status.md`
- `docs/de/development/plan.md`
- `docs/de/development/architecture.md`
- `docs/de/development/adr/`
- `docs/de/development/protocol.md`
- `docs/de/development/accessibility.md`
- `docs/de/development/compatibility.md`
- `docs/de/development/security.md`
- `docs/de/development/testing.md`
- `docs/de/development/latency.md`
- `docs/de/development/changelog.md`

## Components

- `neovim-plugin/`
- `bridge/`
- `nvda-addon/`

## Additional rules

- GitHub releases publish the `.nvda-addon` plus one ZIP containing all German and English quick-guide, handbook, and developer-documentation HTML files; prerelease status also requires explicit user instruction.
- When setting a release version, update `README.md`'s prominent release link and its versioned English and German changelog links; verify them again when publishing.
- Prefer stable public NVDA and Neovim APIs.
- Document private API usage in an ADR before release.
- Never disturb existing tmux or Neovim sessions for testing.
- Never commit real hostnames, usernames, domains or secrets.
- Test Lua with `nvim --headless` where practical.
- Packaging tests must validate the built add-on.
- Do not request a commit for user-visible changes until the user has practically tested them unless explicitly requested.
