# Current status

Status: 2026-07-15, beta test build 0.89.16.

Protocol v2, remote SSH stdio, local Windows loopback RPC, rootless component
installation and explicit per-target removal, F12 claims, multiple runtime instances, and explicit Windows
Terminal bindings are implemented. Local and SSH sessions can run in parallel
across tabs, windows, accounts, and tmux. The global service contains no global
input or focus hooks; Windows-specific behavior is confined to the Windows
Terminal AppModule and failures restore native terminal output.

Component removal runs outside NVDA's main thread for explicitly checked local
or SSH targets. It preserves saved connection profiles, user configuration,
SSH files, unrelated plugins, and running-session data, and reports every
result in a non-blocking summary.
Complete component removal was also confirmed with the installed test build.
An unchanged interactive mapping test with confirmed updated components showed
that F12 did not reach Neovim while NVDA support was active. Returning `True`
from `decide_handleRawKey` permits further NVDA processing but does not
guarantee OS delivery. Build 0.89.11 removes that observer, binds F12 locally
in the Windows Terminal AppModule, and explicitly forwards the original
gesture with `gesture.send()` before claim evaluation.
The interactive 0.89.11 test then confirmed `onKey`, the original mapping
callback, and a successful claim. Build 0.89.12 carries the monotonic timestamp
captured immediately before `gesture.send()` into automatic local evaluation,
so the exact fresh key press is recognized in addition to the activation
baseline.
Build 0.89.12 then confirmed local pairing and one Tessa SSH connection, but
the next F12 left both registries belonging to the actual running Tessa
Neovim processes at `claimSequence=0`. Build 0.89.13 therefore forwards F12
after a ten-millisecond GUI-loop delay, once NVDA's input-hook callback has
returned; evaluation still starts after 250 milliseconds.
Practical testing disproved that synthetic path as well. Manual selection
connected the same Tessa session, and a physical F12 control followed by
further presses advanced its registry to `claimSequence=3`. Build 0.89.14
therefore observes F12 through `decide_executeGesture` without binding an NVDA
script. NVDA's resulting `NoInputGestureAction` path passes the original key
directly, while only claim evaluation is queued to NVDA's event queue.
The 0.89.14 report then confirmed only automatic local pairing; its Tessa
connection was manual. An isolated Neovim 0.10.1 run consistently received
F12 as `typed=<F12>` but represented the internal key as a terminal code and
never resolved the `<F12>` mapping. Build 0.89.15 therefore evaluates `typed`
in the existing `vim.on_key` observer. The NVDA observer now ignores F12
completely while support is disabled.
Practical testing of 0.89.15 confirmed Tessa and the inactive observer while
support was disabled. Local Neovim 0.12.3 connected automatically but
immediately entered the `r?`/hit-enter state and then lost its RPC server.
Build 0.89.16 schedules the registry write with `vim.schedule()` outside
`vim.on_key`.
Final practical testing of 0.89.16 confirmed automatic binding for both local
Neovim 0.12.3 and Tessa with Neovim 0.10.1. Repeated physical F12 marks worked,
and with support disabled the observer remained completely inert and opened no
binding dialog. Marking, the transient registry claim, add-on binding, and the
transport connection are therefore distinct and practically confirmed stages.

The main connection paths were tested with the reference environment, but the
overall maturity remains alpha to beta. Not every speech, menu, editor-mode,
file-manager, profile, reconnect, and error path has extensive practical
coverage. Braille has not been tested with physical hardware and very likely
contains bugs. Physical-display testing and correction are a priority.

Known limits include Windows Terminal as the only approved front end, no GUI
Neovim, no portable or automatic `NVIM_APPNAME` layout, an uninvestigated older
Rocky Linux 9/Neovim failure, limited long-duration and interruption testing,
and no broad Braille hardware matrix.

The reproducible build produces separate German and English Quick Guide,
manual, and developer HTML files.
