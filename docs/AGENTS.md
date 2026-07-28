# Documentation instructions

- German developer documentation is the technical source of truth. Update the English mirror in
  the same change and keep both languages structurally and factually consistent.
- Keep documentation accurate, understandable for its intended audience, internally consistent,
  precise, and ordered from overview to detail. Do not knowingly leave either language stale.
- Identify the audience before editing. User documentation is task-oriented and omits internal
  implementation detail that users do not need; developer documentation explains necessary
  context, reasoning, boundaries, and consequences without assuming expert prior knowledge.
- Keep the architecture understandable from a concise overview before presenting details. Update
  it whenever component ownership, data flow, trust boundaries, or lifecycle responsibilities
  change.
- Do not imply exhaustive testing or guaranteed support. State confirmed scope, open coverage,
  limitations, and best-effort maintenance precisely.
- In user documentation, name UI elements exactly as they appear in the localized interface;
  prefer translation catalogs over remembered wording.
- Preserve each document's target language. Project collaboration and publication text outside
  localized documentation is English.
- Prefer source code and tests over historical reports when describing current behavior.
- Treat plans and dated reports as context, not proof that a feature is implemented now.
- Prefer locally available source for NVDA, Neovim, terminal applications, or add-ons over web
  retrieval. Never copy private environment details into versioned documentation.
- Update relevant indexes, links, changelog entries, and release references with the content they
  describe.
- Build all six German and English HTML documents with `tools/build_documentation.sh` when
  documentation packaging or release output changes.
