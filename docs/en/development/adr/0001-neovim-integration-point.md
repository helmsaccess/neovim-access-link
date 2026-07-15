# ADR-0001: Hybrid Neovim integration point

Status: accepted.

Structured semantics must come from a Lua plugin using Neovim APIs. A separate
bridge isolates Linux RPC and SSH lifecycle, while NVDA remains responsible for
focus and accessible output. Terminal scraping cannot reliably represent mode,
selection, completion, diagnostics, Unicode columns, or multiple sessions and
is rejected as the primary data source.

This split keeps the protocol narrow, allows core tests without NVDA, and
ensures transport errors cannot silently turn terminal pixels into editor
truth.

External message and popup-menu UI capabilities attach only while an
authenticated bridge channel is registered. Before connection and after
disconnect, native TUI ownership is preserved so recovery and confirmation
prompts remain visible fail-open.
