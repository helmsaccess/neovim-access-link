# Changelog

This changelog summarizes completed changes by product version. The
[detailed history](changelog-history.md) preserves earlier development and
test-build entries through August 5, 2026.

## Unreleased

- Starts the 0.97.0 development line after the 0.96.0 beta pre-release.
- Adds the HTTPS project URL to the add-on manifest.
- Adds an optional parameterless Windows build from source. A temporary Python
  environment leaves the system installation unchanged, while the embedded
  Linux package receives portable Python modules and reproducible Unix
  metadata.
- Adds Insert-mode LSP active-parameter speech and held, read-only signature,
  parameter, and diagnostic views with correlated speech and Braille.
- Hardens native completion, `nvim-cmp`, and `blink.cmp`, including
  documentation resolution, menu cues, and the no-selected-candidate state.
  It also fixes the practical-test preflight incorrectly rejecting Blink's
  intentionally disabled automatic menu display.
- Makes native incremental search, `inccommand` replacement previews, Quickfix
  and location lists, replacement prompts, multi-buffer replacement, and LSP
  rename completion accessible. Neovim and the language server retain
  execution; Access Link coalesces internal buffer, cursor, and context changes
  into one evidence-based completion report. Automated multi-file tests cover
  Quickfix files, listed buffers, and argument files; guided L4 through L6
  isolate the remaining practical NVDA checks.
- Unifies diagnostics from LSP, `nvim-lint`, ALE, and `none-ls.nvim`, extends
  navigation commands, and adds distinct error, warning, and empty-result
  cues. On Windows, the Clang-Tidy practical test launches the pinned binary
  directly, uses an explicit C mode and supplied test configuration, and
  consumes both output streams. One bounded wait allowance accommodates cold
  provider starts on Windows and network drives.
  Markdownlint checks the absolute fixture instead of relying on an unreliable
  cold stdin run. Setup probes real linter output first and collects failures
  from all selected profiles in one run.
- Fixes Linux session discovery across differing runtime environments and
  without `XDG_RUNTIME_DIR`, plus focus and remembered-binding paths after the
  optional F12 question.
- Separates safe, SSH, and socket verification into independent test phases
  and expands reproducible completion, LSP, linter, and guided practical tests.
  Compact task cards state purpose, numbered steps, and pass condition; F2
  repeats the task while F1 and F11 remain free because of Neovim and Windows
  Terminal default bindings.
- Updates selection and LSP test APIs for Neovim 0.12 while retaining Neovim
  0.10 compatibility.
- Restructures the Quick Guide and manual around reader tasks. One real,
  tested Lua example generates identical code blocks for GitHub and the German
  and English HTML manuals.
- Clarifies the Global Plugin's remaining process-wide role after a renewed
  architecture audit without broadening the AppModule-owned event path.
- Reorganizes developer documentation around onboarding, current explanation,
  tasks, references, and decisions; removes stale transport claims and adds a
  dedicated CI build with automated German/English structure and HTML metadata
  validation.

## 0.96.0

- Adds structured Braille, cursor routing, standard navigation, and a
  per-session Braille exploration mode.
- Makes Neovim's built-in `z=` spelling suggestions accessible through speech,
  Braille, and contextual NVDA commands.
- Aligns spelling feedback with NVDA document formatting and stabilizes
  Braille viewports across focus, session, and text changes.

## 0.95.2

- Introduces speech exploration by character, word, and line without moving
  the real Neovim cursor.
- Adds origin cues and separate detail settings for normal navigation and
  exploration release.

## 0.95.1

- Slims the Global Plugin into a composition root with dedicated services for
  focus, assignment, editor state, connections, settings, Braille, and runtime
  ownership.
- Preserves local and SSH sessions across multiple Windows Terminal windows,
  tabs, and panes, including clipboard and component management.

## 0.95.0 (beta)

- Moves Windows Terminal events, overlay selection, `nextHandler`, and
  assignable terminal commands into the AppModule.
- Restricts F12 to the concrete AppModule and `TermControl` identity and
  prevents an inserted `<F12>` during an Insert-mode assignment.
- Uses NVDA's Windows bindings and coding conventions in NVDA-side code.

## 0.94.2

- Structures user and developer documentation from basic concepts through
  architecture, current status, plan, and history.
- Aligns UI labels with the gettext catalog and NVDA source and describes
  testing and support as a risk-based best-effort process.

## 0.94.1

- Ships the complete German gettext catalog with reproducible catalog, MO, and
  package verification.

## 0.94.0 (prerelease)

- Unifies the product ID, package names, configuration section, and artifact
  prefix under `NeovimAccessLink`.

## 0.93.0 (prerelease)

- Hardens terminal and buffer switching, structured command-line and process
  messages, and window and tab context output.
- Fixes reassignment from a terminated local session to an SSH Neovim session.

## 0.92.0 beta pre-release

- Adds configurable focus presentation, control-specific Windows Terminal
  isolation, and explicit clipboard commands for local and SSH connections.

## 0.91.0 beta release

- Introduces control-specific Windows Terminal assignment with fail-open focus
  transitions and one-shot F12 authorization.
- Practically confirms local and remote connections across multiple tabs and
  split panes.

## 0.90.0 beta release

- Adds practically confirmed focus context with file, mode, and configured
  connection name.

## 0.89.35 beta release

- Hardens session registration and Windows Terminal bindings for local and
  remote Neovim sessions.
- Takes over Neovim's external UI only after authenticated registration and
  returns it fail-open to the native TUI on errors.
