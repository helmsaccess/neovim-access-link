# Appendix C: Re-audit of the Global Plugin, Windows Terminal AppModule, and shared services

Created: August 4, 2026

Reviewed revision: branch `feature/lsp`, commit
`e9c8abb122c0`

Earlier comparison basis: final audit at commit
`b4195f3d900187f085275981d2ec1b0011a1952f`

Repository: Neovim Access Link

## Purpose and questions

This report re-examines whether the global NVDA portion contains only truly
process-wide work and whether application-specific processing remains in the
Windows Terminal AppModule. It was prompted by growth from LSP, diagnostics,
Braille, developer-context, and binding features since the earlier final
audit.

The review deliberately distinguishes three areas. A split into only “Global
Plugin” and “AppModule” would be technically incorrect:

| Area | Intended responsibility |
|---|---|
| `GlobalPlugin` as the NVDA entry point | one-time composition, publication, global registrations, and orderly shutdown |
| Windows Terminal AppModule | application events, overlay selection, concrete focus, contextual scripts and gestures, physical-key lifetime, and every `nextHandler` |
| ordinary shared services | connections, authentication, gate, editor, claim and focus state, protocol, UI, presentation planning, and output workflows with process lifetime |

Shared connections or editor state must not move into individual AppModule
instances. That would create duplicate owners, stale references, and reload
races across Windows Terminal processes, tabs, or panes. “Not in the
AppModule” therefore does not mean “must be a `GlobalPlugin` method.”

## Executive summary

The result has two aspects that must remain distinct:

1. **The NVDA ownership boundary remains correct.** `GlobalPlugin` contains no
   Windows Terminal event entry points, overlay selection, `nextHandler`,
   configurable NVDA scripts, or registration of the process-wide input
   observers. These parts live in the Windows Terminal AppModule and fail open
   to NVDA's default behavior when the service is missing, stale, or faulty.
2. **The `GlobalPlugin` class is not literally minimal.** It contains 2,857
   lines and 126 methods. Beyond construction and lifecycle, it includes
   substantial process-wide workflow coordination for connections, claims,
   dialogs, clipboard, network events, presentation, and Braille refresh.
   Most of this logic does not belong in the AppModule, but it could move
   incrementally into ordinary process-owned controllers or services.

No critical or high-severity scope defect was found. The primary finding is a
medium architectural and documentation deviation: the security-relevant
AppModule separation remains intact, while ADR-0004's Global Plugin class made
up solely of composition and lifecycle is still the target architecture, not
a fully achieved current state.

## Scope and method

The review covered in particular:

- the Global Plugin class and runtime, registry, terminal, focus, claim,
  editor, Braille, presentation, UI, and settings services;
- the Windows Terminal AppModule;
- structural and dynamic tests of the built add-on;
- ADR-0004, architecture, current status, and Appendices A and B.

The review combined AST-based size and ownership analysis, source searches
for NVDA hooks and back-references, inspection of actual call paths, and
targeted tests of an add-on built from the reviewed worktree.

## Quantitative state

| Component | Physical lines | Methods | fields assigned directly in `__init__` |
|---|---:|---:|---:|
| complete Global Plugin file | 3,232 | – | – |
| `GlobalPlugin` class | 2,857 | 126 | 15 |
| Windows Terminal `AppModule` | 1,076 | 58 | 13 |
| `TerminalIntegrationService` | 1,403 | 59, of which 47 are not private-named | 28 |

The earlier final audit measured 2,499 lines in the Global Plugin file, 112
GlobalPlugin methods, and 352 AppModule lines. The new features explain this
growth, but it warrants reassessing the earlier decision to stop further
extraction.

The present GlobalPlugin class divides approximately as follows:

| Line range | Size | Content |
|---|---:|---|
| 377–639 | about 263 lines | composition, startup/shutdown, scheduler and callback foundation |
| 641–2309 | about 1,669 lines | commands, claims, discovery, dialogs, clipboard, and temporary bindings |
| 2311–2766 | about 456 lines | managed-client events, result correlation, focus and network transitions |
| 2768–3156 | about 389 lines | event delivery, diagnostic sounds, speech, Braille, and developer contexts |
| 3159–3232 | about 74 lines | settings, session passwords, and active-client shutdown |

About 91 percent of the class lines therefore lie outside the first
composition/lifecycle block. This does not prove incorrect application scope,
but it clearly proves that the class does substantially more than a minimal
composition root.

## Confirmed ownership boundaries

### Application events and native delegation

The Windows Terminal AppModule owns overlay selection, focus gain and loss,
and events for text, characters, UIA notifications, live regions, value, name,
and description. It also owns every `nextHandler` call. The Global Plugin
package contains no AppModule event entry point; uncertain state permits
native processing.

### Scripts and concrete application gestures

Activation, Braille exploration, completion documentation, clipboard
commands, connection management, diagnostic report, and held callable and
diagnostic contexts are AppModule scripts. Global Plugin methods prefixed
with `action_` are not decorated as NVDA scripts and have no global gesture
assignment; they are fixed process callbacks of
`TerminalIntegrationService`.

### Process-wide input observers

The AppModule owns registration of `inputCore.decide_executeGesture` and
`inputCore.decide_handleRawKey`: the first instance registers, the last
unregisters symmetrically, and every path checks the concrete focused
AppModule instance. Unrelated gestures remain available; the raw-key path
only observes physical-key lifetime and fails open even on errors.

