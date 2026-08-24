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

The Linux checkout is the development source of truth. Tests and documentation
validation there use automatically discarded output only:

```bash
python3 tools/run_tests.py all
bash tools/build_documentation.sh --test-only
```

`all` runs safe, SSH, and socket phases sequentially; the environment must
permit listeners and disposable Neovim processes. In restricted environments,
run `all-safe`, `ssh`, and `socket` separately as described by the [test
strategy](testing.md).

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

Normal development artifacts are created in the synchronized Windows worktree
with parameterless `build.cmd`. It requires a current Python 3, Git for Windows
with Bash, and an Internet connection. It installs pinned Python dependencies
temporarily. It uses an installed Pandoc from the compatible 3.1 series or
downloads the official Pandoc 3.1.11.1 Windows binary into the same temporary
area and verifies its SHA-256. An incompatible local version is neither used
nor changed. Branch, commit, and synchronization state are compared before
and after the build.

The Windows development and Linux release builds use the same isolated core.
It renders all eight documents, builds the add-on and documentation ZIP from
them, validates the exact expected names, and only then moves those two files
to `dist`. A concurrent source change stops publication of the files.

## Synchronized Windows worktree

`/nfs/src/neovim-access-link` is the persistent test and build worktree exposed
to Windows as an SMB drive. Configure it once from the Linux checkout:

```bash
python3 tools/windows_workspace_sync.py configure /nfs/src/neovim-access-link
```

Local Git hooks then transfer branch-ref changes in the background. Branch
creation, deletion, and switching, including non-fast-forward commit changes,
are mirrored. The target checkout uses a separate staging-ref namespace and
`--no-overwrite-ignore`. Synchronization changes only versioned files and Git
refs; ignored or otherwise untracked virtual environments, human-test state,
tool installations, and build output remain in place. A versioned target edit
or a name collision with an untracked file stops synchronization. Retry it
manually with:

```bash
python3 tools/windows_workspace_sync.py sync
```

Linked Linux worktrees of the same repository share one serialized queue. The
most recently triggering worktree selects the checked-out target branch while
all local branch refs are mirrored independently. Hooks and the worker run
from a branch-independent copy in the shared Git administration directory.
Run `configure` again after changing the synchronization tool or its hooks.

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
   change since the immediately preceding published release;
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

A GitHub pre-release is created from the authorized tag, uses an English
release description, and contains exactly the two assets listed below. Verify
the tag target, pre-release flag, asset names, and downloads on GitHub after
publication.

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
