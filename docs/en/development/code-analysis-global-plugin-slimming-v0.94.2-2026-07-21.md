# Appendix B: Analysis of `feature/global-plugin-slimming` against `v0.94.2`

Created: July 21, 2026, 01:11:58 CEST (UTC+02:00)

Baseline: tag `v0.94.2`, commit `60569a648d363c1a9acc2872b3c81a148ddb6584`

Compared revision: branch `feature/global-plugin-slimming`, commit
`b4195f3d900187f085275981d2ec1b0011a1952f`

Repository: Neovim Access Link

## Purpose and questions

This report examines whether the feature branch achieved its goal: the global
NVDA portion was to become slimmer, application-specific responsibilities
were to move to the Windows Terminal AppModule, and shared state was to gain
clear owners in ordinary, testable services. This work was not allowed to
lose reliability, F12 assignment, or parallel operation of local and remote
Neovim sessions across windows, tabs, and panes.

The central question is therefore not merely whether the `GlobalPlugin` class
contains fewer lines. What matters is whether responsibilities are clearer,
failure paths are safer, changes are easier to verify, and the newly
introduced structural overhead is justified.

## Executive summary

The branch has largely achieved its architectural objective. The global entry
point is not minimal, but it owns substantially less state and no longer owns
Windows Terminal events or `nextHandler`. Events, overlays, and freely
assignable commands now reside in the Windows Terminal AppModule. Shared
connection, focus, F12, editor, UI, presentation, and lifecycle state each
have a named owner. The published AppModule contract is narrow and can be
closed, making stale references inert after an add-on reload.

The slimming did not reduce the whole codebase. Python production code in the
measured core grew by 41.2 percent, the number of classes by 114 percent, and
the number of production modules by 14. A large share of that growth consists
of small immutable result objects, enums, services, and explicit transitions.
At the same time, mean local branching complexity fell by about 23 percent,
the 90th percentile fell from 12 to 9, and the largest former Global Plugin
method fell from a score of 134 to 25. The `GlobalPlugin` class itself shrank
by 36.9 percent, and its directly managed attributes fell from 58 to 12.

Most of the additional structural complexity is justified. It models real
lifetimes, ownership boundaries, and asynchronous races which also existed in
the monolithic implementation but converged implicitly in one class. The
benefits are therefore concrete: better adherence to the NVDA AppModule
model, isolated state transitions, more dependable fail-open behavior,
deterministic startup and shutdown, and stronger regression tests. The cost
is more files, data types, constructor wiring, and a longer path to follow
while debugging.

The largest newly visible quality problem is now less in production code than
in test organization: `test_built_addon.py` has grown to 7,852 lines and 62
percent of the Python test code. Test protection is substantially stronger,
but the central test file is too large, and the NVDA test run takes about
twice as long in the same environment as it did for revision 0.94.2. Splitting
this file along architectural boundaries would be useful without another
production architecture rewrite.

The compared revision was practically tested with multiple Windows Terminal
windows, tabs, horizontal and vertical panes, mixed local and SSH
connections, and clipboard paths without a reported error. Automated tests
and this practical exercise support the robustness assessment but do not
prove absence of defects. Practical Braille hardware testing remains
unavailable.

## Scope and method

### Comparison boundary

`v0.94.2` is the actual published annotated tag and an ancestor of the branch.
There are 51 non-merge commits between that tag and the compared revision. The
complete diff contains:

- 81 changed files;
- 15,937 inserted and 5,798 deleted lines;
- a net increase of 10,139 lines including tests, documentation,
  translations, and build metadata.

The comparison therefore includes more than mechanical Global Plugin
extractions. It covers all development from 0.94.2 to the 0.95.0 feature
state, including the incremental AppModule migration, F12 hardening, NVDA
style alignment, new state services, lifecycle work, documentation, and
additional tests. Aggregate change counts must not be attributed to one
individual refactoring step.

### Metric definition

Production Python measurement includes:

- `protocol/python/nvim_nvda_protocol/`;
- `bridge/python/nvim_nvda_bridge/`;
- `nvda-addon/core/nvim_nvda_core/`;
- `nvda-addon/addon/appModules/`;
- `nvda-addon/addon/globalPlugins/NeovimAccessLink/`.

