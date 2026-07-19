# Quality review of Global Plugin slimming

Review date: July 19, 2026  
Comparison: `feature/global-plugin-slimming` against `main`  
Product state of the reviewed test build: `0.94.2-dev.13`

## Why this report exists

On the NVDA side, Neovim Access Link consists of a Windows Terminal AppModule,
a Global Plugin, and shared services. A technical discussion about NVDA add-on
architecture raised the valid question whether the Global Plugin owned more
responsibility and process-wide reach than necessary.

The `feature/global-plugin-slimming` branch was created in response. Its goal
is to align ownership with NVDA's established extension points without losing
the practically confirmed assignment of multiple Windows Terminal windows,
tabs, and panes or the add-on's fail-open behavior. This review was performed
before a later merge into `main` in order to:

1. verify the actual differences from `main`;
2. compare architecture claims with the implementation;
3. find regressions and unnecessary NVDA-wide participation;
4. prioritize remaining work by risk.

The report evaluates source code, tests, and recorded practical results. It is
not a stability declaration and does not prove that every combination of NVDA,
Windows Terminal, Neovim, SSH, plugins, and Braille hardware was tested.

## Comparison basis and scope

The initial review basis was:

- `main`: `60569a648d363c1a9acc2872b3c81a148ddb6584`
- feature branch: `888522c7dc83b9356e9f8596efe22ff8bf9397f9`
- difference at that point: 16 commits, 67 changed files, 7,916 insertions,
  and 4,836 deletions

During the review, the corrections under “Findings corrected immediately”
were prepared as development build 13 on the same feature branch. The commit
identifiers above retain the reproducible starting point; the overall
assessment and open-finding list describe the corrected dev-13 state.

The primary NVDA reference was the local NVDA source tree at
`/tmp/nvda-source-2026.1.1`. The review examined NVDA's developer
documentation, `inputCore.decide_executeGesture`, the extension-point
implementation, AppModule examples, Windows wrappers, and use of the same
gesture decider in NVDA Remote. Project sources, ADRs, package tests, and built
artifacts were also inspected.

## Executive summary

The feature branch is a substantial architectural improvement over `main`:

- Windows Terminal events, `nextHandler`, overlay selection, and assignable
  terminal commands are now owned by the AppModule.
- Parallel `ctypes` and DLL bindings were replaced with existing NVDA wrappers.
- F12 validates the concrete AppModule instance and focused TermControl, then
  validates focus again after crossing to the main thread.
- UI, presentation, connection coordination, and service registration have
  clearer boundaries.
- Python loaded directly by NVDA follows NVDA's tabs, LF, 110-column, and Ruff
  0.14.5 conventions.
- Reload, multiple AppModules, focus races, fail-open behavior, and F12 have
  broader automated coverage than on `main`.

The review initially found a real Braille regression. The AppModule depended
on an incidental `controlTypes` re-export from the Global Plugin. Removing that
import silently stopped insertion of the structured Braille overlay. Dev build
13 corrects this with a direct AppModule import and tests of the actual NVDA
overlay hook.

The main remaining architecture work is less urgent. The Global Plugin is not
yet a minimal composition root; it remains a large domain facade. This is not
a demonstrated runtime regression and should be changed incrementally. NVDA
translator comments are also missing, and build concurrency and CI coverage
can be improved.

**Recommendation:** retain the direction of the branch. Before merging, run
the complete serial verification and another practical Windows/NVDA test.
Continue shrinking the Global Plugin afterward through small, independently
testable changes.

## Assessment by quality area

| Area | Compared with `main` | State at review completion |
|---|---|---|
| Application-event ownership | substantially better | AppModule owns entry points, overlay list, and `nextHandler` |
| Windows API | substantially better | NVDA wrappers replace private DLL bindings |
| F12 isolation | substantially better | public process-wide decider with strict AppModule, focus, and control validation |
| Fail-open behavior | better | errors and uncertain identities restore native processing |
| Reload and lifetime | better | identity-checked publication and early unpublish |
| Separation of concerns | better but incomplete | several services extracted; Global Plugin remains a large domain facade |
| Braille overlay selection | regression corrected | actual hook and error path covered automatically |
| NVDA Python style | substantially better | Ruff, EditorConfig, and a CI style check are present |
| Localization | catalogs consistent | translator comments remain missing |
| Tests | broader | complete local suites pass serially |
| Packaging | functional | concurrent builds to the same destination remain unsafe |
| Security and threading | no new critical finding | I/O remains off the NVDA main thread; gate fails open |

## Findings corrected immediately

### The structured Braille overlay was not inserted

