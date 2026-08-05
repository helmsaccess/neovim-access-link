# Documentation instructions

- German developer documentation is the technical source of truth. Update the English mirror in
  the same change with the same structure, task order, claims, support levels, and limitations.
- Keep documentation accurate, understandable for its intended audience, internally consistent,
  precise, and ordered from overview to detail. Do not knowingly leave either language stale.
- Give every document a defined reader and purpose. Quick guides follow the shortest verified
  path to first success; manuals put common tasks before settings and reference; developer
  documentation introduces an overview before context, boundaries, reasoning, and detail.
- Define only terms the reader needs. In user documentation, distinguish `NVDA+...` gestures as
  contextual screen-reader commands from keys without NVDA as Neovim or application commands
  whose effects the add-on presents accessibly. State simultaneous and sequential input clearly.
- Do not copy prompts, user-to-agent instructions, conversation history, or temporary working
  directions into documentation. Include a decision or process rule only when it has independent
  value for the document's audience; otherwise keep it in `AGENTS.md`, an issue, a commit, or
  `/nfs/src/nal-tmp/`.
- Keep the architecture understandable from a concise overview before presenting details. Update
  it whenever component ownership, data flow, trust boundaries, or lifecycle responsibilities
  change.
- Do not imply exhaustive testing or guaranteed support. Distinguish practical confirmation,
  automated coverage, and unconfirmed scope; state limitations and best-effort maintenance
  precisely.
- In user documentation, name UI elements exactly as they appear in the localized interface;
  prefer translation catalogs over remembered wording.
- Preserve each document's target language. Project collaboration and publication text outside
  localized documentation is English.
- Prefer source code and tests over historical reports when describing current behavior.
- Treat plans and dated reports as context, not proof that a feature is implemented now.
- Prefer locally available source for NVDA, Neovim, terminal applications, or add-ons over web
  retrieval. Never copy private environment details into versioned documentation.
- Changes to behavior, support, architecture, compatibility, developer workflows, or release
  state update both languages of `development/current-status.md` and
  `development/changelog.md` in the same change. Status is the current snapshot, changelog is
  completed history, and `plan.md` is future work; do not manually repeat volatile generated
  build metadata.
- Update relevant indexes and release references, and validate both Markdown source links and
  generated HTML links. Keep one real H1 per source; fenced examples do not count as headings.
- Build all eight German and English HTML documents with `tools/build_documentation.sh` when
  documentation packaging or release output changes.
