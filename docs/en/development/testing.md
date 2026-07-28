# Test strategy

This chapter describes durable verification. See `changelog.md` for results
from past builds and `current-status.md` for currently confirmed scope. Test
counts are not duplicated here because they become stale after every change.

The lists below define important evidence and repeatable checks. They do not
mean every conceivable combination has been tested or every item in the
practical matrix is repeated for each build. Only cases explicitly listed as
practically confirmed in `current-status.md` have that status; gaps and new
defects remain possible.

## Test goals

Tests must prove more than the successful path. In particular:

- one session never inherits state or output from another;
- unbound terminal controls retain NVDA's native support completely;
- errors, uncertain focus, and disconnects fail open;
- untrusted protocol data cannot execute code or consume unbounded resources;
- byte, Unicode, virtual, and visual columns remain distinct;
- network, SSH, reconnect, parsing, and installation never block NVDA's main
  thread;
- packages work from the files actually shipped;
- automated evidence remains distinct from practical confirmation.

A mock-based automated test is not practical approval of a real plugin,
terminal frontend, or Braille driver.

## Test layers

| Layer | Purpose | Typical location |
|---|---|---|
| Protocol | Framing, schema, limits, sequences, resync, and control payloads | `protocol/python/tests/` |
| Bridge | Session discovery, Neovim RPC, SSH stdio, and allowlist | `bridge/python/tests/` |
| Core | Canonical state, speech, Braille, and fail-open gate without NVDA | `nvda-addon/tests/` |
| Add-on integration | Global Plugin, AppModule, focus, gestures, installation, and package layout with NVDA stubs | `nvda-addon/tests/` |
| Lua specifications | Real Neovim APIs, state events, and adapters | `neovim-plugin/tests/*_spec.lua` |
| TUI/RPC integration | Disposable real Neovim, pseudoterminal, and persistent RPC channel | bridge and plugin tests |
| Build | Actual add-on, embedded Linux package, gettext, and HTML | build and package tests |
| Practical | NVDA, Windows Terminal, local Neovim, SSH, tmux, and later Braille hardware | recorded manual matrix |

TUI, socket, and SSH tests must never attach to a user's existing Neovim or
tmux session. They use separate temporary directories, sockets, processes, and
test accounts.

## Standard checkout verification

Run from the repository root:

```bash
ruff check .
ruff format --check .
tools/run_tests.py all-safe
tools/run_tests.py ssh
python3 tools/build_nvda_addon.py
python3 tools/gettext_catalog.py check
tools/build_documentation.sh
git diff --check
```

`tools/run_tests.py` starts independent files or integration cases in separate
processes. Every process receives its own temporary directory and
`XDG_RUNTIME_DIR`; up to eight jobs run concurrently by default. The
import-intensive package shards additionally use their own Python bytecode
cache, while short jobs produce no bytecode files. Use `-j N` to limit
concurrency and `--list` to inspect selection without running it.

| Group or preset | Contents |
|---|---|
| `unit` | pure and mock-isolated Python tests |
| `package` | built add-on, package contents, and NVDA integration doubles in two isolated process shards; serial within each shard |
| `lua` | headless-Neovim specifications that do not open listeners |
| `ssh` | separately runnable SSH command, Askpass, and failure paths; all external processes are replaced in these automated tests |
| `socket` | real disposable Neovim TUI, RPC, TCP, and Unix-socket cases |
| `quick` | fast feedback; equivalent to `unit` |
| `safe` | default: `quick`, `package`, and `lua` |
| `all-safe` | complete listener-free `unit`, `package`, and `lua` suite; an alias of `safe` for CI and documented complete runs |
| `all` | every group in three sequential phases: `all-safe`, then `ssh`, then `socket` |

The `ssh` group remains a separate phase even though every external process is
replaced. This keeps SSH, Askpass, and process-failure evidence distinct from
the listener-free standard suite:

```bash
tools/run_tests.py ssh
```

