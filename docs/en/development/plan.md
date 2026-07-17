# Active plan

Core architecture, protocol v2, SSH stdio, local Windows CLI, F12 claim handshake,
parallel sessions, and rootless installation and removal are implemented.

## Active: terminal and file-manager hardening

Branch `feature/terminal-file-manager-hardening` is hardening transitions among
structured editor state, direct embedded-terminal input, Terminal-Normal,
Neovim's command line, and semantic file-manager adapters. The first step adds
terminal mode cues with fail-open gate ordering and preserves ordinary command
results whose `msg_show` kind is empty or not yet known. Regression tests cover
command-line mode, message ordering, and terminal transitions. The second
step models `terminalNormal` separately, fixes UTF-8 command-line
echo, adds a correlated freely assignable fixed `stopinsert` command, and
reports `TermClose` with exit status. The third step adds a command-line tone,
unambiguous return feedback, and structured guidance for `:bd` on a running
job and no-op buffer navigation. The fourth step moves UI-protocol handling
out of Neovim's fast-event context, preventing Neovim 0.12 `E5560` hit-enter
states without polling. The fifth step applies the existing profile-aware
focus choice to event-driven buffer switches within the same tab and window,
so `:bp`/`:bn` can be silent, announce the destination line, or report context,
mode, and connection name without changing tab/window feedback or mode cues.
The sixth step separates automatic destination cursor/change events from the
source state so a single target character cannot overwrite the line and text
is never diffed across buffers.
The seventh step coalesces transient spoken return modes for recognized Ex
buffer commands into the configured destination presentation. The mode cue
stays independent, while structured command-line type distinguishes Ex from
identically named search patterns.
The eighth step treats `:terminal` as a structured buffer entry, waits without
polling for the first real terminal line when line output is selected, and
suppresses its automatic trailing character event. Entering direct terminal
input with `i` presents the complete cursor line instead; the cue and fail-open
passthrough stay separate.
The ninth step makes that coalescing independent of terminal-context versus
final-mode event order and prevents command-line text from leaking into the
new terminal buffer as a Normal-mode motion.
The tenth step coalesces Neovim window/tab destination, explicit file or
special context, state, mode, and connection for the Context choice. Spoken
mode is not prefixed, while its independent cue and the other two focus
choices remain unchanged.
The eleventh step distinguishes a merely remembered binding from a still-
authenticated one during F12 pairing. After a local session exits, the same WT
control can therefore be explicitly rebound to a fresh SSH session without
introducing automatic mapping or polling.
The twelfth step starts file-manager hardening with shared UTF-8-validating
byte limits. Long names and paths are cut only at code-point boundaries, while
invalid adapter values never reach transport. Boundary tests cover two-,
three-, and four-byte characters plus invalid sequences without adding queries
or polling.
Practical Windows/NVDA acceptance confirmed command-line echo, Terminal-Normal,
the exit command, process exit, all three `:bp`/`:bn` presentations,
window/tab switching, and fresh SSH pairing without further issues.
Event-driven same-entry file-manager changes, distinct mark and clipboard
semantics, action results, pager variants, and the complete negative Windows
Terminal matrix remain next.

## Completed: explicit copy/paste

Branch `feature/copy-paste` adds four commands without default gestures to
NVDA's Input Gestures dialog: copy the Visual selection, copy register 0, and
paste Windows clipboard text or store it in Neovim's unnamed register for
normal `p`. NVDA's public clipboard API is the only Windows
access; local and SSH transports carry only fixed typed Neovim controls.

Implemented work includes correlated request/result events, a 256-KiB limit,
UTF-8 and NUL validation, immediate Neovim state validation, `nvim_paste`
without retry, rejection of special/terminal/file-manager/read-only/non-
modifiable buffers, and removal of one-shot copy text from every canonical
state cache and diagnostic. Profile-aware success feedback uses the existing
Off/Speech/Sounds/Both model; failures remain audible. Pending requests are
bounded.

After practical testing showed that the product category disappeared when
Input Gestures was opened outside Windows Terminal, freely assignable commands
are exposed as global unbound script metadata. Execution remains isolated by
revalidating the exact WT `TermControl`; elsewhere the original gesture is
passed through unchanged. Automated regression coverage is implemented;
the practical `dev.4` test confirmed visibility, pass-through outside WT, and
execution in the bound Neovim control without problems.

All four commands, including Windows text to the unnamed paste register, were
practically confirmed without problems in the supplied `dev.4` build. Feature
acceptance is complete; merging remains a separate user decision.

The beta close-out work is documentation consistency, full automated package
and documentation verification, practical local/remote multi-session and
fail-open acceptance, and alignment of known limits with evidence.

Configurable focus-context output is practically confirmed locally and over
SSH. The broader negative matrix across multiple unbound WT tabs/panes and
rapid focus switching remains part of beta close-out.

Next priorities are physical Braille display testing and fixes, long-running
and repeated-disconnect tests, broader practical coverage of all add-on
features, reviewed localization, and only then additional front ends or custom
Neovim interfaces through isolated adapters.
