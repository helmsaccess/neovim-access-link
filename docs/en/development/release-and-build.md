# Release, version, and build process

`buildVars.py` is the single maintained source for internal add-on ID, visible
product name, author, user-chosen product version and channel, agent-managed
build number, and NVDA compatibility values. Manifest, diagnostic version,
archive names, and embedded component version are derived from it.

The visible product is “Neovim Access Link”, author Emanuel Helms
`<emanuel@helmsaccess.de>`. The stable
internal ID `nvimNvdaAccess` preserves installation and NVDA profile
compatibility. The current numeric beta build is 0.89.16.

The user controls product version and release channel. The coding agent
increments only the build number when shipped content changes. Stable tags,
releases, or product-version changes require explicit approval. Old `dist/`
artifacts are removed before a new user-testable build, and tests inspect the
actual resulting archive.

The unmodified GPL v2 license is included in both the add-on and the user
component package. See [Licensing and contributions](licensing-and-contributions.md)
for the project and contribution terms.
