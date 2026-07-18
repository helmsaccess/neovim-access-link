# Sounds and earcons

Sounds can supplement or replace speech for configured editor actions. Current
cues cover Insert/direct terminal input, a short mid-pitch command-line tone,
and the transition to Normal or canonical Terminal-Normal,
matching errors, deletion, replace,
line/file boundaries, and crossing a line. Completion open/close and spelling
cues follow the relevant NVDA settings.

Select Off, Speech, Tones, or Both Speech and Tones under `NVDA menu → Preferences
→ Settings... → Neovim Access Link`. Sounds are bundled resources and are
played on NVDA's main thread through its audio facilities. A missing sound must
fail safely without blocking editor feedback or terminal fallback.
