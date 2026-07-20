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
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
ruff check .
ruff format --check .
python3 -m unittest discover -s protocol/python/tests -v
python3 -m unittest discover -s bridge/python/tests -v
python3 -m unittest discover -s nvda-addon/tests -v
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
python3 tools/gettext_catalog.py check
tools/build_documentation.sh
git diff --check
```

The two Ruff commands use Ruff 0.14.5, matching NVDA 2026.1. Configuration in
`pyproject.toml` limits them to Python modules loaded directly by NVDA under
`nvda-addon/addon/`; other components retain their own consistent styles.

`tools/test_neovim_plugin.sh` uses an available supported Neovim. Changes to
version boundaries should additionally run Lua and TUI suites with Neovim
0.10.1 and 0.12.3. An installed plugin must not shadow the checkout, so test
scripts isolate `packpath`.

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

When hardware is available, check current line, selection, Unicode, tabs,
messages, file-manager segments, and routing on multiple Braille displays.
Until then, every hardware claim remains explicitly unconfirmed.

## Classifying a failure

Output from the wrong session, a blocked main thread, unredacted confidential
text, repeated mutation, or suppression in an unbound control is a security or
isolation defect. Under uncertain focus or liveness, loss of an optional
feature is preferable to closing NVDA's native path.
