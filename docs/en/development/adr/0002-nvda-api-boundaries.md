# ADR-0002: NVDA API boundaries for the first beta

Status: accepted with documented exceptions.

Prefer public NVDA APIs for settings, profiles, queueing, speech, Braille,
scripts, AppModules, and add-on metadata. Windows Terminal suppression requires
interception of NVDA terminal event paths for which no complete public add-on
abstraction exists. These narrowly scoped hooks are confined to the Windows
Terminal AppModule, version-tested, fail open, and must be re-reviewed for each
supported NVDA release.

The Global Plugin must not define global event handlers or overlay selection.
It may expose unbound script metadata so configurable commands remain visible
in NVDA's Input Gestures dialog. Those scripts read focus once, delegate only
to a fully validated Windows Terminal control, and pass the original gesture
through unchanged elsewhere; Windows-Terminal-specific focus events, F12,
overlays, and default gestures remain in the AppModule. Replace private
touchpoints when an official extension point becomes available.