Each package shard builds and extracts exactly one actual add-on. Normal tests
share that unchanged extraction; a fingerprint over names and contents detects
unintended writes. Only the two tests that deliberately change configuration
or remove bundled sounds receive their own fresh extraction.

The `socket` run requires an environment that permits local listeners and Unix
sockets, so it is deliberately separate:

```bash
tools/run_tests.py socket
```

In a restricted sandbox, an `operation not permitted` failure must not be
reinterpreted as a product defect. Running outside the sandbox remains
mandatory before a push or release when socket, session, or TUI code is
affected. The automated `ssh` group opens no real SSH connection; practical
SSH checks continue to use a disposable test account under this chapter's
rules.

## GitHub Actions

`.github/workflows/repository-tests.yml` runs five independent job types for
pushes and pull requests:

1. unit, package, and listener-free Lua tests through `all-safe`;
2. real completion-plugin API contracts in three separate Neovim/plugin
   configurations;
3. real diagnostic-provider contracts with nvim-lint, ALE, and
   `none-ls.nvim`, plus seven real linters on two Neovim versions;
4. mocked SSH and Askpass paths through `ssh`;
5. disposable TUI, TCP, and Unix-socket cases serially through `socket -j 1`.

The safe, SSH, and socket Python test jobs set up the same fixed Python version
and then install the version-pinned Python test dependencies from
`tools/requirements-ci.txt`. This keeps results independent of Python versions
or packages that happen to be preinstalled on the runner. The diagnostic
provider job separately uses `tools/requirements-linter-ci.txt`; those
packages supply the Python-based Clang-Tidy, Ruff, and ShellCheck tools. The
completion contract job needs no Python dependencies.

The safe and socket jobs download the official Neovim 0.10.1 Linux archive
from GitHub. The workflow pins its URL and SHA-256 digest and verifies the
archive before extraction. The completion contract job expands into three
matrix configurations: `nvim-cmp` and `blink.cmp` v1 on Neovim 0.10.1 and
0.12.3, plus `nvim-cmp` and the provisional `blink.cmp` v2 revision with
`blink.lib` on Neovim 0.12.3. SHA-256 digests pin the Neovim archives and exact
commit IDs pin all three external Lua repositories. The job needs no compiler,
Python packages, test-time network access, or private credentials. The
diagnostic matrix likewise downloads verified Neovim archives, pinned
nvim-lint, ALE, `none-ls.nvim`, and its sole test dependency `plenary.nvim`,
plus exact Python wheels for Clang-Tidy, Ruff, and ShellCheck. Exact commit IDs
pin every Lua plugin. It additionally sets up Go 1.26.5 with Staticcheck
2026.1, Rust 1.97.1 with Clippy, Ruby 3.4.10 with RuboCop 1.88.2, and Node.js
24.18.0 with `markdownlint-cli2` 0.23.2. Setup actions and Lua plugins use
exact commit IDs; language runtimes and direct linters use exact versions.
After installation the matrix runs without test-time network access or
listeners. The SSH job also receives no credentials and contacts no SSH host.
Every job has a time limit, and a new run for the same branch cancels an older
run that is still in progress.

GitHub Actions does not replace practical NVDA and Windows Terminal
verification. It supplies reproducible Linux feedback and prevents a failed
specialized path from being hidden inside a general suite. Socket cases run
serially in CI so multiple real Neovim TUIs do not compete for constrained
runner time. GitHub's **Actions** tab lists each run; opening a failed job
shows the affected test file or isolated case.

The two Ruff commands use Ruff 0.14.5, matching NVDA 2026.1. Configuration in
`pyproject.toml` limits them to Python modules loaded directly by NVDA under
`nvda-addon/addon/`; other components retain their own consistent styles.

`tools/test_neovim_plugin.sh` remains the serial compatibility run with an
available supported Neovim. Changes to version boundaries should additionally
run Lua and TUI suites with Neovim 0.10.1 and 0.12.3. An installed plugin must
not shadow the checkout, so test scripts isolate `packpath`.

