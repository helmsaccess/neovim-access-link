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
the German changelog. For a release, `manifest_changelog()` combines every
version section after `manifest_changelog_base_version` through the current
version. The Store manifest therefore describes the exact upgrade from the
last version published there; update the base after an actual Store
publication when preparing the next release.

Development states collect completed changes under `Unveröffentlicht` and
`Unreleased`; their manifests use that section. When a release is set, those
entries are curated into the new German and English version sections. Each
section describes only changes since the immediately preceding published
version, after which the unreleased sections remain empty for the next
development line. The build selects the section but never edits a changelog
source.

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

The successful build changes no versioned file. Tag exactly its `HEAD` as
`vMAJOR.MINOR.PATCH`, push the commit and tag after approval, and publish the
two files from the Linux `dist` with `gh release create --verify-tag`.
`build.cmd` is not the release origin; it produces the corresponding versioned
development artifacts for prior practical Windows validation.

## Release preparation

An approved version requires one coherent state containing:

1. product version, manifest update channel,
   `manifest_changelog_base_version`, and `development_build = None` in
   `buildVars.py`;
2. current release and changelog links in `README.md` plus German and English
   version sections curated from the unreleased entries and containing every
   change since the immediately preceding published release, with the unreleased section reset;
3. current status, compatible metadata, and complete German/English
   documentation;
4. successful full tests and artifacts freshly built from this Linux state
   with `tools/build_release.py`;
5. one commit and an annotated or lightweight `vMAJOR.MINOR.PATCH` tag on that
   exact commit.

Push, tag, and GitHub publication require explicit approval. Before tagging,
verify that the worktree, version, README links, and artifact names agree.

## Stop conditions

Stop before tagging or publication when tests or builds fail, the worktree
contains unexpected changes, version and links disagree, an artifact was not
built from the tagged revision, or a required practical check remains open. Do
not silently move an existing tag. After the user's decision, a correction
gets a new product version or an explicitly rebuilt tag that has not been
published.

## GitHub and Add-on Store

After explicit approval, build the prepared release commit on clean Linux
`main` and push the commit and its existing tag to GitHub first. Before
publication, verify the built base and localized manifests against the current
official NVDA AddonTemplate. Every applicable field must contain a valid
value. Write English notes covering changes since the previous published
version, compatibility and testing limits, tag-pinned documentation links,
and the purpose of both downloads. Keep the temporary file under `../nal-aux/`.

```bash
gh release create "v<VERSION>" "dist/NeovimAccessLink-<VERSION>.nvda-addon" \
  "dist/neovim-access-link-<VERSION>-documentation.zip" \
  --repo helmsaccess/neovim-access-link --verify-tag --fail-on-no-commits \
  --title "Neovim Access Link <VERSION>" --notes-file "<RELEASE_NOTES_FILE>" <STATUS_FLAGS>
```

Use `--prerelease --latest=false` below 1.0.0 and `--latest` from 1.0.0.
The add-on embeds the server package. After publication, verify the tag
target, title, draft, prerelease and latest status, notes, exact two asset
names, and successful downloads.

Submission to the NVDA Add-on Store is a separate operation in the add-on
datastore. It points to an already published, immutable revision and follows
the datastore's current submission checks. Do not replace its tag or assets
after a store submission; publish a new product version for a correction.

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
