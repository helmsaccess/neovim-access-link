# Sounds and earcons

Sounds can supplement or replace speech for configured editor actions. Current
cues cover Insert and Normal mode, matching errors, deletion, replace,
line/file boundaries, and crossing a line. Completion open/close and spelling
cues follow the relevant NVDA settings.

Select Off, Speech, Sounds, or Speech and sounds under `NVDA menu → Preferences
→ Settings... → Neovim Access Link`. Sounds are bundled resources and are
played on NVDA's main thread through its audio facilities. A missing sound must
fail safely without blocking editor feedback or terminal fallback.