`bash tools/test_completion_plugins.sh NVIM_CMP_CHECKOUT BLINK_CMP_CHECKOUT
[BLINK_LIB_CHECKOUT]` loads real, locally available upstream modules in an
isolated Neovim process. It proves the public API, event registration, and
adapter normalization while injecting selection values deliberately. It is a
reproducible API-contract test, not complete TUI or Windows/NVDA acceptance.
Test `blink.cmp` v2 with Neovim 0.12 and the third `blink.lib` checkout.

`bash tools/test_linter_plugins.sh NVIM_LINT_CHECKOUT ALE_CHECKOUT` loads both
real providers sequentially in fully isolated headless Neovim processes.
Clang-Tidy 22.1.8, Ruff 0.15.4, ShellCheck 0.11.0, Staticcheck 2026.1, Clippy
from Rust 1.97.1, RuboCop 1.88.2, and `markdownlint-cli2` 0.23.2 must be on
`PATH`; a missing or mismatched version fails clearly. The test creates only
disposable C, Python, Bash, Go, Rust, Ruby, and Markdown fixtures, waits for
the actual linter process and `DiagnosticChanged`, then inspects only
`vim.diagnostic` and the Access Link snapshot. ALE selects
`markdownlint-cli2` through its documented executable option; its output is
compatible with ALE's existing Markdownlint handler. The test reads no private
provider state and opens no listener.

`bash tools/test_none_ls.sh NONE_LS_CHECKOUT PLENARY_CHECKOUT` loads the real
LSP bridge and its declared Lua dependency in another isolated headless
process. Its built-in `trail-space` source publishes a real diagnostic through
the none-ls LSP client and `DiagnosticChanged`; the test then checks client
attachment, range, source, and the provider-neutral Access Link snapshot. It
needs neither an external linter executable nor an extracted none-ls source.

## What automated suites prove

### Protocol and transport

Required cases include:

- protocol v2, SSH marker, and size-bounded MessagePack framing;
- rejection of v1, oversized frames, invalid types, and malformed UTF-8;
- session ID, monotonic sequence, heartbeat, gap, resync, and `fullState`;
- local client only for the registered port on exactly `127.0.0.1`;
- nonce validation on the persistent RPC channel before `setup()`;
- fixed control allowlist with field, size, and state validation;
- no retry of an already dispatched state-changing action.
- strict exploration actions, identifiers, origin, text bounds, and rejection
  of foreign or late results;
- end-to-end plugin capability confirmation: an older installed or still
  running plugin must not expose or receive exploration controls.

### Session registry, claim, and binding

Tests distinguish:

1. physical F12 mark in the focused control;
2. monotonic claim in the private session record;
3. unique resolution relative to the activation baseline;
4. binding the complete `TerminalIdentity` to a `ConnectionInstance`;
5. authentication through the first valid `fullState`.

Cases include old or absent claims, concurrent candidates, focus changes during
pending resolution, two controls with the same process and window handle but
different runtime IDs, and concurrent local and SSH instances. Without a fresh
unique claim, no binding, suppression, choice, or connection announcement may
occur.
The NVDA decider is also exercised with F12 in an unrelated application, a
foreign or stale AppModule, a second WT process, and a rapid focus change
before main-thread evaluation. Real TUI tests must obtain a claim in both
Normal and Insert mode; Insert mode must retain neither `<F12>` nor any part of
the terminal sequence in the buffer. This matrix runs against Neovim 0.10.1
and 0.12.3.

Graceful exit, SIGKILL, PID/endpoint/nonce reuse, dead or uncertain records,
owned and foreign sockets, and closed Windows Terminal controls must be
non-destructive. Cleanup must terminate neither Neovim nor tmux.

