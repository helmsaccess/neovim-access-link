# Troubleshooting and diagnostic report

## Copy a diagnostic report

The command is under `NVDA menu → Preferences → Input gestures... → Neovim
Access Link` and defaults to `NVDA+Alt+D`. Editor text, selections, registers,
passwords, and tokens are redacted. Installation paths, profile names, or SSH
targets may still identify a system, so review the report before sharing it.

## No response

Confirm Windows Terminal has focus, the add-on is enabled, and an activation
gesture is assigned. The add-on deliberately does nothing in Notepad, PuTTY,
or unknown applications. Restart NVDA after installation or upgrade.

## Local plugin not found

Close every local Neovim, update “This computer”, and restart Neovim. Check:

```vim
:echo exists(':NvimNvdaSessionName')
```

Expected result is `2`.

## F12 does not connect

Wait for the inventory-ready message, focus Neovim, press F12 once, and wait
up to two seconds. Do not press repeatedly. Try the manually assigned “Choose a
server...” command. Diagnostic categories `claimInventoryReady`,
`sessionClaimGestureReceived`, `automaticLocalClaimChecked`,
`automaticClaimResolutionCompleted`, `localTcpStart`, and `sshProcessStart`
separate discovery, key handling, claim resolution, and transport startup.

## SSH failure

Test the same account visibly with Windows OpenSSH. Resolve host-key prompts,
key permissions, agent/passphrase handling, or server-side password policy
there first. Then update the Linux components and restart Neovim.

## Terminal fragments or output from another tab

Deactivate immediately. Normal terminal output must return. Record focused
window/tab, local or SSH transport, mode, preceding tab switch, and whether
F12 or manual selection was used. Copy a redacted report before restarting NVDA
when possible.

Because this is alpha-to-beta software, also verify untested features in a
disposable buffer. Braille issues are especially expected until physical
hardware testing has been completed.
