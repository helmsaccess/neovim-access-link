#!/usr/bin/env python3
"""Build development artifacts from a local Windows Git checkout."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

from tools import distribution_build

ROOT = pathlib.Path(__file__).resolve().parent


def _require_windows() -> None:
	if os.name != "nt":
		raise RuntimeError(
			"development artifacts are built on Windows; "
			"Linux release assets use tools/build_release.py"
		)


def _find_bash() -> pathlib.Path:
	configured = os.environ.get("NAL_GIT_BASH")
	path_bash = shutil.which("bash")
	candidates = (
		pathlib.Path(configured) if configured else None,
		pathlib.Path(path_bash) if path_bash else None,
		pathlib.Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe",
	)
	for candidate in candidates:
		if candidate is not None and candidate.is_file():
			return candidate
	raise RuntimeError("Git for Windows Bash is required; install Git for Windows or set NAL_GIT_BASH")


def build() -> None:
	_require_windows()
	if len(sys.argv) != 1:
		raise RuntimeError("This Windows build entry point does not accept arguments")
	distribution_build.build_distributions(
		ROOT,
		bash=_find_bash(),
		snapshot=lambda: distribution_build.development_source_snapshot(ROOT),
		prepare_pandoc=distribution_build.prepare_windows_pandoc,
		temporary_prefix="windows-distributable-",
	)


def main() -> int:
	try:
		build()
	except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
		print(f"Build failed: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
