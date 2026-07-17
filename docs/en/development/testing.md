# Test strategy

Python protocol, bridge, and NVDA-independent core tests run separately. Lua
specifications use real `nvim --headless`; TUI tests use disposable Neovim and
pseudoterminals and never attach to a user's tmux or editor session. Packaging
tests extract and import the actual built add-on and embedded Linux package.

```bash
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
python3 -m unittest discover -s protocol/python/tests -v
python3 -m unittest discover -s bridge/python/tests -v
python3 -m unittest discover -s nvda-addon/tests -v
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
git diff --check
```

Regression coverage includes framing, resync, Unicode, empty buffers, modes,
editing, completion, menus, settings profiles, installation, multiple local
and SSH sessions, focus/runtime IDs, F12 claims, delayed callbacks, redaction,
and fail-open suppression.

The F12 path distinguishes four stages: physical session marking, the
transient session-file claim, unique claim resolution, and terminal-to-connection
binding. While support is enabled, NVDA treats each physical F12 as one
authorization for the exact focused control and does not synthesize or consume
the key. Neovim matches the
unchanged `typed` value and schedules the session-file write outside `vim.on_key`.
Manual target selection prepares the same physical F12 proof before using the
typed connection path.

Lifecycle regressions cover graceful exit, SIGKILL, PID/endpoint nonce reuse,
legacy schemas, passive bounded inventory, permission uncertainty,
bounded entry counts, UTF-8-safe names, uncertain process checks,
nonce-owned versus inherited socket handling, one closed WT
window beside a live window, individual tabs sharing one HWND, the periodic
idle-tab sweep, off-main-thread client shutdown, and fail-open suppression.
Socket tests prove that cleanup removes only an exact nonce-owned plugin path.
Real RPC tests prove that the permanent channel verifies the nonce before
setup and that mismatch disconnects without a reconnect loop.
Isolated local and Tessa SIGKILL tests must leave discovery empty
without touching existing user Neovim or tmux sessions.

## Copy/paste feature-branch acceptance

Prerequisites: the current feature build, updated local and remote components,
one explicitly bound local and one SSH session, and freely assigned NVDA
gestures for all four clipboard commands.

Before testing a session, open NVDA's Input Gestures dialog from an unrelated
application. “Neovim Access Link” and its freely assignable commands must be
visible. An assigned test gesture must reach the focused non-WT application
unchanged and must produce no add-on output, activation, or binding change.

1. Copy characterwise, linewise, and blockwise selections containing ASCII,
   non-ASCII text, emoji, tabs, and multiple lines; verify in a neutral Windows
   application.
2. Use `yy` and another yank to populate register 0, then copy it with the
   second command. Delete registers must not be selected accidentally.
3. Paste single- and multiline Windows text with Unicode and CRLF in Normal
   and Insert mode; verify cursor position, one undo with `u`, and `.` behavior.
4. Store Windows text with and without a trailing newline in Neovim's unnamed
   paste register. Normal `p` and `"0p` must use characterwise or linewise type
   as appropriate; named user registers must remain unchanged.
5. Change focus, tab, pane, buffer, or mode during a request. A late response
   to copy must not change the clipboard. A paste already dispatched may reach
   the previously and explicitly addressed buffer at most once, but must never
   affect the new session, repeat, or announce success there.
6. Check a shell pane, Neovim terminal buffer, file manager, read-only buffer,
   and `nomodifiable` buffer. The command must reject clearly and leave native
   terminal output unchanged.
7. Repeat locally and over SSH, then inspect the redacted diagnostic report.
   Transferred text must not be present.

Expected: identical local/remote behavior, exactly one mutation per command,
no automatic synchronization or retry, and success feedback governed by “Copy
and paste”.

Practical test on 16 July 2026: the installed `0.91.0-dev.4` feature build and
the existing bound Neovim sessions were used. NVDA's Input Gestures dialog was
opened from an unrelated application; a freely assigned gesture was invoked
outside WT and then in the bound Neovim control. The exact key was not
recorded. Expected were a visible product category, unchanged pass-through
outside WT, and a Neovim action only in the bound control. These points and
all four clipboard commands worked without problems. Result: passed.

## Required Windows Terminal isolation tests

For focus-context output, alternate focus between a bound Neovim control, an
unbound shell-only tab, and, where possible, two split panes. Test all three
choices: no announcement, current line, and existing file/special context with
mode and connection name. In the bound control, Insert or Normal focus must
offer the permitted mode sound independently of that choice; speech-only mode
feedback remains silent. Rapid switching must never announce stale context.
After disconnect, native WT output must remain immediately available. Record
the request ID, choice, sound, result, and actual output in the redacted test
report.

Practical acceptance on 2026-07-16:

- Prerequisites: installed `0.91.0-dev.1` feature build plus one bound local
  and one bound SSH Neovim session in Windows Terminal.
- Procedure: select and save each `General → Session focus` value in turn, then
  move focus from another application back to each Neovim session.
- Expected: respectively no announcement, current line, or existing context;
  all three retain the Insert/Normal sound permitted by existing settings and
  produce no stale or foreign output.
- Actual result: no problems locally or over SSH; passed.

### Terminal mode, command line, and following messages

