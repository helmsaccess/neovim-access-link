# Manual: Add-on settings

Open the category through `NVDA menu → Preferences → Settings... → Neovim
Access Link`. The add-on deliberately adds no duplicate settings item directly
to the Preferences submenu.

The category has “General”, “Feedback”, “Navigation”, “Braille”, and
“Connections” tabs.
OK saves and closes, Apply saves without closing, and Cancel discards unsaved changes.
Values use NVDA's normal configuration profiles. Manage those through
`NVDA menu → Configuration profiles...`; the add-on neither selects nor
activates a profile itself.

## Session focus and buffer changes

“When focusing or changing buffers in a Neovim session” controls the
additional output after a bound Neovim control regains focus and its structured
context is confirmed. The same choice applies to a real buffer switch in the
current window, for example after `:bp` or `:bn`:

- No announcement;
- Current line, using “blank” for an empty line;
- Current context, modified/read-only state, mode, and connection name. This
  remains the default.

The choice affects only the focus/buffer-switch announcement and normally its
transient Braille message. When Braille exploration is active in the
destination session, the focus announcement remains audible but does not
cover the restored exploration viewport with a transient Braille message.
Tab and window destination position remains present; Context
combines it with destination, state, mode, and connection in exactly one
announcement. A short file name is explicit as `file T`. A terminal reports
only `terminal mode` or `terminal-normal mode` for its state, never the
duplicated `terminal, terminal mode`.
Structured Braille and secure focus confirmation remain active.
Insert-, direct-terminal-input, and Normal-mode sounds also play for confirmed focus when Global action
feedback and Insert and normal mode changes permit sounds. Actual mode changes
during a buffer, window, or tab switch continue to use those cues independently
of this choice.
For `:bp`/`:bn`, transient spoken return modes are folded into the selected
destination presentation: No announcement stays silent, Current line is not
prefixed by a mode fragment, and Context already includes the destination
mode. Command-line entry remains announced.

For an Ex command that immediately produces only a message and returns to the
same editor state, the same choice controls what follows the message: nothing,
the current line, or context with return mode and connection. The message
itself is never suppressed. The return cue remains independent of this choice
and continues to follow the feedback settings.

The choice also applies when `:terminal` creates a terminal buffer. Current
line waits for the first actual terminal line instead of first reporting blank
and then only its first character. Entering direct terminal input with `i`
subsequently presents the complete line at the terminal cursor independently
of that entry choice; the Insert/focus cue still follows feedback settings.

## Automatic active-parameter speech

The profile-aware “Automatically speak the active function parameter while
typing” checkbox is enabled by default. In Insert mode it reports the
language-server-selected parameter when the cursor enters a function argument
list or changes arguments. Returning to an already filled argument speaks it
again; motion within the same argument stays silent. This is speech-only and
does not change the Braille display.

The checkbox is independent of action cues on the Feedback tab because it is
orientation from LSP signature data, not confirmation of an editor action.
When disabled, or when the server supplies no unambiguous active parameter,
there is no automatic announcement. The explicit held `NVDA+Shift+P` query
remains available.

## Feedback

Global action feedback and individual actions use Off, Speech, Tones, or
Both Speech and Tones. Individual settings cover mode changes, deletion, replace,
line/file boundaries, crossing a line, and unmatched pairs.
The two sound-only diagnostic line and diagnostic position settings
deliberately offer only Off and Tones. Complete diagnostic text remains
available through explicit inspection and diagnostic navigation. The cue for
an explicit query with no match follows the Diagnostic line or Diagnostic
position setting used by that query; passive movement over clean lines stays
silent.

The mode setting also governs the focus cue for direct embedded-terminal input,
the Normal cue for canonical Terminal-Normal, and the short command-line tone.
Command-line mode remains spoken for safe orientation even when ordinary
Insert/Normal speech is disabled.

Existing NVDA settings remain authoritative:

| Function | NVDA location |
| --- | --- |
| Typed characters and words | Preferences → Settings... → Keyboard |
| Indentation and spelling | Preferences → Settings... → Document Formatting |
| Automatic suggestions | Preferences → Settings... → Object Presentation |

“Copy and paste” controls success feedback for four freely assignable NVDA
commands: copy the active Visual selection, copy Neovim register 0 (the last
yank), paste Windows clipboard text, and store Windows text in Neovim's current
unnamed register. Failures remain audible. There is no default gesture,
automatic synchronization, or automatic retry.

