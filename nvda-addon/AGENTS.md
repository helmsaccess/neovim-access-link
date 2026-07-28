# NVDA add-on instructions

- Follow NVDA's coding style for NVDA-facing Python: UTF-8, LF, tabs for indentation,
  110 columns, and Ruff configuration from `pyproject.toml`. Never hand-align indentation with
  spaces.
- Preserve NVDA callback and API names. Add a concise `# Translators:` comment immediately before
  translatable user-facing text, and use type annotations consistently with the surrounding NVDA
  interface.
- Python components with an established different style keep it; otherwise use the NVDA style.
- Prefer stable public NVDA APIs. Use an existing public NVDA Windows wrapper where suitable,
  otherwise use `winBindings`; never define parallel Windows DLL bindings.
- Use the narrowest NVDA scope and permissions that preserve reliability. Prefer AppModule
  ownership and contextual registration over global hooks; keep the GlobalPlugin limited to
  behavior that genuinely requires process-wide lifetime.
- Keep application events, overlays, `nextHandler`, and contextual scripts in the corresponding
  AppModule. Shared services must not own or forward NVDA event chains.
- Assign settings, tools, scripts, and registrations by required scope and lifetime: contextual
  behavior belongs to the AppModule; only genuinely process-wide behavior belongs to the minimal
  GlobalPlugin.
- Keep shared implementation behind narrow service interfaces. Registrations and shared
  references must be symmetric, reload-safe, and released before teardown.
- Outside an authenticated, focus-confirmed supported terminal session, preserve native NVDA,
  application, keyboard, speech, and Braille behavior. Errors and teardown must restore that
  behavior immediately.
- Any broader global hook requires explicit architectural justification and fail-open tests.
- Document private NVDA API usage in an ADR before release.
- Run `ruff check .` and `ruff format --check .` for NVDA-facing Python changes.
- Run relevant add-on unit tests and package tests through `python3 tools/run_tests.py`.
- Packaging tests must validate the built add-on rather than only the source tree.
