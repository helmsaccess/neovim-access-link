# Braille support

After connecting, Neovim Access Link presents the current Neovim line on the
Braille display. Braille translation, the display driver, and cursor
presentation remain controlled by NVDA.

The features have been practically tested with a Papenmeier BRAILLEX EL 80c
with 80 Braille cells. They use NVDA's standard display-driver and navigation
commands. Other NVDA-supported displays are not practically confirmed with
Access Link.

The display contains only information relevant to working in Neovim. Windows
Terminal labels such as “Windows PowerShell”, status lines, and content from
other terminal areas are not placed before the editor text.

## What appears on the Braille display

In the editor, the Braille display presents:

- the text of the current line,
- the cursor position,
- a Visual selection on the current line,
- tabs expanded into blank cells according to Neovim's `tabstop` value,
- indentation,
- transient messages such as a spelling suggestion.

In supported file managers, the current entry's name, type, and state replace
the decorated plugin line. See
[Embedded terminals and file managers](terminals-and-file-managers.md) for
details.

For the normal editor display, set NVDA's Braille mode to “follow cursors”.
With “display speech output”, the display presents spoken output as NVDA
defines it instead of remaining on the editor line.

When the Neovim cursor moves outside the currently visible window, NVDA pans
the Braille display automatically. This also applies while typing a long line
in Insert mode and while moving the cursor on Neovim's command line. A window
selected with Left or Right remains in place while the cursor is still
visible within it.

## Braille settings supplied by the add-on

Neovim Access Link has its own `Braille` tab in the Settings dialog. It
contains only behavior added by this add-on:

| Setting | Default | Purpose |
| --- | --- | --- |
| Braille display follows the speech exploration mode position | On | Temporarily presents the virtual speech position in Braille as well. |
| Double routing press on a word | Route only | Can optionally run `cw` or `dw`. |
| Triple routing press on a line | Route only | Can optionally run `c$` or `d$`. |
| Start triple-press line action at | Routed position | Starts at the routing key, indentation, or absolute line beginning. |
| Start spelling suggestions at Braille cell | 1 | Moves only the transient spelling suggestion. |
| Start temporary developer information at Braille cell | 1 | Positions held function parameters and diagnostics. |