Before correction, `appModules/windowsterminal.py` used
`NeovimAccessLink.controlTypes.Role.TERMINAL`. After a style cleanup, the
Global Plugin module no longer imported `controlTypes`. The resulting
`AttributeError` was deliberately caught by the fail-open path. NVDA therefore
did not crash and native terminal output remained available, but
`StructuredTerminalBrailleOverlay` was not added to NVDA's overlay class list.

The existing suite did not reveal the defect because one test instantiated the
overlay directly, while no test called the real
`AppModule.chooseNVDAObjectOverlayClasses` hook.

Development build 13 corrects dependency ownership:

- the Windows Terminal AppModule imports `controlTypes` directly;
- its role check uses `controlTypes.Role.TERMINAL`;
- one regression test invokes the real hook with matching and non-matching
  controls;
- another forces an identity failure and confirms no overlay insertion, a
  fail-open gate, a diagnostic entry, and no escaping exception.

The specific regression is therefore corrected automatically. No physical
Braille display was available for this review, so hardware, driver, and routing
behavior remain practically unverified.

### The technical scope of the F12 decider was described too absolutely

F12 is neither an NVDA script nor a raw global keyboard hook. However, NVDA
technically invokes the `inputCore.decide_executeGesture` extension point
process-wide whenever its callback is registered.

The documentation now states precisely that:

- the Windows Terminal AppModule owns registration and unregistration;
- the callback exists only while at least one such AppModule instance lives;
- non-claim keys return immediately without querying focus;
- F12 is evaluated only for the exact AppModule instance and TermControl
  identity;
- the same focus is revalidated on NVDA's main thread before assignment;
- the original gesture continues unchanged.

This wording distinguishes NVDA's public extension point from a separately
installed system-wide keyboard hook.

### Small convention cleanups

- The file-wide Ruff `E402` exemption was replaced with individual justified
  exemptions on the imports that must be late.
- `AppModule.terminate` no longer expects a `LookupError` that NVDA's
  `HandlerRegistrar.unregister` does not use.
- The plan, ADRs, and changelog distinguish the original finding from the
  corrected dev-13 state.

## Remaining findings

### 1. Medium: the minimal Global Plugin role is not yet achieved

ADR-0004 describes a small Global Plugin for genuinely global registration
and lifetime as the target. The branch moves toward that target but does not
yet complete it.

Measurable change at the initial comparison point:

- `GlobalPlugin`: 3,961 to 3,556 lines
- methods on `GlobalPlugin`: 154 to 147
- new components: `NvdaUiManager`, `NvdaPresentation`,
  `ConnectionCoordinator`, and `ServiceRegistrar`

The Global Plugin still coordinates claim inventory, session resolution,
connection dialogs, instance switching, network events, lifecycle sweeps,
clipboard operations, and parts of focus handling. `ServiceRegistrar` still
publishes the concrete plugin instance, and the AppModule uses several private
methods and attributes from that class.

This is a maintainability boundary, not a currently demonstrated functional
defect. A large rewrite would be riskier than the present state.

**Recommendation:** define a small named service facade or `Protocol` for the
AppModule, then extract one domain workflow at a time. Multi-window, tab, pane,
reload, and fail-open tests must pass after every step. Until completion, the
documentation must describe the minimal role as a target rather than a fully
realized state.

### 2. Medium: NVDA translator comments are missing

The POT and German PO catalogs are synchronized, and German forms have been
shown in practical testing. The NVDA-facing source still lacks NVDA-style
`# Translators:` comments before messages, command descriptions, and complex
UI strings.

This is mostly inherited debt and is not a runtime regression.

**Recommendation:** comment new or moved strings first, then cover existing
strings with useful context rather than meaningless boilerplate. Repeat
gettext, package, and documentation tests afterward.

### 3. Low: concurrent built-add-on tests use the same destination

Two add-on suites started at the same time can write the same archive with
`ZipFile(..., "w")`. This produced CRC and `BadZipFile` failures during the
review; the complete serial rerun passed. The build path already exists on
`main`, so this is not a feature-branch regression.

**Recommendation:** do not run add-on suites concurrently in one working tree
for now. Later, build to a unique temporary file and replace atomically, or use
a separate artifact for each test run.

### 4. Low: CI currently checks only NVDA Python style

The new workflow has narrow permissions, pins dependencies, and checks Ruff
0.14.5. Protocol, bridge, add-on, gettext, documentation, and Neovim tests are
not GitHub merge checks.

**Recommendation:** add suites to CI incrementally. Built-add-on tests must run
serially or use isolated build destinations.

### 5. Low, inherited from `main`: `vim.region` is deprecated in Neovim 0.12

The Neovim 0.12.3 suite passes but reports a deprecation warning for
`neovim-plugin/lua/nvim_nvda/state.lua`. A public replacement should be
evaluated before a future compatibility increase. An unverified replacement
does not belong in this architecture branch.

