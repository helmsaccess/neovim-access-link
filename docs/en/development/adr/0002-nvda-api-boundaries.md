# ADR-0002: NVDA API boundaries for the first beta

## Status

Accepted for beta build 0.89.1. Re-review before changing the supported NVDA
major version.

## Principle

The add-on uses ordinary public add-on entry points:
`globalPluginHandler.GlobalPlugin`, an application-specific AppModule,
`scriptHandler.script`, `addonHandler.getCodeAddon()`, NVDA event handlers,
`queueHandler`, `ui.message`, speech and Braille objects, and NVDA's native
configuration profile stack. It modifies no NVDA source file and replaces no
global NVDA function.

NVDA 2026.1.1 provides no equivalent, explicitly stable add-on API for four
narrow tasks. These exceptions must not expand silently.

## Exception 1: `Terminal._reportNewLines`

The Braille/LiveText overlay class overrides the protected
`_reportNewLines` method to suppress native terminal fragments only for the
authenticated, focused Neovim session. There is no public hook between a
terminal diff and NVDA's native LiveText output.

- Risk: its signature or call order can change with NVDA.
- Containment: a missing session, error, focus loss, or deactivation
  immediately delegates to `super()._reportNewLines`; behavior is fail-open.
- Replacement: review source and regression tests for each NVDA major
  version, and adopt a public terminal-output gate if NVDA provides one.

## Exception 2: UIA runtime ID through `NVDAObject.UIAElement`

Windows Terminal provides no add-on-controlled durable control ID for tab
contents and panes. For runtime-only, never persisted control correlation, the
add-on reads `cachedClassName` and `getRuntimeId()` from the underlying
`UIAElement`. To recognize closed controls, it checks the same element and
then follows NVDA's UIA pattern with a `RuntimeId` property condition within
the still-validated window handle's subtree. Values are used only after
checking the Windows Terminal AppModule, process, and allowed UIA class.

- Risk: the UIA wrapper's shape or lifetime can change.
- Containment: missing or invalid values disable correlation and suppression.
  COM/UIA errors are uncertain and do not trigger cleanup. Window titles and
  terminal text are never substitute heuristics.
- Replacement: prefer a future public, stable terminal-control identifier and
  remove the runtime-ID dependency.

## Exception 3: NVDA Settings and Tools integration

Registration through `NVDASettingsDialog.categoryClasses`, access to the Tools
menu, and `gui.runScriptModalDialog` are common NVDA add-on practice, but are
not promised as independent long-term stable extension interfaces.

- Risk: menu or dialog structure can change between NVDA major versions,
  making the feature unavailable.
- Containment: registration and removal are symmetric and exception-safe.
  Network and installation work never runs in a dialog or NVDA main thread. A
  GUI failure must not suppress terminal output.
- Replacement: adopt official registrable Settings and Tools extension points
  when available; until then, test each target version with real NVDA and the
  extracted built add-on.

## Exception 4: immediately ending one owned Braille message

Neovim's spelling suggestion and held developer information are presented through the public
`braille.handler.message` path. NVDA itself uses this path for suggestion and
selection feedback. Releasing the NVDA key must immediately reveal the
preserved editor buffer, but NVDA 2026.1.1 exposes neither a public inverse of
`message` nor a lifetime argument for one message.

After the public `message()` call, the add-on therefore reads
`BrailleHandler.messageBuffer`, `BrailleHandler.buffer`, and
`BrailleBuffer.regions` to retain the concrete region created by that call. It
claims ownership only if the visible buffer is the message buffer and its last
region is a new object compared with the state before the call. A no-op
`message()` call, for example when Braille messages are disabled or NVDA is in
“display speech output” mode, therefore cannot claim a pre-existing foreign
message.

Only for this proven owned region does the add-on call `Stop()` on the current
private `_messageCallLater`, so the active selection cannot time out while the
user is reading it. It does not overwrite the timer field. It invokes
`BrailleHandler._dismissMessage` only while the same message buffer is visible
and exactly the same region remains its last region. A newer message from NVDA
or another add-on is not dismissed.

Longer held developer information replaces this proven owned standard region
with a custom public `braille.Region`. It translates the complete text once
and exposes at most one display width as a local page. Its public `nextLine()`
and `previousLine()` methods page only within those pages, so neither
horizontal Braille commands nor line commands can reach the editor region at
a boundary. NVDA starts its general message timer again after the public
scroll command returns. A `core.callLater` callback then repeats the
identity-checked `Stop()` only for the same still-visible owned region. A
newer foreign message remains untouched.

- Private touchpoints: `BrailleHandler.messageBuffer`,
  `BrailleHandler.buffer`, `BrailleBuffer.regions`,
  `BrailleBuffer.update`, `BrailleBuffer.windowStartPos`,
  `BrailleHandler._messageCallLater`, `CallLater.Stop()`, and
  `BrailleHandler._dismissMessage`.
- Risk: buffer, region, method, and timer names, identities, or lifetimes can
  change with NVDA.
- Containment: every access uses `getattr`, identity comparisons, and a
  complete exception boundary. Missing buffer details, a no-op public
  presentation, a foreign current region, or any exception merely leaves
  NVDA's normal message behavior in control. Editor state, input, transport,
  and speech are not changed.
- Rationale: while the NVDA key is held, the suggestion or developer
  information is an active control value, not a notification that may expire
  while being read. On release, the
  already-built editor region must return immediately. NVDA 2026.1.1 offers
  neither a public per-message lifetime nor a targeted operation to dismiss
  exactly the owned message. Rebuilding focus does not dismiss the active
  message buffer, and waiting for the global timeout satisfies neither
  requirement.
- Replacement: use a public targeted message-dismiss API as soon as NVDA
  provides one. Until then, repeat source review, identity/fail-open package
  tests, and practical Braille acceptance for every supported NVDA major
  version.

## Exceptions that are not permitted

Raw global keyboard hooks, monkeypatches, terminal screen scraping, persisted
UIA IDs, private network interfaces, and blocking work on NVDA's main thread
remain prohibited. F12 is observed through the public, process-wide gesture
decider. Registration and strict context checks belong to the Windows
Terminal-only AppModule; F12 is neither bound as an NVDA script nor forwarded
synthetically.

The Global Plugin must not register global event handlers, configurable
terminal scripts, or overlay selection. Focus events, configurable commands,
F12, overlays, and default gestures belong to the Windows Terminal AppModule.
NVDA initially lists unassigned commands when Windows Terminal was focused
before opening Input Gestures. Once that AppModule class has loaded, NVDA's
user gesture map can display a saved assignment elsewhere, but runtime
resolution selects it only in the Windows Terminal application context.
