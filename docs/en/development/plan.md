# Active plan

Core architecture, protocol v2, SSH stdio, local Windows CLI, F12 claim handshake,
parallel sessions, and rootless installation and removal are implemented.

## Active: configurable session-focus output

Branch `feature/focus-context-settings` adds one profile-aware choice to the
General settings tab:

1. no focus announcement;
2. current line;
3. current file or special context, mode, and connection name as before.

The existing context output remains the default. This setting controls only
the focus announcement and its transient Braille message. Structured Braille,
focus correlation, authentication, exact control binding, and fail-open
suppression remain independent. A correlated `focusContext` must therefore
still be requested and validated even when announcements are disabled.

Every accepted focus context additionally offers the Insert- or Normal-mode
sound for all three choices. Existing global and mode-specific sound settings
still gate that sound; the new choice does not change normal mode-change speech
or sound settings.

Implementation plan:

1. Add a validated native NVDA setting with the compatibility-preserving
   default and integrate it with the dialog, persistence, normalization, and
   profile switching. A schema upgrade must never re-import an obsolete legacy
   JSON backup over an already migrated native configuration.
2. Model the three presentation variants in the NVDA-independent speech
   planner. Current-line output uses structured `lineText`, identifies an empty
   line, and reuses indentation handling; the existing file/special-context
   output remains available unchanged.
3. Separate focus-time Insert/Normal sound playback from speech selection.
   Each accepted response produces at most one mode sound; stale, unbound, or
   unauthenticated responses remain completely inert.
4. Add regression coverage for the compatible default, every choice, empty and
   Unicode lines, local and remote labels, NVDA profiles, invalid values,
   legacy migration, Braille, and independent speech/sound gating.
5. Update settings, architecture, accessibility, testing, current status, and
   changelog documentation, then run practical local/SSH NVDA and Windows
   Terminal tests across bound and unbound tabs/panes and rapid focus changes.

All steps are implemented. Practical NVDA and Windows Terminal testing
confirmed all three choices and their independent mode sounds locally and over
SSH without problems.

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