### 6. Low: very late Insert-F12 mappings are an edge case

At `setup()`, the Neovim plugin checks whether Insert-F12 is already mapped and
preserves existing user mappings. A mapping set dynamically only afterward,
for example through unusual lazy loading, is not covered. A real Neovim test
must first establish how `vim.on_key` and the later mapping interact.

## Positive detailed findings

### Event ownership and fail-open behavior

The AppModule calls `nextHandler` itself. On focus changes, the shared service
prepares an immutable decision, the AppModule runs NVDA's native processing
exactly once, and the service completes structured handling only if generation
and identity still match. Errors and ambiguous terminal identities restore
native processing.

The published service is removed from the registrar early during termination.
Instance and token checks prevent a delayed `terminate` from an old instance
from removing a newly published service. The gate, clients, scheduled work,
UI, and caches are then shut down in a controlled sequence.

### Threading and latency

No new blocking network path on NVDA's main thread was found in the diff. Local
and remote session discovery, claim waits, and component installation run in
workers. Results, dialogs, speech, and Braille updates return through
`queueHandler` or `wx.CallAfter` to the appropriate UI paths.

### NVDA API and Python style

Window and process checks use `winUser`, `winBindings`, and `winKernel`.
Failures produce an unknown state and do not trigger destructive cleanup.
Handle cleanup is exception-safe and tested.

The NVDA style zone is limited to `nvda-addon/addon/**/*.py`. Core, bridge,
protocol, tests, and tools retain their respective consistent styles. NVDA's
tab convention is therefore not imposed unnecessarily on unrelated components.

### Security

No real credentials or production host names were found in the branch diff.
Passwords are not persisted. Session IDs, nonces, sequence numbers, request
IDs, size limits, and focus identities remain validated. The extractions do
not weaken these boundaries.

## Verification evidence at review completion

| Check | Result |
|---|---|
| `git diff --check` | passed |
| Ruff 0.14.5 `check` | passed |
| Ruff 0.14.5 `format --check` | passed |
| protocol tests | 42 passed |
| bridge tests | 31 passed |
| add-on and package tests, serial | 316 passed |
| gettext catalog check | passed |
| German and English HTML documentation | 6 files built |
| Neovim plugin with 0.10.1 | passed |
| Neovim plugin with 0.12.3 | passed; `vim.region` warning |
| dev-13 archive with `unzip -t` | passed |

Development artifact built during the review:

```text
NeovimAccessLink-0.94.2-dev.13+feature.global-plugin-slimming.888522c7.nvda-addon
SHA-256: 9f94446b8eeb0f7bba3d6fc45b60c5f7ea71660105f302f0f3e1971f8959a2d1
```

The commit suffix identifies the branch HEAD at the initial comparison point.
The dev-13 file also contains the review corrections that were still
uncommitted at that time. A later commit requires a new artifact with its own
build identifier.

## Practical evidence and review limits

During development, mixed local and remote connections were exercised across
multiple Windows Terminal windows, tabs, and horizontal and vertical panes.
Focus changes, F12, assignable commands, and the German UI were used without a
reported error.

The dev-13 corrections were checked automatically and in the built package,
but were not practically re-accepted under Windows and NVDA during this review.
No Braille display was available. Automated mocks also do not replace a long-
running check with real UIA, SSH, and user configurations.

## Recommended order of work

### Before merging into `main`

1. Practically test dev build 13 with Windows Terminal and NVDA, including F12,
   focus changes, multiple tabs and panes, and native output outside bound
   Neovim controls.
2. If hardware is available, test Braille overlay selection and routing. Lack
   of hardware alone need not block the remaining architecture review, but it
   must remain documented as a limit.
3. After committing, build a newly identified package and repeat the serial
   suites, gettext, documentation, and archive checks.
4. Do not combine another large extraction with the same acceptance step.

### In separate follow-up changes

1. introduce a neutral AppModule service facade instead of publishing the
   concrete Global Plugin;
2. extract remaining domain coordination incrementally;
3. add translator comments;
4. make package builds atomic or test-run-specific;
5. run the complete suites in CI;
6. investigate `vim.region` and dynamic F12 mappings separately.

## Conclusion

`feature/global-plugin-slimming` follows NVDA add-on boundaries considerably
better than the compared `main` state. The AppModule now owns application-
specific events and commands, the global portion uses public NVDA interfaces
more narrowly, and responsibilities have clearer separation. The Braille
regression found during the review is corrected in dev build 13 and covered
through the actual overlay hook.

Slimming is not complete: the Global Plugin remains a large domain facade.
That remaining work does not justify a risky rewrite before merging. With
another practical acceptance pass and small, independently testable follow-up
changes, the branch is a sound basis for a narrower and more conventional NVDA
add-on.
