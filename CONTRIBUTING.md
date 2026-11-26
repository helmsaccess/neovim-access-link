# Contributing to Neovim Access Link

Thank you for considering a contribution. Please discuss substantial features,
protocol changes, new dependencies, or additional terminal front ends before
implementation. Bug fixes should include a regression test. Follow
the root `AGENTS.md`, any more specific `AGENTS.md` in the component being
changed, the architecture documents, and the test strategy.

## Contribution workflow

1. Create a focused working branch from current `main`. Keep unrelated
   cleanup out of the diff and use English for commits and pull requests.
2. Add the relevant tests and update the German and English documentation
   and changelogs. Follow the [version and release guide](docs/en/development/release-and-build.md)
   for release preparation.
3. Review your own diff and run the relevant [checks](docs/en/development/testing.md).
   Run the `ssh` and `socket` groups separately when applicable.
4. Push the working branch and open a GitHub pull request targeting `main`.
   Keep it focused and explain the problem, the change, test results, and
   specific risks or gaps. Link related issues and use a draft while work is incomplete.
5. Address blocking feedback and resolve review discussions. Before merging,
   all required CI checks must pass. Ask for an independent review when an
   eligible reviewer is available, and always follow the repository's configured approvals.

Every change to `main`, including a documentation fix, hotfix, or release
preparation, goes through a pull request. Direct pushes to `main` are
prohibited. Maintainer approval is required to merge. Prefer squash merge
for incremental commits that form one change. Preserve individually
reviewable commits when they carry useful standalone history.

For maintainers, use a [GitHub ruleset](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
or [branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
on `main` to require a pull request, resolved conversations, and the checks
that run on every PR. Block force pushes and deletion and apply the PR rule
to administrators. Require an independent approval once the project has a
second eligible reviewer. Keep path-filtered jobs out of the global required
check list unless a check always reports a result.

Do not submit passwords, tokens, private editor text, real infrastructure
names, personal diagnostic paths, or artifacts from ignored `tmp/`.

## License and contribution agreement

The project is distributed under the GNU General Public License version 2 only
(`GPL-2.0-only`). By submitting a contribution, you certify that you have the
right to submit it and agree that it may be distributed as part of this project
under GPL-2.0-only.

In addition, by submitting a contribution, you grant Emanuel Helms
<emanuel@helmsaccess.de> a
perpetual, worldwide, non-exclusive, royalty-free, irrevocable license to use,
reproduce, modify, prepare derivative works of, publicly display, publicly
perform, distribute, sublicense, and relicense your contribution, in source or
binary form, under GPL-2.0-only or under other license terms. This permits the
project to publish contributed code additionally under another license in the
future. It does not revoke GPL rights already granted for an existing release,
and you retain copyright in your contribution.

You also grant a perpetual, worldwide, non-exclusive, royalty-free,
irrevocable patent license for patent claims you can license that are
necessarily infringed by your contribution alone or in combination with the
project version to which it was submitted.

Submitting a pull request or other contribution constitutes acceptance of
these contribution terms. If you cannot agree, do not submit the contribution.
This policy is legally significant; prospective organizational contributors
should obtain any employer approval they require.