Automated coverage for the NVDA-side Windows adapters distinguishes live and
exited processes, invalid PIDs, access denial, and uncertain failures. Only a
conclusively exited process may delete an owned session record; a closed
terminal identity still requires two conclusive negative lifecycle checks
before cleanup.

### Editor, presentation, and focus

Core and add-on tests cover modes, navigation, editing, selection, completion,
signature help, search, diagnostics, spelling, indentation, messages,
terminal, file managers, speech, sounds, and Braille.

Important cases are:

- UTF-8 with combining marks, wide characters, emoji, and tabs;
- overlapping `TextChanged` diffs without duplicate typing echo;
- correlated focus responses and rejection of late responses;
- all three focus presentations without a character fragment or duplicate
  mode;
- native output in shells, wrong UIA classes, empty runtime IDs, disabled
  support, and disconnects;
- complete event, overlay, and `nextHandler` ownership in the Windows Terminal
  AppModule;
- exactly one native focus invocation before structured speech suppression,
  with fail-open behavior and no repeat after early or late failures;
- late `loseFocus` and reentrant focus completion without clearing newer WT
  focus or losing a pending `fullState`;
- unbound configurable gesture metadata only on the Windows Terminal
  AppModule and none on the Global Plugin;
- exact focused-AppModule and control validation, with one pass-through of the
  original gesture if focus changes before execution;
- separate AppModule instances never execute one another's command.
- only NVDA's normal script resolution for the six fixed exploration chords,
  exact-pane authorization, a passive always-`True` raw-key callback, rapid
  release handling, and a bounded autorepeat barrier;
- virtual character, line, and word movement without changing the real
  cursor, buffer, changed tick, mode, or view;
- built-package structure checks keep all application-event entry points out
  of the Global Plugin and reject Global Plugin dependencies from extracted
  runtime, UI, focus, claim, editor, Braille, registry, and terminal-service
  modules.

### Terminal and command line

Automated TUI and add-on tests distinguish:

- file-buffer Normal, `terminalNormal`, direct terminal input, and command-line
  mode;
- Insert/Normal cues, command-line tone, and passthrough ordering;
- `stopinsert` as the terminal-exit command's only operation;
- complete command-line echo using its UTF-8 byte position;
- the immediate Ex return message from a later asynchronous message;
- `:bp`, `:bn`, `:terminal`, window, and tab changes under all focus choices;
- `E89` for `:bd` on a live terminal job and `TermClose` with exit status;
- Neovim 0.12 UI handling outside fast-event context.

### File managers and prompts

Suites cover netrw, Oil, mini.files, nvim-tree, and Neo-tree only to the extent
proven by their public APIs. Cases include:

- UTF-8-safe byte limits for names, paths, and roots;
- kind, mark, Copy/Cut, expansion, and same-entry state changes;
- deduplication, render-event coalescing, and inactive-target rejection;
- create, rename, copy, move, delete, restore, batching, failure, and cancel
  where public evidence exists;
- `vim.ui.input`, `vim.ui.select`, and `vim.fn.confirm` acceptance/cancel;
- Oil's narrow `oil_preview` fallback without path or name transport;
- draft name before `:w` versus confirmed path identity;
- semantic Braille and routing only through an unambiguous name range.

A real external plugin may be tested only in a disposable, version-pinned work
tree. Such an isolated run does not replace Windows/NVDA acceptance.

## Build and documentation verification

Package tests must extract the actual `.nvda-addon`, open its embedded
`server-user.tar.gz`, and install Linux components into a temporary prefix.
Testing repository sources alone is insufficient.

Verify at least:

- matching component and F12 configuration on both package sides;
- only intended add-on, plugin, bridge, and protocol files;
- German manifest and `locale/de/LC_MESSAGES/nvda.mo`, with no PO/POT sources
  in the archive;
- byte-identical repeated MO compilation and matching named placeholders;
- German and English quick guide, user manual, and developer documentation;
- exactly one H1 per HTML file, valid internal targets, and no remaining `.md`
  links;
