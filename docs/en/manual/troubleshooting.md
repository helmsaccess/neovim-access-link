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

Wait for the inventory-ready message, focus Neovim in the same terminal
control, press F12 once, and wait up to two seconds. Do not
press repeatedly. The manually assigned “Choose a server...” command selects a
target and then also requires F12. Diagnostic categories `claimInventoryReady`,
`sessionClaimGestureReceived`, `automaticLocalClaimChecked`,
`automaticClaimResolutionCompleted`, `localTcpStart`, and `sshProcessStart`
separate discovery, key handling, claim resolution, and transport startup.
If `sessionClaimGestureReceived` is absent, support may be disabled, focus may
have moved, or the gesture may not have reached the Windows Terminal AppModule.
Without a fresh Neovim claim, claim evaluation is deliberately silent.

## SSH failure

Test the same account visibly with Windows OpenSSH. Resolve host-key prompts,
key permissions, agent/passphrase handling, or server-side password policy
there first. Then update the Linux components and restart Neovim.

## The wrong session is bound

Focus the affected Windows Terminal control, disconnect it or forget its
temporary binding, then focus the intended Neovim session and press F12 once.
If several sessions use the same working directory, an optional session name
can make the selection clearer, for example:

```text
NVIM_NVDA_SESSION_NAME=Documentation nvim
```

## Terminal fragments or output from another tab

Deactivate immediately. Normal terminal output must return. Record focused
window/tab, local or SSH transport, mode, preceding tab switch, and whether
F12 or manual selection was used. Copy a redacted report before restarting NVDA
when possible.

Because this is alpha-to-beta software, first try unfamiliar or unconfirmed
features in a disposable buffer. Braille behavior has not yet been practically
confirmed on physical hardware.

## NVDA appears stuck after a dialog

Component work and SSH password handling run outside NVDA's main thread, but a
result or password dialog may still be open. Use Alt+Tab to locate it and close
or cancel it. Restart NVDA if necessary, then preserve a diagnostic report and
the preceding NVDA log. Review both for credentials, local paths, SSH targets,
or confidential text before sharing them.
