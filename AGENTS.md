# Repository instructions for coding agents

This root-level `AGENTS.md` applies to the entire repository. It is a concise
working map, not the complete product specification. The documents listed
below are the maintained public sources of truth. Direct system, developer,
and current user instructions take precedence over this file.

## Project goal and non-negotiable boundaries

- Build a low-latency, reliable, structured Neovim integration for NVDA
  2026.1.x on Windows and Neovim on Rocky Linux 10.
- Obtain editor state from Neovim APIs and semantic events. Do not substitute
  terminal screen scraping for structured data that Neovim can provide.
- Use polling between the NVDA add-on and Neovim plugin only as a fallback when
  no reliable event structure or event-driven solution exists.
- Keep transport, protocol, state modeling, speech/Braille planning, and
  focus/gating logic separated.
- Never block NVDA's main thread with SSH, DNS, network I/O, reconnects,
  substantial parsing, or slow logging.
- Suppress native terminal output only for the explicitly activated and
  authenticated Neovim session. Errors, disconnects, and deactivation must
  always fail open to normal NVDA output.
- Treat byte, Unicode code-point, virtual, and visual columns as distinct.
  Preserve correct behavior for UTF-8, tabs, combining characters, wide
  characters, and emoji.
- Use bounded queues, session and sequence validation, heartbeat, resync, and
  `fullState`. Never speak stale events or events from an unbound session.
- Use SSH and private local sockets by default. Do not expose network listeners,
  commit secrets, or execute code derived from untrusted protocol messages.

## Repository map and sources of truth

- `docs/de/development/current-status.md`: verified current behavior, known problems, recent tests,
  and next work.
- `docs/de/development/plan.md`: public active implementation plan.
- `docs/de/development/architecture.md` and `docs/de/development/adr/`: boundaries, threading model, and decisions.
- `docs/de/development/protocol.md` and `protocol/`: wire format, validation, sequencing, and resync.
- `docs/de/development/accessibility.md`: feature and accessibility coverage matrix.
- `docs/de/development/compatibility.md`: tested NVDA, Windows, Rocky Linux, Neovim, and Python
  versions.
- `docs/de/development/security.md`, `docs/de/development/testing.md`,
  `docs/de/development/latency.md`, and `docs/de/development/changelog.md`: operational
  requirements and evidence.
- `neovim-plugin/`, `bridge/`, and `nvda-addon/`: Linux editor, transport, and
  Windows NVDA components respectively.

Update the relevant source-of-truth documents while implementing a change, not
only at the end. Architectural decisions, rejected approaches, measurements,
and known limitations must not exist only in chat or commit messages.

## Working practices

- Before editing, inspect the affected implementation, tests, and relevant
  documentation. Prefer small, reversible changes that follow local patterns.
- Preserve user configuration and unrelated worktree changes. Do not use
  destructive Git operations or rewrite history without explicit permission.
- Do not change system-wide configuration or install system-wide packages
  without explicit authorization, justification, and documented rollback.
- Never disturb, attach to, stop, or replace a user's existing tmux or Neovim
  session merely to run tests.
- Never place real usernames, hostnames, account names, organization domains,
  home-directory paths, process/window identifiers, or other workstation
  fingerprints in maintained source, tests, documentation, examples, or build
  artifacts. Use explicit placeholders and reserved domains such as
  `example.invalid`. Keep diagnostic and local test material only in ignored
  `tmp/` or `debug/incoming/` paths and redact it before sharing.
- Prefer public, stable NVDA and Neovim APIs. Before adding a dependency,
  document its purpose, license, maintenance state, size, latency impact, and
  installation/packaging impact.
- Follow the official NVDA add-on conventions, Add-on Template structure, and
  public NVDA APIs as closely as the product permits. Any use of a private,
  deprecated, unstable, or convention-breaking NVDA interface requires a
  separate ADR or compatibility note before release. That document must name
  the interface, explain why no public alternative is sufficient, describe
  risks and affected NVDA versions, and state a migration or removal plan.
- For a fundamental uncertainty: research alternatives, build the smallest
  useful prototype, measure behavior, document the result, and then implement
  the most reversible sound option.

## Tests and completion criteria

- Add a regression test for every bug fix. Exercise new behavior proportionate
  to risk, including cancellation, disconnect/reconnect, delayed events,
  Unicode, empty buffers, and multiple sessions where relevant.
