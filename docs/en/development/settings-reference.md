# Add-on settings reference

The “Neovim Access Link” category is registered in NVDA's normal Settings
dialog and stores validated values in `config.conf` section
`nvimNvdaAccess`. NVDA configuration profiles provide inheritance and active-
profile writes. `post_configProfileSwitch` reloads effective values without
stopping an authenticated runtime connection.

Tabs are “General”, “Feedback”, and “Connections”. Feedback values are numeric
Off, Speech, Sounds, or Speech and sounds. Existing NVDA Keyboard, Document
Formatting, and Object Presentation settings remain authoritative for typing
echo, indentation/spelling, and automatic suggestions.

General also contains a profile-aware session-focus choice: no announcement,
current structured line, or the existing file/special context with mode and
connection name. Existing context is the default. The choice does not alter
focus correlation, structured Braille, or the existing mode-sound settings.

Feedback also contains a profile-aware copy/paste success setting using the
same Off, Speech, Sounds, or Speech and sounds values. Failures remain audible.
The four clipboard commands have no default gestures and are assigned through
NVDA's Input Gestures dialog. Transfer direction, register, and target buffer
cannot be supplied as free-form commands, and no automatic synchronization is
provided. The register command replaces fixed register 0 and points the
unnamed register to it; named user registers are not touched.

SSH profile schema 2 stores ID, display name, host/alias, optional Linux user,
port, optional key, and authentication method. Inputs are validated against
option injection and duplicate IDs. Password values are runtime-only. Local
Windows Neovim is the typed `localWindowsTcp` target and has no saved profile
or configurable port.

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
Manual target/session selection remains available for passwords and special
cases. Remembered terminal bindings use stable runtime IDs and live only in
memory.
