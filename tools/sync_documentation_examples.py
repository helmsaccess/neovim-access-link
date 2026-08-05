#!/usr/bin/env python3
"""Synchronize executable examples into GitHub-renderable Markdown blocks."""

from __future__ import annotations

import argparse
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY_ROOT / "examples/neovim-lazy-python/init.lua"
TARGETS = (
	REPOSITORY_ROOT / "docs/de/manual/example-configuration.md",
	REPOSITORY_ROOT / "docs/en/manual/example-configuration.md",
)
START_MARKER = "<!-- BEGIN lazy-python-example -->"
END_MARKER = "<!-- END lazy-python-example -->"


def _render_block() -> str:
	source = SOURCE.read_text(encoding="utf-8").rstrip("\n")
	return f"{START_MARKER}\n```lua\n{source}\n```\n{END_MARKER}"


def _synchronize(path: Path, *, write: bool) -> bool:
	content = path.read_text(encoding="utf-8")
	if content.count(START_MARKER) != 1 or content.count(END_MARKER) != 1:
		raise RuntimeError(f"expected exactly one example marker pair in {path}")
	prefix, remainder = content.split(START_MARKER, 1)
	_, suffix = remainder.split(END_MARKER, 1)
	expected = f"{prefix}{_render_block()}{suffix}"
	if expected == content:
		return False
	if write:
		path.write_text(expected, encoding="utf-8")
	return True


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	mode = parser.add_mutually_exclusive_group(required=True)
	mode.add_argument("--check", action="store_true", help="fail when Markdown is stale")
	mode.add_argument("--write", action="store_true", help="update the committed Markdown blocks")
	args = parser.parse_args()

	stale = []
	for target in TARGETS:
		if _synchronize(target, write=args.write):
			stale.append(target.relative_to(REPOSITORY_ROOT))

	if args.check and stale:
		for path in stale:
			print(f"stale generated example: {path}")
		print("run: python3 tools/sync_documentation_examples.py --write")
		return 1
	if args.write:
		for path in stale:
			print(f"updated {path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
