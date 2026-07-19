# ADR-0002: NVDA API boundaries for the first beta

Status: accepted with documented exceptions.

Prefer public NVDA APIs for settings, profiles, queueing, speech, Braille,
scripts, AppModules, and add-on metadata. Windows Terminal suppression requires
interception of NVDA terminal event paths for which no complete public add-on
abstraction exists. These narrowly scoped hooks are confined to the Windows
Terminal AppModule, version-tested, fail open, and must be re-reviewed for each
supported NVDA release.

The Global Plugin must not define global event handlers, configurable terminal
scripts, or overlay selection. Windows-Terminal-specific focus events,
configurable commands, F12, overlays, and default gestures remain in the
AppModule. NVDA initially lists unassigned commands when Windows Terminal was
focused before opening Input Gestures. Its user gesture map may later display
a saved mapping elsewhere once the AppModule class is loaded, but runtime
resolution selects it only in the Windows Terminal application context.
Replace private touchpoints when an official extension point becomes available.