Test measurement includes the corresponding three Python test directories.
Lua plugin and test sizes were counted separately. LOC means physical lines,
including comments and blank lines. The complexity figure is a reproducible
AST-based, McCabe-like branching score: a base value of one plus control
branches, handlers, comprehensions, assertions, and Boolean subconditions.
Nested functions are counted separately. This score is a trend indicator, not
an exact substitute for an established tool such as Radon.

LOC, class count, and complexity are not quality judgments on their own. They
are evaluated together with ownership, failure paths, tests, and practical
results. Line coverage was not measured because the project has no comparable
coverage baseline. Latency and CPU costs were likewise not remeasured for
this comparison.

## Quantitative results

### Production code

| Metric | `v0.94.2` | Branch | Change |
|---|---:|---:|---:|
| Python files | 32 | 46 | +14 / +43.8% |
| Python LOC | 8,551 | 12,070 | +3,519 / +41.2% |
| Lua LOC | 3,134 | 3,163 | +29 / +0.9% |
| Python and Lua combined | 11,685 | 15,233 | +3,548 / +30.4% |
| Python classes | 43 | 92 | +49 / +114.0% |
| Python functions and methods | 390 | 601 | +211 / +54.1% |
| mean function length | 19.29 | 17.06 | -11.6% |
| median function length | 10 | 9 | -10.0% |
| 90th percentile function length | 43 | 39 | -9.3% |
| maximum function length | 447 | 447 | unchanged |
| mean branching score | 6.35 | 4.87 | -23.3% |
| median branching score | 3 | 3 | unchanged |
| 90th percentile branching score | 12 | 9 | -25.0% |
| functions with score > 10 | 46 / 11.8% | 51 / 8.5% | absolute +5, proportion improved |
| functions with score > 20 | 19 / 4.9% | 21 / 3.5% | absolute +2, proportion improved |

The absolute number of more complex functions rose slightly because there
are substantially more functions. Their proportion, however, fell by about
28 percent. This is more meaningful for this refactoring than the absolute
count: logic was distributed among more units that are smaller and locally
simpler on average.

The built add-on grew from 349,521 to 376,259 bytes, or about 7.6 percent.
Package growth is therefore much smaller than source-line growth, but it is a
real cost of the additional structure.

### The global entry point and the AppModule

| Metric | `v0.94.2` | Branch | Assessment |
|---|---:|---:|---|
| `GlobalPlugin.__init__.py` LOC | 3,961 | 2,499 | -36.9% |
| direct `GlobalPlugin` methods | 154 | 112 | -27.3% |
| `self` attributes assigned in the class | 58 | 12 | -79.3% |
| attributes already assigned in `__init__` | 49 | 12 | -75.5% |
| Global Plugin methods accepting `nextHandler` | 8 | 0 | responsibility removed |
| intentional composition properties | 0 | 2 | `_gate`, `_instanceManager` |
| AppModule LOC | 207 | 352 | +70.0% |
| AppModule methods | 19 | 31 | +63.2% |
| total AppModule scripts | 1 | 11 | terminal commands moved to the proper boundary |

The increase in AppModule size is not a regression. The added methods are
application-specific events and commands that NVDA expects there. Revision
0.94.2 accepted events in the AppModule but forwarded them, including a
guarded `nextHandler`, to private Global Plugin methods. The AppModule now
decides native forwarding itself and invokes `nextHandler` in its own event
path. The shared service returns decisions only.

The change is especially clear in the former central method:

- `GlobalPlugin._handleEvent`: 245 lines and score 134 in 0.94.2;
- `GlobalPlugin._handleEvent`: 87 lines and score 25 on the branch.

The largest unchanged complexity hotspot is `SpeechPlanner.plan`, with 447
lines and score 178. It belongs to the neutral speech planner and was not the
target of this slimming work. Its size remains separate technical debt, but
this branch neither worsens nor hides it.

### Largest files in the new NVDA area

| File | LOC | Primary responsibility |
|---|---:|---|
| `globalPlugins/NeovimAccessLink/__init__.py` | 2,499 | composition and remaining NVDA/transport boundaries |
| `session_claim.py` | 1,380 | F12, inventory, selection, and transactional connection transitions |
| `nvda_ui.py` | 892 | settings, Tools menu, and component forms |
| `editor_session.py` | 772 | isolated editor state and neutral action plans |
| `appModules/windowsterminal.py` | 352 | application events, overlays, commands, and `nextHandler` |
| `terminal_focus.py` | 327 | identity, focus generation, and lifecycle checks |
| `terminal_integration.py` | 319 | narrow public AppModule/Braille contract |
| `connection_coordinator.py` | 309 | connection and runtime state |
| `nvda_presentation.py` | 250 | concrete NVDA output |

