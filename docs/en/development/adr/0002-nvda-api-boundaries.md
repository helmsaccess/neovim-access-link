# ADR-0002: NVDA API boundaries for the first beta

Status: accepted with documented exceptions.

Prefer public NVDA APIs for settings, profiles, queueing, speech, Braille,
scripts, AppModules, and add-on metadata. Windows Terminal suppression requires
interception of NVDA terminal event paths for which no complete public add-on
abstraction exists. These narrowly scoped hooks are confined to the Windows
Terminal AppModule, version-tested, fail open, and must be re-reviewed for each
supported NVDA release.

The global service must not define global event handlers, overlay selection,
input scripts, or generic focus inspection. Replace private touchpoints when an
official extension point becomes available.
