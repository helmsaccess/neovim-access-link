# Release, version, and build process

`buildVars.py` is the single maintained source for internal add-on ID, visible
product name, author, user-chosen product version and channel, branch-local
development build number, and NVDA compatibility values.

`store_version()` supplies only the normal numeric `MAJOR.MINOR.PATCH` product
version to the NVDA manifest and Store. `development_version()` adds a SemVer
pre-release identifier such as `0.89.0-dev.1` plus branch/commit metadata when
available. `artifact_version()` uses that traceable identifier for archive
names, embedded components, runtime diagnostics, and logs. The Store therefore
sees no internal build number.

`development_build = None` is reserved for a user-approved release; in that
case the artifact version also equals the normal product version. Coding agents
must not make that switch as an independent stability or release decision.

The visible product is “Neovim Access Link”, author Emanuel Helms
`<emanuel@helmsaccess.de>`. The stable
internal ID `nvimNvdaAccess` preserves installation and NVDA profile
compatibility. The current beta version is 0.90.0; overall product maturity
remains between alpha and beta.

The user controls product version and release channel. The coding agent
increments the development build number only within the current branch when
shipped content changes. Parallel branches have independent sequences and
remain distinguishable through branch/commit metadata. Stable tags,
releases, or product-version changes require explicit approval. Old `dist/`
artifacts are removed before a new user-testable build, and tests inspect the
actual resulting archive.

The unmodified GPL v2 license is included in both the add-on and the user
component package. See [Licensing and contributions](licensing-and-contributions.md)
for the project and contribution terms.
