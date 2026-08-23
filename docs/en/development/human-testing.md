# Guided practical tests with NVDA

## Purpose and scope

These practical tests check a finished Neovim Access Link build only where an
automated test cannot decide reliably: real NVDA speech, audible sounds, a
physical Braille display, held NVDA gestures, and actual focus in Windows
Terminal. One task combines related perceptions of the same interaction, so
Neovim does not have to start twice with the same fixture merely to separate
speech from sounds. LSP responses,
diagnostic ranges, jump targets, adapter state, and file formats remain the
responsibility of automated tests.

The automatic-parameter task therefore assesses only whether real Pyright
transitions are spoken clearly without disruptive delay and whether Braille
stays on source text. Resolver behavior, nesting, overloads, returning to an
already filled parameter, deduplication, bounds, and stale replies have
separate automated regressions.

The fixtures nevertheless provide deliberate real choices: at least three
completion candidates, two function signatures with three parameters each,
and two diagnostics on the first diagnostic line. Thus, an instruction to
cycle always causes a visible content change. The smoke suite's audio portions
cover all five distinct sounds in this area: completion menu opened,
completion menu closed, diagnostic warning, diagnostic error, and confirmation
of an explicit diagnostic query with no match. Information and hint
diagnostics intentionally have no dedicated diagnostic sound and are therefore
not presented as additional sound types.

The runner is intended even for testers with little Neovim experience. Before
every task, it structures the instruction as follows:

| Display | Meaning |
| --- | --- |
| **Purpose of this test** | feature being checked and why it matters |
| **Keys and steps** | short numbered sequence with the effect of each key |
| **Pass when** | expected perceptible output |
| `Escape`, then `F2` | display and report the test ID, purpose, steps, and pass condition again in Neovim |
| `Escape`, then `F10` | safely close test Neovim and return to runner PowerShell |

Hard line breaks separate numbered steps only. Windows Terminal wraps longer
lines to its current width, so a maximized window uses the available space.
Longer native workflows are assigned to the function keys named by the task;
testers do not have to enter colon commands. The personal `init.lua`, Lazy
configuration, and Neovim data directories are not changed.

## Which suite should be used?

| Suite | Contents | When to run it |
| --- | --- | --- |
| `smoke` | native LSP, search, replacement, and completion, Ruff diagnostics, focus isolation, and fail-open behavior | normal practical check; recommended, about 20 to 30 minutes |
| `compatibility` | nvim-cmp and blink.cmp completion menus, C/Clang-Tidy and Markdown/markdownlint diagnostics, and lazy.nvim plugin management | after changes to adapters, linter integration, plugin management, or dependencies |
| `all` | both suites in one result | only when both areas are affected |
| individual selection | individual tasks grouped by category in the menu | targeted recheck of an affected area; saves time and unnecessary downloads |

| Individual-selection category | Examples |
| --- | --- |
| LSP and language intelligence | LSP status, automatic active parameters, held function signatures, native search/replacement, and LSP rename |
| Completion | native completion, nvim-cmp, and blink.cmp |
| Diagnostics and linters | Ruff, Clang-Tidy, and markdownlint |
| Session and terminal integration | focus isolation and fail-open behavior |
| Plugin management | lazy.nvim window, installation, update, and synchronization |

### Stable test IDs

Every task has a unique two-character ID. The first letter identifies its
category (`L` for LSP/language intelligence, `C` for completion, `D` for
diagnostics, `S` for session integration, and `P` for plugin management); the second character
distinguishes tasks. IDs are never renumbered or reused. They appear in the
selection menu, before every task, in the JSON result, and when `F2` is pressed
in test Neovim. Thus, “failure in D3” is an unambiguous reference.

