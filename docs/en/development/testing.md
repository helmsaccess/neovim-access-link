# Test strategy

This page explains which verification belongs to a change and what a passing
run actually proves. Detailed user actions belong in the separate [guided
practical tests](human-testing.md), not here.

## Goals and evidence types

The strategy primarily protects against:

- blocking I/O on NVDA's main thread;
- mixing sessions, windows, tabs, or panes;
- output or suppression without confirmed focus and state;
- invalid, oversized, or unnegotiated protocol data;
- regressions in speech, Braille, localization, and package contents;
- divergence between documented and built behavior.

Automated tests, practical NVDA checks, and code/source review are distinct
forms of evidence. None alone confirms every platform, device, or user
configuration. Status and compatibility therefore state the exact verified
scope.

## Test groups and presets

`tools/run_tests.py` inventories test files and runs independent jobs in
separate temporary directories.

| Group or preset | Contents |
|---|---|
| `unit` | pure and mock-isolated Python tests |
| `package` | built add-on, archive contents, and NVDA integration doubles |
| `lua` | headless-Neovim specifications without listeners |
| `ssh` | mocked SSH, Askpass, command, and failure paths |
| `socket` | real disposable TUI, RPC, TCP, and Unix-socket cases |
| `guided-desktop` | Windows VM with focus, speech, and Braille checks |
| `guided-audio` | Windows VM with PCM recordings and muted controls |
| `quick` | fast feedback; `unit` only |
| `all-safe` | `unit`, `package`, and listener-free `lua` |
| `all` | `all-safe`, then `ssh` and `socket` in separate phases |

Without a group argument, the runner uses the safe preset. The default number
of parallel jobs follows the logical processors available to Python. Use `-j N`
to set the limit for a run. Package tests use up to twelve independent shards.
Each shard builds its own package. Use `--list` to inspect the selection
without running it. Every isolated job runs in its own process group. After
180 seconds, the runner terminates the entire group, including Neovim and
helper processes it started, and reports the job as failed. The real-TUI send
helper additionally bounds pseudo-terminal draining to one second and 8 MiB
per physical-key step.
The compact output also reports skipped cases and Python warnings per job and
in the overall total. Every observation is followed by a `SKIP` or `WARN` line
with its job and reason or warning text; a passing run with
`0 skipped, 0 warnings` therefore explicitly proves that neither was hidden.

## Recommended workflow

During a change:

```bash
python3 tools/run_tests.py quick
```

Before a commit, run at least the affected group and then the safe complete
path:

```bash
ruff check .
ruff check --config 'include = ["nvda-addon/tests/**/*.py"]' .
ruff format --check .
python3 tools/run_tests.py all-safe
python3 tools/run_tests.py ssh
git diff --check
```

Socket tests need an environment that permits loopback listeners, private
Unix sockets, and short-lived Neovim processes:

```bash
python3 tools/run_tests.py socket
```

On Windows the runner executes the local TCP tests in this group. They verify
session registration and a real Neovim process with authenticated initial
state and cursor routing through the Python client. Use a Linux checkout for
the complete group with Unix sockets and Pexpect PTYs.

In a restricted sandbox, a listener failure is an environment limitation, not
a passing test. Run the socket phase later in a permitted environment.
`python3 tools/run_tests.py all` is appropriate only where all three phases are
allowed.

### Guided workflows over real Neovim RPC

With Neovim 0.12.x on `PATH`, the socket phase also loads the guided test
profile in fresh editors. It queues the actual mapped keys using `nvim_input`
and receives semantic events through the authenticated production client.
Assertions cross-check events with native buffer, cursor, quickfix, diagnostic
and completion state, external linter output, or unchanged fixture files.

L4 and L6 need only Neovim. The other cases use versions from
`tests/human/dependencies.json` and skip with a reason if a required tool
or path is missing. Set these variables before running the socket phase:

| Variable or executable | Expected dependency | Cases |
| --- | --- | --- |
| `NAL_GUIDED_PYRIGHT` and `node` on `PATH` | Pyright's `langserver.index.js` and Node.js | L1–L3, L5, C1–C3, D1, D2 |
| `NAL_GUIDED_COMPLETION_ROOT` | Parent directory of the pinned Git checkouts `nvimCmp`, `cmpNvimLsp` and `blinkCmp` | C2, C3 |
| `NAL_GUIDED_NVIM_LINT` | Pinned nvim-lint Git checkout | D1–D4 |
| `ruff` on `PATH` | Pinned Ruff executable | D1, D2 |
| `NAL_GUIDED_CLANG_TIDY` | Pinned Clang-Tidy executable | D3 |
| `NAL_GUIDED_MARKDOWNLINT` | Pinned markdownlint-cli2 executable or Windows command wrapper | D4 |
| `NAL_GUIDED_LAZY` | Pinned lazy.nvim Git checkout | P1 |

