# Protocol instructions

- Treat every frame, field, session claim, and control request as untrusted input.
- Validate protocol version, authentication, session identity, sequence numbers, message sizes,
  capabilities, heartbeat, resync, and `fullState` before updating canonical state.
- Reject malformed, oversized, stale, unauthenticated, or capability-incompatible data without
  allocating unbounded work.
- Keep transport framing, protocol validation, canonical state, and presentation planning
  independent.
- Preserve exact distinctions between byte, Unicode character, virtual, and visual columns.
- Do not add compatibility paths for obsolete development-only add-on or plugin clients unless
  the user explicitly changes the compatibility policy.
- Protocol changes require synchronized endpoint tests and updates to
  `docs/de/development/protocol.md` and its English mirror.
- Run protocol unit tests through `python3 tools/run_tests.py quick` or `all-safe`.
- Run `python3 tools/run_tests.py ssh` and `python3 tools/run_tests.py socket` as separate phases
  when the affected boundary belongs to those groups.