Not all files are small yet, but they are divided by a coherent
responsibility. `session_claim.py` and the remaining composition root in
particular deserve observation during future changes. Further splitting only
to reduce line count would not automatically help: it should create a new
unambiguous owner, a smaller public interface, or a directly testable failure
path.

## Test metrics and executed verification

### Python tests

Both Python revisions were actually run in the current Linux environment:

| Suite | `v0.94.2` | Branch |
|---|---:|---:|
| protocol | 42 passed | 42 passed |
| bridge/RPC | 31 passed | 31 passed |
| NVDA/add-on including the built archive | 287 passed | 362 passed |
| total | 360 passed | 435 passed |

The branch has 75 additional Python tests, all in the NVDA/add-on area. The
tests of the compared revision were run again specifically for this report.
The complete current Lua run also passed: clipboard, completion, file-manager
and workflow handling, menus, selection/state, session registry, and
spelling/diagnostic paths were executed.

The complete Lua run from the extracted 0.94.2 tree could not finish in a
comparable way in this sandbox. Several suites passed before the environment
blocked the simulated Windows loopback `serverstart` with “operation not
permitted”. No comparative Lua pass figure is therefore inferred from that
run. Static Lua test size increased only from 1,459 to 1,488 lines.

### Test structure

| Metric | `v0.94.2` | Branch | Change |
|---|---:|---:|---:|
| Python test files | 22 | 24 | +2 |
| Python test LOC | 9,452 | 12,662 | +34.0% |
| test functions | 360 | 435 | +20.8% |
| static assertion occurrences | 1,267 | 1,890 | +49.2% |
| assertions per 1,000 production LOC | 148.2 | 156.6 | +5.7% |
| test/production LOC ratio | 1.105 | 1.049 | slightly lower |
| mean test function length | 14.72 | 16.39 | +11.3% |
| 90th percentile test function length | 34 | 37 | +8.8% |
| share of `test_built_addon.py` | 52.9% | 62.0% | substantially more concentrated |

Test protection is stronger overall: there are more concrete cases,
substantially more assertions, and direct tests for partial initialization,
service replacement, late callbacks, focus races, `nextHandler`, F12,
Braille fallback, and local/remote parallel operation. The slightly lower
ratio of test to production lines is therefore not evidence of less
protection.

Test maintainability is mixed, however. `test_built_addon.py` grew from 5,002
to 7,852 lines. Many of those tests deliberately load the actual built archive
and therefore verify an important package boundary, but placing 62 percent of
the Python test code in one file impairs navigation, shared fixtures, and
targeted test selection. Mean test function length also rose.

Reported runtimes in the same environment were:

- 0.94.2 Python suites combined: about 69.2 seconds;
- branch Python suites combined: about 137.7 seconds.

The slower cycle is primarily due to the larger NVDA/package suite. It is
partly justified by greater integration safety but should not grow without
limit. Fast pure-service tests and slower archive/integration cases should be
clearly selectable or separately runnable in the future.

## Assessment of the architecture objective

### 1. Application-specific events belong to the AppModule

Achieved.

The Windows Terminal AppModule still owns all ten application-specific NVDA
event entry points and now also owns native forwarding decisions and every
`nextHandler` invocation. It furthermore owns overlay selection and the ten
freely assignable terminal commands. No Global Plugin method accepts
`nextHandler` anymore.

This is more than a cosmetic change. A failure in the shared service can fall
back directly to native NVDA processing in the AppModule. The former unclear
boundary—“the AppModule receives the event, the Global Plugin owns it”—has
been removed.

### 2. The global area contains only genuinely process-wide work

Largely achieved.

The following responsibilities reasonably remain process-wide:

- single registration of settings and the Tools menu;
- shared local and SSH connections;
- publication and withdrawal of the narrow terminal service;
- ordered startup and shutdown;
- concrete NVDA, dialog, diagnostic, and transport boundaries.

The global entry point still composes these services and contains remaining
NVDA-side callbacks. At 2,499 lines and 112 methods it remains large. Its own
state burden, however, has fallen substantially: it holds twelve composition
objects rather than dozens of domain-state containers. The two `_gate` and
`_instanceManager` properties are deliberately retained, frequently used
composition views. Another forwarding layer would add lines and navigation
without creating a new owner.