L3 and D2 verify the context data supplied to NVDA. They compare the real
provider results, correlate requests with the editor snapshot, and check
that the query leaves the cursor unchanged. D2 also submits a stale
snapshot and requires an explicit rejection.

For P1, a separate client attaches using `nvim_ui_attach` and receives the
real Neovim redraw stream. The test also reads native buffer state and checks
the semantic command bar and expanded state through the production client.
For P2–P4, `bash tools/test_lazy_plugin.sh PATH_TO_PINNED_LAZY_NVIM` runs the
real Lazy commands with disposable local Git repositories. It checks the
operation lifecycle and then checks Git revisions and removal independently.
The fixture verifier must also detect a real rollback and, for Sync, a
reintroduced stale directory.

These checks cover the Neovim and protocol portions of the tasks. Windows
focus, NVDA's speech and Braille output, and physical perception require
separate observations. See the [guided test scope](human-testing.md).

### Guided Windows and audio checks

The optional groups run serially in an isolated Windows guest. `--list`
shows case IDs. Repeat `--guided-case` to limit a run to selected cases.

```powershell
python tools/run_tests.py guided-desktop guided-audio --list
python tools/run_tests.py guided-desktop guided-audio --guided-config $labConfig --guided-addon $addon
```

`tests/guided/windows/README.md` describes VM configuration, tools, and
evidence. VM data stays in the local auxiliary workspace. Guest reports
record the package checksum and cleanup acknowledgement. The checks observe
digital Braille patterns, sequences sent to the speech synthesizer, and
rendered audio. Device-specific Braille perception, acoustic intelligibility,
and subjective latency lie outside these measurements.

## Mapping changes to tests

Check operating-system focus and key gestures on an interactive, isolated
Windows desktop. A Windows guest can observe Win32 foreground, UI Automation
focus, and keys from a virtual keyboard device. The harness under
`tests/guided/windows/` uses a separate NVDA configuration and
portable Windows Terminal. Use explicit failure checks in the portable NVDA
test code. NVDA runs Python with optimization and omits `assert` statements.

| Change | Required emphasis |
|---|---|
| Protocol field or control | validator, codec, bridge, local client, capability-negative path, Lua, and security documentation |
| Neovim event or adapter | affected Lua specification, real Neovim run, state and presentation test |
| SSH or session discovery | `ssh`, registry/ownership checks, timeout, and non-destructive failure path |
| Local Windows RPC | local client, loopback/nonce/process validation, and `socket` |
| Focus, AppModule, or suppression | multi-instance, focus-race, `nextHandler`, and fail-open package tests plus practical WT negative path |
| Speech, sound, or Braille | neutral planner, NVDA adapter, Unicode/routing/region cases, and practical output |
| Setting or UI | schema, profile switch, localization, package test, and both manual languages |
| Installer or package content | package, installation, removal, and built-archive tests |
| Documentation | example synchronization, language mirror, HTML metadata, Markdown/HTML links, and a fresh documentation build |

Where practical, a bug-fix commit adds a regression test at the lowest useful
layer and integration evidence at the boundary where the defect appeared.

AST-based add-on architecture tests enforce the minimal Global Plugin entry
point, the public AppModule API, an acyclic local import graph, and exactly one
production path each for `send_control` and `client.stop`. Real worker tests
use deliberately blocking clients; scheduler and rollback tests execute late
callbacks and failures at every resource-owning construction stage. These
tests therefore exercise concurrency contracts rather than only source-text
fragments. The second Ruff command explicitly lints every Python test; format
checking remains limited to the configured NVDA product code.

The domain owners `AddonRuntime`, `ManagedClientFactory`,
`TemporaryBindingWorkflow`, `EventDelivery`, `TerminalActions`, and
`ConnectionWorkflow` have direct tests with small injected doubles. Package
tests remain responsible for real composition, NVDA registration,
persistence, and complete focus/disconnect scenarios. The bridge follows the
same boundary: mock-isolated contracts live in `test_nvim_bridge_mock.py`, and
real TUI/socket scenarios in `test_nvim_bridge_socket.py`. The runner discovers
and shards methods from each file instead of maintaining a second manual name
list.

`test_contract_mutations.py` checks four particularly critical contracts
against temporary, deliberately modified protocol packages. The suite must
detect removal of the Boolean distinction, an incorrect exact size boundary,
a relaxed field set, and a loosened initial sequence comparison. This is a
small deterministic selection by design, not a general mutation framework or
a coverage-percentage target.

## Specialized contract checks

Additional scripts exercise real public plugin and tool contracts:

- `tools/test_completion_plugins.sh` for `nvim-cmp` and `blink.cmp`;
- `tools/test_linter_plugins.sh` for `nvim-lint`, ALE, and real linters;
- `tools/test_none_ls.sh` for the `none-ls.nvim` LSP bridge;
- `tools/test_lazy_plugin.sh PATH_TO_LAZY_NVIM` for public lazy.nvim commands,
  lifecycle events, and local Git end states;
