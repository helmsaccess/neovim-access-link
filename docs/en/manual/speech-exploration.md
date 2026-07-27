# Speech exploration mode

Speech exploration mode reads characters, words, or lines without moving the
real Neovim cursor. It is a speech feature of the add-on, not a Braille mode.
A connected Braille display can optionally present the explored position as
well.

The mode is useful, for example, for briefly checking the next word or an
adjacent line while typing. Releasing the NVDA key lets you continue
immediately at the unchanged insertion point.

## Operation

Keep the NVDA key held during speech exploration mode:

| Key | Virtual reading movement |
| --- | --- |
| `NVDA+h` / `NVDA+l` | previous / next character |
| `Shift+NVDA+h` / `Shift+NVDA+l` | previous / next word |
| `NVDA+k` / `NVDA+j` | previous / next line |

The first movement starts at the real Neovim cursor. Further movements change
only the virtual reading position. Text, selection, viewport, and real cursor
remain unchanged.

The commands apply in an exactly connected and focused Neovim pane in Normal,
Insert, Replace, Visual, and Operator-pending modes, as well as on Neovim's
command line, in Terminal-normal mode, and during direct Terminal input. The
same key combinations retain their normal NVDA behavior in a shell, an unbound
pane, another tab, or another application.

## Ending speech exploration mode

Releasing the NVDA key ends speech exploration mode and returns output to the
unchanged real cursor:

- After character speech exploration, the cursor character is spoken.
- After word or line speech exploration, the settings under
  `Neovim Access Link → Navigation → Speech exploration mode release` apply.

Word output can additionally include the cursor character. Line output can add
the current word, the cursor character, or both. These settings affect only
the release announcement, not the virtual positions read during speech
exploration mode.

A short two-note cue marks a return to the original character, word, or line.
It follows the configured sound output for line boundaries.

## Optional Braille display support

Speech exploration mode works without a Braille display. By default, however,
a connected Braille display also presents the virtual reading position
temporarily. It returns to the real cursor when the mode ends.

Disable “Braille display follows the speech exploration mode position” under
`Neovim Access Link → Braille → Speech exploration mode` if the Braille
display should remain at the real cursor during speech movements.

Pressing one routing key at the temporarily displayed position adopts that
position as the real Neovim cursor. Double- and triple-press routing editing
actions are disabled during the read-only speech exploration mode.

The independent
[Braille exploration mode](braille.md#braille-exploration-mode-read-lines-while-leaving-the-cursor-in-place),
in contrast, belongs to Braille-display navigation. It is operated with the
display's navigation controls, remains active after being selected, and owns a
separate virtual line position. The two modes share no speech- or
Braille-exploration state.

## Speech exploration mode and Braille exploration mode

| Property | Speech exploration mode | Braille exploration mode |
| --- | --- | --- |
| Primary output | Speech | Braille display |
| Operation | NVDA key together with `h`, `j`, `k`, or `l` | Braille display navigation controls |
| Duration | Only while the NVDA key is held | Independently in each connected Neovim session until toggled again or disconnected |
| Virtual movement | Characters, words, and lines | Lines and visible segments |
| Real cursor | Remains in place | Remains in place for Up and Down; routing can adopt the position |
| Braille display required | No | Yes |
