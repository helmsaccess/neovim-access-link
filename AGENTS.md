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
- Current implementation and support limits: `current-status.md` and `compatibility.md`;
  completed changes: `changelog.md`; planned work: `plan.md`.
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
- Before web research, check `../nvda-shared-aux/`; store NVDA and add-on sources or references
  there when they are likely to remain useful across add-ons.
- Use `../nal-aux/` for all Neovim Access Link-specific temporary sources, tools, test
  workspaces, reproductions, and reports.
- Follow the established conventions of each component and upstream API; do not impose one
  component's style on another.
- Avoid meta-commentary about instructions, process, or text organization. State the actionable
  rule or result directly unless context is necessary for safety or traceability.
- Logging is diagnostic only; correctness must never depend on it.
- Do not add unowned TODOs. Record intentional follow-up work with scope and a durable reference.
- For bug fixes, add a regression test where practical.
- Keep behavior, tests, architecture records, and affected German and English documentation
  current in the same change. Changes to behavior, support, architecture, compatibility,
  developer workflows, or release state also update both languages of `current-status.md` and
  `changelog.md`; do not complete the change while either snapshot or history is stale.

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
- Development and CI may build packages and rendered documentation only in disposable test
  directories. Normal development artifacts are created in the synchronized Windows workspace;
  an explicitly approved release is built from clean Linux `main` with the release builder.
- Full prerequisites and build checks are documented in `docs/de/development/testing.md`.

## Workspace synchronization and artifact builds

- The Linux checkout is the development source of truth. Configure its persistent Windows-visible
  worktree with `python3 tools/windows_workspace_sync.py configure /nfs/src/neovim-access-link`.
  Git hooks then mirror committed branches and the selected branch asynchronously. Synchronization
  updates only Git-managed state and must abort on tracked target changes or untracked collisions;
  never clean, reset, or replace ignored virtual environments, human-test state, or build output.
  Linked Linux worktrees share one serialized queue; the most recent triggering worktree selects
  the target branch. Rerun `configure` after changing the synchronization tool or its hooks.
- Use `bash tools/build_documentation.sh --test-only` only for disposable documentation validation.
  Package tests may call Python builders with explicit temporary output directories.
- Create development artifacts from the synchronized Windows worktree with parameterless
  `build.cmd`. For an explicitly approved release state with `development_build = None`, use
  parameterless `python3 tools/build_release.py` from clean Linux `main`. Both entry points reuse
  the same isolated renderer and packagers, verify a stable source snapshot, and publish exactly
  the matching add-on and documentation ZIP to `dist`. Do not invoke internal builders directly
  for publication.

## Git, versioning, and releases

- Never use destructive Git operations. Do not push, merge, tag, release, or otherwise publish
  externally without explicit user authorization.
- Use a focused feature branch for substantial work. Create focused English commits
  independently after relevant validation instead of waiting for a separate commit request.
- Before an authorized merge, review the branch history and squash fixup or noisy intermediate
  commits when that produces coherent, traceable units. Never rewrite already shared history
  without explicit authorization.
- The user owns `MAJOR.MINOR.PATCH`, release channel, stability, tags, and publication approval.
- On every new non-release branch, the first changed installable state uses
  `development_build = 1`, regardless of inherited or other branch values. Increment only for
  changed installable states on that branch; an unchanged reproducible rebuild may reuse it.
- Keep version metadata in `buildVars.py`. A release-version change also updates README release
  and German/English changelog links in the same change.
- Record development changes under German `Unveröffentlicht` and English `Unreleased`. When
  `development_build` becomes `None`, curate them into the matching version section with only
  changes since the preceding published release, then reset the unreleased section.
- Before publication, validate the built base and localized manifests against the current official
  NVDA AddonTemplate. Populate every applicable template field; omit one only when it is genuinely
  inapplicable, and treat unknown, malformed, or empty applicable fields as release blockers.
- GitHub releases contain the `.nvda-addon` plus one ZIP with all eight German and English
  quick-guide, handbook, developer-documentation, and guided-human-testing HTML files.

### GitHub release contract

- Release only from an explicitly approved, clean `main`: push the release commit and its existing
  `v<VERSION>` tag first, and require `gh release create --verify-tag` rather than allowing GitHub
  to create a tag implicitly.
- Build the final two assets on Linux with `python3 tools/build_release.py` before tagging. Require
  the release metadata, clean `main`, final test results, and exact expected asset names.
- Use title `Neovim Access Link <VERSION>`. Versions below `1.0.0` are published with
  `--prerelease --latest=false`; versions from `1.0.0` onward are regular releases with `--latest`.
- Attach exactly `dist/NeovimAccessLink-<VERSION>.nvda-addon` and
  `dist/neovim-access-link-<VERSION>-documentation.zip`. Do not attach the standalone server
  package; it is embedded in the add-on.
- Write curated English notes to a temporary file under `../nal-aux/`. Summarize changes
  since the immediately preceding published version, relevant compatibility or test boundaries,
  tag-pinned documentation links, and the purpose of both assets.
- Use this non-interactive command shape, substituting the placeholders and status flags above:

  ```bash
  gh release create "v{VERSION}" "dist/NeovimAccessLink-{VERSION}.nvda-addon" \
    "dist/neovim-access-link-{VERSION}-documentation.zip" \
    --repo helmsaccess/neovim-access-link --verify-tag --fail-on-no-commits \
    --title "Neovim Access Link {VERSION}" --notes-file "{RELEASE_NOTES_FILE}" {STATUS_FLAGS}
  ```
- After publication, verify the tag target, title, draft/pre-release/latest state, notes, exact two
  asset names, and successful downloads. Do not replace a published tag or asset silently.

## Documentation and publication

- Keep documentation accurate, understandable, internally consistent, and logically ordered.
- Current-facing documentation describes only the present implementation. Keep history in
  changelogs, explicitly dated reports, and ADRs; mark an ADR as superseded and link its
  replacement when the decision no longer governs the current architecture.
- Use prose, lists, and tables according to the reader's task. Lists and tables must materially
  improve scanning or comparison; use them with judgment rather than as a default or an obstacle.
- State scope, limitations, testing, and support as risk-based best effort; do not imply
  exhaustive coverage or response-time guarantees.
- In manuals, use localized UI names from the translation catalogs.
- Never commit private paths, hostnames, usernames, domains, credentials, or secrets.
- Before asking technical questions externally, check code and official documentation; ask only
  unresolved questions, with at most three per focused message.
- Write commits, issues, pull requests, release text, and other project collaboration text in
  English. Documentation and localized user-facing text remain in their target language.
