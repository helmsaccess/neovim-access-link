# Test instructions for coding agents

This file adds rules for the `tests/` subtree. Repository-wide instructions still apply.

## Guided human tests

- Add a guided human test only when real perception, NVDA, Windows Terminal, sound, physical
  Braille hardware, or an explicit user request makes it necessary. Prefer automated coverage
  for behavior that code can decide reliably, and do not duplicate it as manual work.
- Optimize every guided flow for tester comfort. Keep setup and repetition short, preserve
  resumability, and ask the tester to enter a command only when command entry itself is under
  test. Otherwise expose prepared actions through function-key mappings.
- Keep mappings predictable and logically ordered, such as previous before next or setup before
  execution. Reuse established meanings across profiles where practical. Do not use `F1`, which
  Neovim reserves for help, or `F11`, which Windows Terminal reserves for full-screen mode. Use a
  documented modifier with an otherwise suitable key when the available function keys are
  insufficient.
- Reserve `F2` in Normal and Insert mode for repeating the complete current instruction: stable
  test ID, purpose, numbered keys and steps, and pass condition. Keep it available in every profile.
- Before handing a human test to the user, exercise its complete setup, key sequence, state
  transitions, boundaries, cleanup, and expected semantic events as far as automation permits.
  Use isolated real Neovim processes and cover relevant headless, TUI, RPC, bridge, or transport
  paths; leave only genuinely perceptual or hardware-dependent observations to the tester.

## Test descriptions

- Present each localized task in this order: stable test ID, one-sentence purpose and scope, only
  necessary preconditions, sequentially numbered keys and actions, and one observable pass
  condition. The task must be understandable and executable on its own.
- Apply the useful parts of W3C ACT structure without its web-conformance boilerplate: make
  applicability, expectations, and outcome-relevant assumptions or limitations explicit. Keep
  every expectation distinct, unambiguous, in plain language, and based only on evidence the
  tester can perceive; distinguish pass, fail, blocked, skipped, and not applicable.
- Keep the complete description compact. Cover one primary behavior per task; remove repeated
  setup, location reminders, implementation details, and vague language. Mention expected speech,
  Braille, sound, focus, or fail-open behavior only when relevant. Use hard line breaks only
  between steps and let the terminal wrap text to its current width.
- Record outside the tester-facing description why manual testing remains necessary and link the
  automated evidence that already protects the rest of the flow.
