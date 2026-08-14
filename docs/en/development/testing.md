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
| `quick` | fast feedback; `unit` only |
| `all-safe` | `unit`, `package`, and listener-free `lua` |
| `all` | `all-safe`, then `ssh` and `socket` in separate phases |

Without a group argument, the runner uses the safe preset. `-j N` limits
parallelism, and `--list` shows selection without running it. Every isolated
job runs in its own process group. After 180 seconds, the complete group,
including Neovim and helper processes it started, is terminated and the job is
reported as failed. The real-TUI send
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

In a restricted sandbox, a listener failure is an environment limitation, not
a passing test. Run the socket phase later in a permitted environment.
`python3 tools/run_tests.py all` is appropriate only where all three phases are
allowed.

## Mapping changes to tests

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

A green matrix job confirms only its named contract. Practical NVDA, Windows
Terminal, and Braille output remains a separate acceptance activity.

## Build verification

After a change to installable code, rebuild the add-on from the final worktree:

```bash
python3 tools/build_nvda_addon.py
```

Package tests open the actual `.nvda-addon` and strictly check base and
localization manifests against the applicable official NVDA AddonTemplate
fields, plus
resources, all eight localized installed HTML documents, bundled Linux
components, licenses, translation catalog, and forbidden files. An earlier
archive is not evidence for later source changes.

After documentation changes, rebuild documentation:

```bash
tools/build_documentation.sh
```

The local reference build and the CI job use the official Pandoc 3.1.11.1
binary build. The build script rejects repackaged builds because they can
produce different syntax highlighting despite reporting the same Pandoc
version. CI downloads the official archive with a pinned SHA-256 digest.

The build checks the canonical Lua example, German and English source files
and heading structures, local Markdown links, generated HTML targets,
language, title, and description metadata, and the eight expected files in the
ZIP. The same results are synchronized for installed help; CI rejects stale
copies. Historical archives explicitly excluded from current documentation are
validated but not included in HTML.

When work changes both installable code and documentation, build both
artifacts from the same final worktree.

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
