# Feature and accessibility matrix

This reference maps implemented accessible workflows to their semantic source
and available evidence. “Automated” does not mean that every real combination
of NVDA, Neovim, plugins, and Braille hardware has been practically tested.
See [compatibility](compatibility.md) for the reference environment and known
limits.

## Editor and navigation

| Area | Semantic source and output | Evidence |
|---|---|---|
| Modes and focus | `ModeChanged`, `nvim_get_mode()`, and correlated focus context provide speech or cues for Normal, Insert, Replace, Visual, Select, Operator-pending, Command-line, and terminal modes. | Automated; core workflows practical under Windows/NVDA. |
| Characters, words, and lines | Cursor events, UTF-8-safe positions, and state differences provide character, word, and line output with configurable cursor detail. | Automated; navigation and detail combinations practically tested. |
| Speech exploration | Contextual `NVDA+h/j/k/l` gestures read characters, words, or lines at a virtual position without moving the real cursor. Separate detail options apply on release. | Protocol, Lua, controller, AppModule, and package tests; base paths practically tested. |
| Editing and selection | Text, cursor, and selection events describe typing, deletion, replacement, and Visual character, line, and block selection. | Unit, protocol, and real Neovim tests; core paths practically tested. |
| Search and structure | Public Neovim state describes search, matching pairs, folds, marks, registers, and macros. | Real TUI and presentation tests. |
| Buffers, windows, and tabs | `BufEnter`, `WinEnter`, and `TabEnter` provide distinct context and status transitions. | Real TUI and presentation tests; practical multi-window and tab switching. |

Line and word navigation have their own settings for adding the current word
or cursor character. Speech exploration uses separate settings for its release
output.

## Messages, menus, and development tools

| Area | Semantic source and output | Evidence |
|---|---|---|
| Command line and messages | Neovim external-UI events provide command line, cursor position, messages, and confirmed return to the previous mode. Speech, Braille, and cues remain separate plans. | Package, presentation, RPC, and real TUI tests; rare pager variants remain bounded. |
| Completion | Neovim completion, `nvim-cmp`, and `blink.cmp` provide selection, kind, source, and available documentation. | Listener-free Neovim 0.10.1 and 0.12.3 tests plus real module contracts; some external-plugin practical acceptance remains open. |
| LSP context | Hover, signature help, active parameter, and held function context use public LSP responses with request and editor identity. | Parser, race, multi-client, real LSP, and package tests; the held view is not yet fully accepted practically. |
| Diagnostics | `vim.diagnostic` is the provider-neutral boundary for message, range, severity, and navigation. Deliberate entry into an error or warning may play a cue. | Automated contracts with LSP, `nvim-lint`, ALE, and `none-ls.nvim`; practical Windows/NVDA breadth remains limited. |
| Spelling | Neovim `spell` and the native `z=` list provide error state and numbered suggestions. The add-on removes numbers from output, navigates contextually, and accepts only a validated index. | Parser, protocol, RPC, AppModule, and Braille tests; `z=` practically tested with one physical Braille display. |
| `vim.ui` choices | `vim.ui.select()` and `vim.ui.input()` provide prompt, selection, and completion semantically. | Real TUI tests. |

Background diagnostic refresh does not automatically speak every result.
Explicit commands read the current, previous, next, first, or last diagnostic.
Spelling output follows NVDA's document-formatting settings for speech, sound,
and Braille.

## Braille

| Area | Behavior | Evidence |
|---|---|---|
| Current line | A public NVDA `TextInfoRegion` represents text, cursor, tabs, selection, and edits. | Automated for Unicode, tabs, empty lines, and focus startup; practical on BRAILLEX EL 80c. |
| Routing | Routing keys set the cursor in Normal, Insert, and Command-line modes; stale or ambiguous targets are rejected. | Protocol, controller, transport, Lua, and package tests; practical on BRAILLEX EL 80c. |
| Standard navigation | NVDA's public line and scroll commands pan the view or move to an adjacent line with a defined target column. | Automated locally and over SSH; basic hardware path confirmed. |
| Repeated routing | Optional double or triple presses perform configured word or line actions. The default is routing only. | State, setting, protocol, transport, and RPC tests; reference workflow practically tested. |
| Braille exploration | Per-Neovim-session virtual line state preserves position and horizontal viewport without moving the real cursor. Edits to the displayed line refresh it fully; routing accepts only current validated state. | Instance, interleaving, edit, routing, transport, and real RPC tests; core path on BRAILLEX EL 80c. |
| Transient views | Spelling suggestions and held LSP or diagnostic information use a temporary public Braille region and then restore the editor region. | Controller, AppModule, region, and package tests; spelling view practically tested. |

Practical Braille testing covers one display and driver combination. It does
not establish support for every display, translation table, or input mapping.

## Terminal, files, and clipboard

| Area | Behavior | Evidence |
|---|---|---|
| Embedded terminal | Direct terminal input uses native pass-through; Terminal-Normal mode, process exit, command-line return, and buffer changes remain structured. | Protocol, gate, TUI, and package tests; core paths practically tested. |
| File managers | Adapters for Oil, netrw, mini.files, nvim-tree, and Neo-tree provide name, kind, and state without visual decoration. Confirmed actions are coalesced. | Broad adapter and Unicode tests; only Oil practically tested under Windows/NVDA. |
| Clipboard | Four assignable NVDA commands explicitly and correlatively transfer a Visual selection, register 0, or Windows clipboard text. | Protocol, Lua, bridge, and package tests; all four paths practical locally and over SSH. |

There is no automatic clipboard synchronization. File managers are supported
only through their documented public state; a new plugin name alone does not
justify an adapter.

## Session isolation and failure behavior

One concrete UI Automation `TermControl` is assigned to one confirmed Neovim
session. Local and remote sessions, ordinary shell panes, tabs, split panes,
windows, and multiple Windows Terminal processes therefore remain separate.
Focus, instance, sequence, and editor identity are revalidated before output,
suppression, or control.

When a capability is absent, an assignment is uncertain, or a connection
fails, the add-on consumes no domain action and restores NVDA's native terminal
behavior. Multi-instance, focus-race, disconnect, reload, and negative paths
have automated coverage; mixed local and remote windows, tabs, and panes have
been practically exercised.

See [architecture](architecture.md), [protocol](protocol.md), the [test
strategy](testing.md), and [guided practical tests](human-testing.md) for more
detail.