| ID | Task |
| --- | --- |
| `L1` | LSP status |
| `L2` | automatic active parameters |
| `L3` | held function signatures and parameters |
| `L4` | native search, Quickfix, and project-wide replacement |
| `L5` | native LSP rename across files |
| `L6` | native replacement across listed buffers |
| `C1` | native completion |
| `C2` | nvim-cmp |
| `C3` | blink.cmp |
| `D1` | Python/Ruff diagnostics |
| `D2` | held diagnostics |
| `D3` | C/Clang-Tidy diagnostics |
| `D4` | Markdown/markdownlint diagnostics |
| `S1` | focus isolation and disconnect |
| `P1` | lazy.nvim window and navigation |
| `P2` | installation of an isolated test plugin |
| `P3` | update of an isolated test plugin |
| `P4` | synchronization with install, update, and cleanup |

Standard tasks always run in this order: native LSP, diagnostics, then focus
isolation. Missing audio or a missing Braille display does not prevent the
other tasks. Without audio, explicitly conditional sound portions are not
assessed and the JSON environment records that fact. Tasks requiring physical
Braille hardware are marked `notApplicable` automatically.

## Two views in the same terminal tab

This distinction is important:

| View | What happens there | How to leave it |
| --- | --- | --- |
| **Runner PowerShell** | start `run.ps1`, read the instruction, and select the outcome after the task | Enter starts the announced task in test Neovim |
| **Test Neovim** | perform exactly the one announced task | `Escape`, then `F10` closes only test Neovim; the same runner PowerShell reappears |

Only the focus task requires a second Windows Terminal tab. The runner says
exactly when to open and leave it. All other work stays in the original tab.

## Prerequisites

| Prerequisite | What it is needed for |
| --- | --- |
| Windows 11, Windows Terminal, and NVDA with the build under test | the practical test itself |
| current local Neovim components installed through the NVDA menu | the connection between Neovim and Access Link |
| Neovim 0.12.x, Git for Windows, Node.js LTS, and Python 3.12 | isolated test environment, LSP, linters, and completion plugins |
| internet access during initial setup | downloading pinned test dependencies |
| audio output | sound portions of completion and diagnostic workflows; without audio only speech and usability are assessed |
| physical Braille display | Braille tasks only; without one they are marked `notApplicable` |

The runner compares the runtime code of the installed Neovim plugin with the
current repository. If they differ, reinstall local components from the NVDA
menu first. This prevents an old plugin revision from being assessed by
mistake.

## Beginner-friendly start

### 1. Open PowerShell in the correct directory

Open an ordinary PowerShell in Windows Terminal. Change to the repository
root: the directory containing `tests`, `docs`, `neovim-plugin`, and
`nvda-addon`, among other entries. For example:

```powershell
Set-Location "C:\path\to\the\repository"
Get-ChildItem tests\human\framework\run.ps1
```

The second command must display `run.ps1`. If it does not, PowerShell is still
in the wrong directory.

### 2. Start the runner

```powershell
.\tests\human\framework\run.ps1
```

