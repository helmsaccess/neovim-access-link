#!/usr/bin/env python3
"""Mirror committed Git state into a persistent Windows test worktree."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTE_NAME = "windows-workspace"
SYNC_REF_PREFIX = "refs/nal-sync/heads"
STATE_DIRECTORY_NAME = "nal-windows-sync"
TARGET_MANAGED_MARKER = "nal-windows-sync-managed"
TARGET_STATUS_NAME = "nal-windows-sync-status.json"
RUNTIME_DIRECTORY_NAME = "runtime"


class WorkspaceSyncError(RuntimeError):
	"""A safe workspace synchronization could not be completed."""


def _git_environment() -> dict[str, str]:
	environment = os.environ.copy()
	try:
		names = subprocess.run(
			("git", "rev-parse", "--local-env-vars"),
			cwd=ROOT,
			check=True,
			capture_output=True,
			text=True,
		).stdout.splitlines()
	except (OSError, subprocess.CalledProcessError):
		names = ()
	for name in names:
		environment.pop(name, None)
	return environment


def _run_git(
	repository: Path,
	*arguments: str,
	input_text: str | None = None,
	check: bool = True,
) -> subprocess.CompletedProcess[str]:
	try:
		completed = subprocess.run(
			("git", "-C", str(repository), *arguments),
			check=False,
			capture_output=True,
			text=True,
			input=input_text,
			env=_git_environment(),
		)
	except OSError as error:
		raise WorkspaceSyncError(f"cannot run Git: {error}") from error
	if check and completed.returncode != 0:
		detail = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
		raise WorkspaceSyncError(detail)
	return completed


def _git_path(repository: Path, name: str) -> Path:
	value = _run_git(repository, "rev-parse", "--path-format=absolute", "--git-path", name).stdout
	return Path(value.strip())


def _common_git_directory(repository: Path) -> Path:
	value = _run_git(
		repository,
		"rev-parse",
		"--path-format=absolute",
		"--git-common-dir",
	).stdout
	return Path(value.strip()).resolve()


def _repository_root(path: Path) -> Path:
	value = _run_git(path, "rev-parse", "--show-toplevel").stdout.strip()
	return Path(value).resolve()


def _ensure_trusted_directories(source: Path, directories: tuple[Path, ...]) -> None:
	existing = _run_git(source, "config", "--global", "--get-all", "safe.directory", check=False)
	trusted = set(existing.stdout.splitlines()) if existing.returncode == 0 else set()
	for directory in directories:
		value = str(directory)
		if value not in trusted:
			_run_git(source, "config", "--global", "--add", "safe.directory", value)
			trusted.add(value)


def _current_branch(repository: Path) -> str:
	result = _run_git(repository, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
	if result.returncode != 0 or not result.stdout.strip():
		raise WorkspaceSyncError("the source repository must have a branch checked out")
	return result.stdout.strip()


def _head_commit(repository: Path) -> str:
	return _run_git(repository, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()


def _tracked_changes(repository: Path) -> tuple[str, ...]:
	output = _run_git(
		repository,
		"status",
		"--porcelain=v1",
		"--untracked-files=no",
	).stdout
	return tuple(line for line in output.splitlines() if line)


def _heads(repository: Path, prefix: str = "refs/heads") -> dict[str, str]:
	output = _run_git(
		repository,
		"for-each-ref",
		"--format=%(refname) %(objectname)",
		f"{prefix}/",
	).stdout
	result: dict[str, str] = {}
	prefix_with_slash = f"{prefix}/"
	for line in output.splitlines():
		ref_name, object_name = line.split(" ", 1)
		if not ref_name.startswith(prefix_with_slash):
			raise WorkspaceSyncError(f"unexpected Git reference: {ref_name}")
		result[ref_name.removeprefix(prefix_with_slash)] = object_name
	return result


def _remote_target(source: Path, remote_name: str) -> Path:
	value = _run_git(source, "config", "--get", f"remote.{remote_name}.url", check=False)
	if value.returncode != 0 or not value.stdout.strip():
		raise WorkspaceSyncError(
			f"Git remote {remote_name!r} is not configured; run the configure command first"
		)
	target = Path(value.stdout.strip()).expanduser()
	if not target.is_absolute():
		target = source / target
	return target.resolve()


def _write_json(path: Path, value: dict[str, object]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
	temporary.write_text(
		json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	temporary.replace(path)


def _status(branch: str, commit: str, *, success: bool, error: str = "") -> dict[str, object]:
	return {
		"branch": branch,
		"commit": commit,
		"error": error,
		"schemaVersion": 1,
		"success": success,
		"updatedAt": dt.datetime.now(dt.UTC).isoformat(),
	}


def _update_target_heads(target: Path, source_heads: dict[str, str]) -> None:
	target_heads = _heads(target)
	commands: list[str] = ["start"]
	for branch, object_name in sorted(source_heads.items()):
		commands.append(f"update refs/heads/{branch} {object_name}")
	for branch in sorted(target_heads.keys() - source_heads.keys()):
		commands.append(f"delete refs/heads/{branch} {target_heads[branch]}")
	commands.extend(("prepare", "commit", ""))
	_run_git(target, "update-ref", "--stdin", input_text="\n".join(commands))


def synchronize(source: Path = ROOT, remote_name: str = REMOTE_NAME) -> dict[str, object]:
	"""Synchronize committed branches and the selected branch into the Windows worktree."""
	source = _repository_root(source)
	branch = _current_branch(source)
	commit = _head_commit(source)
	target = _remote_target(source, remote_name)
	target_state_directory = _git_path(target, STATE_DIRECTORY_NAME)
	target_status = target_state_directory / TARGET_STATUS_NAME
	try:
		target_changes = _tracked_changes(target)
		if target_changes:
			preview = ", ".join(target_changes[:5])
			raise WorkspaceSyncError(
				"the Windows workspace has changes to versioned files; "
				f"synchronization was refused ({preview})"
			)
		_write_json(
			target_status,
			_status(branch, commit, success=False, error="synchronization in progress"),
		)
		source_heads = _heads(source)
		_run_git(
			source,
			"push",
			"--atomic",
			"--porcelain",
			"--prune",
			remote_name,
			f"+refs/heads/*:{SYNC_REF_PREFIX}/*",
		)
		sync_heads = _heads(target, SYNC_REF_PREFIX)
		if sync_heads != source_heads:
			raise WorkspaceSyncError("the staged NFS branch references differ from the source")
		if branch not in sync_heads or sync_heads[branch] != commit:
			raise WorkspaceSyncError("the selected branch was not staged at the expected commit")

		desired_ref = f"{SYNC_REF_PREFIX}/{branch}"
		_run_git(
			target,
			"switch",
			"--detach",
			"--no-overwrite-ignore",
			"--no-recurse-submodules",
			desired_ref,
		)
		_update_target_heads(target, source_heads)
		_run_git(
			target,
			"switch",
			"--no-guess",
			"--no-overwrite-ignore",
			"--no-recurse-submodules",
			branch,
		)
		if _current_branch(target) != branch or _head_commit(target) != commit:
			raise WorkspaceSyncError("the Windows workspace did not reach the requested branch and commit")
		if _tracked_changes(target):
			raise WorkspaceSyncError("the Windows workspace is not clean after synchronization")
		status = _status(branch, commit, success=True)
		_write_json(target_status, status)
		return status
	except WorkspaceSyncError as error:
		with contextlib.suppress(OSError, WorkspaceSyncError):
			_write_json(target_status, _status(branch, commit, success=False, error=str(error)))
		raise


def _state_directory(source: Path) -> Path:
	return _common_git_directory(source) / STATE_DIRECTORY_NAME


def _install_runtime(source: Path) -> Path:
	state_directory = _state_directory(source)
	runtime = state_directory / RUNTIME_DIRECTORY_NAME
	hooks = runtime / ".githooks"
	tools = runtime / "tools"
	hooks.mkdir(parents=True, exist_ok=True)
	tools.mkdir(parents=True, exist_ok=True)
	for name in ("post-checkout", "reference-transaction"):
		shutil.copy2(ROOT / ".githooks" / name, hooks / name)
	shutil.copy2(Path(__file__).resolve(), tools / Path(__file__).name)
	return hooks


def request_synchronization(source: Path = ROOT, reason: str = "manual") -> Path:
	"""Record the latest requested state and start one coalescing worker."""
	source = _repository_root(source)
	state_directory = _state_directory(source)
	request_path = state_directory / "request.json"
	_write_json(
		request_path,
		{
			"reason": reason,
			"requestedAt": dt.datetime.now(dt.UTC).isoformat(),
			"requestId": uuid.uuid4().hex,
			"source": str(source),
		},
	)
	if os.environ.get("NAL_WINDOWS_SYNC_NO_SPAWN") == "1":
		return request_path
	log_path = state_directory / "worker.log"
	with log_path.open("a", encoding="utf-8") as log:
		subprocess.Popen(
			(sys.executable, str(Path(__file__).resolve()), "worker", "--source", str(source)),
			cwd=source,
			env=_git_environment(),
			stdin=subprocess.DEVNULL,
			stdout=log,
			stderr=subprocess.STDOUT,
			start_new_session=True,
			close_fds=True,
		)
	return request_path


def run_worker(source: Path = ROOT) -> bool:
	"""Run serialized synchronization until no newer request remains."""
	source = _repository_root(source)
	state_directory = _state_directory(source)
	state_directory.mkdir(parents=True, exist_ok=True)
	request_path = state_directory / "request.json"
	lock_path = state_directory / "worker.lock"
	local_status = state_directory / "status.json"
	with lock_path.open("a+", encoding="utf-8") as lock:
		try:
			fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
		except BlockingIOError:
			return False
		while request_path.exists():
			try:
				request = json.loads(request_path.read_text(encoding="utf-8"))
				request_id = request["requestId"]
				requested_source = _repository_root(Path(request["source"]))
			except (OSError, KeyError, json.JSONDecodeError, WorkspaceSyncError) as error:
				_write_json(local_status, _status("", "", success=False, error=str(error)))
				return False
			try:
				time.sleep(0.1)
				result = synchronize(requested_source)
			except WorkspaceSyncError as error:
				try:
					current_id = json.loads(request_path.read_text(encoding="utf-8"))["requestId"]
				except (OSError, KeyError, json.JSONDecodeError):
					current_id = request_id
				if current_id != request_id:
					continue
				branch = ""
				commit = ""
				with contextlib.suppress(WorkspaceSyncError):
					branch = _current_branch(requested_source)
					commit = _head_commit(requested_source)
				_write_json(local_status, _status(branch, commit, success=False, error=str(error)))
				return False
			_write_json(local_status, result)
			try:
				current_id = json.loads(request_path.read_text(encoding="utf-8"))["requestId"]
			except (OSError, KeyError, json.JSONDecodeError):
				continue
			if current_id == request_id:
				request_path.unlink(missing_ok=True)
		return True


def configure(source: Path, target: Path, *, trust_target: bool = True) -> dict[str, object]:
	"""Configure the source checkout and prepare the persistent target worktree."""
	source = _repository_root(source)
	target = target.expanduser().resolve()
	if source == target:
		raise WorkspaceSyncError("source and Windows workspace must be different repositories")
	expected_hooks = _state_directory(source) / RUNTIME_DIRECTORY_NAME / ".githooks"
	existing_hooks = _run_git(source, "config", "--get", "core.hooksPath", check=False)
	allowed_hooks = {"", ".githooks", str(source / ".githooks"), str(expected_hooks)}
	if existing_hooks.returncode == 0 and existing_hooks.stdout.strip() not in allowed_hooks:
		raise WorkspaceSyncError(
			"core.hooksPath is already configured; preserve or migrate those hooks before enabling sync"
		)
	existing_remote = _run_git(
		source,
		"config",
		"--get",
		f"remote.{REMOTE_NAME}.url",
		check=False,
	)
	if (
		existing_remote.returncode == 0
		and existing_remote.stdout.strip()
		and Path(existing_remote.stdout.strip()).expanduser().resolve() != target
	):
		raise WorkspaceSyncError(f"Git remote {REMOTE_NAME!r} already points to a different location")
	if trust_target:
		_ensure_trusted_directories(source, (target,))
	target = _repository_root(target)
	if trust_target:
		# Local receive-pack resolves the non-bare remote to its Git directory and
		# applies the ownership check to that path independently of the worktree.
		_ensure_trusted_directories(source, (_common_git_directory(target),))
	marker = _git_path(target, STATE_DIRECTORY_NAME) / TARGET_MANAGED_MARKER
	source_identity = str(_common_git_directory(source))
	if marker.is_file():
		try:
			owner = json.loads(marker.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError) as error:
			raise WorkspaceSyncError(
				f"the Windows workspace ownership marker is invalid: {error}"
			) from error
		if owner.get("sourceGitDirectory") != source_identity:
			raise WorkspaceSyncError(
				"the Windows workspace is already managed by a different source repository"
			)
	_run_git(target, "config", "core.filemode", "false")
	_run_git(source, "config", f"remote.{REMOTE_NAME}.url", str(target))
	_run_git(
		source,
		"config",
		"--replace-all",
		f"remote.{REMOTE_NAME}.push",
		f"+refs/heads/*:{SYNC_REF_PREFIX}/*",
	)
	result = synchronize(source)
	hooks = _install_runtime(source)
	_run_git(source, "config", "nal.windowsWorkspaceEnabled", "true")
	_run_git(source, "config", "core.hooksPath", str(hooks))
	marker.parent.mkdir(parents=True, exist_ok=True)
	_write_json(
		marker,
		{
			"schemaVersion": 1,
			"sourceGitDirectory": source_identity,
		},
	)
	return result


def _enabled(source: Path) -> bool:
	value = _run_git(source, "config", "--bool", "--get", "nal.windowsWorkspaceEnabled", check=False)
	return value.returncode == 0 and value.stdout.strip() == "true"


def _parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description=__doc__)
	subparsers = parser.add_subparsers(dest="command", required=True)
	configure_parser = subparsers.add_parser("configure")
	configure_parser.add_argument("target", type=Path)
	configure_parser.add_argument("--source", type=Path, default=ROOT)
	configure_parser.add_argument("--no-trust-target", action="store_true", help=argparse.SUPPRESS)
	sync_parser = subparsers.add_parser("sync")
	sync_parser.add_argument("--source", type=Path, default=ROOT)
	request_parser = subparsers.add_parser("request")
	request_parser.add_argument("--source", type=Path, default=ROOT)
	request_parser.add_argument("--reason", default="manual")
	worker_parser = subparsers.add_parser("worker")
	worker_parser.add_argument("--source", type=Path, default=ROOT)
	return parser


def main(arguments: tuple[str, ...] | None = None) -> int:
	parsed = _parser().parse_args(arguments)
	try:
		if parsed.command == "configure":
			result = configure(parsed.source, parsed.target, trust_target=not parsed.no_trust_target)
		elif parsed.command == "sync":
			result = synchronize(parsed.source)
		elif parsed.command == "request":
			source = _repository_root(parsed.source)
			if not _enabled(source):
				return 0
			request_synchronization(source, parsed.reason)
			return 0
		else:
			return 0 if run_worker(parsed.source) else 1
	except WorkspaceSyncError as error:
		print(f"Windows workspace synchronization failed: {error}", file=sys.stderr)
		return 1
	print(f"Windows workspace synchronized: {result['branch']} at {result['commit']}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
