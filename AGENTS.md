# Repository instructions for coding agents

## Runtime invariants

- Keep Neovim integration low-latency and reliable. Prefer semantic Neovim APIs and events;
  document any screen-scraping fallback.
- Separate transport, protocol validation, canonical state, speech/Braille planning, and focus
  ownership. Keep network, reconnect, parsing, and logging off NVDA's main thread.
- Fail open toward native NVDA and terminal behavior on errors or disconnects. Authenticate
  and validate discovered sessions and bounded protocol data before use.
- Use SSH stdio, private Unix sockets, or loopback-only TCP. Never execute protocol data.
- Treat logging as diagnostic only and never attach tests to active Neovim or tmux sessions.

## Local development and checks

- Develop in a local Windows checkout. Use the configured `origin` for explicit Git fetches.
  Use Linux for the Unix socket, PTY, and SSH target checks.
- In PowerShell use `python tools/run_tests.py quick`, then `all-safe` for Python, package,
  and listener-free Lua tests. Run `ssh` and `socket` separately. On Windows, `socket` runs
  the local TCP check. Run the full socket group on Linux where listeners are allowed.
- Use parameterless `build.cmd` from a clean committed Windows branch for development
  artifacts. Use disposable output directories for tests. See the
  [development setup](docs/en/development/getting-started.md) and
  [build and release guide](docs/en/development/release-and-build.md).
- Use `python -m SCons` for a standalone package check and `python -m SCons pot`
  for the gettext template. Keep the NVDA manifest templates aligned with upstream.
- Keep project tools, temporary sources, reproductions, and reports in `../nal-aux/`.
  Check `../nvda-shared-aux/` before web research for reusable NVDA references.

## Changes and documentation

- Start with [developer documentation](docs/de/development/README.md). Follow scoped
  `AGENTS.md` files in `nvda-addon/`, `neovim-plugin/`, `bridge/`, `protocol/`, `docs/`,
  and `tests/`. Inspect the affected code and tests before editing.
- Preserve unrelated work and established boundaries. Prefer existing interfaces and cover
  bug fixes with regression tests where practical. Record follow-ups with scope and a durable reference.
- Keep the German technical source and English mirror aligned. Update both current-status
  and changelog pages for changes to behavior, support, architecture, compatibility,
  development workflows, or release state. Use the linked architecture, ADRs, and
  protocol/security references when changing those boundaries.
- Use a focused working branch and make focused English commits after validation.
  Ordinary pushes of working branches to GitHub are authorized. Keep private paths, hosts,
  usernames, credentials, and secrets out of commits and pull requests.
- Bring every change to `main` through a GitHub pull request, including hotfixes and release
  preparation. Direct pushes to `main` and destructive Git operations are prohibited.
  Follow [CONTRIBUTING.md](CONTRIBUTING.md) for self-review, validation, review and CI gates.
  Merging, tagging and publishing still require explicit approval.
- The user owns product version, release channel, stability, and publication. Set
  `development_build = 1` for the first changed installable state on each non-release branch.
  Increment only for subsequent changed installable states. Use SemVer for product changes,
  keep the NVDA manifest version numeric, and curate both unreleased changelogs into dated
  sections at release. Follow the [version and release guide](docs/en/development/release-and-build.md)
  for channel selection, Store upgrade notes, and explicitly authorized publication.
