# Current status

Status: 2026-07-15, beta test build 0.89.5.

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
