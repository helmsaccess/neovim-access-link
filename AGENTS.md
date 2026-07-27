# Repository instructions for coding agents

This file defines repository-wide rules. System, developer and user instructions take precedence.
Subdirectories may provide a more specific `AGENTS.md`, which overrides this file for that subtree.

## Universal principles

- Preserve correctness, accessibility, reliability and security over performance.
- Inspect existing code, tests and documentation before editing.
- Do not guess. Ask before irreversible architectural changes.
- Prefer extending existing APIs over creating parallel ones.
- Prefer removing code over adding code.
- Keep changes small, reversible and consistent with existing patterns.
- Follow each component's and upstream API's established conventions; do not mix styles within a component or impose one component's style on another.
- Logging is diagnostic only; correctness must never depend on logs.
- Do not leave TODO comments unless explicitly requested.

## Git

- Never rewrite history or use destructive Git operations without permission.
- Preserve unrelated user changes.
- Use a dedicated feature branch for substantial work.
- Never merge into `main` without explicit approval.
- Write commit messages in English.

## Versioning

- The user exclusively owns the product version (`MAJOR.MINOR.PATCH`).
- Never classify or change build/release stability or channel without explicit user instruction.
- When setting a release version, update versioned README and changelog links in the same change.
- Use Semantic Versioning.
- Development builds use pre-release identifiers, e.g. `0.89.0-dev.12`.
- Each non-release branch owns an independent development-build sequence. Its first changed
  installable state must use `dev.1`, regardless of an inherited value or numbers used on
  `main`, its parent branch or other branches; increment only numbers assigned on that branch.
  Never use a release-only artifact version on a feature branch.
- Optional build metadata may include branch/commit, e.g. `0.89.0-dev.12+feature.nvim-api.a3f6c2d`.
- Build numbers increase only within a branch and are never carried between branches.
- Prefer CI/build-system generated build numbers. Otherwise maintain a branch-local counter.
- Every changed installable branch state must have a new `dev.N`; branch or commit metadata improves traceability but never substitutes for that increment. An unchanged reproducible rebuild may reuse its number.
- Keep version metadata in one machine-readable source.

## Documentation

- Update documentation together with implementation.
- Keep documentation accurate, understandable, internally consistent and ordered logically.
- Avoid ambiguous or misleading generalizations; state scope and limitations precisely.
- Present testing and support as risk-based best effort; never imply exhaustive coverage or promise response times.
- In manuals, name UI elements exactly as they appear in the localized interface; use the
  translation catalogs as the preferred source so instructions match what users encounter.
- Prefer inspecting locally available source code of target applications over web retrieval;
  sources for applications and add-ons are often available under `/tmp`.
- Before sending technical questions externally, check local source, project documentation and official documentation; ask only unresolved questions, with at most three per focused message.
- Add regression tests for bug fixes.
- A task is complete only when implementation, tests and documentation agree.
- Write project, collaboration and publication text in English, including issue,
  pull-request and release titles and descriptions. Documentation and localized
  user-facing text remain in their respective target language.
