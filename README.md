# Neovim Access Link

Neovim Access Link makes command-line Neovim practical with the NVDA screen
reader. Instead of reading every visible terminal update, it receives
structured information from Neovim itself. NVDA can therefore report what
actually happened: a mode change, cursor movement, edited text, a selection,
completion item, command-line message, or menu entry.

The result is focused editor feedback through speech, sounds, and advanced
Braille display support. Local Neovim on Windows and Neovim over SSH can use
the same accessible workflow.

[0.98.0 pre-release](https://github.com/helmsaccess/neovim-access-link/releases/tag/v0.98.0) —
release notes: [English](docs/en/development/changelog.md#0980) or
[German](docs/de/development/changelog.md#0980).

## What it helps with

Supported workflows include:

- Normal, Insert, and Visual editing with mode feedback;
- character, word, and line navigation with configurable cursor context;
- read-only speech exploration of characters and lines with `NVDA+h/j/k/l`,
  plus words with `Shift+NVDA+h/l`, without moving Neovim's real cursor;
- selections, editing, messages, buffer changes, and Neovim's built-in
  completion plus `nvim-cmp` and `blink.cmp`;
- LSP status, hover, signature and active-parameter feedback, completion item
  details, and completion reports for Neovim-owned rename operations;
- diagnostics from Neovim's provider-neutral diagnostic API, with navigation,
  held speech or Braille views, and separate error, warning, and empty-result
  cues;
- Neovim's command line and embedded terminal;
- the built-in `:Tutor` on Neovim 0.12, including accessible exercise
  assessments;
- the Lazy plugin manager, including its command bar, plugin row state, and
  conservative lifecycle feedback;
- copying Visual selections or register 0 to Windows and sending Windows
  clipboard text back to Neovim, locally and over SSH;
- configurable focus announcements with the current line, mode, and connection
  name; and
- file management through the Neovim plugin Oil, including navigation, rename
  preview, boundary sounds, and confirmation prompts.

## LSP, completion, and linters

Access Link does not replace or install language servers, completion plugins,
or linters. Neovim and the configured tools perform the language operation;
Access Link presents their results through Neovim's public LSP, completion, and
diagnostic APIs. The same accessible path can therefore serve different
languages and toolchains.

The guided reference workflow has been exercised with Pyright for Python LSP
features and Ruff through `nvim-lint` for diagnostics. Automated contract tests
also cover native completion, `nvim-cmp`, `blink.cmp`, `nvim-lint`, ALE, and
`none-ls.nvim`. Real automated linter processes include Clang-Tidy for C/C++,
ShellCheck for shell scripts, Staticcheck for Go, Clippy for Rust, RuboCop for
Ruby, and `markdownlint-cli2` for Markdown. These examples verify the shared
interfaces; they do not promise every provider version or project
configuration.

The [language-tools chapter](docs/en/manual/language-tools.md) explains the
boundary and provides a tested Pyright and Ruff setup.

## Braille and sound feedback

Advanced Braille support includes a structured editor line instead of
terminal-screen fragments, cursor routing in Normal, Insert, and command-line
modes, routing to the insertion position after the final character, optional
word and line editing with repeated routing presses, automatic cursor
following on long lines in Braille cursor mode, and standard display
navigation controls. The independent Braille exploration mode reads other
lines without moving the real cursor and preserves its manually selected
viewport. Speech exploration remains a separate speech feature and can
optionally present its virtual position on the Braille display.

Configurable sound feedback covers entering Insert or direct Terminal input,
the command line, returning to Normal or Terminal-normal, deletion,
replacement, matching errors, reaching the start or end of a line or file, and
crossing a line. Completion and spelling cues follow the relevant NVDA
settings. Indentation feedback also follows NVDA's Document Formatting setting
and can use speech, tones, both, or no additional output. These sound and
indentation paths have automated test coverage. Exploration also uses a short
two-note cue when its virtual reading position returns to its starting
character, word, or line.

Automated tests cover additional editor behavior. The
[feature matrix](docs/en/development/accessibility.md) distinguishes automated
coverage from practical NVDA testing.

## The Windows Terminal party trick

Windows Terminal can contain multiple windows, tabs, and horizontally or
vertically split panes. Each pane is effectively its own terminal. Neovim
Access Link can keep separate local and SSH Neovim connections in these areas
while ordinary PowerShell or SSH shells continue to use NVDA's normal terminal
support.

This mixed workflow has been practically tested with multiple windows, tabs,
split panes, local Neovim, remote Neovim, ordinary shell controls, and tmux.
After a Neovim area has been associated with F12 and remembered for the current
NVDA run, moving among the areas restores the matching editor context. The
add-on does not guess from window titles, prompts, accounts, or terminal text.

## Get started

Install the current `.nvda-addon`, focus Windows Terminal, and press
`NVDA+Alt+N` to enable the service. The gesture is available by default and
remains reassignable in NVDA's Input Gestures dialog. Install or update the
bundled Neovim components from the top-level `Neovim Access Link` menu in
NVDA, start Neovim, and press F12 once in each Neovim terminal area you want
to use.

The component dialog can leave an existing Neovim configuration unchanged,
install a small starter configuration with Lazy and Oil, or copy the local
Windows configuration to selected Linux connections with a backup on each
target.

Follow the [English Quick Guide](docs/en/manual/quick-guide.md) or
[German Quick Guide](docs/de/manual/quick-guide.md) for the exact accessible
steps.

Windows users who want a current development build can download or clone the
source, install Python 3.10 or newer, and double-click `build.cmd`. The launcher
downloads pinned build dependencies into a temporary environment and puts
the resulting `.nvda-addon` in `dist`; it does not change the system Python
environment. An internet connection is required while dependencies are
installed.

## Compatibility and status

The confirmed reference environment uses Windows 11, NVDA 2026.1.x, Windows
Terminal, local Windows Neovim 0.12.3, and Neovim 0.10.1 or 0.12.3 on Rocky
Linux 10 over Windows OpenSSH. Local Neovim 0.10.1 remains covered by
automated tests.

Windows Terminal is currently the only supported terminal front end. Portable
Windows layouts and `NVIM_APPNAME` are not supported. See
[compatibility](docs/en/development/compatibility.md) for exact boundaries.

This is beta software. Testing is risk-based rather than exhaustive. Braille
planning has broad automated coverage, and the principal routing, long-line,
navigation, exploration, and spelling-suggestion workflows have been tested
with a Papenmeier BRAILLEX EL 80c. Other NVDA-supported displays are expected
to use the same standard interfaces but are not part of that practical
hardware evidence. See
[current status](docs/en/development/current-status.md) for confirmed evidence
and remaining gaps.

## Documentation

The installed add-on opens the localized Quick Guide, user manual, and
developer documentation directly from NVDA's top-level `Neovim Access Link`
menu. The same sources are available here:

- [English user manual](docs/en/manual/README.md)
- [German user manual](docs/de/manual/README.md)
- [Developer overview](docs/en/development/overview.md)
- [Complete developer documentation](docs/en/development/README.md)

## Contributing, security, and license

Bug reports, practical testing, documentation improvements, and focused code
reviews are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) before submitting
changes and [SECURITY.md](SECURITY.md) for private security reports.

Neovim Access Link is licensed under `GPL-2.0-only`. See
[LICENSE](LICENSE). Contributors additionally grant the project maintainer the
relicensing rights described in [CONTRIBUTING.md](CONTRIBUTING.md); existing
GPL rights remain unaffected.