If the local execution policy blocks direct startup:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\tests\human\framework\run.ps1
```

Select **Start a new short standard test**. This menu item deliberately starts
a new JSON file; after an interruption, select **Resume an incomplete run**
instead. An invalid entry leaves the menu open and requests a valid number
again.
For a targeted recheck, select **Select individual test tasks by category**
instead. A number toggles its task; `S` starts only the marked tasks.

### 3. Declare available equipment

Answer the audio and physical Braille questions accurately. Enter accepts the
displayed default. Not having a Braille display is not a failure; applicable
tasks are omitted.

### 4. Perform one task

Every task is one small, complete cycle:

```text
Read one instruction in PowerShell
-> press Enter
-> perform only that task in test Neovim
-> press Escape, then F10
-> select only that outcome back in PowerShell
```

Before startup, the runner states **Purpose of this test**, **Keys and steps**,
and **Pass when**. Only then press Enter.

When test Neovim appears:

1. Press `Escape` once. This ensures Neovim Normal mode is active, preventing
   accidental text insertion.
2. Enable Access Link from the NVDA menu if needed.
3. Focus the original Windows Terminal tab, press `F12` exactly once, and wait
   briefly for the connection.
4. Perform only the displayed task.
5. If uncertain, press `Escape`, then `F2`. The test ID, purpose, numbered
   steps, and pass condition are displayed again as a Neovim notification and
   reported by Access Link.
6. After observing the result, press `Escape`, then `F10`. The runner
   PowerShell is now visible again in the original tab.
7. Assess only the task just performed as pass, fail, blocked, or skipped.

A fresh test Neovim starts for the next task. Nobody has to remember several
checks or reset a fixture manually.

## Keys used by the runner

Each task names only the keys it needs. This table is a reference:

| Key | Meaning in test Neovim |
| --- | --- |
| `Escape`, then `F2` | repeat the ID, purpose, steps, and pass condition at any time |
| `F3` in L1 | report the active LSP status through Access Link |
| `F3` in insertion and completion tasks | open the prepared insertion location and enter Insert mode automatically; in a completion task, press `F5` next |
| `F3`, `F4`, `F5` in L4 | run the native project search and open its Quickfix list, then select the next and previous result within the list |
| `F6` in L4 | start native project-wide replacement with Neovim's confirmation prompts |
| `F3`, `F4` in L5 | open an empty name field, pass its input to Neovim's native LSP rename, and then report both renamed reference rows in sequence |
| `F3`, `F4` in L6 | run the prepared `bufdo` replacement and then report both files that actually changed |
| `F5` in the diagnostic profile | move to a prepared clean position and explicitly query its current diagnostic |
| `F6` | run the selected linter, wait for readiness, and place the cursor on the first expected test diagnostic |
| `F7` | report the diagnostic at the current position |
| `F8` / `F9` | jump to the previous or next diagnostic |
| `F3`, `F4`, `F5` in P1 through P4 | open lazy.nvim, start the prepared public management action, and verify the actual isolated Git end state; P1 uses only F3 and Lazy's normal keys |
| `Escape`, then `F10` | close test Neovim without saving and return to PowerShell |

Completion is navigated with `Ctrl+N` and `Ctrl+P`, accepted with `Ctrl+Y`,
and closed with `Ctrl+E`. Braille tasks spell out the required held NVDA
gesture. L4 deliberately uses the short slash search; testers do not have to
type longer colon commands because task-specific function keys execute the
prepared native commands directly. Neovim retains execution and every
confirmation prompt; generated command characters are not presented as typed
input. In L4, `F3` reports the result count and `F4` or `F5` reports the
complete result row and position. Repeated selection remains in the open
Quickfix window; source files and windows are not announced as focus changes.
Another press at the first or last result reports the reached boundary;
neither an isolated character nor Neovim's “No more items” message may be
presented. `F6` presents every native confirmation prompt before an answer is
required, followed by exactly one aggregate summary; internally visited files
or windows must not appear as focus changes. `F1` and `F11` are deliberately
unused: F1 opens Neovim help, while F11 toggles Windows Terminal full-screen
mode by default.

In L5, the known reference file is already loaded before interaction. `F3`
therefore accepts only the new name; Neovim, Pyright, and Neovim's normal
`WorkspaceEdit` handler continue to own the rename. Each press of `F4` reports
the next reference row that was actually changed without switching the current
buffer. An automated TUI/RPC test drives those physical function keys with a
deterministic test language server and excludes additional text, cursor, and
context reports. The guided test is left to assess only speech and perceived
latency under Windows/NVDA.

L6 complements L4 with Neovim's buffer list. The second file is loaded and
explicitly listed before interaction; `F3` lets Neovim run `bufdo` across both
files. Access Link should provide only one aggregate result. Two presses of
`F4` then verify the actual buffer contents without changing the current
buffer. An automated real TUI/RPC test drives the same function keys and
excludes additional text, cursor, and context reports.

## What happens automatically before the first test

The runner first validates plans, German and English text, and every referenced
file. On the first run, it creates an isolated environment below
`tmp/human-test-state/` containing:

| Component | Use |
| --- | --- |
| pinned versions of Pyright, Ruff, Clang-Tidy, and markdownlint-cli2 | reproducible LSP and diagnostic responses; only tools required by the selection are installed |
| pinned revisions of nvim-lint, nvim-cmp, cmp-nvim-lsp, blink.cmp, and lazy.nvim | reproducible provider, completion, and plugin-management compatibility; only plugins required by the selection are loaded |
| separate Neovim configuration, data, state, and cache directories | complete isolation from the personal Neovim environment |

Pyright is provided as a pinned npm package archive and verified with SHA-512
before extraction. This avoids the `npm install` path that can stall in
mounted directories on Windows. The runner verifies the package version,
server and CLI files, and a real CLI invocation, then starts the JavaScript
language server explicitly with Node instead of a Windows batch wrapper.

Later runs compare a separate environment fingerprint, the tool versions
required by the selection, and the required plugin revisions. Changes only to task
wording, translations, or result logic therefore do not trigger setup again.
If the required tools and plugins already match, they are reused without
package installation. Saved state also records which profiles passed
preflight; newly selected profiles run their own preflight even when their
files are already present. Clang-Tidy and markdownlint are not installed
preemptively for a normal smoke run. Only the technical preflight for actually
selected profiles is repeated after a relevant runtime change.

A direct probe first checks the real output of every required linter against
its pinned fixture. A technical preflight then starts every selected test
profile. For LSP tasks, it waits for an attached Pyright client. The rename
task requires its native rename capability. In completion profiles the
preflight requests the three named candidates; signature tasks additionally
require at least two signatures with three parameters each. In the Python
diagnostic profile, it requires
two real Ruff F401 warnings on the first line and at least one Ruff F821 error.
That readiness check considers only the diagnostic namespace of the linter
under test, so Pyright diagnostics can neither satisfy nor obscure the Ruff
result. The C and Markdown profiles require a real Clang-Tidy error and markdownlint
MD025 warning, respectively. A direct tool failure includes its output; a
linter failure names the configured provider and whether its process is still
running. Preparation stops at the first failure. A human tester
only sees a perception task after these machine-decidable foundations work.

**Set up or repair test dependencies** is the explicit repair operation: it
reinstalls the managed plugin revisions required by the selection and repeats
this preflight. The normal
standard test does not perform this forced reinstall. The personal Neovim
environment remains untouched.
Only the test Neovim process uses a temporary global Git configuration that
marks the managed plugin directories below `tmp/human-test-state/` as safe.
The personal global Git configuration is not modified.

## Outcome choices

| Choice | Meaning |
| --- | --- |
| **pass** | The observed output matched the expectation. |
| **fail** | The task could be performed but behaved incorrectly. A complete result has state `fail`. |
| **blocked** | An external prerequisite or technical problem prevented observation. The run remains incomplete. |
| **skipped** | An applicable task was deliberately not checked. The run remains incomplete. |
| `notApplicable` | Set automatically when a task strictly needs unavailable hardware, currently the Braille tasks. |
| `pending` | The task has not been assessed yet. |

Only **pass** is positive human evidence. All other manually selected states
require a short reason. Do not enter private paths, account names, keys, or
other secrets there.

## Interrupt and resume easily

Progress is saved after every task. After an interruption, start the runner
again without parameters and select **Resume an incomplete run**. If
several incomplete files exist, the runner lists the newest names for
selection.

Tasks already passed or failed remain unchanged. The runner asks whether
blocked or skipped tasks should be reopened. This is explicit; a result is
never rewritten silently.

A file can also be supplied directly:

```powershell
.\tests\human\framework\run.ps1 run `
  -ResultPath .\tmp\human-test-results\EXAMPLE.json
```

