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
- For NVDA-facing Python, follow NVDA's coding style exactly: UTF-8 and LF, tabs for indentation, 110 columns, and Ruff formatting/lint from `pyproject.toml`; never hand-align with spaces inside indentation. Preserve NVDA callback/API names, add a concise `# Translators:` comment immediately before translatable user-facing text, and use type annotations consistently where the surrounding NVDA interface does. Python components with an established different style keep it; otherwise use this NVDA style. The Neovim plugin follows its Lua conventions.
- Use an existing public NVDA Windows wrapper where suitable, otherwise use `winBindings`; never define parallel Windows DLL bindings in the add-on.
- Keep application-specific NVDA events, overlays, `nextHandler`, and contextual scripts in the corresponding AppModule; shared services must not own or forward NVDA event chains. Any broader global hook requires explicit architectural justification and fail-open tests.
- Assign settings, tools, scripts, and registrations by required scope and lifetime, not code size: context-only features belong to the AppModule; process-wide features may be registered by a minimal GlobalPlugin.
- Keep shared implementation behind narrow service interfaces; registrations and shared references must be symmetric, reload-safe, and released before teardown.
- Document private API usage in an ADR before release.
- Never disturb existing tmux or Neovim sessions for testing.
- Never commit real hostnames, usernames, domains or secrets.
- Test Lua with `nvim --headless` where practical.
- Packaging tests must validate the built add-on.
- Do not request a commit for user-visible changes until the user has practically tested them unless explicitly requested.