Copy reads only the current Visual selection or register 0. Paste uses
Neovim's structured paste API and is limited to normal modifiable editor
buffers in Normal or Insert mode. Terminal buffers, file managers, read-only
buffers, and non-modifiable buffers are rejected. The register command changes
no buffer. It replaces register 0 and points the unnamed register to it, so
normal `p` and `"0p` subsequently use the transferred text. Local and SSH
sessions use the same behavior.

The separate freely assignable “Leave direct input in the active Neovim
terminal” command can replace the layout-dependent Neovim sequence
`Ctrl+\`, `Ctrl+N`. It has no default gesture and is sent only while the exact
bound terminal buffer is in direct input.

## Navigation

The “Navigation” tab controls supplementary cursor context independently for
ordinary Neovim navigation and for the announcement when the NVDA key ends
speech exploration mode. It does not disable the basic word or line:

- “Word navigation” and “After word speech exploration” offer “Word only” or
  “Word and cursor character”.
- “Line navigation” and “After line speech exploration” offer “Line only”,
  “Line and current word”, “Line and cursor character”, or “Line, current word
  and cursor character”.

“Word only” and “Line only” therefore turn off all supplementary context, not
the base announcement.

The default is word plus cursor character and line plus cursor character,
which preserves the behavior from before these choices were added. When both
line details are enabled, speech follows the stable order line, current word,
cursor character. Character navigation and speech exploration mode are
unchanged. These values follow the active NVDA configuration profile and take
effect after Apply or OK.

## Braille

All settings on this tab are profile-aware. They supplement rather than
replace NVDA's own Braille settings. Translation table, display driver,
cursor shape, selection indication, and “Speak character when routing cursor
in text” remain controlled by NVDA's `Braille` category.

### Speech exploration mode

“Braille display follows the speech exploration mode position” is profile-aware
and enabled by default. During speech exploration with `NVDA+h`, `NVDA+j`,
`NVDA+k`, `NVDA+l`, and `Shift+NVDA+h/l`, the Braille display then presents
the reached virtual position without moving the real Neovim cursor. It returns
to the cursor position when speech exploration mode ends.

When this option is disabled, speech exploration leaves the Braille display
at the real cursor. It does not change the independent Braille exploration
mode.

Example: the real cursor is in `example`. `NVDA+l` temporarily explores the next
character, while `Shift+NVDA+l` explores the next word. With the option
enabled, the Braille display presents that virtual position and returns to
`example` when the NVDA key is released.

Speech exploration mode is a speech feature, not a Braille mode. This option
merely lets the Braille display support it as a second output. See
[Speech exploration mode](speech-exploration.md) for its complete operation
and its difference from Braille exploration mode. See
[Navigating with the display's navigation controls](braille.md#navigating-with-the-displays-navigation-controls)
for the two Braille navigation modes and typical use cases.

### Routing keys

“Double routing press on a word” controls two quick presses of the same routing
key at the same text position:

| Choice | Effect |
| --- | --- |
| Route only | The second press performs no edit. This is the default. |
| Change word (`cw`) | Neovim runs `cw` and remains in Insert mode for replacement text. |
| Delete word (`dw`) | Neovim runs `dw`, which normally also removes the following space. |

“Triple routing press on a line” can remain at the default Route only, change
to the line end (`c$`), or delete to the line end (`d$`).

“Start triple-press line action at” applies only when a triple action is
enabled:

| Choice | Effect |
| --- | --- |
| Routed position | Start exactly at the pressed routing key. This is the default. |
| First non-blank character | Preserve line indentation. |
| Beginning of line | Include indentation in the action. |

The first press always routes immediately. If both double- and triple-press
actions are configured, the word action waits briefly for a possible third
press. The interval comes from NVDA's `Keyboard → Multiple key press timeout`
setting.

Editing actions are available only in Normal and Insert modes. Command-line
mode, direct terminal input, and read-only speech exploration retain ordinary
routing.

### Spelling suggestions

“Start spelling suggestions at Braille cell” positions only the transient
suggestion shown while inspecting Neovim's built-in `z=` list. It is a
one-based cell number: 1, the default, starts at the first cell; 40 starts at
cell 40. This can keep the suggestion clear of the hand holding the NVDA key.
When the left hand holds Caps Lock as the NVDA key, the hand and arm can
obscure the left part of the display. Starting the suggestion farther right
makes it considerably more comfortable to read with the right hand.

If the connected display has fewer cells than the configured number, the
offset is ignored and the suggestion starts at cell 1. Speech, the persistent
editor line, and every other Braille presentation are unchanged. If the
fully translated suggestion would not fit from the requested cell, the add-on
moves it left only as far as needed to fit it right-aligned. A suggestion
longer than the display starts at cell 1. The value uses NVDA's normal
configuration profiles.

### Developer information

“Start temporary developer information at Braille cell” positions the held
function-parameter and diagnostic views. It follows the same short-display
and right-alignment rules as spelling suggestions but has an independent,
profile-aware value. The default is cell 1. Longer developer information
starts at the first cell and can be paged forward and back within the held
view.

## Connections

Local Windows Neovim needs no saved profile. “Saved SSH connections” stores a
display name, host or OpenSSH alias, Linux user, port, optional key file, and
authentication method. Empty Linux user means OpenSSH must obtain it from its
configuration; the Windows user name is never substituted.

“Use OpenSSH setup” uses normal Windows OpenSSH configuration, keys, and
`ssh-agent`. “Ask for the SSH password” uses an accessible prompt and keeps the
password only in memory until deactivation or NVDA exit. Secrets are not saved
or placed on the command line.

Changes take effect for future discovery and connections. Existing bound
sessions are not terminated merely because a profile or NVDA configuration
profile changes.

## Component update and gestures

`NVDA menu → Tools → Neovim Access Link: Install or update components...`
opens an initially unselected checklist containing “This computer” and saved
Linux targets. “Select all connections” follows the individual checkboxes. The
operation runs in the background and ends with spoken counts and a compact
success/failure summary.

## Completely removing components

Close Neovim on every intended target, then open
`NVDA menu → Tools → Neovim Access Link: Remove components...`. The add-on
does not stop or alter running Neovim or tmux sessions. The initially clear,
accessible checklist and its initially focused “Select all connections” box
work like the installation dialog. Password prompts, background processing,
spoken progress, and the final results summary also follow the same workflow.

For “This computer”, removal is limited to:

```text
%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda
```

For each selected Linux account, removal is limited to:

```text
~/.local/bin/nvim-nvda-bridge
~/.local/share/nvim/site/pack/nvim-nvda
~/.local/share/nvim-nvda
~/.cache/nvim-nvda-install
```

Already absent components count as successfully removed. Saved connection
profiles, Neovim configuration, SSH keys and configuration, unrelated plugins,
and session data remain intact. The same connection can therefore be selected
for installation again later.

Focus Windows Terminal before opening `NVDA menu → Preferences → Input
gestures... → Neovim Access Link` to assign activation, manual connection,
disconnect, forget-binding, and diagnostic-report commands. NVDA lists and
resolves the freely assignable commands through the Windows Terminal
AppModule, not globally. F12 is the default session-claim key shared with the
installed plugin and should not be reassigned as activation.

After upgrading from a feature build that exposed these commands through the
Global Plugin, assign the desired gestures once again. Once the AppModule has
loaded, NVDA may show a saved AppModule mapping in Input Gestures from another
application for the rest of that NVDA run. Runtime resolution nevertheless
remains AppModule-scoped, so the assignment cannot displace another NVDA
command in an unrelated application. Invocation still rechecks the exact
focused UI Automation control before running a Neovim action.

The four copy/paste commands are assigned in that dialog as well. They do not
replace Windows Terminal selection or `Ctrl+Shift+C`/`Ctrl+Shift+V`. Each use
is one action correlated with the current terminal-control binding and current
Neovim state; a late response after a focus, tab, pane, buffer, or mode change
is discarded.

Temporary control bindings use a Windows Terminal UI Automation runtime ID that
is stable for the lifetime of that control. They remain only in memory and
never inspect terminal text or titles. Depending on the layout, one control
represents the content of a tab or an individual pane.

While the service is enabled, every physical F12 press authorizes one pairing
attempt for exactly the focused terminal control. Without a fresh Neovim claim,
that attempt stays silent and creates no binding, dialog, or suppression.
Separate windows, tabs, and panes can remain bound in parallel and can be
switched without repeating F12.
