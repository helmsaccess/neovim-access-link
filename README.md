# Neovim Access Link

Neovim Access Link makes command-line Neovim practical with the NVDA screen
reader. Instead of reading every visible terminal update, it receives
structured information from Neovim itself. NVDA can therefore report what
actually happened: a mode change, cursor movement, edited text, a selection,
completion item, command-line message, or menu entry.

The result is focused editor feedback through speech and sounds, with
experimental Braille support also included. Local Neovim on Windows and
Neovim over SSH can use the same accessible workflow.

[Current GitHub release](https://github.com/helmsaccess/neovim-access-link/releases/tag/v0.95.1) —
release notes for 0.95.1: [English](docs/en/development/changelog.md#0951) or
[German](docs/de/development/changelog.md#0951).

## What it helps with

Practically tested workflows include:

- Normal, Insert, and Visual editing with mode feedback;
- character, word, and line navigation;
- selections, editing, messages, built-in completion, and buffer changes;
- Neovim's command line and embedded terminal;
- copying Visual selections or register 0 to Windows and sending Windows
  clipboard text back to Neovim, locally and over SSH;
- configurable focus announcements with the current line, mode, and connection
  name; and
- file management through the Neovim plugin Oil, including navigation, rename
  preview, boundary sounds, and confirmation prompts.

Configurable sound feedback covers entering Insert or direct Terminal input,
the command line, returning to Normal or Terminal-normal, deletion,
replacement, matching errors, reaching the start or end of a line or file, and
crossing a line. Completion and spelling cues follow the relevant NVDA
settings. Indentation feedback also follows NVDA's Document Formatting setting
and can use speech, tones, both, or no additional output. These sound and
indentation paths have automated test coverage.

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

Install the current `.nvda-addon`, assign an activation gesture while Windows
Terminal is focused, and install or update the bundled Neovim components from
NVDA's Tools menu. Start Neovim, enable the service, and press F12 once in each
Neovim terminal area you want to use.

Follow the [English Quick Guide](docs/en/manual/quick-guide.md) or
[German Quick Guide](docs/de/manual/quick-guide.md) for the exact accessible
steps.

## Compatibility and status

The confirmed reference environment uses Windows 11, NVDA 2026.1.x, Windows
Terminal, local Windows Neovim, and Neovim on Rocky Linux 10 over Windows
OpenSSH. Neovim 0.10.1 is the reference version; selected local Windows and
file-management workflows with Oil have also been tested with Neovim 0.12.3.

Windows Terminal is currently the only supported terminal front end. Portable
Windows layouts and `NVIM_APPNAME` are not supported. See
[compatibility](docs/en/development/compatibility.md) for exact boundaries.

This is alpha-to-beta software. Testing is risk-based rather than exhaustive.
Braille planning is covered by automated tests, but no physical Braille display
has been tested yet. See [current status](docs/en/development/current-status.md)
for confirmed evidence and remaining gaps.

## Documentation

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
