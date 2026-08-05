# Release, version, and build process

## Central metadata

`buildVars.py` is the single maintained source for product identity and
version data. It contains:

- internal add-on identifier and visible product name;
- author, numeric product version, and release channel;
- branch-local development build number;
- minimum and last-tested NVDA versions.

`store_version()` returns only `MAJOR.MINOR.PATCH` for the manifest and NVDA
Add-on Store. For development states, `artifact_version()` adds `-dev.N` and,
when available, branch and commit metadata for filenames, diagnostic reports,
and bundled components. The installed manifest is generated from these values
during the build and is not maintained separately.

## Development states

`development_build` is a positive integer on feature branches. The first
changed installable state on a new branch uses `1`; later installable changes
increase it within that branch. An unchanged reproducible build may reuse the
same value.

`development_build = None` identifies only an explicitly approved release
state. Product version, channel, tag, and pre-release status are not inferred
from branch name or prior history.

## Validation and build

Before a distributable build, validate the final worktree:

```bash
python3 tools/run_tests.py all
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
```

`all` runs safe, SSH, and socket phases sequentially; the environment must
permit listeners and disposable Neovim processes. In restricted environments,
run `all-safe`, `ssh`, and `socket` separately as described by the [test
strategy](testing.md).

The add-on build validates the manifest, bundled components, dependencies, and
archive contents. The documentation build synchronizes executable examples,
checks Markdown and HTML links, German/English structure, and each output's
language, title, and description, and creates eight HTML documents.

## Release preparation

An approved version requires one coherent state containing:

1. product version, channel, and `development_build = None` in `buildVars.py`;
2. current release and changelog links in `README.md` plus German and English
   changelog sections;
3. current status, compatible metadata, and complete German/English
   documentation;
4. successful full tests and freshly built artifacts;
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
