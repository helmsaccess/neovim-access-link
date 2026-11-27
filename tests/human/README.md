# Guided human tests

This directory contains the small set of checks that need a real NVDA,
Windows Terminal, sound output, or physical Braille display. It is not a
second automated test suite and must not duplicate behavior that Python or Lua
can decide reliably.

Start with the German or English tester documentation:

- `docs/de/development/human-testing.md`
- `docs/en/development/human-testing.md`

The [developer test guide](../../docs/en/development/testing.md#guided-workflows-over-real-neovim-rpc)
describes the automated Neovim and protocol checks that complement these
tasks.

The Windows entry point is `framework/run.ps1`. Each pending task gets a fresh
isolated `framework/init.lua` session through `nvim -u`, and F2 repeats the
short test ID, purpose, numbered steps, and pass condition inside Neovim. The
runner never copies over the user's normal Neovim configuration. Downloaded
dependencies and run results stay in the ignored repository `tmp/` directory.

## Maintained surface

- `plans/*.json`: semantic test cards with stable IDs;
- `locales/de.json` and `locales/en.json`: all runner and card text;
- `fixtures/`: intentionally small source files opened by the cards;
- `dependencies.json`: exact plugin revisions and tool versions;
- `framework/run.ps1`: accessible Windows setup, execution, resume, and result capture;
- `framework/validate.py`: definition/runtime fingerprints and result validation;
- `framework/init.lua`: isolated Neovim profile used only by the runner.

The required `smoke` suite contains native LSP, search/replacement, completion,
Python diagnostic presentation, and focus/fail-open checks. The `compatibility`
suite contains short nvim-cmp, blink.cmp, C/Clang-Tidy, and
Markdown/markdownlint checks.
The interactive category selector and short IDs such as `-TestId D3` can run
any task individually. The longer `plan.step` names remain accepted as
compatibility aliases. Result schema 4 records the exact short IDs on both the
selection and each result step, so a custom run remains resumable and
machine-checkable.

## Adding a test

Add a human step only when its expected outcome depends on real perception or
hardware. Every step must name a `manualReason` and related automated evidence.
If a protocol value, range, event order, provider result, or adapter state can
be asserted in code, add an automated regression test instead.

Every step has a globally unique, immutable two-character `testId`: `L` for
language intelligence, `C` for completion, `D` for diagnostics, or `S` for
session integration, followed by one uppercase alphanumeric character. Never
renumber or reuse a published ID. Every step belongs to one of the fixed
user-facing categories. Plans may
select only one of the fixed profiles implemented by `init.lua`.
They cannot contain PowerShell, shell, Lua, or Neovim commands. This keeps
versioned test data non-executable.

Every localized task uses one short paragraph for its purpose, sequentially
numbered action lines, and one short paragraph for its pass condition. The
validator rejects other line breaks, leaving display-width wrapping to Windows
Terminal.

After editing definitions, run:

```bash
python3 tests/human/framework/validate.py plans
python3 -m unittest tests/human/test_framework.py
```

The normal `tools/run_tests.py quick` run includes these checks.
