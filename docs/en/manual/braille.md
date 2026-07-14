# Braille support

> **Important test warning:** Braille has not been tested with a physical
> Braille display and very likely contains bugs. This chapter describes the
> intended and automatically tested model, not confirmed hardware reliability.
> Physical-display testing and fixes are an important priority TODO.

The intended model presents the current logical line, cursor, indentation,
selection, mode-relevant state, and supported messages through NVDA's Braille
APIs. NVDA and Liblouis remain responsible for translation and display-driver
communication.

Selection uses dots 7 and 8 without replacing text. Routing keys request a
validated cursor move in the bound Neovim session. Byte, character, virtual,
and display columns remain distinct so tabs, combining characters, wide
characters, and emoji are not treated as one-byte cells.

Expected fail-open behavior is essential: an invalid route, stale state,
disconnect, or unknown tab must not move a cursor in another session. Please
report display model, translation table, exact action, expected result, actual
result, and a redacted diagnostic report. Do not include confidential buffer
text.
