# Release, version, and build process

`buildVars.py` is the single maintained source for internal add-on ID, visible
product name, author, explicitly selected product version and channel,
branch-local development build number, and NVDA compatibility values.

`store_version()` supplies only the normal numeric `MAJOR.MINOR.PATCH` product
version to the NVDA manifest and Store. `development_version()` adds a SemVer
pre-release identifier such as `1.2.3-dev.1` plus branch/commit metadata when
available. `artifact_version()` uses that traceable identifier for archive
names, embedded components, runtime diagnostics, and logs. The Store therefore
sees no internal build number.

`development_build = None` is reserved for an explicitly approved release
state; in that case the artifact version also equals the normal product
version. It must not be inferred from the branch name, build environment, or
previous version history.

The visible product is “Neovim Access Link”, author Emanuel Helms
`<emanuel@helmsaccess.de>`. The internal ID is `NeovimAccessLink`. Its change
from the former `nvimNvdaAccess` ID is an intentional clean break: uninstall
the old add-on and restart NVDA before testing a new build. Settings, profiles,
and gesture assignments stored under the old ID are not imported. The
current product version, release channel, and product maturity are read from
`buildVars.py`.

Product version and release channel are explicit release decisions rather than
derived values. The development build number increases only within the current
branch when shipped content changes. Parallel branches have independent
sequences and remain distinguishable through branch/commit metadata. Stable
tags, releases, or product-version changes require explicit approval. Old
`dist/` artifacts are removed before a new testable build, and tests inspect
the actual resulting archive.

`tools/build_documentation.sh` builds the German and English quick guide, user
manual, developer documentation, and separate guided-practical-test guide. The
build explicitly verifies that both user manuals contain their Braille chapter
and both tester guides contain their expected main section. It bundles all
eight HTML files in exactly one versioned documentation ZIP under `dist/`.

The unmodified GPL v2 license is included in both the add-on and the user
component package. See [Licensing and contributions](licensing-and-contributions.md)
for the project and contribution terms.