### 3. Shared state has unambiguous owners

Achieved for the areas addressed by the branch.

- `ConnectionCoordinator` owns instances, the gate, runtime states, and
  correlated requests.
- `TerminalFocusService` owns identity, focus generation, adapter correlation,
  and lifecycle checks.
- `SessionClaimService` owns F12 authorization, inventory, selection, and
  connection transitions.
- `EditorSessionController` owns isolated editor state and neutral output and
  control plans.
- `SettingsService`, `NvdaUiManager`, and `NvdaPresentation` separate
  configuration, UI, and concrete output.
- `AddonRuntime` owns publication, partial-initialization rollback, and the
  fixed shutdown order.
- `service_registry.py` publishes the service without importing the Global
  Plugin class back into the registry.

Package tests enforce that the extracted runtime, UI, focus, F12, editor,
Braille, registry, and terminal-service modules do not depend on the
`GlobalPlugin` class. This is a stronger result than merely splitting a file.

### 4. Narrow public interface instead of Global Plugin access

Achieved.

`TerminalIntegrationService` accepts only a complete fixed set of
`TerminalCommand` values and narrow callbacks. The AppModule can no longer
invoke arbitrary private Global Plugin methods by name. Focus, F12, and
Braille operations check the closed state and concrete identities. The
service generation prevents an F12 authorization from a stale pre-reload
service from entering the new runtime.

### 5. Reliability and multi-instance operation remain intact

Supported by strong evidence, but not formally proven.

Automated coverage includes multiple instances, separate tabs and windows,
focus races, local and SSH selection, service replacement, delayed callbacks,
shutdown failures, temporary dialog focus, clipboard, and fail-open behavior.
Practical testing exercised multiple windows, tabs, and panes with mixed local
and remote connections, including clipboard operations, without a newly
reported error.

Real regressions were found during the migration, particularly focus changes
caused by the modal “remember connection” question and a later F12 offer that
was discarded because of that focus change. The correction is now bound to
identity, instance, and a one-shot reactivation. The occurrence of these
defects demonstrates the risk of the migration. Their reproduction,
isolation, automated coverage, and subsequent practical retest strengthen the
current solution.

## Effects on testability

### Improvements

- Services can be tested with injected dependencies without a complete NVDA
  instance.
- Immutable result objects make transitions and rejection reasons explicit
  and directly testable.
- Startup, partial failure, and shutdown have one fixed owner and a testable
  order.
- Focus generations, adapter tokens, service generations, and request IDs
  allow targeted race tests instead of timing assumptions.
- The built add-on remains tested as a package, preventing the source tree and
  shipped archive from silently diverging.
- AppModule fail-open behavior and `nextHandler` can be tested independently
  from connection and editor logic.

### Disadvantages and limits

- Many tests use extensive NVDA stubs and structural checks. They cannot fully
  replace verification against the real NVDA API.
- The very large central archive-test file impairs maintenance and targeted
  diagnosis.
- The complete NVDA test run has become noticeably slower.
- Without measured line or branch coverage, no direct percentage of executed
  code can be stated.
- Braille planning and fallback are covered automatically, but actual hardware
  operation is not.

Overall assessment: domain testability is clearly better; organizational test
maintainability should be improved next.

## Effects on maintainability

### Improvements

- Responsibilities are named and documented in ADR-0004.
- Changes to focus, F12, editor state, UI, or output no longer have to modify
  the same large state block.
- The AppModule/Global Plugin boundary follows NVDA conventions more closely.
- Moving to public NVDA Windows wrappers or `winBindings` removes parallel DLL
  bindings.
- Symmetric registration and idempotent shutdown reduce reload and partial
  initialization special cases.
- Small fixed public contracts limit accidental coupling.

### Costs

- More modules and almost twice as many classes increase onboarding effort.
- Many dataclasses and enums intentionally add definitions that must be
  followed while debugging.
- The composition constructor and callback wiring remain long.
- `session_claim.py`, `nvda_ui.py`, `editor_session.py`, and the remaining
  Global Plugin root are still large files.
- Documentation must keep these boundaries consistent; outdated phase
  descriptions could otherwise become confusing.

Overall assessment: maintainability improves for targeted changes and defect
isolation, while initial orientation becomes more demanding. For an add-on
with multiple processes, transports, and focus identities, that trade-off is
reasonable.

## Effects on robustness and security

### Positive changes

- Uncertainty about focus, identity, service generation, or authentication
  consistently returns to native NVDA processing.
