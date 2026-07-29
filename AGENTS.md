# Repository instructions for coding agents

This file defines repository-wide rules. More specific `AGENTS.md` files in component
directories add rules for their subtree. System, developer, and explicit user instructions
take precedence.

## Mission and non-negotiable invariants

- Build a low-latency, reliable Neovim integration for NVDA on Windows and Neovim on Linux.
- Prefer Neovim APIs and semantic events; use screen scraping only as a documented fallback.
- Keep transport, protocol validation, canonical state, speech/Braille planning, and focus
  ownership separated.
- Never block NVDA's main thread with network I/O, reconnects, parsing, or logging.
- Fail open: on disconnects, invalid state, or internal errors, preserve native NVDA and
  terminal behavior.
- Treat protocol data and discovered sessions as untrusted until authenticated and validated.
- Use SSH stdio, private Unix sockets, and loopback-only local TCP. Never bind local services to
  non-loopback interfaces or execute protocol data.

## Repository map

- `nvda-addon/`: NVDA integration, Windows Terminal AppModule, UI, presentation, and add-on
  packaging. Follow `nvda-addon/AGENTS.md`.
- `neovim-plugin/`: Lua plugin and semantic Neovim event production. Follow
  `neovim-plugin/AGENTS.md`.
- `bridge/`: stdio, RPC, and connection bridge. Follow `bridge/AGENTS.md`.
- `protocol/`: shared protocol types, framing, and validation. Follow `protocol/AGENTS.md`.
- `docs/`: German and English user and developer documentation. Follow `docs/AGENTS.md`.
- `tools/`: repository test, build, localization, and release entry points.

## Documentation map

- Start with `docs/de/development/README.md` or its synchronized English mirror
  `docs/en/development/README.md`.
- Architecture or ownership changes: `architecture.md` and the relevant ADR.
- Protocol or trust-boundary changes: `protocol.md`, `security.md`, and the relevant ADR.
- Tests, builds, or releases: `testing.md` and `release-and-build.md`.
- Current support and remaining limits: `current-status.md`, `compatibility.md`, and `plan.md`.
- German developer documentation is the technical source of truth; update its English mirror
  in the same change so both languages make the same claim.

## Working rules

- Inspect relevant code, tests, and authoritative documentation before editing.
- Make reversible, in-scope assumptions explicit; ask before consequential or irreversible
  architectural choices.
- Preserve the documented architecture and established component boundaries. Reuse existing
  structures and interfaces; extend them only for a demonstrated need.
- Prefer simplification and deletion over new layers, state, or parallel paths when tests show
  required behavior is preserved.
- Preserve unrelated user changes and keep changes focused.
- Follow the established conventions of each component and upstream API; do not impose one
  component's style on another.
- Logging is diagnostic only; correctness must never depend on it.
- Do not add unowned TODOs. Record intentional follow-up work with scope and a durable reference.
- For bug fixes, add a regression test where practical.
- Keep behavior, tests, architecture records, and affected German and English documentation
  current in the same change; do not knowingly leave stale documentation behind.

## Validation

- Use `python3 tools/run_tests.py quick` for fast unit feedback.
- Use `python3 tools/run_tests.py all-safe` for unit, package, and listener-free Lua tests.
- Run `python3 tools/run_tests.py ssh` separately for mocked SSH, Askpass, and failure paths.
- Run `python3 tools/run_tests.py socket` separately where local TCP and Unix sockets and
  disposable Neovim TUI processes are permitted.
- `python3 tools/run_tests.py all` orchestrates the safe, SSH, and socket phases sequentially;
  it does not make restricted environments suitable for socket tests.
- Keep tests classified as `unit`, `package`, `lua`, `ssh`, or `socket`, and keep parallel jobs
  independent with no shared mutable paths, processes, or sessions.
- Treat restricted-sandbox listener failures as environment limitations; validate affected
  socket, TUI, or session code in a permitted environment before push or release.
- Before handing changes back to the user, rebuild every affected distributable artifact from
  the final worktree state. Documentation-only changes require a fresh documentation build;
  changes only to installable add-on or component code require a fresh `.nvda-addon` build; when
  both areas changed, rebuild both. Do not rebuild an unaffected artifact merely to refresh it.
- Full prerequisites and build checks are documented in `docs/de/development/testing.md`.

## Git, versioning, and releases

- Never use destructive Git operations. Do not push, merge, tag, release, or otherwise publish
  externally without explicit user authorization.
- Use a focused feature branch for substantial work. Create focused English commits
  independently after relevant validation instead of waiting for a separate commit request.
- Before an authorized merge, review the branch history and squash fixup or noisy intermediate
  commits when that produces coherent, traceable units. Never rewrite already shared history
  without explicit authorization.
- The user owns `MAJOR.MINOR.PATCH`, release channel, stability, tags, and prerelease status.
- On every new non-release branch, the first changed installable state uses
  `development_build = 1`, regardless of inherited or other branch values. Increment only for
  changed installable states on that branch; an unchanged reproducible rebuild may reuse it.
- Keep version metadata in `buildVars.py`. A release-version change also updates README release
  and German/English changelog links in the same change.
- GitHub releases contain the `.nvda-addon` plus one ZIP with all six German and English
  quick-guide, handbook, and developer-documentation HTML files.

## Documentation and publication

- Keep documentation accurate, understandable, internally consistent, and logically ordered.
- State scope, limitations, testing, and support as risk-based best effort; do not imply
  exhaustive coverage or response-time guarantees.
- In manuals, use localized UI names from the translation catalogs.
- Prefer locally available target-application or add-on source, often under `/tmp`, over web
  retrieval. Never commit private paths, hostnames, usernames, domains, credentials, or secrets.
- Before asking technical questions externally, check code and official documentation; ask only
  unresolved questions, with at most three per focused message.
- Write commits, issues, pull requests, release text, and other project collaboration text in
  English. Documentation and localized user-facing text remain in their target language.
