# Changelog

This changelog summarizes completed changes by product version. The
[detailed history](changelog-history.md) preserves earlier development and
test-build entries through August 5, 2026.

## Unreleased

- Makes Neovim's built-in `:Tutor` specifically more accessible without adding
  separate tutorial logic. From Neovim 0.12, genuine unambiguous Tutor extmarks
  provide localized announcements when an assessment changes, the assessment
  when its line is read again, and persistent non-routable Braille markers.
  Other buffers and extmarks remain untouched. Invalid transitions are
  rejected before canonical state, while existing Braille routing and source
  mappings are preserved. On Neovim 0.10 the Tutor path is fully inactive and
  registers no observers. Isolated headless boundary tests and a real 0.12.3
  TUI contract test cover the scope.
- Restores NVDA's normal terminal behavior immediately after a remote Neovim
  instance exits. The SSH client now treats the authenticated bridge
  `disconnected` state as connection lifecycle rather than an ordinary editor
  event, even while SSH and the bridge remain alive. Invalid state values are
  rejected, and a later reconnect again requires a valid `fullState`.
- Adds a component-dialog configuration choice that remains unchanged by
  default and can install a basic configuration with Lazy, Oil, the bundled
  Access Link copy, actual tab characters on two-column tab stops, disabled
  line numbers, and leader commands for Oil and Lazy. The indentation
  remains fixed after filetype-specific Neovim defaults are applied. An
  isolated headless startup with local Access Link, Lazy, and Oil directories
  is checked under Neovim 0.10.1.
  Existing regular `init.lua` and `init.vim` files move to unique backup paths
  named in the results dialog before atomic replacement; failures restore the
  originals from the retained backups. Symbolic links and unusual targets
  remain unchanged, and component removal deletes neither configuration nor
  backups. The local Windows basic configuration has practical acceptance.
- Adds a second configuration path that safely copies the complete local
  Windows configuration directory to selected Linux connections. A bounded,
  link-free snapshot is transferred separately from the component package over
  SSH and validated again on the target; existing configurations are backed up
  as complete directories before atomic replacement. Windows-specific content
  and execute permissions are neither guessed nor rewritten. Lazy must still
  list the installed Access Link copy explicitly as a local plugin.
- Hardens component removal with an explicit warning that defaults to
  declining and a repeated results notice. The plugin and Linux bridge are
  removed; Neovim configuration and backups remain unchanged, including any
  explicit plugin load instruction that the user must remove when appropriate.
- Adds robust baseline support for `lazy.nvim`: Access Link gives the real
  Lazy buffer an unambiguous context name and speaks the complete command bar
  regardless of its initial blank line or width-dependent wrapping. Line
  navigation omits visual-only edge and padding spaces. Graphical private-use
  Unicode characters remain silent throughout the Lazy buffer, including
  speech exploration, while Braille retains the unmodified text. Only documented
  lifecycle events produce neutral start/end reports through speech and
  Braille. Plugin rows identified unambiguously through public icon highlights
  report NVDA's localized `collapsed` or `expanded` state when entered or
  toggled; Braille shows the corresponding tree-view markers `+` and `-`.
  Toggling does not obscure them with a transient Braille message, and existing
  NVDA line exploration reads the command bar again when needed. Unclear
  rendering remains silent. Synchronization collapses child operations
  without guessing progress, result, or success from Lazy's rendering.
- Adds four guided lazy.nvim practical tests for window operation, install,
  update, and synchronization. Isolated local Git fixtures and pinned headless
  contract tests verify actual end states without changing user configuration
  or installed plugins. The individual selector lists these tasks under
  plugin management. Technical preflight accounts for Lazy deliberately not
  opening its UI in headless mode; local fixture repositories run without
  line-ending conversion or distracting Git progress output.
  The F5 final-state check treats an empty optional path list consistently as
  an array instead of Lua `vim.NIL` and names the revisions and removals it
  actually confirmed. All four guided workflows were practically confirmed in
  the Windows/NVDA reference path; their completion reports remain explicitly
  neutral until F5 proves the Git end state.
- Integrates all eight German and English HTML documents into the add-on. A
  top-level `Neovim Access Link` menu opens settings, component management,
  and installed help selected for NVDA's language.
- Adds the default help file and a change log generated from the current
  German or English changelog section to the manifest.
  Development builds use the unreleased section; releases curate it into the
  version section and then reset it.
- Starts the 0.98.0 development line after the 0.97.0 pre-release.

## 0.97.0

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
