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
- Use Semantic Versioning.
- Development builds use pre-release identifiers, e.g. `0.89.0-dev.12`.
- Optional build metadata may include branch/commit, e.g. `0.89.0-dev.12+feature.nvim-api.a3f6c2d`.
- Build numbers increase only within a branch.
- Prefer CI/build-system generated build numbers. Otherwise maintain a branch-local counter.
- Every installable build must have a unique version or filename.
- Keep version metadata in one machine-readable source.

## Documentation

- Update documentation together with implementation.
- Keep documentation accurate, understandable and ordered logically.
- Avoid ambiguous or misleading generalizations; state scope and limitations precisely.
- Add regression tests for bug fixes.
- A task is complete only when implementation, tests and documentation agree.
- Write project, collaboration and publication text in English, including issue,
  pull-request and release titles and descriptions. Documentation and localized
  user-facing text remain in their respective target language.
