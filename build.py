#!/usr/bin/env python3
"""Build development artifacts in the synchronized Windows workspace."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass

from tools import distribution_build

ROOT = pathlib.Path(__file__).resolve().parent
SYNC_STATE_DIRECTORY = "nal-windows-sync"
SYNC_MANAGED_MARKER = "nal-windows-sync-managed"
SYNC_STATUS_NAME = "nal-windows-sync-status.json"


@dataclass(frozen=True)
class WorkspaceSnapshot:
	branch: str
	commit: str
	managed: bool
	synchronization_token: str = ""


def _require_windows() -> None:
	if os.name != "nt":
		raise RuntimeError(
			"development artifacts are built on Windows; "
			"Linux release assets use tools/build_release.py"
		)


def _run_git(*arguments: str) -> str:
	completed = subprocess.run(
		("git", "-C", str(ROOT), *arguments),
		check=False,
		capture_output=True,
		text=True,
	)
	if completed.returncode != 0:
		detail = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
		raise RuntimeError(detail)
	return completed.stdout.strip()


def _workspace_snapshot() -> WorkspaceSnapshot:
	branch = _run_git("symbolic-ref", "--quiet", "--short", "HEAD")
	commit = _run_git("rev-parse", "--verify", "HEAD^{commit}")
	tracked_changes = _run_git("status", "--porcelain=v1", "--untracked-files=no")
	if tracked_changes:
		raise RuntimeError("the Windows workspace has changes to versioned files")
	state_directory = pathlib.Path(
		_run_git("rev-parse", "--path-format=absolute", "--git-path", SYNC_STATE_DIRECTORY)
	)
	marker = state_directory / SYNC_MANAGED_MARKER
	if not marker.is_file():
		raise RuntimeError("the Windows workspace is not managed by the Linux synchronization tool")
	status_path = state_directory / SYNC_STATUS_NAME
	try:
		status = json.loads(status_path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise RuntimeError(f"the Windows workspace synchronization status is unavailable: {error}") from error
	if not status.get("success"):
		raise RuntimeError(
			"the Windows workspace is not synchronized successfully: "
			f"{status.get('error') or 'unknown synchronization failure'}"
		)
	if status.get("branch") != branch or status.get("commit") != commit:
		raise RuntimeError("the Windows workspace branch or commit differs from its synchronization status")
	token = status.get("updatedAt")
	if not isinstance(token, str) or not token:
		raise RuntimeError("the Windows workspace synchronization status has no update token")
	return WorkspaceSnapshot(branch, commit, True, token)


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
		snapshot=_workspace_snapshot,
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
