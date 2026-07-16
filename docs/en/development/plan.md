# Active plan

Core architecture, protocol v2, SSH stdio, local Windows CLI, F12 claim handshake,
parallel sessions, and rootless installation and removal are implemented.

## Active: stronger Windows Terminal isolation

- Treat each physical F12 press as one authorization for exactly the focused
  UIA terminal-control identity; keep no separate time-limited pre-arm.
- Keep no-claim attempts silent and remove activity-based rebinding. The
  activation command remains the global on/off toggle in every control.
- Preserve parallel windows, tabs, and panes; every focus switch fails open
  until the exact authenticated instance returns a correlated focus context.
- Automated negative multi-control and multi-window tests are in place.
  Practical NVDA/Windows Terminal tests passed for local and remote tabs and
  horizontal and vertical split panes. Separate windows, tmux, and the complete
  shell-only-pane negative matrix remain required.

The beta close-out work is documentation consistency, full automated package
and documentation verification, practical local/remote multi-session and
fail-open acceptance, and alignment of known limits with evidence.

Before beta close-out, the new focus-context announcement must be tested with
local and remote connections, multiple bound and unbound WT tabs and panes,
and rapid focus switching. Late replies and shell-only controls must cause no
output or suppression.

Next priorities are physical Braille display testing and fixes, long-running
and repeated-disconnect tests, broader practical coverage of all add-on
features, reviewed localization, and only then additional front ends or custom
Neovim interfaces through isolated adapters.
