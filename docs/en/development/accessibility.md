# Feature and accessibility matrix

This matrix describes implemented, primarily automated behavior in an
alpha-to-beta build. It does not imply exhaustive practical verification.

Implemented areas include mode reporting; character/word/line navigation;
editing and deletion; Visual character/line/block selection; indentation;
completion and signature help; search, pairs, diagnostics and spelling; folds,
marks, registers and macros; command line; embedded terminal transitions; and
adapters for common file managers.

Speech and sounds are configurable where NVDA has no better native setting.
Multiple bound sessions are isolated by runtime identity, session, sequence,
and full-state validation. Unknown windows and failures remain fail open.

Braille state, indentation, selection dots 7/8, and routing are implemented in
the model and automated tests, but no physical display has been tested. Bugs
are very likely. Hardware coverage and fixes are explicitly important priority
work before reliable Braille support can be claimed.
