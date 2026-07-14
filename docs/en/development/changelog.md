# Changelog

## 0.89.4 beta test build

- Complete German and English Markdown sources and separate HTML outputs for
  the Quick Guide, manual, and developer documentation.
- Project licensing is GPL-2.0-only. The unmodified license is included in both
  installable packages; contribution and additional relicensing terms are
  documented separately.
- Standard GitHub community files were added and private product requirements
  removed from the public source tree.

## 0.89.3 beta test build

- Separate German and English Quick Guide, user manual, and developer HTML
  documents with validated links.
- Bounded local F12 follow-up handles delayed atomic registry updates.
- Diagnostics distinguish local/remote inventory and claim resolution without
  exposing editor text.

## 0.89.2 beta test build

- A unique local F12 claim is resolved immediately without waiting for slower
  SSH inventory work.

## 0.89.1 first beta preparation

- Centralized product metadata and the visible “Neovim Access Link” name.
- Stable internal add-on ID retained for upgrades and profile settings.
- NVDA private API exceptions documented in ADR-0002.

Earlier development established protocol v2, SSH stdio, local loopback RPC,
rootless embedded components, multiple explicitly bound runtime sessions,
Windows Terminal AppModule isolation, fail-open terminal behavior, and
structured speech/Braille planning. Git retains the detailed experimental
history.
