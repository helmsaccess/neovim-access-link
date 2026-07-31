# Sounds and earcons

Sounds can supplement or replace speech for configured editor actions. Current
cues cover Insert/direct terminal input, a short mid-pitch command-line tone,
and the transition to Normal or canonical Terminal-Normal,
matching errors, deletion, replace,
line/file boundaries, and crossing a line. Completion open/close and spelling
cues follow the relevant NVDA settings.

The spelling cue is emitted after completing a misspelled word and when normal
word navigation or word speech exploration reaches an affected word. NVDA's spelling
and grammar settings remain authoritative; the add-on introduces no separate
option. In that NVDA setting, Speech controls the localized “spelling error”
or “grammar error” label, Sound controls `textError.wav`, and Braille controls
only the error markers on the display. Normal word navigation and word
speech exploration mode interpret the same combination; the reached word remains spoken
independently.

Diagnostic errors and warnings use two short accessibility signals from the
MIT-licensed Code - OSS source of Visual Studio Code. The bundled sound
license records the pinned source commit, source and WAV hashes, WAV decoding,
and the complete MIT license. As in VS Code, the line and position signals
reuse the same file for each severity. During explicit cursor navigation, the
line cue plays once on entering a diagnostic line and the position cue plays
at every cursor position reached within a diagnostic range. Typing and
asynchronous `DiagnosticChanged` refreshes stay silent: unlike VS Code, the
terminal integration does not receive equivalent internal editor state for
its marker timer and typing debounce. The Diagnostic line and Diagnostic
position feedback settings can disable the two signal classes separately.

Select Off, Speech, Tones, or Both Speech and Tones under `NVDA menu → Preferences
→ Settings... → Neovim Access Link`. Sounds are bundled resources and are
played on NVDA's main thread through its audio facilities. A missing sound must
fail safely without blocking editor feedback or terminal fallback.
