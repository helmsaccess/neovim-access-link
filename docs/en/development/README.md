# Developer documentation

This documentation explains how Neovim Access Link is built, how to develop a
change safely, and which claims are actually supported by code or tests. See
the [user manual](../manual/README.md) for operation of the installed add-on.

## Recommended starting path

New contributors should read these pages in order:

1. [Architecture](architecture.md) — mental model, terminology, components,
   and the complete path of one event from Neovim to NVDA.
2. [Repository layout](repository-layout.md) — where the corresponding sources
   and tests live.
3. [Development and test onboarding](getting-started.md) — prerequisites,
   first commands, and checks for common kinds of changes.
4. [Current status](current-status.md) — confirmed platforms, maturity, and
   known limitations of the current revision.

The first three documents explain durable relationships. Current status is a
snapshot and must not be used as an architecture specification.

## Continue by task

### Behavior or accessibility changes

- [Feature and accessibility matrix](accessibility.md)
- [Test strategy](testing.md)
- [Compatibility](compatibility.md)
- [NVDA 2026.1 API review](nvda-2026.1-api-notes.md)

### Connection, installation, or security changes

- [Protocol v2](protocol.md)
- [Component installation and SSH stdio](component-installation.md)
- [Security and privacy](security.md)
- [Latency](latency.md)

### Settings, localization, or release changes

- [Settings reference](settings-reference.md)
- [Localization with gettext](localization.md)
- [Release, version, and build process](release-and-build.md)
- [Bundled dependencies](dependencies.md)
- [Licensing and contributions](licensing-and-contributions.md)

## Decisions, planning, and history

Architecture decision records explain why a durable boundary was chosen. They
are neither user instructions nor substitutes for the current code.

- [ADR-0001: hybrid Neovim integration point](adr/0001-neovim-integration-point.md)
- [ADR-0002: NVDA API boundaries](adr/0002-nvda-api-boundaries.md)
- [ADR-0003: narrow Oil confirmation fallback](adr/0003-oil-confirmation-fallback.md)
- [ADR-0004: NVDA lifetime and application-event ownership](adr/0004-nvda-lifetime-and-event-ownership.md)
- [Active plan](plan.md)
- [Changelog](changelog.md)

## Which page is authoritative for what?

- `architecture.md` describes current components, responsibilities, and
  dependency boundaries.
- `protocol.md` is the reference for messages, validation, and controls.
- `security.md` defines trust boundaries and fail-open requirements.
- `testing.md` contains reproducible evidence and manual acceptance steps.
- `current-status.md` records confirmed platforms and remaining coverage gaps.
- `plan.md` describes intended work; a plan is not an implemented feature.
- `changelog.md` preserves chronology; an older entry does not automatically
  describe current behavior.
- Dated quality reviews record the comparison basis and evidence for one
  development state. Architecture, current status, and code govern behavior
  changed afterward.

Every claim should state its scope. For example, “Windows Terminal” must not be
generalized to “tab”: the code binds one concrete UI Automation `TermControl`,
which may represent a tab's content or a pane depending on the layout.

## Appendices: dated quality reports

The reports preserve their comparison basis, measurements, and contemporary
recommendations. They appear at the end of the built developer documentation
and replace neither current architecture, status, plan, nor source code.

- [Appendix A: Quality review of Global Plugin slimming, July 19, 2026, 20:04:03 CEST](quality-review-global-plugin-slimming-2026-07-19.md) — an
  intermediate review of the feature branch against `main`, including fixed
  regressions and the residual risks known at that time.
- [Appendix B: Analysis of the completed feature state against `v0.94.2`, July 21, 2026, 01:11:58 CEST](code-analysis-global-plugin-slimming-v0.94.2-2026-07-21.md) —
  a quantitative and qualitative final assessment of testability,
  maintainability, robustness, and added structural complexity.
