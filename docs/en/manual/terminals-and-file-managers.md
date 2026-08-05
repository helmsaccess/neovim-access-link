# Embedded terminal and file managers

## Use an embedded terminal

`:terminal` opens a Neovim terminal buffer. During direct input, Access Link
releases NVDA's native Windows Terminal output. Shells and TUI applications
running inside them therefore remain usable through NVDA's normal terminal
support. The Access Link session and its association remain active.

Starting direct terminal input uses the Insert-mode sound. Leave direct input
with `Ctrl+\`, then `Ctrl+n`. Neovim enters Terminal-Normal mode, Access Link
resumes structured navigation, and the Normal-mode sound plays.

If that sequence is difficult on your keyboard layout, assign an NVDA gesture
to `Leave direct input in the active Neovim terminal` under
`NVDA menu > Preferences > Input gestures... > Neovim Access Link`. This NVDA
command works only in the connected and focused terminal buffer.

`i` without the NVDA key is then a Neovim command again and starts direct
terminal input. Access Link ends neither the shell nor the terminal buffer.

A running terminal job prevents ordinary `:bd`; Neovim reports `E89`. `:bd!`
explicitly ends the job. Open a terminal with `:new | terminal` when the
previous editor buffer needs to remain visible.

## Neovim command line and messages

`:` opens Neovim's command line. Access Link presents Command-line mode,
input, errors, and the structured result message. After execution, the setting
under `General > Session focus` applies:

- `No announcement` leaves only the message.
- `Current line` adds the cursor line.
- `Current context, mode and connection name` adds the destination context.

When a command produces only a message and returns to the same mode, Access
Link still plays the matching return sound. A later asynchronous message is
not attributed to that command.

## File managers and test status

Access Link does not perform file operations itself. The file manager opens,
creates, renames, copies, moves, or deletes files. Access Link makes the
selected entry, type, state, and confirmation prompt accessible.

| File manager | Access Link status |
| --- | --- |
| Oil | practically confirmed on Windows with NVDA and Neovim 0.12 |
| netrw | adapter automatically tested with Neovim 0.10.1 and 0.12.3 |
| nvim-tree | adapter automatically tested against its public plugin API |
| Neo-tree | adapter automatically tested against its public plugin API |
| mini.files | adapter automatically tested against its public plugin API |

Oil is therefore the only file manager with practical confirmation from the
current Windows/NVDA testing. The other adapters remain available, but their
complete workflows are not practically confirmed.

## Navigate entries

For a recognized file-manager entry, Access Link presents the full name and
semantic type. Types include file, directory, symbolic link, socket, pipe, and
device file. Available state such as selection or expanded tree node is also
presented in speech and Braille.

Names with spaces, Unicode, and punctuation remain complete. In a file
manager, the persistent Braille line shows name, type, and state instead of
decorative icons and extra columns. Routing within the real name moves the
Neovim cursor; synthetic type and state text has no routing position.

When a file opens, `General > Session focus` applies. Access Link does not
repeat the following automatic cursor event as one character.

## Use Oil

The [Optional example configuration with Lazy and
Oil](example-configuration.md) provides a directly usable setup.

Oil represents a directory as an editable buffer. A name first changes only in
that buffer. Example rename workflow:

1. Navigate to the entry.
2. Press `0`, then `c$`.
3. Type the new name and press `Escape`.
4. Check the new draft name through speech or Braille.
5. Save with `:w`.
6. Confirm or reject Oil's prompt.

Access Link shows the edited name before `:w`, but reports an executed file
operation only after Oil supplies its result.

Set `skip_confirm_for_simple_edits = false` in Oil. Oil then prompts before
simple renames and duplicates as well. Deletions and complex actions have a
confirmation independently of this setting.

For an Oil confirmation, Access Link presents the action, count, and Y/N, but
not complete paths. `y` and `n` without the NVDA key are input to Oil. Access
Link never answers the prompt automatically. After `y`, Oil's result reports
success or failure; `n` is presented as cancellation.

## Prompts in other file managers

For structured selection and input prompts, use `select_prompts = true` in
nvim-tree and `use_popups_for_input = false` in Neo-tree. These options route
prompts through Neovim's central selection or input API. Access Link does not
change plugin options.

mini.files uses an accessible yes/no/cancel prompt for grouped changes. When a
file manager supplies no semantic result, its own message remains authoritative;
Access Link does not announce invented success.

Other file managers retain normal Neovim navigation. Semantic file type,
selection, and tree state are not promised without a dedicated adapter.
