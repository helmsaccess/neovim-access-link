# Manual: Add-on settings

Open the category through `NVDA menu → Preferences → Settings... → Neovim
Access Link`. The add-on deliberately adds no duplicate settings item directly
to the Preferences submenu.

The category has “General”, “Feedback”, and “Connections” tabs. OK saves and
closes, Apply saves without closing, and Cancel discards unsaved changes.
Values use NVDA's normal configuration profiles. Manage those through
`NVDA menu → Configuration profiles...`; the add-on neither selects nor
activates a profile itself.

## Feedback

Global action feedback and individual actions use Off, Speech, Sounds, or
Speech and sounds. Individual settings cover mode changes, deletion, replace,
line/file boundaries, crossing a line, and unmatched pairs.

Existing NVDA settings remain authoritative:

| Function | NVDA location |
| --- | --- |
| Typed characters and words | Preferences → Settings... → Keyboard |
| Indentation and spelling | Preferences → Settings... → Document Formatting |
| Automatic suggestions | Preferences → Settings... → Object Presentation |

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

Use `NVDA menu → Preferences → Input gestures... → Neovim Access Link` to
assign activation, manual connection, disconnect, forget-binding, and
diagnostic-report commands. F12 is the default session-claim key shared with
the installed plugin and should not be reassigned as activation.

Temporary tab bindings use a stable Windows Terminal UI Automation runtime ID,
remain only in memory, and never inspect terminal text or titles.
