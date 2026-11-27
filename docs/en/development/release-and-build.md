# Release, version, and build process

## Central metadata

`buildVars.py` is the single maintained source for product identity and
version data. It contains:

- internal add-on identifier and visible product name;
- author, numeric product version, and manifest update channel;
- branch-local development build number;
- comparison version last published in the NVDA Add-on Store;
- minimum and last-tested NVDA versions;
- project URL, default help file, and English manifest changelog.
- source URL, license identifier, and license URL for the NVDA Add-on Store.

`store_version()` returns only `MAJOR.MINOR.PATCH` for the manifest and NVDA
Add-on Store. For development states, `artifact_version()` adds `-dev.N` and,
when available, branch and commit metadata for filenames, diagnostic reports,
and bundled components. The installed manifest is generated from these values
and the matching changelog sections during the build and is not maintained
separately. The German localization manifest receives the same sections from
the German changelog. For releases, `manifest_changelog()` combines the sections after
`manifest_changelog_base_version` through the current version. Verify that
baseline against the actual Store version from which the intended audience
upgrades. For stable releases, use the preceding stable Store version even
if a newer beta exists. For the first stable release, choose the oldest
published predecessor covered by the intended upgrade path. Include relevant
changes from intermediate betas and GitHub-only releases.

## Version and changelog policy