- `tools/test_neovim_plugin.sh` for the serial complete Lua compatibility run.
  It also includes session specifications with local listeners and therefore
  needs an environment that permits them.

The GitHub matrix runs these contracts with Neovim, plugin, language, and tool
versions pinned by the workflow. Checkouts are test-only dependencies and are
not shipped.

## GitHub Actions

`.github/workflows/repository-tests.yml` runs for pushes and pull requests.
Jobs are deliberately separated into:

- safe unit, package, and listener-free Lua tests;
- a focused Neovim 0.12.3 contract for native Tutor extmarks and the real TUI
  event path;
- the PowerShell runner for guided practical tests;
- completion-plugin contracts;
- public lazy.nvim contracts with real install, update, and sync operations;
- diagnostic providers and real linters;
- mocked SSH and Askpass paths;
- real TUI, TCP, and Unix-socket cases;
- build and link validation for all eight documentation files.

A green matrix job confirms its named contract. The full desktop and audio
evidence comes from the isolated Windows guest.

The hosted `.github/workflows/guided-windows-hosted.yml` workflow builds
the add-on, loads it in portable NVDA, and verifies the focused `TermControl`
and keyboard delivery to the console process. The S1 test also checks that
F12 binds the editor and F10 restores native terminal events, caret editing,
and digital Braille in the original PowerShell tab. Its control omits F10 and
must fail at that step.
The observed `windows-2025` runner had no default WASAPI render endpoint.
Guest captures use the render endpoint inside the Windows guest.
[Hosted NVDA focus and S1 evidence](https://github.com/helmsaccess/neovim-access-link/actions/runs/46000887969)

The reusable `.github/workflows/guided-windows-vm.yml` workflow runs all 18
cases and the complete audit in a provisioned Windows lab. A private
repository under the same owner pins the workflow to a reviewed commit SHA
and its owner starts it manually from the default branch. Runner access is
restricted to the private repository. The job uses the project's own Windows
runner, so it consumes zero GitHub-hosted minutes. Raw logs, guest media, and
recordings stay in the lab. See `tests/guided/windows/README.md` for setup and
invocation.
The full guest suite has been verified locally. Running it through Actions
requires a provisioned private lab runner.

## Build verification

Package tests build the add-on with an explicit temporary output directory,
open the actual `.nvda-addon`, and strictly check base and
localization manifests against the applicable official NVDA AddonTemplate
fields, plus
resources, all eight localized installed HTML documents, bundled Linux
components, licenses, translation catalog, and forbidden files. An earlier
archive is not evidence for later source changes. The Linux development
checkout receives neither a distributable add-on nor persistent build output.

After documentation changes, render and validate the complete documentation in
temporary storage:

```bash
bash tools/build_documentation.sh --test-only
```

The Linux release build and CI validation job use the respective official
Pandoc 3.1.11.1 binary from an archive with a pinned SHA-256 digest. The
Windows development build uses installed Pandoc 3.1.11.1 with the expected
build features. Otherwise it downloads the verified official binary into its
temporary build directory.

The build checks the canonical Lua example, German and English source files
and heading structures, local Markdown links, generated HTML targets,
language, title, and description metadata, and the eight expected documents.
The script deletes its output after validation; CI publishes no end-user
artifact. Historical archives explicitly excluded from current documentation are
validated but not included in HTML.

After complete validation, `build.cmd` creates development artifacts in the
local Windows checkout. The approved Linux state creates the later
published release artifacts with `python3 tools/build_release.py`. Both entry
points use the same isolated core and build the add-on and documentation ZIP
from one stable branch and commit. See [release, version, and build
process](release-and-build.md) for prerequisites and stop conditions.

## Practical testing

The guided runner lives under `tests/human/framework/`; its versioned plans
live under `tests/human/plans/`. It writes installed tools and setup
fingerprints to `tmp/human-test-state/`, while results go to
`tmp/human-test-results/`. These tool-owned paths are not agent workspaces or
locations for manual project files.

Practical checks are selected by risk. Connection or focus changes cover at
least:

1. one connected local or remote success path;
2. an unbound shell control in the same Windows Terminal environment;
3. switching between relevant tabs, panes, or windows;
4. disconnect or uncertain focus with native fail-open output.

Braille, speech, plugin, or LSP changes use the applicable suites in the
guide. Results name hardware, versions, and untested breadth and are not
presented as exhaustive approval.

## Classifying a failure

1. Identify the smallest reproducing test and its group.
2. Confirm that the environment provides required listeners, binaries,
   plugins, or language servers.
3. For a real failure, isolate the owning layer: producer, transport,
   validation, state, focus, or presentation.
4. Add a regression test, then repeat the next broader relevant run.
5. If a claim changed, update status, compatibility, architecture, or the
   relevant reference in both languages.

Logs support diagnosis but never participate in the correct control path.
Private content is not versioned in reproductions or failure messages.
