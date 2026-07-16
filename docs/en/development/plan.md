# Active plan

Core architecture, protocol v2, SSH stdio, local Windows CLI, F12 claim handshake,
parallel sessions, and rootless installation and removal are implemented.

## Active: explicit copy/paste

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
