# Contributing to Neovim Access Link

Thank you for considering a contribution. Please discuss substantial features,
protocol changes, new dependencies, or additional terminal front ends before
implementation. Bug fixes should include a regression test. Follow
`AGENTS.md`, the architecture documents, and the test strategy.

## Contribution workflow

1. Create a focused branch from the current default branch.
2. Keep unrelated cleanup out of the change.
3. Add or update tests and German and English documentation as appropriate.
4. Run the relevant Python, Lua, packaging, and documentation checks from
   `docs/en/development/testing.md`.
5. Open a pull request describing behavior, risks, tests, and known limits.

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