- explicit assignment of every published Markdown source to an HTML build.

## Rules for practical tests

A practical record includes:

- date and OS, NVDA, Windows Terminal, Neovim, and OpenSSH versions;
- local or remote transport and relevant add-on settings;
- initial state, exact commands, and keys;
- expected and actual speech, sounds, and Braille;
- outcome and a redacted diagnostic excerpt on failure.

Never record real hostnames, accounts, domains, key paths, passwords, or
confidential editor content. Do not use existing Neovim or tmux sessions for
destructive tests.

## Practical end-to-end matrix

This matrix is a risk-based checklist for changes and release candidates, not
a claim that one exhaustive acceptance run has already covered it all. Select
the affected and adjacent paths for each change, prioritizing security,
isolation, and data-changing behavior.

### Installation and basic connection

1. Install the add-on, restart NVDA, and update local components plus one
   disposable saved SSH target through the Tools dialog.
2. Confirm that the dialog remains operable, reports targets separately, and
   one failing target does not block the others.
3. Start local `nvim.exe` and remote Neovim. Enable support, wait for inventory,
   and bind each session with a physical F12 press.
4. Check Normal, Insert, Visual, navigation, editing, and one message.
5. Disable support and end a transport. Native terminal output must return
   immediately and globally.

### Windows Terminal isolation

Use at least:

- one bound local Neovim control;
- one bound SSH Neovim control;
- one unbound PowerShell, Command Prompt, or WSL tab;
- horizontal and vertical split panes;
- two Windows Terminal windows where possible.

Move among all controls slowly and rapidly. Expected behavior:

- structured output only from the exactly focused bound instance;
- no output, binding, or suppression from another active instance;
- F12 in a shell without a fresh Neovim claim has no effect;
- a remembered binding opens the gate only after a matching correlated focus
  response;
- closed tabs or windows stop only their NVDA client;
- disconnect does not bind another session automatically;
- a new session in the same control requires another physical claim;
- unbound controls retain NVDA focus, text, LiveText, and Braille behavior.

Record the UIA class and complete runtime ID in redacted form so tabs, panes,
and windows are not confused.

### Speech exploration mode

Update components and restart every running Neovim instance. While physically
holding NVDA, exercise `h/l`, `k/j`, and `Shift+h/l`. Expected behavior:

- characters, lines, and words follow only the virtual position; the real
  cursor, buffer, mode, changed tick, and view stay unchanged;
- after mixed movements, release reads the character or the configured
  word/line details at the real cursor according to the last-used unit;
- on the Navigation settings tab, check word only versus word plus cursor
  character and all four line combinations independently for normal
  navigation and exploration release; when enabled together, the order is
  line, current word, cursor character;
- rapid release, autorepeat, and releasing NVDA before the direction key send
  no bare `h/j/k/l` to Neovim;
- Normal, Insert, Replace, Visual, Operator-pending, command line,
  Terminal-Normal, and direct terminal input remain readable;
- boundaries, empty and short lines, tabs, combining marks, wide characters,
  and emoji remain stable;
- backward word exploration stops at the preceding word on another line and
  never merges keyword characters across a newline;
- moving away and returning to the original character, word, or line plays
  exactly one short two-note cue; remaining at that unit does not repeat it;
- local and SSH Neovim work across mixed tabs, split panes, and windows;
- the same chords retain normal NVDA behavior in every unbound shell, foreign
  pane/tab, and other application;
- focus, disconnect, or Neovim-context changes end exploration silently and a
  late result cannot appear in the new session.

On July 23, 2026, this core path was exercised practically under Windows and
NVDA. Character, word, and line exploration, backward word movement, the
two-note origin cue, release feedback, and the independent word and line
choices for normal navigation and exploration produced no observed defect.
This evidence complements the automated matrix; it does not replace testing
with other keyboard layouts, languages, GlobalPlugins, or physical Braille
hardware.

### Built-in spelling suggestions