Use a bound local or SSH Neovim session with an embedded `:terminal`. Direct
terminal input must play the Insert/focus cue and allow native output. After
both `Ctrl+\`, `Ctrl+N` and the assigned “Leave direct input in the active
Neovim terminal” gesture, “terminal-normal mode” and exactly one Normal cue
must follow and structured navigation must resume; `i` must reverse that
transition. Then run `:echo 'test message'` and
`:lua print('test message')`. Command-line mode must be announced before input,
with a short mid-pitch tone, and the Normal cue must mark return; the result
must follow Enter in speech and Braille. On a terminal buffer whose job is
still running, execute `:bd`: expect structured `E89` guidance including the
hit-enter instruction and no terminated job. Press Enter, then run `:bp` or
`:bn` with no other listed buffer and expect “no other listed buffer”. With an
actual second buffer created by `:new | terminal`, `:bp` must instead switch
to it; test both `:bp` and `:bn` with each General → Session focus choice.
Expect no announcement, the destination's current line, or its context with
mode and saved connection name, respectively. Tab/window announcements remain
unchanged, and the mode cue remains independent. Transient return modes must
not also be spoken: No announcement stays silent after the command, Current
line has no leading mode fragment, and Context has no duplicate mode. A `/bn`
search must not trigger this coalescing.
The complete destination line must remain identical for different source-buffer
cursor columns; a following automatic cursor event must not shorten it or
replace it with one destination character.
With Context selected, also switch between a modified, short-named file buffer
and a terminal buffer in separate Neovim windows and tabs. Each switch must
produce exactly one combined announcement, for example `window 1 of 2, file T,
modified, normal mode, on Example` and `window 2 of 2, terminal-normal mode, on
Example`. A bare `T`, `terminal, terminal mode`, or a second prefixed spoken
mode is a failure. No announcement and Current line must retain their already
verified behavior; the configured mode cue remains independent in all three
choices.
End a local Neovim session in a bound WT control and wait for its transport to
report `disconnected`. In that same control, focus an already inventoried SSH
Neovim session and press F12. Diagnostics must show `selected=true` together
with `selectedAuthenticated=false`, then start automatic resolution across
local and SSH targets; ending in local `localClaimWaitCompleted` without an SSH
scan is a failure. Without the physical F12 gesture, disconnect must still only
fail open and must never rebind a session automatically.

Practical acceptance on 2026-07-17: the implemented terminal, buffer,
window/tab, and fresh pairing paths from an ended local Neovim to the SSH
session in the same WT control worked without further issues; passed.

Disabling mode speech must not hide command-line mode; disabling sounds must silence all transition
cues. With NVDA character echo enabled, type `:terminal` and a command
containing Unicode; every character must be heard once, not just the first.
Run `exit` in the shell and expect one structured terminal-exit message with
status. Running shell output remains native. Disconnect and an unbound shell
tab must always retain native output.

Also run `:terminal` from a normal file buffer with all three focus choices.
Expect no entry output, the first complete terminal line, or Terminal-Normal
context with connection name. This must also hold when terminal context and
the final mode event arrive in the opposite order. The automatic cursor event
must never speak only the line's first character. Then press `i`: the complete
cursor line and one
permitted Insert cue must follow without competing spoken mode output.

The isolated Neovim 0.12 TUI test also exercises command-line input, an
ordinary UI message, and search through the attached UI-protocol path. The
structured channel must continue delivering events afterwards; `E5560` and a
blocking hit-enter prompt are failures.

Automated tests establish the intended gating behavior, but complete practical
non-interference across Windows Terminal layouts remains an open acceptance
area. Practical tests must cover all of these negative cases:

- unbound PowerShell, Command Prompt, and WSL panes retain native focus, text,
  input, speech, LiveText, and Braille behavior while add-on support is active;
- F12 in an unbound shell may perform one bounded claim check as an explicit
  user action, but without a fresh claim it does not announce, bind, suppress,
  or open a dialog;
- events from another connected Neovim never offer or perform a rebind in an
  unrelated shell pane;
- a remembered identity cannot suppress native output before fresh structured
  state, including when a shell replaces Neovim in the pane while its RPC
  channel remains alive;
- separate Windows Terminal processes, windows, tabs, and split panes neither
  cross-bind nor register duplicate gesture observers; and
- the add-on overlay does not change unbound Braille or LiveText fallback.

Tests must record the focused UIA class and runtime identity so pane-level and
tab-level behavior are not conflated. Any uncertain result is a fail-open
defect and remains documented until practically reproduced and corrected.

Practical regression test on 16 July 2026 with NVDA 2026.1.1 and
`0.90.0-dev.3`: local `nvim test.txt` was started in the first WT tab, support
was enabled, F12 was pressed, and the control binding was remembered. A second
tab opened `ssh user@example.invalid` and remote `nvim test.txt`; F12 connected
it without another activation command. Deactivation was then invoked from the
second tab. Expected and actual results matched: independent second-tab pairing
worked and the global off command worked from that tab. Result: passed. Split
panes were then tested in both horizontal and vertical orientations while
local and SSH connections remained active in other tabs. Both orientations
worked without errors or crossed connections. Result: passed. Separate WT
windows, tmux, and the complete unbound-shell-pane negative matrix remain
practically unverified.

Manual tests must record prerequisites, exact actions, expected and actual
results, and avoid confidential text. Confirmed tests used Windows 11 25H2,
NVDA 2026.1.1, Windows Terminal 1.24.x, OpenSSH 9.5p2/LibreSSL 3.8.2, Rocky
Linux 10.2, Python 3.12.13, and Neovim 0.10.1.

Automated coverage is not a stable-release claim. Many add-on features still
need deeper practical tests. No physical Braille display has been tested;
Braille hardware testing, routing, selection dots, translation tables, and
bug fixing are priority TODO work.

The documentation build must produce six independent HTML files: German and
English Quick Guide, manual, and developer documentation. Every published
source is assigned explicitly; private ignored material is excluded.
