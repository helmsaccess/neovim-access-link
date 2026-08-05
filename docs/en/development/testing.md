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
parallelism, and `--list` shows selection without running it.

## Recommended workflow

During a change:

```bash
python3 tools/run_tests.py quick
```

Before a commit, run at least the affected group and then the safe complete
path:

```bash
ruff check .
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
| Documentation | example synchronization, language mirror, Markdown/HTML links, and a fresh documentation build |

Where practical, a bug-fix commit adds a regression test at the lowest useful
layer and integration evidence at the boundary where the defect appeared.

## Specialized contract checks

Additional scripts exercise real public plugin and tool contracts:

- `tools/test_completion_plugins.sh` for `nvim-cmp` and `blink.cmp`;
- `tools/test_linter_plugins.sh` for `nvim-lint`, ALE, and real linters;
- `tools/test_none_ls.sh` for the `none-ls.nvim` LSP bridge;
- `tools/test_neovim_plugin.sh` for listener-free Lua specifications.

The GitHub matrix runs these contracts with Neovim, plugin, language, and tool
versions pinned by the workflow. Checkouts are test-only dependencies and are
not shipped.

## GitHub Actions

`.github/workflows/repository-tests.yml` runs for pushes and pull requests.
Jobs are deliberately separated into:

- safe unit, package, and listener-free Lua tests;
- the PowerShell runner for guided practical tests;
- completion-plugin contracts;
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

Package tests open the actual `.nvda-addon` and inspect its manifest,
resources, bundled Linux components, licenses, translation catalog, and
forbidden files. An earlier archive is not evidence for later source changes.

After documentation changes, rebuild documentation:

```bash
tools/build_documentation.sh
```

The build checks the canonical Lua example, German and English source files
and heading structures, local Markdown links, generated HTML targets, and the
eight expected files in the ZIP. Historical archives explicitly excluded from
current documentation are validated but not included in HTML.

When work changes both installable code and documentation, build both
artifacts from the same final worktree.

## Practical testing

The guided runner lives under `tests/human/framework/` and writes plans,
fingerprints, and results to ignored `tmp/human-test-state/`. This tool-owned
path is not an agent workspace or a location for manual project files.

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