Update the Neovim components, restart Neovim, and enable `:set spell` in a
disposable buffer. Focus a misspelled word and press `z=`. Expected behavior:

- one brief spoken message announces the available non-empty list;
- while NVDA remains held, `NVDA+j/k` cycles through suggestions; speech and
  Braille contain the suggestion but no number;
- in NVDA's “follow cursors” Braille mode, NVDA's transient Braille message
  changes immediately on every step; enable Braille messages in NVDA for this
  test. “Display speech output” follows spoken output instead and does not
  test a fixed start cell;
- the default Braille start cell 1 adds no padding; a configured in-range cell
  such as 40 starts the transient suggestion there, while a value beyond the
  connected display is ignored and falls back to cell 1; if the suggestion
  translated with the active Braille table does not fit to the right, its
  start is limited leftward to the last position where it fits completely;
- releasing the final NVDA key discards only the local selection, restores
  the editor Braille line, and leaves Neovim's prompt open;
- exploring again and pressing `NVDA+Enter` accepts exactly the selected item;
- `NVDA+Enter` without a local selection reports “No item selected” and in
  particular does not run a gesture assigned to clipboard paste;
- NVDA Input Help describes gestures without moving or accepting a choice;
- `Escape` cancels the native prompt, while focus, mode, buffer, tab, pane, or
  connection changes leave no transient selection behind;
- outside the proven `z=` prompt, in a shell, or in another control, J, K,
  Enter, and user-assigned add-on gestures retain their previous behavior.

Also set NVDA's spelling and grammar formatting to “sound” or “speech and
sound”: normal word navigation and `Shift+NVDA+h/l` word exploration play
`textError.wav` when they reach an erroneous word. A correct word does not
trigger the cue.

Automated parser, protocol, transport, controller, AppModule, Braille, and
built-add-on tests cover positive and negative paths. This includes the
immediate message buffer, cell-accurate positioning, targeted restoration of
the editor buffer, and preservation of a newer Braille message from another
source. A real TUI/RPC matrix
also covers the blocking Neovim 0.10 prompt and the scheduled Neovim 0.12
path, including acceptance of the native index. Practical Windows/NVDA
acceptance of the suggestion path succeeded with one physical Braille display;
a broader hardware matrix remains pending.

The post-acceptance Braille architecture audit adds two fail-open regressions.
First, `StructuredLineRegion.routeTo` must call neither the local nor the SSH
client directly; it must submit an immutable `routeCursor` payload to the
bounded `ControlDispatcher`. The test therefore supplies a client whose
`send_control` must not be called and verifies only the dispatcher submission.
Second, a no-op public `braille.handler.message()` call must not claim an
already visible foreign Braille message, stop its timer, or dismiss it later.
Only a newly created last message region which remains identical proves
ownership.

Automatic caret following has a package regression: a semantic cursor change
must use public `braille.handler.handleCaretMove`, while content-only updates
remain on `handleUpdate`. The structured region must be a `TextInfoRegion` but
translate its Neovim content through `Region.update()`. NVDA's own buffer can
therefore restore the viewport first and scroll to the Braille cursor only
when needed.

Braille-display line navigation has coverage at four levels:

- protocol tests reject extra fields, unknown directions, command-line or
  target rules, terminal modes, and oversized virtual columns;
- local and SSH transports negotiate `brailleLineNavigation` only with a
  matching new plugin and forward only the fixed `moveBrailleLine` entry
  point;
- the built-add-on test calls NVDA's public `previousLine()` and `nextLine()`
  region methods, distinguishes direct Up/Down from horizontal line
  transitions, and expects dispatcher jobs rather than main-thread I/O. The
  down-command marker is exactly bound, one-shot, input-help safe, and expires
  in the next event turn;
- Lua and real RPC tests move across a short intermediate line in Normal and
  Insert modes. `curswant` must retain the preferred virtual column and
  restore it on the next longer line. Horizontal line transitions instead
  select the previous end or next start. Empty lines, tabs, UTF-8/wide
  characters, buffer boundaries, stale changed ticks, and Normal/Insert end
  positions are included.