### Legitimate process-wide owners

| Owner | Reason for process lifetime |
|---|---|
| `ConnectionCoordinator` and instance manager | shared local and SSH connections and unique association of several controls |
| `SessionGate` | one fail-open suppression decision for the active authenticated control context |
| `EditorSessionController` | isolated runtime state per connection without AppModule copies |
| `SessionClaimService` | generations, inventory, and one-shot F12 authorization across several targets |
| `TerminalFocusService` | focus generation, concrete control identity, and protection from late events |
| `SettingsService` and `NvdaUiManager` | one-time profile, Settings, and Tools registration |
| `NvdaPresentation` and sound caches | audio resources loaded once and central NVDA delivery |
| `AddonRuntime` | late publication and fixed idempotent shutdown order |

These components do not inherit from `GlobalPlugin`. None of the reviewed
extracted services references the class or retains a broad `_plugin` or
`_runtime` back-reference. `ServiceRegistrar` publishes only
`TerminalIntegrationService`; an identity token protects replacement during
reload.

## Findings

### M1 – Medium: not a minimal composition root

The class still, or once again, implements complete selection and connection
flows, concrete dialogs, restoration of temporary bindings, clipboard and
terminal-control flows, network-event distribution, diagnostic sounds,
typing echo, Braille refresh, held developer contexts, and the session
password dialog.

This is not an AppModule-scope defect. The workflows are shared and need one
owner across focus changes and multiple AppModule instances. They do not,
however, have to remain methods of the NVDA-loaded subclass.

### M2 – Medium to low: clean but broad service contract

`TerminalIntegrationService` has no Global Plugin back-reference, and the
AppModule accesses no private service fields. This most important contract
property is satisfied. The concrete service nevertheless has 47 public-named
methods. The AppModule uses 26, the Braille module ten, and further methods
form result and lifecycle boundaries. “Bounded” therefore accurately
describes trust and ownership, not a small API.

Consumer-specific ports could clarify the allowed surface later. An immediate
split based only on method count is not justified.

### N1 – Low: private package exports in the AppModule

The AppModule obtains the published service rather than the plugin instance,
but it also imports private constants from the package. This is not access to
mutable runtime state, yet it weakens the claim of a completely explicit
public adapter contract. A small API module or a statically checked symbol
allowlist would be clearer.

### N2 – Low: large but correctly scoped AppModule

At 1,076 lines and 58 methods, the AppModule is also large. Events, scripts,
gesture resolution, physical-key lifetime, and focus revalidation belong
there. Stateless helpers or an AppModule-owned input controller may be
extracted if it grows further; NVDA hooks, `nextHandler`, overlay selection,
and the final fail-open decision must remain there.

## Recommendations

### 1. Name current state and target architecture separately

Until further decomposition, documentation should describe the Global Plugin
as a “process-wide NVDA-edge controller and composition root.” ADR-0004
remains the target decision for a minimal root. This clarification was applied
to architecture, current status, plan, and test strategy together with this
report.

### 2. Decompose only in domain-focused slices

Suitable independently testable candidates are:

1. a connection and claim workflow for discovery, selection, dialogs,
   connection startup, and temporary restoration;
2. an NVDA event-delivery boundary for managed events, diagnostic sounds,
   typing echo, and Braille refresh;
3. a context-presentation boundary for numbered choices and held developer
   text;
4. small named adapters for terminal identity, configuration schema, and
   public AppModule symbols;
5. consumer-specific ports for the AppModule, Braille, and internal results.

Each slice must preserve reload, multiple AppModule instances, stale
callbacks, focus races, fail-open behavior, and fixed shutdown ordering. Mere
line movement or a rigid LOC limit is not a quality improvement.

### 3. Protect contract boundaries with focused automated checks

Useful additions include source tests against application hooks in the Global
Plugin, an allowlist of AppModule package exports, consumer-specific test
doubles, and the existing ban on GlobalPlugin back-references. A maximum
method count would not be a meaningful architecture test.

## Verification evidence

Existing package tests cover separate UI registration, single ownership of
focus and claim state, token-safe service publication, fault-tolerant
shutdown, AppModule ownership of every event and script, service access
without the plugin instance, fail-open behavior, exact F12 focus binding,
symmetrical observer registration, and exactly-once native delegation.

For this audit, the freshly built add-on passed:

- eight architecture, registry, runtime, and contract checks;
- seven observer, AppModule, event, and fail-open checks.

Total: **15 of 15 targeted tests passed**.

## Limits of this assessment

The audit assesses source structure, dependencies, the built package, and
simulated NVDA contracts. It is not a new Windows/NVDA practical test, load or
latency test, or Braille-hardware test. The scope boundary has strong
structural evidence; the recommendation for further slimming concerns
maintainability and documentation, not an observed runtime defect.

## Conclusion

Everything that necessarily belongs to the Windows Terminal application
context remains in the AppModule. The global portion does not reach into
other applications through NVDA events, `nextHandler`, overlays, or global
scripts.

Under a strict reading, the `GlobalPlugin` class still contains more than the
absolutely necessary composition and lifetime work. This remainder must not
be moved wholesale into the AppModule. Where ownership or testability clearly
benefits, it should move incrementally into ordinary process-owned services,
bringing the code closer to the documented target architecture without a new
parallel path.
