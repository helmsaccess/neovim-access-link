# Troubleshooting and diagnostic reports

Start with the first missing step: add-on active, plugin loaded, session found,
connection established, and optional tool configured.

## Copy a diagnostic report

Focus Windows Terminal and press `NVDA+Alt+D`. The same command appears under
`NVDA menu → Preferences → Input gestures... → Neovim Access Link`. The report
is copied to the Windows clipboard.

Editor text, selections, registers, passwords, and tokens are replaced with
placeholders. Installation messages can still contain local paths, profile
names, or SSH targets. Review the report before sharing it.

## The add-on does not respond

1. Focus Windows Terminal. Access Link does not intervene in other
   applications.
2. Confirm that Neovim Access Link is enabled in NVDA's installed add-ons.
3. With Windows Terminal focused, open Input gestures and assign a gesture to
   the activation command.
4. Restart NVDA after an installation or update.

If the category is absent from Input gestures, close the dialog, focus Windows
Terminal, and open it again.

## The Neovim plugin is installed but not loaded

Close every affected Neovim instance, update components for the correct target,
and restart Neovim. Then check:

```vim
:echo exists(':NvimNvdaSessionName')
```

The expected result is `2`. A plugin manager that replaces `packpath` or
start-package loading must register the local copy installed by the add-on. Do
not install a second copy. See
[Setting up LSP, completion, and linters](language-tools.md#access-link-plugin-and-plugin-managers)
for details and a `lazy.nvim` example.

## F12 does not connect

1. Activate Access Link and wait for the inventory-ready message.
2. Focus the intended Neovim pane.
3. Press F12 exactly once and wait up to two seconds.
4. As a comparison, use the assignable “Choose a server and connect this
   terminal to a new Neovim session” command.

Rapid repeated F12 presses each start another binding check. Copy the
diagnostic report directly in the affected pane if the connection remains
absent.

## The wrong session is connected

1. Focus the affected Windows Terminal pane.
2. Disconnect it or forget its temporary binding.
3. Focus the intended Neovim and press F12 once.

When several sessions look alike, an optional name makes selection clearer,
for example on Linux:

```text
NVIM_NVDA_SESSION_NAME=Documentation nvim
```

## SSH connection fails

Test the same target outside the add-on in Windows Terminal first:

```text
ssh user@example.invalid
```

Confirm the host key there and resolve key files, passphrases, `ssh-agent`, or
server-side password authentication. Access Link changes neither the Windows
SSH configuration nor the server's `sshd_config`. Then update the Linux
components and restart Neovim.

## Access Link works but LSP or diagnostics are absent

Press the LSP status sequence defined by your Neovim configuration or run
`:NvimNvdaLspStatus`. If Access Link reports no active client, use
`:checkhealth vim.lsp` to inspect the Neovim configuration and confirm that the
language server is found on the computer where Neovim runs.

Diagnostics appear only after a language server or linter publishes them
through Neovim's diagnostic API. Check the tool command in the same terminal
and run a manually mapped linter action. The [setup guide](language-tools.md)
contains a complete Python test path.

## Terminal fragments are spoken

A connected and safely associated Neovim session uses structured output.
Native terminal output remains active in an unconnected pane, during direct
input in `:terminal`, after disconnecting, and whenever Access Link cannot
safely confirm the association.

If unexpected fragments occur after switching windows, tabs, or panes, copy
the diagnostic report immediately in the affected pane. Deactivate Access Link
as a safety check; complete native terminal output must return.

## NVDA does not respond after a dialog

Use `Alt+Tab` to locate an open result, confirmation, or password dialog and
close or cancel it. Restart NVDA if it no longer responds. Then preserve the
diagnostic report and the preceding NVDA log. Review both for confidential
information before sharing them.