A run can resume only with exactly the same test definition. The validator
compares a SHA-256 fingerprint covering plans, translations, fixtures,
dependencies, runner, validator, and the test Neovim configuration.

## JSON results and machine assessment

New files are stored below `tmp/human-test-results/`. The filename contains a
timestamp, suite, and short random component, so rapidly started runs do not
collide. Every selection atomically replaces the file.

The JSON records:

| Area | Recorded data |
| --- | --- |
| Run | run ID, creation time, and completion time |
| Selection | suite, exact two-character test IDs, language, and declared audio/Braille equipment |
| Source state | repository Git commit and dirty state |
| Runtime versions | Neovim, installed add-on, and running NVDA versions when discoverable |
| Consistency | fingerprints of the test definition and installed Neovim plugin |
| Results | two-character test ID, technical task key, status, and entered reason |

Editor content, host names, and credentials are not collected automatically.
Files in ignored `tmp/` are not committed, uploaded, or collected by CI.

Use **Verify an existing JSON result file** from the menu, or run:

```powershell
.\tests\human\framework\run.ps1 verify `
  -ResultPath .\tmp\human-test-results\EXAMPLE.json
```

The validator is also platform-independent:

```bash
python3 tests/human/framework/validate.py result tmp/human-test-results/EXAMPLE.json
```

| Exit code | Overall state |
| --- | --- |
| `0` | complete; every applicable task passed |
| `1` | structurally invalid or incompatible with current definitions |
| `2` | complete, but at least one task failed |
| `3` | pending, blocked, or skipped and therefore incomplete |

## Optional compatibility and individual tests

After changes to nvim-cmp, blink.cmp, linter integration, or Access Link
adapters, select **Run optional compatibility tests (completion, C, and
Markdown)**. It also contains
one small C and one Markdown reality check. Each task starts separately.
The most useful direct invocations are:

| Goal | PowerShell invocation |
| --- | --- |
| run standard and compatibility tasks together | `.\tests\human\framework\run.ps1 run -Suite all` |
| run exactly the C diagnostic test | `.\tests\human\framework\run.ps1 run -Suite custom -TestId D3` |
| run two specific tasks | `.\tests\human\framework\run.ps1 run -Suite custom -TestId L1,D4` |
| explicitly use the German interface | `.\tests\human\framework\run.ps1 -Language de` |
| explicitly use the English interface | `.\tests\human\framework\run.ps1 -Language en` |

Older technical long forms such as
`c-diagnostics.clang-tidy-presentation` remain valid compatibility aliases.
Use the short test ID for all new reports and invocations.

## Cleanup and common problems

**Remove downloaded test dependencies** deletes only
`tmp/human-test-state/`. JSON results remain.

If Access Link does not connect:

1. verify that the current add-on build is installed and enabled in NVDA;
2. install or update local Neovim components from the NVDA menu;
3. ensure the original tab containing test Neovim is focused;
4. press `F12` exactly once there and wait briefly;
5. press `Escape`, `F2` to check whether the test ID, purpose, steps, and pass
   condition are reported.

If Pyright, a linter, or a completion plugin is unavailable, select **Set up or
repair test dependencies**. A failed technical preflight is a setup problem,
not a human test failure.

## Maintaining the framework

The compact implementation lives below `tests/human/`:

| Path | Contents |
| --- | --- |
| `plans/` | declarative task cards only |
| `locales/` | synchronized German and English text |
| `fixtures/` | small, controlled test files |
| `dependencies.json` | pinned third-party versions and revisions |
| `framework/` | runner, validator, and isolated Neovim configuration |

A new human task receives one of the four fixed categories and needs a reason
that cannot be automated reliably and a link
to related automated evidence. If code can decide the result unambiguously,
the case belongs in an automated test. Validate definitions with:

```bash
python3 tests/human/framework/validate.py plans
python3 tools/run_tests.py quick
```

GitHub Actions also executes the PowerShell runner on Windows. This finds
PowerShell-specific parser and runtime errors, but never declares speech,
sounds, Braille, or focus as having passed a human check.
