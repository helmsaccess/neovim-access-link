# Add-on settings reference

The “Neovim Access Link” category is registered in NVDA's normal Settings
dialog and stores validated values in `config.conf` section
`NeovimAccessLink`. NVDA configuration profiles provide inheritance and active-
profile writes. `post_configProfileSwitch` reloads effective values without
stopping an authenticated runtime connection.

Tabs are “General”, “Feedback”, “Navigation”, and “Connections”. Feedback
values are numeric Off, Speech, Tones, or Both Speech and Tones. Existing NVDA
Keyboard, Document Formatting, and Object Presentation settings remain
authoritative for typing echo, indentation/spelling, and automatic suggestions.

General also contains a profile-aware session-focus choice: no announcement,
current structured line, or the existing file/special context with mode and
connection name. Existing context is the default. The choice does not alter
focus correlation, structured Braille, or the existing mode-sound settings.

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