Practical BRAILLEX EL 80c coverage must check horizontal panning of a long
line, Up/Down in Normal and Insert modes, short intermediate lines, and buffer
boundaries. This hardware check is not recorded as passed before user
feedback.

The separate Braille exploration mode adds these automated layers:

- validators accept only fixed line actions, complete origin identity, a
  bounded desired column, one of three fixed target rules, and correlated
  results;
- controller tests cover the toggle, boundaries, UTF-8, stale or superseded
  replies, bounded pending queues, dispatch failure, and unchanged canonical
  editor position. They retain the virtual display across real-cursor and
  mode movements and edits on other lines. On the explored real-cursor line,
  they adopt the complete new line-derived state, including a subsequent
  return from Insert to Normal mode, without re-anchoring the virtual line,
  reading column, or viewport. Routing requires the displayed content and
  canonical state to share one current `changedtick`; stale content from an
  edit elsewhere remains visible but cannot be routed. They advance
  `changedtick` only within the same context and still reject navigation in
  command-line and terminal modes;
- transport tests cover independent capability negotiation, fixed plugin
  entry points only, and removal of one-shot results from state caches;
- package tests cover the freely assignable AppModule script, absence of a
  default gesture, off-thread dispatch, exact focus/instance binding, Braille
  mode and numbered-choice controllers isolated across concurrently tracked
  instances, restoration of each session's mode, virtual line, and horizontal
  NVDA viewport on return from a control or application switch, clamping of a
  stored viewport against shorter content, an audible focus announcement
  without a covering Braille message in exploration mode, targeted reset of only the
  disconnected runtime, and cancellation of repeated-routing and focus
  sequences when the control changes,
  refresh, routing from the virtual line, suppression of an apparent virtual
  cursor, retention of the real cursor after routing and then editing that
  line, clearing of a concurrently set follow-caret marker only in Braille
  exploration mode, and pass-through of native caret
  navigation keys only in the exactly suppressed Neovim control;
- Lua and real Insert-mode RPC cover a short then longer line, the Insert line
  end, a subsequently moved real cursor, and interleaving with separate
  speech exploration. The general navigation specification requires exactly
  one semantic movement event for one arrow-key press.

Practical hardware acceptance must additionally confirm the toggle, its
unambiguous mode message, Up/Down without real-cursor movement, routing from
the virtual line, independent mode selection across local and remote sessions,
loss of the transient position only on an internal Neovim buffer, window, or
tab change, restoration of position and horizontal viewport after session and
application switches, targeted reset only when that session disconnects, and
independence from `NVDA+h/j/k/l`.

For optional speech-exploration following, protocol and Lua tests cover the
bounded complete virtual line. Core and package tests verify that it replaces
the derived Braille view only when configured, disappears on release, and
never mutates canonical editor state. Separate Braille exploration must retain
priority; invalid, absent, or oversized lines must not take over the Braille
plan.

Repeated presses of the same routing key add a separate automated matrix:

- the pure recognizer covers an immediate first press, an immediate word
  action without a configured triple action, a deferred word action with a
  triple action, replacement by the third press, token invalidation, timeout,
  and changed target signature. The service revalidates a deferred action
  against the current instance and editor state immediately before dispatch;
- settings and package tests cover safe zero defaults, every choice value,
  profile persistence, NVDA's multiple-press timeout, and dispatcher-only
  transport;
- protocol and transport tests reject extra fields, arbitrary commands,
  invalid modes, actions, and line starts, missing capability, and stale
  state;
- Lua tests cover `dw`, `^d$`, `0d$`, whitespace, read-only buffers, UTF-8
  boundaries, and changed tick. A real socket test covers deleting a word in
  the middle of a line while returning to Insert mode, plus `^c$` entering
  Insert mode.

