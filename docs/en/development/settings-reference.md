# Add-on settings reference

The “Neovim Access Link” category is registered in NVDA's normal Settings
dialog and stores validated values in `config.conf` section
`NeovimAccessLink`. NVDA configuration profiles provide inheritance and active-
profile writes. `post_configProfileSwitch` reloads effective values without
stopping an authenticated runtime connection.

Tabs are “General”, “Feedback”, “Navigation”, “Braille”, and “Connections”.
The Braille tab groups speech-exploration presentation, routing actions, and
spelling-suggestion placement. Feedback values are numeric Off, Speech, Tones,
or Both Speech and Tones. Existing NVDA Keyboard, Document Formatting, Object
Presentation, and Braille settings remain authoritative for typing echo,
indentation/spelling, automatic suggestions, translation, drivers, and cursor
presentation.

General also contains a profile-aware session-focus choice: no announcement,
current structured line, or the existing file/special context with mode and
connection name. Existing context is the default. The choice does not alter
focus correlation, structured Braille, or the existing mode-sound settings.

The top-level profile-aware integer `brailleSuggestionStart` is one-based and
defaults to 1. It positions only the transient text of an active spelling
choice. The NVDA Braille adapter compares it with
`braille.handler.displaySize`; values beyond the current display are ignored
at presentation time and cell 1 is used. Before adding blank cells, the region
translates the unshifted suggestion with NVDA's active Braille table. The last
start at which the translated result completely fits then limits the requested
cell to the left; a longer suggestion starts at cell 1. The setting never
changes speech or the persistent editor Braille plan.

The top-level profile-aware integer `brailleDeveloperStart` follows the same
validation and fit rules. It positions only held function-parameter and
diagnostic views and remains independent of `brailleSuggestionStart`. Both
values default to 1.

The top-level profile-aware Boolean `brailleFollowSpeechExploration` defaults
to `true`. It allows the Braille plan to present the contextual speech
exploration controller's validated virtual line while canonical editor state
remains unchanged. The separate Braille exploration controller takes
priority. With `false`, Braille planning remains at the canonical cursor
during `NVDA+h/j/k/l` and `Shift+NVDA+h/l`.

The nested profile-aware `brailleRouting` section contains three choice
indices:

- `wordAction`: 0 for route only, 1 for `cw`, and 2 for `dw`;
- `lineAction`: 0 for route only, 1 for `c$`, and 2 for `d$`;
- `lineStart`: 0 for the routed position, 1 for the first non-blank
  character, and 2 for the absolute line beginning.

All defaults are 0. `lineStart` is consulted only when a line action is
enabled. Repeat timing comes from NVDA's public
`config.conf["keyboard"]["multiPressTimeout"]` setting; the add-on has no
second timing value. `SettingsService` validates these indices and exposes
only resolved symbolic values to terminal integration.

The nested `navigationDetails` section stores four profile-aware choice
indices: `navigationWord` and `explorationWord` are 0 for the base word only
or 1 for word plus cursor character. `navigationLine` and `explorationLine`
are bit-like choice indices: 0 is the base line only, 1 adds the current word,
2 adds the cursor character, and 3 adds both in word-then-character order.
Defaults 1, 2, 1, and 2 preserve the behavior predating these controls.
`SettingsService` resolves the indices to booleans before passing them through
the neutral editor and exploration planning interfaces; core planners never
read NVDA configuration directly. Exploration values are resolved from the
active profile when NVDA is released; they change neither virtual exploration
steps nor character exploration.

Feedback also contains a profile-aware copy/paste success setting using the
same Off, Speech, Tones, or Both Speech and Tones values. Failures remain audible.
`diagnosticLine` and `diagnosticPosition` independently gate passive error or
warning cues on entering an affected line or exact range. The settings UI
offers only Off and Tones for these keys; complete text remains available
through explicit diagnostic inspection and navigation.
The four clipboard commands have no default gestures and are assigned through
NVDA's Input Gestures dialog after Windows Terminal was focused before opening
it. Like the other configurable terminal commands, they belong to that
AppModule and are not resolved in unrelated applications. After the class has
loaded, NVDA may nevertheless continue displaying a saved assignment elsewhere
through its global user gesture map. Transfer direction, register, and target
buffer cannot be supplied as free-form commands, and no automatic
synchronization is provided. The register command replaces fixed register 0
and points the unnamed register to it; named user registers are not touched.

An SSH profile stores ID, display name, host/alias, optional Linux user, port,
optional key, and authentication method. Host and user are separate fields;
combined values from older add-on IDs are not migrated. Inputs are validated
against option injection and duplicate IDs. Password values are runtime-only.
Local Windows Neovim is the typed `localWindowsTcp` target and has no saved
profile or configurable port. There is no separate JSON settings store or
import from former add-on IDs.

F12 is the default claim gesture shared by packaged configuration. Activation
inventories eligible targets; F12 selects only a newly incremented claim.
The Windows Terminal app module observes F12 through
`decide_executeGesture` without binding an NVDA script. NVDA therefore passes
the original physical key directly to Neovim, while the observer separately
queues claim evaluation. Neovim matches the unchanged `typed` value instead
of relying on terminal-code mapping. While support is disabled, the observer
is inert and F12 has no add-on effect. While support is enabled, each physical
F12 authorizes one attempt for the exact focused control; the add-on refreshes
terminal identity and looks for the fresh claim. Without one, it remains silent
and creates no binding, dialog, or suppression.
Authorization additionally requires NVDA's current focus object, that exact
Windows Terminal AppModule instance, the complete UIA control identity, and
the gate to agree. A single remaining AppModule is not a fallback. In Insert
mode F12 remains observable as the physical claim but produces no text when
the key was otherwise unbound. Existing Insert-mode mappings are preserved.
Because no reverse channel from NVDA to that Neovim instance exists before the
first connection, this narrow reservation also applies inside Neovim when NVDA
does not authorize that press for assignment; F12 remains unchanged outside
Neovim.
Manual target/session selection remains available for passwords and special
cases. Remembered terminal bindings use stable runtime IDs and live only in
memory.
