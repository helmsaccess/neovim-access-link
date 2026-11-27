"""Build the two release assets from a clean Linux main worktree."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from tools import distribution_build


def _find_bash() -> Path:
	bash = shutil.which("bash")
	if not bash:
		raise RuntimeError("bash is required for the Linux release build")
	return Path(bash)


def build() -> tuple[Path, ...]:
	if os.name != "posix":
		raise RuntimeError("release assets are built from the Linux release worktree")
	if len(sys.argv) != 1:
		raise RuntimeError("This Linux release build entry point does not accept arguments")
	return distribution_build.build_distributions(
		ROOT,
		bash=_find_bash(),
		snapshot=lambda: distribution_build.release_source_snapshot(ROOT),
		prepare_pandoc=distribution_build.prepare_linux_pandoc,
		temporary_prefix="linux-release-",
	)


def main() -> int:
	try:
		build()
	except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
		print(f"Release build failed: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