- The service is published only after full initialization and is withdrawn
  and closed before the rest of shutdown.
- Late main-thread, network, F12, and Braille callbacks are rejected again
  after unpublication.
- Shutdown continues with remaining steps after an individual failure.
- AppModule events preserve NVDA LiveText through exactly one native focus
  invocation.
- F12 checks the concrete focused AppModule and complete terminal identity; a
  single available AppModule is not treated as focus evidence.
- Local and remote state is separated per instance, and correlated responses
  are discarded after focus loss.
- The public command surface is allowlisted and cannot dynamically grow to
  arbitrary methods.

### Remaining risks

- The essential state machine is distributed; defects may now occur at
  service transitions rather than inside one class.
- Additional callback layers can be wired incorrectly. Completeness and
  partial-initialization tests reduce but do not eliminate that risk.
- `SpeechPlanner.plan` remains a large, complex neutral hotspot.
- `SessionClaimService` still combines many related but demanding F12 and
  connection transitions.
- Practical Braille and other untested NVDA/WT combinations remain open.
- No new latency or memory benchmark is available. The extra local method and
  dataclass transitions are probably small compared with UIA, SSH, and RPC,
  but that assessment has not been measured.

Overall assessment: explicit invariants and shutdown paths protect robustness
better. The additional transitions create new possible defect locations, but
those locations are narrower and more directly testable than the former
shared state block.

## Is the additional complexity justified?

### Yes, for the domain boundaries

The add-on coordinates all of the following simultaneously:

- NVDA process lifetime and Windows Terminal AppModule lifetime;
- multiple windows, tabs, panes, and processes;
- local TCP and remote SSH sessions;
- asynchronous connection, focus changes, reload, and delayed replies;
- speech, sound, and Braille output;
- F12 as a narrowly constrained but process-wide observed assignment signal.

This complexity exists independently of the number of files. In revision
0.94.2, much of it was hidden as mutable state and private-method coupling in
the Global Plugin. The branch makes it visible and gives it testable
boundaries. The substantial reduction in root attributes, function length,
and local branching scores confirms that code was not merely moved.

### Not every additional abstraction would remain justified

The restructuring should not continue from this point merely to force
`GlobalPlugin.__init__.py` below an arbitrary line limit. A new layer is useful
only if at least one of the following gains can be demonstrated:

- one unambiguous new state owner;
- a smaller or more stable public contract;
- a failure path that thereby becomes testable without NVDA;
- removal of a real feedback dependency or duplicate state copy;
- a measurable reduction in startup, reload, or focus risk.

Pure forwarding methods or another facade name without owned state would
impair navigation and further enlarge the codebase.

## Concrete advantages

1. **Correct NVDA ownership:** events, overlays, commands, and `nextHandler`
   reside in the Windows Terminal AppModule.
2. **Less global mutable state:** reducing root attributes from 58 to 12
   lowers unintended cross-coupling.
3. **Better reload and shutdown:** publication, closure, and idempotent
   teardown have a fixed order.
4. **Stronger fail-open behavior:** a closed, stale, or uncertain service
   falls back to native terminal support.
5. **Better parallel isolation:** state and requests are correlated per
   instance and concrete terminal identity.
6. **Stronger tests:** 75 additional Python cases and 49 percent more static
   assertion occurrences protect the new boundaries.
7. **Smaller local decision blocks:** mean and high-percentile function
   complexity are substantially lower.
8. **Narrower attack and failure surface:** the AppModule contract exposes
   only fixed commands and validated operations rather than arbitrary private
   Global Plugin calls.

## Concrete disadvantages

1. **More total code:** Python production code grows by 41 percent.
2. **More structural concepts:** files, classes, dataclasses, and enums
   increase onboarding effort.
3. **Larger archive:** the add-on grows by about 7.6 percent.
4. **Slower test cycle:** the Python suites take almost twice as long in this
   measurement.
5. **Test monolith:** 62 percent of the Python test code resides in one file.
6. **Distributed debugging:** an event may cross AppModule, service, owner,
   planning, and NVDA presentation.
7. **Migration risk was real:** focus and F12 regressions had to be found and
   corrected through practical testing during the work.
8. **No demonstrated latency gain:** the architecture improves boundaries,
   not proven runtime speed.

## Quality assessment by common criteria