The reference repeated-routing workflow has been accepted on the BRAILLEX
EL 80c. Broader practical coverage must still exercise every combination of
the three line starts, `cw`, `dw`, `c$`, `d$`, an intentionally slow double
press, a routing-position change, unchanged command-line behavior, and more
than one display driver.

### Focus presentation, buffers, and terminal

Check every Session focus value:

1. no announcement;
2. current line;
3. current context, mode, and connection name.

Mode sounds remain a separate setting. Focus return, `:bp`, `:bn`,
`:terminal`, Neovim windows, and tabs must not speak a single name character
or duplicate mode. Different source-buffer cursor positions must not change
the destination line.

In an embedded terminal, also check:

- `i` into direct input: complete cursor line, Insert cue, and native shell
  output;
- `Ctrl+\`, `Ctrl+N`, and the assigned exit gesture: exactly one Normal cue
  and structured Terminal-Normal navigation;
- `:echo`, `:lua print`, a later `vim.notify`, and Unicode command-line echo;
- `:bd` on a live job, no-op `:bp`/`:bn`, a real buffer switch, `exit`, and
  exit status.

### Clipboard

Focus Windows Terminal before opening NVDA's Input Gestures dialog. The product
category and freely assignable commands must be visible there, absent from an
unrelated application's AppModule command set, and executable only for the
exact focused Windows Terminal AppModule. After assigning a gesture and
loading that AppModule class, reopening the dialog elsewhere may still list
the saved mapping through NVDA's global user map; verify that execution remains
scoped. Reassign commands once after moving from a build that stored them under
the Global Plugin.

Locally and over SSH, check:

- characterwise, linewise, and blockwise Visual selections with ASCII,
  Unicode, emoji, tabs, and multiple lines;
- register 0 after `yy` and other yanks;
- single- and multiline Windows text with CRLF through `nvim_paste`;
- register 0 with and without a trailing line break followed by `p`;
- focus, buffer, tab, pane, or mode change during a request;
- rejection in shells, terminal buffers, file managers, readonly, and
  `nomodifiable` buffers;
- redacted diagnostics without transferred text.

Each action may take effect at most once. There is no automatic
synchronization or retry.

### File managers

For each manager being accepted practically, use a disposable project with
source, tests, notes, chapters, and media. Names include spaces, accented and
non-Latin characters, and punctuation.

1. Enter or expand directories, navigate siblings, and open files.
2. Create, rename, duplicate, move, and delete a file and directory.
3. Mark multiple entries and perform a batch action.
4. Answer overwrite or delete with No/Cancel, then Yes.
5. Check a conflict, invalid name, read-only target, and focus change during
   the action.
6. Move among manager, file, terminal, WT tab, pane, and window.

For Oil, additionally check draft names before `:w`, boundary cues with `0`,
`$`, `gg`, and `G`, and its custom confirmation float. For nvim-tree,
`select_prompts = true`, and for Neo-tree, `use_popups_for_input = false`, can
make their public `vim.ui` paths available; the add-on does not set these
options.

Success must come only from a proven completion event. No or Cancel must leave
the project unchanged. Complete paths and names of unrelated entries must not
appear in compact action messages or diagnostics.

### Localization and Braille

With English and German NVDA, compare at least settings, Tools dialogs,
activation, errors, focus presentation, modes, clipboard, and file managers.
Document content and third-party Neovim messages are not translated by the
add-on.

One physical Braille display confirms current line, Unicode, tabs, an empty
line, the virtual end position, initial-region rebuild, messages, and routing
in Normal, Insert, and command-line modes. Selection, file-manager segments,
different translation tables and drivers, and additional displays remain in
the broader matrix.

## Classifying a failure

Output from the wrong session, a blocked main thread, unredacted confidential
text, repeated mutation, or suppression in an unbound control is a security or
isolation defect. Under uncertain focus or liveness, loss of an optional
feature is preferable to closing NVDA's native path.