Translation table, driver, cursor shape, selection indication, and speaking
the character reached by routing remain normal NVDA settings. See
[Add-on settings](settings.md#braille) for every choice and its effect.

## Moving the cursor with routing keys

A routing key above a character moves the Neovim cursor to that character.
This works in Normal, Insert, and command-line modes.

When NVDA's “Speak character when routing cursor in text” option is enabled
under `Preferences → Settings → Braille`, NVDA announces the reached
character.

The position after the final character depends on the Neovim mode:

- **Insert mode:** An additional blank Braille cell follows the last
  character. Its routing key places the insertion point at the end of the
  line.
- **Command-line mode:** An additional blank cell also follows the entered
  command, allowing the cursor to move after its final character.
- **Normal mode:** The cursor rests on an existing character, so there is no
  additional routing position after the final character.
- **Empty line:** A completely empty line contains one cursor cell.

The additional cell in Insert and command-line modes does not insert a space.
It represents only the position after the end of the text.

Routing over tabs, accented characters, wide characters, and emoji is mapped
to the corresponding text position. If displayed information does not
represent a text position, its routing key has no effect.

## Why the cursor moves left when leaving Insert mode

When switching from Insert to Normal mode, the cursor often appears to move
one character to the left. This is normal Neovim behavior, not a Neovim
Access Link defect.

In Insert mode, the cursor represents an insertion point between characters.
That position may be immediately after the final character:

```text
Insert mode: hello|
```

In Normal mode, the cursor instead identifies the character on which the next
command operates:

```text
Normal mode:  hell[o]
```

Pressing `Escape` does not change the text. Neovim places the Normal-mode
cursor on the character to the left of the former insertion point. Commands
such as `x` and `r` can then act on the character under the cursor, while `i`
inserts before it and `a` inserts after it.

The same rule applies in the middle of a line:

```text
Insert mode: hel|lo
Normal mode:  he[l]lo
```

Neovim Access Link presents Neovim's actual position in both modes. `gi`
resumes Insert mode at the insertion position that was last left.

See Neovim's official help for
[Insert mode](https://neovim.io/doc/user/insert/) and
[cursor motions](https://neovim.io/doc/user/motion/) for more information.

## Editing words and line ranges with routing keys

A routing key can optionally trigger a Neovim change or delete command when
the same key is pressed quickly two or three times. These editing actions are
disabled by default. A single press therefore always moves only the cursor.

Configure the actions under `NVDA menu → Preferences → Settings → Neovim
Access Link → Braille`:

- **Double press on a word:** Route only, change word (`cw`), or delete word
  (`dw`).
- **Triple press on a line:** Route only, change to end of line (`c$`), or
  delete to end of line (`d$`).
- **Start of the line action:** The routed position, the first non-blank
  character, or the absolute beginning of the line.

“Change word” removes the word and remains in Insert mode so replacement text
can be entered immediately. “Delete word” uses Neovim's normal `dw` behavior,
which usually also removes the following space. Line actions include the
character at their starting position and continue to the end of the line.
Starting at the first non-blank character preserves indentation; starting at
the beginning includes indentation in the action.

The first press moves the cursor immediately. If a triple-press action is
enabled, a configured double-press word action waits briefly so a third press
can still be recognized. The delay is NVDA's `Preferences → Settings →
Keyboard → Multiple key press timeout`.

Every press must use the same routing key at the same text position. A
different position, text change, mode change, or expired timeout begins a new
single cursor movement. Editing actions are available only in Normal and
Insert modes. On Neovim's command line and in the direct-input mode of an
embedded terminal, routing retains its normal cursor-positioning behavior.

## Navigating with the display's navigation controls

Neovim Access Link uses the standard navigation commands of the Braille
display driver selected in NVDA. Their names and physical location vary by
display. On a Papenmeier BRAILLEX, for example, press the navigation bar left,
right, up, or down.

Left and right pan the visible window within a long line. An 80-cell display
can therefore show successive parts of the line without moving the Neovim
cursor. Two separate navigation modes control what up and down do.

In accordance with NVDA's standard Braille behavior, attempting to pan again
before the start or after the end of a line also moves to the previous or next
line. Panning left beyond the line start displays the end of the previous
line. Panning right beyond the line end displays the start of the next line.
Returning to a long line this way therefore starts at its beginning instead
of restoring a previously panned viewport. Up and down, by contrast, retain
the previous column where possible.

### Braille cursor mode: move the cursor while reading

Braille cursor mode is active after connecting:

- Up and down move the Neovim cursor to the previous or next line.
- Neovim Access Link tries to retain the same visual column.
- On a shorter intermediate line the cursor uses the reachable line end; on
  a later longer line it returns to the original column.
- At the start or end of the buffer, the cursor remains on the existing line.

This mode is useful for editing: after pressing Up or Down, the real Neovim
cursor is already on the line being read. You can immediately insert text or
use a Normal-mode command there.

### Braille exploration mode: read lines while leaving the cursor in place

Braille exploration mode lets you read other lines without moving the Neovim
cursor:

- Up and down display the previous or next buffer line.
- The same visual column is retained where possible.
- A routing key moves the real Neovim cursor to the selected position on the
  currently displayed line. Braille exploration mode remains enabled.
- Real-cursor movements and mode changes do not alter the virtual Braille
  position. Text input and edits on another line also leave the explored line
  and reading column in place.
- When the real cursor is on the currently explored line, changes to that
  line are instead refreshed immediately on the Braille display. This
  includes routing followed by `r`, insertion, or deletion. Only the current
  viewport changes visibly when the edit affects it. The real cursor and
  changes outside that viewport do not pull the Braille output toward them.
  The virtual line position and selected viewport remain in place.
- Routing never uses an older buffer state that is no longer proven current.
  If the buffer changes while the real cursor is on another line, the explored
  display stays in place for uninterrupted reading, but its routing keys are
  temporarily not executed. Use the display navigation controls to show
  another line and then return to the wanted line. It then comes from the
  current buffer state and can be routed again.
- Only the display's navigation controls move the virtual reading position.
- The virtual reading position is not rendered as a Braille cursor. The real
  Neovim cursor appears only when it is actually on the explored line and
  that line's displayed text still matches. There is therefore never a
  second, apparent cursor.
- A buffer, Neovim window, or Neovim tab change within the same session
  discards the previous virtual position. Switching to another Windows
  Terminal session or another application instead retains the virtual line,
  reading column, and horizontal viewport in the associated Neovim session.
  Returning restores that exact view; the other session owns a separate one.
  The configured focus announcement remains audible but creates no transient
  Braille message that covers that viewport until the message timeout.
  Only disconnect resets the affected session to Braille cursor mode.

No key combination is assigned to the toggle by default. Under
`NVDA menu → Preferences → Input gestures`, in the `Neovim Access Link`
category, assign a gesture to “Toggle Braille navigation between Braille cursor
mode and Braille exploration mode”. NVDA announces “Braille exploration mode”
or “Braille cursor mode” when switching.

For example, use this mode to read several lines above and below the current
insertion point without having to find that point again before continuing to
type. To make an explored location the editing location, press its routing key
once.

Both Braille navigation modes are available in structured editor modes. They
are unavailable while Neovim's command line is active or while an embedded
terminal is in direct-input mode. Disconnecting resets only the affected
session to Braille cursor mode. Switching to another Windows Terminal tab or
pane never carries the previously focused session's mode or viewport with it.

### Speech exploration mode: a speech feature with optional Braille presentation

[Speech exploration mode](speech-exploration.md) is not a Braille mode. While
the NVDA key is held, it reads characters, words, or lines without moving the
real Neovim cursor. It works fully without a Braille display.

A Braille display can optionally support this speech feature. By default it
also presents the virtual speech position temporarily, then returns to the
real cursor when the NVDA key is released. Disable “Braille display follows
the speech exploration mode position” under `NVDA menu → Preferences →
Settings → Neovim Access Link → Braille → Speech exploration mode` if this is
not wanted.

Braille exploration mode is independent. It is operated with the display's
navigation controls, remains active after being selected, and owns a separate
virtual line position. In either mode, one routing key can adopt the displayed
text position as the real cursor. Double- and triple-press routing editing
actions are disabled during the read-only speech exploration mode.

### Which navigation should I use?

| Goal | Suitable function |
| --- | --- |
| Move the real cursor while reading with Up and Down | Braille cursor mode |
| Read several lines on the Braille display without moving the cursor | Braille exploration mode |
| Briefly inspect a character, word, or line with speech and return automatically | Speech exploration mode while holding NVDA |
| Continue working at an explored location | Press its routing key once |

Braille exploration mode and speech exploration mode have separate virtual
positions. Toggling Braille navigation does not change speech exploration mode.
While Braille exploration mode is active, its line position takes priority
over the optional Braille presentation of speech exploration mode.

## Visual selections

For a Visual selection, NVDA marks the selected part of the current line in
Braille. For a multi-line selection, the marking changes with the displayed
line. NVDA uses dots 7 and 8 for this marking. NVDA's Braille settings control
whether selections are shown and which shape the Braille cursor uses.

## Spelling suggestions

Use Neovim's built-in spelling suggestions as follows:

1. Place the cursor on a misspelled word and press `z=`.
2. Hold the NVDA key.
3. Move through the suggestions with `j` and `k`.
4. Press `NVDA+Enter` to accept the selected suggestion.

Speech and Braille present only the suggestion without its number. Releasing
the NVDA key restores the editor line on the Braille display. Neovim's
suggestion list remains open and can be closed with `Escape`.

Under `NVDA menu → Preferences → Settings → Neovim Access Link → Braille`,
choose the Braille cell at which the suggestion should begin.
Counting starts at 1. If the selected position or the suggestion does not fit
on the display, its placement is adjusted automatically. This setting does
not shift the normal editor line.

The offset is particularly useful ergonomically when Caps Lock is configured
as the NVDA key and the left hand remains on it while selecting a suggestion.
The hand and left arm can obscure the left part of the Braille display while
the right hand reads the suggestions. Starting the suggestion farther to the
right keeps it accessible to the right hand and makes it considerably more
comfortable to read.

## Embedded terminals

In the direct-input mode of a buffer opened with `:terminal`, NVDA uses its
normal Windows Terminal presentation. After switching to Terminal-Normal
mode, Neovim Access Link presents the structured Neovim line again.

## If the display is incorrect

If “Windows PowerShell” remains visible instead of the editor line after
connecting, no cursor cell is present, or a routing key at a text position
does not respond:

1. Confirm that the correct Windows Terminal tab or pane has focus.
2. Confirm that the Neovim session was connected with F12.
3. Set NVDA's Braille mode to “follow cursors”.
4. Copy a redacted diagnostic report immediately after the problem.

See [Troubleshooting and diagnostic report](troubleshooting.md) for further
steps.