| Criterion | Assessment against `v0.94.2` | Reason |
|---|---|---|
| correctness of NVDA boundaries | substantially better | AppModule owns events, overlays, scripts, and `nextHandler` |
| cohesion | better | named services own related state |
| coupling | better at leaves, higher in composition | services do not import `GlobalPlugin`; the root composes more components |
| local complexity | substantially better | mean score 6.35 to 4.87; P90 12 to 9 |
| structural complexity | higher | 14 additional Python files and 49 additional classes |
| testability | substantially better | injectable services, fixed results, 75 new cases |
| test maintainability | partly worse | very large central package-test file and longer run |
| robustness | better protected | fail-open, service generation, rollback, teardown, and race tests |
| practical functional behavior | preserved so far | mixed local/SSH windows, tabs, panes, and clipboard without a reported error |
| performance/latency | open | no comparable runtime measurement of the product path |
| security/isolation | better | narrower commands, exact identity, and stale-callback fences |
| documented architecture | better | ADR-0004 and parallel developer documentation describe owners |

## Findings outside the core assessment

`git diff --check v0.94.2..HEAD` reports four trailing-whitespace locations in
the German and English quality reports from July 19. They appear to be
Markdown line breaks made with two spaces, but they prevent a completely clean
`diff --check` run. Before a merge, the hard breaks should be replaced with
normal paragraphs or another Markdown structure if a clean whitespace check
is a merge requirement. This is not a functional add-on defect.

Appendix integration note: the four warnings were removed on July 21, 2026 by
using normal paragraphs in Appendix A. The finding remains recorded here
because it existed at the documented comparison time.

## Recommendations

1. **Keep the current architecture.** The branch fulfills the domain slimming
   objective. Returning to the 0.94.2 monolith would lose real ownership and
   reload benefits.
2. **Do not extract further based on LOC.** Split production code again only
   for a concrete ownership, testing, or robustness gain.
3. **Modularize tests.** Divide `test_built_addon.py` into stable areas such as
   AppModule/focus, runtime/teardown, F12/connection, editor/clipboard,
   UI/localization, and package contents. Encapsulate shared NVDA stubs in a
   small test helper.
4. **Make fast and slow tests separately runnable.** Pure service unit tests
   should remain quick to select; archive and real Neovim RPC tests remain
   mandatory before a push or release.
5. **Observe complexity hotspots.** Plan `SpeechPlanner.plan` separately;
   split `SessionClaimService` only in response to concrete change pressure.
6. **Continue practical coverage.** Repeat the established matrix of multiple
   windows, tabs, and panes, local/SSH, focus changes, F12, clipboard,
   terminal, and reload before merge or release.
7. **Keep the Braille gap explicit.** Automated planning is not a substitute
   for hardware tests; do not infer a broader stability claim.
8. **Optionally add a latency baseline.** Record focus response, event
   planning, and main-thread time with a small reproducible measurement for
   future architecture changes.
9. **Remove the four `diff --check` warnings** if clean whitespace is intended
   as a merge requirement.

## Conclusion

If “slimming” means only fewer total lines, the branch did not achieve the
goal. That definition would be too narrow for this task. Under the relevant
architecture and quality objectives, the branch is successful: the global
entry point owns substantially less state, application-specific NVDA
responsibility resides in the AppModule, shared state has ordinary owners,
and reload, race, and fail-open paths are more explicit and more testable.

The increased structural complexity is mostly justified by these benefits.
It should now be stabilized rather than increased on principle. The most
useful next quality improvement is to divide and accelerate the test suite and
measure the remaining hotspots, not to continue a merely cosmetic
decomposition of the Global Plugin.

## Repository evidence

- architecture decision: [`ADR-0004`](adr/0004-nvda-lifetime-and-event-ownership.md)
- current implementation status: [`current-status.md`](current-status.md)
- active plan: [`plan.md`](plan.md)
- Windows Terminal AppModule: [`windowsterminal.py`](../../../nvda-addon/addon/appModules/windowsterminal.py)
- public terminal contract: [`terminal_integration.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/terminal_integration.py)
- ordered lifecycle: [`addon_runtime.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/addon_runtime.py)
- F12 and selection owner: [`session_claim.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/session_claim.py)
- editor state: [`editor_session.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/editor_session.py)
- connection owner: [`connection_coordinator.py`](../../../nvda-addon/core/nvim_nvda_core/connection_coordinator.py)
- central package/NVDA tests: [`test_built_addon.py`](../../../nvda-addon/tests/test_built_addon.py)
