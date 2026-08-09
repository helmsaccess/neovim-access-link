# Search, replacement, completion, and diagnostics

Access Link presents Neovim's search, replacement, and structured development
information in speech and Braille. Keys without the NVDA key remain Neovim or
plugin commands. Combinations containing the NVDA key open only the documented
Access Link views.

## Search and replace

Neovim still executes search and replacement itself. Access Link adds
accessible feedback:

- With `incsearch` enabled, `/pattern` or `?pattern` reports the preview match
  displayed by Neovim while the pattern is being typed. The report includes
  match position and count. It also says when Neovim bounded the count or
  continued at the opposite end of the buffer. After `Enter`, `n` and `N`
  retain their normal Neovim behavior.
- With `inccommand` enabled, a typed `:substitute` reports Neovim's previewed
  line and the number of affected lines through speech and Braille. This works
  with both `inccommand=nosplit` and `inccommand=split`. Large buffers mark the
  count as incomplete. Neovim provides this live preview only for a direct
  replacement command in the current buffer, not for `:bufdo`, `:argdo`, or
  result-list loops.
- After an accepted search, Access Link reports active search highlighting.
  `:nohlsearch` or `:set nohlsearch` reports that it has been cleared.
- A confirmed replacement such as `:%s/old/new/gc` includes the affected line
  and position in every native `y/n/a/q/l` question. Only Neovim processes the
  answer.
- After a replacement, Access Link uses Neovim's own result message. When
  Neovim's `report` setting provides no count, the report instead includes the
  observed number of changed lines. This is not a separately calculated count
  of individual substitutions.
- `:vimgrep` and `:grep`, including their `add` variants, report the size of
  their Quickfix list; `:lvimgrep` and `:lgrep` do the same for the location
  list. Navigation in an open result window includes the current result
  position.
- Replacements through `:cdo`, `:cfdo`, `:ldo`, `:lfdo`, `:argdo`, or `:bufdo`
  receive one aggregate completion report. It names observed changed and
  unsaved buffers instead of every intermediate edit. Buffers visited
  internally by Neovim are not presented as focus changes. Neovim still
  decides which Quickfix files, arguments, or listed buffers each command
  visits.

This support applies to native Neovim commands. A plugin-specific search UI
needs public structured state or a dedicated adapter.

## Completion menus

Supported sources are:

- Neovim's built-in popup menu with `complete()`, `completefunc`, `omnifunc`,
  and LSP completion;
- `nvim-cmp` through its public selection API;
- `blink.cmp` through public APIs.

The exact automated coverage by plugin and Neovim version is listed in the
[compatibility overview](../development/compatibility.md).

Freely drawn floating windows and ghost text without a visible selection menu
are not automatically accessible menus.

### Operate a menu

Neovim or the completion plugin processes the menu keys. For Neovim's standard
completion, common keys are:

- `Ctrl+n`: next item;
- `Ctrl+p`: previous item;
- `Ctrl+y`: accept the selection;
- `Escape`: close the menu or leave Insert mode.

Access Link does not replace these keys. It presents the item selected by
Neovim, its position, type, source, signature, and short description when the
completion system supplies those fields. Speech and Braille use the same
selection.

After the last item, Neovim's built-in menu has a state with no selected
suggestion. The originally typed text remains; `Ctrl+n` then selects the first
item again. Access Link reports this state explicitly.

NVDA's setting for automatic suggestion sounds controls the menu opening and
closing sounds.

### Read detailed documentation

Under `NVDA menu > Preferences > Input gestures... > Neovim Access Link`,
assign a gesture to `Read documentation for the selected Neovim completion
item or LSP hover`.

The command reads longer documentation while the selected item or current LSP
hover provides content. A missing description is not automatically an Access
Link error: not every completion system exposes documentation through its
public interface.

## Check LSP status

Enter this Neovim command:

```vim
:NvimNvdaLspStatus
```

It names the LSP clients attached to the current buffer or reports that no
client is attached. It is a Neovim command and does not contain the NVDA key.

## Rename symbols with LSP

Use Neovim's existing LSP rename command or your own mapping; Neovim 0.12 maps
`grn` by default. The attached language server must support
`textDocument/rename`.

Access Link replaces neither the rename prompt nor the LSP handler. It observes
Neovim's public `LspRequest` events and the buffers which actually changed.
After completion it reports the observed number of changed and unsaved
buffers without presenting internal text, cursor, or focus changes
individually. It does not claim success when no edit was observed.

## Function parameters while typing

When an LSP server supplies signature help, Access Link speaks the active
parameter in Insert mode on entering a function call and on changing the
argument. Movement within the same argument remains silent. For nested calls,
the innermost call applies.

Automatic output is speech only. Disable it under
`General > Automatically speak the active function parameter while typing`
when you do not need this feedback.

## Inspect signatures and parameters on demand

Place the cursor on a function name or its associated opening or closing
parenthesis:

1. Press `NVDA+Space`.
2. Release only Space and continue holding the NVDA key.
3. Use `NVDA+h` and `NVDA+l` for parameters.
4. Use `NVDA+k` and `NVDA+j` for multiple signatures.
5. Use Braille navigation controls to read long content.
6. Release the NVDA key to return to the editor line.

The first parameter movement after opening or changing a signature shows
parameter 1. The real Neovim cursor does not move. Speech uses complete labels;
Braille shortens only structural prefixes, such as `S 1 of 2`, `P 1 of 3`, and
`D:`.

## Read diagnostics

Access Link consumes diagnostics from Neovim's public `vim.diagnostic` API.
LSP, `nvim-lint`, ALE, `none-ls.nvim`, or another provider can supply the data.
Access Link does not install or start linters itself.

On a diagnostic jump, Access Link presents source, severity, optional code,
message, and position. Background updates and typing remain silent. Errors and
warnings can play a configured sound during deliberate navigation; information
and hints remain silent.

### Explore diagnostics without moving the cursor

1. Press `NVDA+Shift+Space`.
2. Release only Space and continue holding the NVDA key.
3. Use `NVDA+k` and `NVDA+j` to move through diagnostics under the cursor and
   on the current line.
4. Release the NVDA key to return to the editor line.

With no result, Access Link reports `no diagnostic` and plays the configured
neutral confirmation sound. The real Neovim cursor remains in place.

### Neovim diagnostic commands

The following commands are available for custom Neovim mappings:

- `:NvimNvdaDiagnosticPrevious`;
- `:NvimNvdaDiagnosticNext`;
- `:NvimNvdaDiagnosticFirst`;
- `:NvimNvdaDiagnosticLast`;
- `:NvimNvdaDiagnosticCurrent`.

These commands do not change existing mappings. Several diagnostics at one
position remain individually reachable; navigation wraps from the last item
to the first and vice versa.

## If a menu or LSP remains silent

1. Check the Access Link connection.
2. Use `:NvimNvdaLspStatus` to check whether the current buffer has an LSP
   client.
3. Test Neovim's built-in completion menu to isolate a completion-plugin
   problem.
4. Check whether the menu actually has a selected item.
5. Copy the diagnostic report while the affected menu is open.

See [Set up LSP, completion, and linters](language-tools.md) for server and
linter setup.
