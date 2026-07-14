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

SSH profile schema 2 stores ID, display name, host/alias, optional Linux user,
port, optional key, and authentication method. Inputs are validated against
option injection and duplicate IDs. Password values are runtime-only. Local
Windows Neovim is the typed `localWindowsTcp` target and has no saved profile
or configurable port.

F12 is the default claim gesture shared by packaged configuration. Activation
inventories eligible targets; F12 selects only a newly incremented claim.
Manual target/session selection remains available for passwords and special
cases. Remembered terminal bindings use stable runtime IDs and live only in
memory.