- Test Lua with real `nvim --headless` where possible. Keep Python core logic
  testable without a running NVDA instance. Packaging tests must extract and
  import the actual built add-on.
- If the local sandbox prevents socket, TUI, or SSH tests, run them on an
  isolated test host without touching existing user sessions.
- Before committing, run the relevant tests and `git diff --check`. Before
  handing an installable build to the user, run the appropriate Add-on/Core,
  protocol, Bridge/TUI, Lua, packaging, and documentation checks.
- For user-observable fixes, provide a compact manual test procedure and allow
  time for the user's practical test before asking for commit approval. Do not
  commit merely because automated tests pass; ask only after the user reports
  the practical result, unless the user explicitly requested an immediate
  commit.
- Document manual tests with prerequisites, exact commands and keystrokes,
  expected output, actual output, and result. Never place confidential editor
  text, passwords, or tokens in logs or test artifacts.
- A task is complete only when implementation, regression tests, fail-open and
  security behavior, documentation, compatibility information, and known
  follow-up work agree.

Common verification entry points are:

```bash
PYTHONPATH=protocol/python:bridge/python:nvda-addon/core python3 -m unittest discover -s nvda-addon/tests
PYTHONPATH=protocol/python:bridge/python:nvda-addon/core python3 -m unittest discover -s protocol/python/tests
PYTHONPATH=protocol/python:bridge/python:nvda-addon/core python3 -m unittest discover -s bridge/python/tests
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
```

Run the Lua specs under `neovim-plugin/tests/*_spec.lua` with the installed
minimum supported Neovim version. See `docs/de/development/testing.md` for environment-specific and
manual end-to-end commands.

## Branch and merge workflow

- Before changing files, compare the active branch name and recent branch work
  with the current task. A feature, fix, cleanup, or experiment branch must be
  used only for its stated purpose; do not place unrelated work on it merely
  because it is already checked out.
- If the current request does not clearly belong to the active branch, switch
  to the appropriate existing branch or create a suitably named branch. When
  branch ownership, intended scope, or the correct base is uncertain, ask the
  user before editing or committing.
- Use a dedicated feature branch for substantial features, cross-component
  changes, architectural work, risky migrations, or work expected to require
  several commits. Use a descriptive `feature/<topic>` name unless the user
  requests another convention.
- Small, isolated documentation updates or low-risk fixes may be committed on
  the current branch when that matches the user's request.
- Keep feature-branch commits logically scoped and tested. Do not mix unrelated
  cleanup into a feature.
- When a feature appears complete, do not merge it into `main` automatically.
  Report the implemented behavior, tests, remaining limitations, branch name,
  and relevant commits, then explicitly ask the user whether it should be
  merged into `main`.
- Merge only after the user confirms. After merging, verify the active branch,
  clean worktree, merge commit, and relevant build/test status.

## Versions and build artifacts

- The user exclusively chooses the product/release version and release channel.
  Coding agents must not invent, advance, reinterpret, or normalize that
  product version without explicit user approval.
- Coding agents own the monotonically increasing build number within the
  user-selected product version. If shipped code, bundled components, or other
  installable content changed since the last build, increment the build number.
- Keep product identity and version metadata in one central, machine-readable
  source file. Manifest data, runtime diagnostics, package filenames and build
  metadata must be derived from it; do not duplicate product names, author or
  version literals across source files. Generated artifacts may contain the
  derived values required by NVDA.
- Do not repeatedly overwrite a materially different build under the same
  versioned filename. Each new build supplied for testing must have a distinct,
  traceable version or pre-release identifier and filename. Rebuilding the same
  revision reproducibly may retain its existing name.
- The generated NVDA manifest version must follow the Add-on Store's numeric
  `major.minor` or `major.minor.patch` convention and remain strictly orderable.
  A separate derived display label may include words such as `build` or
  `beta`, but it must not replace the store-compatible manifest version.
  Create stable tags/releases only after explicit approval.
- Keep source and maintained Markdown in Git. Put installable artifacts in
  `dist/`, generated combined documentation in `build/`, and private or
  temporary test material in ignored `tmp/`.

## Nested instructions

If a subtree later needs specialized commands or conventions, place a concise
`AGENTS.md` or temporary `AGENTS.override.md` in that directory. Its instructions
apply only to that subtree and take precedence there. Avoid growing this root
file into a duplicate of the detailed project documentation.