Use [SemVer](https://semver.org/spec/v2.0.0.html) for product versions. PATCH
covers compatible fixes and MINOR covers compatible features and
deprecations. From 1.0.0, MAJOR covers breaks in promised compatibility,
including supported platforms, durable settings and the protocol between
separately upgradable components. Before 1.0.0, use MINOR for deliberate
compatibility breaks and explain them in the release notes. Define the
supported versions and upgrade behavior before approving 1.0.0.

The user approves the product version and channel. Reserve a unique numeric
version across channels and check Git tags, GitHub releases and NVDA Store
entries before release. [NVDA Store version and channel rules](https://github.com/nvaccess/addon-datastore/blob/master/docs/design/jsonMetadata.md)

Record notable changes in both changelogs under `Unveröffentlicht` and
`Unreleased` in the same change. Explain their effects and group entries
where useful under Added, Changed, Deprecated, Removed, Fixed and Security.
For a release, curate the changes since the preceding release on the same
line under `## [X.Y.Z] - YYYY-MM-DD`, link the version to its tag and reset
both unreleased sections. An empty unreleased section produces a localized
placeholder in development manifests. [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## Development states

`development_build` is a positive integer on feature branches. The first
changed installable state on a new branch uses `1`; later installable changes
increase it within that branch. An unchanged reproducible build may reuse the
same value.

`development_build = None` identifies only an explicitly approved release
state. Product version, channel, tag, and pre-release status are not inferred
from branch name or prior history.

## Validation and build

Development uses the local Windows checkout. Linux also covers Unix sockets,
PTYs, and SSH targets. Tests and documentation validation use disposable output:

```bash
python3 tools/run_tests.py all
bash tools/build_documentation.sh --test-only
```

`all` runs safe, SSH, and socket phases sequentially; the environment must
permit listeners and disposable Neovim processes. In restricted environments,
run `all-safe`, `ssh`, and `socket` separately as described by the [test
strategy](testing.md).

The build follows the official NVDA AddonTemplate with `sconstruct`, separate
templates for the base and translated manifests, the `pot` target, and gettext
catalogs under `nvda-addon/addon/locale/`. Running `python -m SCons` directly
creates a test archive under `build/scons/` with the HTML files in the checkout.
`build.cmd` and the Linux release builder give SCons freshly rendered
documentation and keep their intermediate files isolated.
[NVDA AddonTemplate](https://github.com/nvdaaddons/AddonTemplate/tree/30318eae085fa81fe3a39045956c7a0516a0f981)

Package tests build the add-on in their temporary test directory and validate
the manifest, eight installed localized HTML
documents, bundled components, dependencies, and archive contents. The
manifest contract follows the official NVDA AddonTemplate field set: every
applicable field must be a trimmed scalar; unknown, empty, or malformed
metadata, missing default English help, and incomplete localization manifests
stop the build. A field may be omitted only when it is genuinely inapplicable
to the project. The temporary documentation check synchronizes executable examples,
checks Markdown and HTML links, German/English structure, and each output's
language, title, and description, and creates eight HTML documents.
Those files are deleted afterwards; CI does not publish or refresh end-user
artifacts.

Build development artifacts with parameterless `build.cmd` from a clean
local Windows branch with a development build number. The build uses Python 3,
Git Bash, and an Internet connection for the pinned Python dependencies.
Provide Git Bash via `PATH`, the default Git for Windows installation, or
`NAL_GIT_BASH`. The build uses an installed Pandoc 3.1.11.1 or
downloads the official Windows 3.1.11.1 binary temporarily and verifies its
SHA-256.

The Windows development build and Linux release build render all eight HTML
documents and package them through the same isolated core. They verify the
branch, commit, and cleanliness of tracked files before and after the build.
The add-on and documentation ZIP reach `dist` after these checks pass and
their names match. Use `git fetch origin` to compare with an existing repository.

## Linux release build

The final state that will be tagged and published on GitHub is built in the
Linux checkout. After complete validation, approval of release metadata, and
the merge to `main`, run:

```bash
python3 tools/build_release.py
```

The parameterless command accepts only a clean `main` worktree with
`development_build = None`. It downloads the official Pandoc 3.1.11.1 Linux
binary into temporary storage, verifies its SHA-256, and uses the same
temporary Python environment with pinned build dependencies as the Windows
entry point. Branch, commit, and versioned cleanliness are compared before
and after the build. Only the add-on and documentation ZIP from the unchanged
state reach `dist`; Pandoc, the environment, and intermediate output are then
removed.

In the Windows worktree the two files are named
`NeovimAccessLink-<artifact_version>.nvda-addon` and
`neovim-access-link-<artifact_version>-documentation.zip`. For a development
state, `<artifact_version>` contains `-dev.N` and, when available, branch and
commit metadata. The Linux release build instead uses the plain product
version, for example `NeovimAccessLink-0.99.0.nvda-addon`.

A successful build leaves tracked files unchanged. Use local Windows
development artifacts from `build.cmd` with isolated NVDA profiles.
The build suffix distinguishes packages and diagnostics. NVDA sees the
numeric manifest version, so upgrade tests need different numeric versions.

## Release preparation

1. Prepare the release in a GitHub pull request targeting `main`. Set the
   approved version, channel, Store baseline and `development_build = None`
   in `buildVars.py`. Set the NVDA API minimum to the supported minimum and
   the last-tested API according to successful tests. Stable releases need
   a stable NVDA API.
2. Finalize both changelogs, README release links, and the German and English
   status and compatibility pages. Merge only with approval and passing
   required checks.
3. Run the full tests and `python3 tools/build_release.py` on clean Linux
   `main` at the merged commit. Validate the base and localized manifests
   against the current NVDA AddonTemplate and verify both artifacts and
   the applicable install and upgrade paths.
4. After approval, create an annotated `vMAJOR.MINOR.PATCH` tag at exactly
   the built commit and push that tag. The commit reaches GitHub `main`
   through the pull request. Confirm the remote tag target before drafting
   the release.

Stop on failed checks, missing approval, a previously used version or a
mismatch between tag, manifests, links and assets. Keep published tags and
assets immutable. Package corrections receive a new version.

## GitHub and Add-on Store

After publication approval, create a draft against the existing tag. Derive
English notes from the changelog since the previous GitHub release on the
same line. Include compatibility, migration, verification limits and
tag-pinned documentation links. Keep the notes file under `../nal-aux/`.

```bash
gh release create "v<VERSION>" "dist/NeovimAccessLink-<VERSION>.nvda-addon" \
  "dist/neovim-access-link-<VERSION>-documentation.zip" \
  --repo helmsaccess/neovim-access-link --draft --verify-tag --fail-on-no-commits \
  --title "Neovim Access Link <VERSION>" --notes-file "<RELEASE_NOTES_FILE>" <STATUS_FLAGS>
```

Use `--prerelease --latest=false` for previews, `--latest` for the current
stable line and `--latest=false` for older stable maintenance releases.
Check the draft's tag, notes, file names and SHA-256 of both downloads before
publishing. Verify the public release afterward. Use
[immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
as repository protection.

Store submission requires separate approval. Use the direct HTTPS URL
and SHA-256 of the verified published add-on. Confirm the actual Store entry
before using it as a baseline. Experimental NVDA API versions require a
beta or dev Store channel. [NVDA Store submission guide](https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md)

## Publication artifacts

A GitHub publication contains exactly two downloadable files:

- `NeovimAccessLink-<version>.nvda-addon`;
- `neovim-access-link-<version>-documentation.zip` containing the Quick Guide,
  user manual, developer documentation, and guided practical tests in German
  and English.

Release notes summarize changes since the previous product version, state
important limits, and link a durable technical analysis when useful. Release
and collaboration text is English.

The unmodified GPL v2 license is included in the add-on and user component
package. See [licensing and contributions](licensing-and-contributions.md) and
[dependencies](dependencies.md) for more information.
