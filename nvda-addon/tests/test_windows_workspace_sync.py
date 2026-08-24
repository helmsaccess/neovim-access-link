from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tools import windows_workspace_sync as workspace_sync


def run_git(repository: Path, *arguments: str) -> str:
	return subprocess.run(
		("git", "-C", str(repository), *arguments),
		check=True,
		capture_output=True,
		text=True,
	).stdout.strip()


def write(path: Path, content: str) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(content, encoding="utf-8")


class WindowsWorkspaceSyncTests(unittest.TestCase):
	def setUp(self) -> None:
		self.temporary = tempfile.TemporaryDirectory(prefix="nal-windows-workspace-")
		self.root = Path(self.temporary.name)
		self.source = self.root / "source"
		self.target = self.root / "target"
		run_git(self.root, "init", "--initial-branch=main", str(self.source))
		run_git(self.source, "config", "user.name", "Test User")
		run_git(self.source, "config", "user.email", "test@example.invalid")
		write(self.source / ".gitignore", ".venv/\ntmp/\nbuild/\ndist/\n")
		write(self.source / "tracked.txt", "main\n")
		write(self.source / "workspace" / "tracked.txt", "tracked child\n")
		run_git(self.source, "add", ".gitignore", "tracked.txt", "workspace/tracked.txt")
		run_git(self.source, "commit", "-m", "Initial state")
		run_git(self.root, "clone", str(self.source), str(self.target))
		run_git(self.target, "config", "user.name", "Test User")
		run_git(self.target, "config", "user.email", "test@example.invalid")
		run_git(
			self.source,
			"config",
			f"remote.{workspace_sync.REMOTE_NAME}.url",
			str(self.target),
		)
		run_git(self.target, "config", "core.filemode", "false")
		self.preserved = {
			self.target / ".venv" / "Scripts" / "python.exe": "environment\n",
			self.target / "tmp" / "human-test-state" / "profile.json": "state\n",
			self.target / "build" / "local-result.txt": "build\n",
			self.target / "workspace" / ".venv" / "cache.bin": "nested ignored\n",
			self.target / "local-notes.txt": "notes\n",
		}
		for path, content in self.preserved.items():
			write(path, content)

	def tearDown(self) -> None:
		self.temporary.cleanup()

	def assert_preserved_files(self) -> None:
		for path, content in self.preserved.items():
			with self.subTest(path=str(path)):
				self.assertEqual(content, path.read_text(encoding="utf-8"))

	def test_create_switch_rewrite_and_delete_mirror_without_touching_untracked_files(self) -> None:
		run_git(self.source, "switch", "-c", "feature/windows-test")
		write(self.source / "tracked.txt", "feature one\n")
		write(self.source / "feature.txt", "feature\n")
		run_git(self.source, "rm", "workspace/tracked.txt")
		run_git(self.source, "add", "tracked.txt", "feature.txt")
		run_git(self.source, "commit", "-m", "Feature state")

		first = workspace_sync.synchronize(self.source)

		self.assertEqual("feature/windows-test", first["branch"])
		self.assertEqual("feature/windows-test", run_git(self.target, "branch", "--show-current"))
		self.assertEqual("feature one\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))
		self.assertEqual("feature\n", (self.target / "feature.txt").read_text(encoding="utf-8"))
		self.assertFalse((self.target / "workspace" / "tracked.txt").exists())
		self.assert_preserved_files()

		run_git(self.source, "branch", "temporary-branch")
		workspace_sync.synchronize(self.source)
		self.assertIn("temporary-branch", run_git(self.target, "branch", "--format=%(refname:short)"))

		write(self.source / "tracked.txt", "rewritten\n")
		run_git(self.source, "add", "tracked.txt")
		run_git(self.source, "commit", "--amend", "--no-edit")
		rewritten = workspace_sync.synchronize(self.source)
		self.assertEqual(rewritten["commit"], run_git(self.target, "rev-parse", "HEAD"))
		self.assertEqual("rewritten\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))

		run_git(self.source, "branch", "-D", "temporary-branch")
		workspace_sync.synchronize(self.source)
		self.assertNotIn(
			"temporary-branch",
			run_git(self.target, "branch", "--format=%(refname:short)"),
		)

		run_git(self.source, "switch", "main")
		final = workspace_sync.synchronize(self.source)
		self.assertEqual("main", run_git(self.target, "branch", "--show-current"))
		self.assertEqual(final["commit"], run_git(self.target, "rev-parse", "HEAD"))
		self.assertFalse((self.target / "feature.txt").exists())
		self.assertEqual(
			"tracked child\n",
			(self.target / "workspace" / "tracked.txt").read_text(encoding="utf-8"),
		)
		self.assert_preserved_files()
		self.assertEqual("", run_git(self.target, "status", "--porcelain", "--untracked-files=no"))

	def test_ignored_path_collision_aborts_before_changing_the_worktree(self) -> None:
		original_commit = run_git(self.target, "rev-parse", "HEAD")
		original_branch = run_git(self.target, "branch", "--show-current")
		run_git(self.source, "switch", "-c", "tracked-environment-collision")
		write(self.source / ".venv" / "Scripts" / "python.exe", "tracked replacement\n")
		run_git(self.source, "add", "--force", ".venv/Scripts/python.exe")
		run_git(self.source, "commit", "-m", "Create collision")

		with self.assertRaisesRegex(workspace_sync.WorkspaceSyncError, "would be overwritten"):
			workspace_sync.synchronize(self.source)

		self.assertEqual(original_branch, run_git(self.target, "branch", "--show-current"))
		self.assertEqual(original_commit, run_git(self.target, "rev-parse", "HEAD"))
		self.assert_preserved_files()
		status_path = (
			Path(run_git(self.target, "rev-parse", "--git-dir"))
			/ workspace_sync.STATE_DIRECTORY_NAME
			/ workspace_sync.TARGET_STATUS_NAME
		)
		if not status_path.is_absolute():
			status_path = self.target / status_path
		status = json.loads(status_path.read_text(encoding="utf-8"))
		self.assertFalse(status["success"])

	def test_tracked_target_change_aborts_without_updating_any_target_ref(self) -> None:
		write(self.target / "tracked.txt", "manual Windows edit\n")
		run_git(self.source, "switch", "-c", "new-source-state")
		write(self.source / "tracked.txt", "new committed state\n")
		run_git(self.source, "add", "tracked.txt")
		run_git(self.source, "commit", "-m", "New state")

		with self.assertRaisesRegex(workspace_sync.WorkspaceSyncError, "changes to versioned files"):
			workspace_sync.synchronize(self.source)

		self.assertEqual("main", run_git(self.target, "branch", "--show-current"))
		self.assertEqual("manual Windows edit\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))
		self.assertEqual({}, workspace_sync._heads(self.target, workspace_sync.SYNC_REF_PREFIX))
		self.assert_preserved_files()

	def test_uncommitted_source_content_is_not_transferred(self) -> None:
		write(self.source / "tracked.txt", "uncommitted\n")
		result = workspace_sync.synchronize(self.source)
		self.assertTrue(result["success"])
		self.assertEqual("main\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))
		self.assertEqual("uncommitted\n", (self.source / "tracked.txt").read_text(encoding="utf-8"))
		self.assert_preserved_files()

	def test_request_is_local_and_worker_coalesces_to_the_latest_state(self) -> None:
		run_git(self.source, "config", "nal.windowsWorkspaceEnabled", "true")
		with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
			first_path = workspace_sync.request_synchronization(self.source, "first")
			first = json.loads(first_path.read_text(encoding="utf-8"))
			second_path = workspace_sync.request_synchronization(self.source, "second")
			second = json.loads(second_path.read_text(encoding="utf-8"))
		self.assertEqual(first_path, second_path)
		self.assertNotEqual(first["requestId"], second["requestId"])
		self.assertEqual("second", second["reason"])

		self.assertTrue(workspace_sync.run_worker(self.source))
		self.assertFalse(second_path.exists())
		self.assert_preserved_files()
		local_status = json.loads((second_path.parent / "status.json").read_text(encoding="utf-8"))
		self.assertTrue(local_status["success"])

	def test_worker_retries_when_a_newer_request_arrives_during_failure(self) -> None:
		with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
			request_path = workspace_sync.request_synchronization(self.source, "first")

		def synchronize_with_interleaved_request(source: Path) -> dict[str, object]:
			if synchronize.call_count == 1:
				with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
					workspace_sync.request_synchronization(source, "newer")
				raise workspace_sync.WorkspaceSyncError("transient first request failure")
			return {
				"branch": "main",
				"commit": run_git(source, "rev-parse", "HEAD"),
				"error": "",
				"schemaVersion": 1,
				"success": True,
				"updatedAt": "test",
			}

		with mock.patch.object(
			workspace_sync,
			"synchronize",
			side_effect=synchronize_with_interleaved_request,
		) as synchronize:
			self.assertTrue(workspace_sync.run_worker(self.source))
		self.assertEqual(2, synchronize.call_count)
		self.assertFalse(request_path.exists())

	def test_configure_uses_a_separate_remote_and_marks_the_target(self) -> None:
		result = workspace_sync.configure(self.source, self.target, trust_target=False)

		self.assertTrue(result["success"])
		self.assertEqual(
			str(self.target),
			run_git(
				self.source,
				"config",
				"--get",
				f"remote.{workspace_sync.REMOTE_NAME}.url",
			),
		)
		self.assertEqual(
			str(
				workspace_sync._state_directory(self.source)
				/ workspace_sync.RUNTIME_DIRECTORY_NAME
				/ ".githooks"
			),
			run_git(self.source, "config", "--get", "core.hooksPath"),
		)
		self.assertEqual("false", run_git(self.target, "config", "--get", "core.filemode"))
		marker = (
			self.target / ".git" / workspace_sync.STATE_DIRECTORY_NAME / workspace_sync.TARGET_MANAGED_MARKER
		)
		self.assertTrue(marker.is_file())
		ownership = json.loads(marker.read_text(encoding="utf-8"))
		self.assertEqual(
			str(workspace_sync._common_git_directory(self.source)),
			ownership["sourceGitDirectory"],
		)
		second = workspace_sync.configure(self.source, self.target, trust_target=False)
		self.assertEqual(result["commit"], second["commit"])
		self.assert_preserved_files()

	def test_configure_trusts_the_worktree_and_local_receive_pack_git_directory(self) -> None:
		with mock.patch.object(workspace_sync, "_ensure_trusted_directories") as trust:
			workspace_sync.configure(self.source, self.target)

		self.assertEqual(
			[
				mock.call(self.source.resolve(), (self.target.resolve(),)),
				mock.call(self.source.resolve(), ((self.target / ".git").resolve(),)),
			],
			trust.call_args_list,
		)
		self.assert_preserved_files()

	def test_failed_initial_sync_does_not_enable_hooks_or_mark_the_target(self) -> None:
		write(self.target / "tracked.txt", "dirty target\n")
		with self.assertRaisesRegex(workspace_sync.WorkspaceSyncError, "changes to versioned files"):
			workspace_sync.configure(self.source, self.target, trust_target=False)

		self.assertEqual(
			1,
			subprocess.run(
				("git", "-C", str(self.source), "config", "--get", "core.hooksPath"),
				check=False,
				capture_output=True,
			).returncode,
		)
		marker = (
			self.target / ".git" / workspace_sync.STATE_DIRECTORY_NAME / workspace_sync.TARGET_MANAGED_MARKER
		)
		self.assertFalse(marker.exists())

	def test_configure_refuses_conflicting_hook_or_remote_configuration(self) -> None:
		run_git(self.source, "config", "core.hooksPath", "/existing/hooks")
		with self.assertRaisesRegex(workspace_sync.WorkspaceSyncError, "hooksPath"):
			workspace_sync.configure(self.source, self.target, trust_target=False)
		run_git(self.source, "config", "--unset", "core.hooksPath")
		run_git(
			self.source,
			"config",
			f"remote.{workspace_sync.REMOTE_NAME}.url",
			str(self.root / "different-target"),
		)
		with self.assertRaisesRegex(workspace_sync.WorkspaceSyncError, "different location"):
			workspace_sync.configure(self.source, self.target, trust_target=False)

	def test_configure_refuses_a_target_owned_by_another_source_repository(self) -> None:
		workspace_sync.configure(self.source, self.target, trust_target=False)
		marker = (
			self.target / ".git" / workspace_sync.STATE_DIRECTORY_NAME / workspace_sync.TARGET_MANAGED_MARKER
		)
		marker.write_text(
			json.dumps({"schemaVersion": 1, "sourceGitDirectory": "/different/source/.git"}),
			encoding="utf-8",
		)
		with self.assertRaisesRegex(workspace_sync.WorkspaceSyncError, "different source"):
			workspace_sync.configure(self.source, self.target, trust_target=False)

	def test_configured_hooks_queue_branch_commit_switch_and_delete(self) -> None:
		workspace_sync.configure(self.source, self.target, trust_target=False)
		request_path = workspace_sync._state_directory(self.source) / "request.json"
		with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
			run_git(self.source, "switch", "-c", "hook-driven")
			write(self.source / "tracked.txt", "hook commit\n")
			run_git(self.source, "add", "tracked.txt")
			run_git(self.source, "commit", "-m", "Hook-driven state")
		self.assertTrue(request_path.is_file())
		self.assertEqual("main", run_git(self.target, "branch", "--show-current"))

		self.assertTrue(workspace_sync.run_worker(self.source))
		self.assertEqual("hook-driven", run_git(self.target, "branch", "--show-current"))
		self.assertEqual("hook commit\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))

		with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
			run_git(self.source, "switch", "main")
			run_git(self.source, "branch", "-D", "hook-driven")
		self.assertTrue(request_path.is_file())
		self.assertTrue(workspace_sync.run_worker(self.source))
		self.assertEqual("main", run_git(self.target, "branch", "--show-current"))
		self.assertNotIn("hook-driven", run_git(self.target, "branch", "--format=%(refname:short)"))
		self.assert_preserved_files()

	def test_background_workers_coalesce_real_hook_burst(self) -> None:
		workspace_sync.configure(self.source, self.target, trust_target=False)
		run_git(self.source, "switch", "-c", "background-burst")
		for index in range(3):
			write(self.source / "tracked.txt", f"background {index}\n")
			run_git(self.source, "add", "tracked.txt")
			run_git(self.source, "commit", "-m", f"Background {index}")
		expected = run_git(self.source, "rev-parse", "HEAD")
		deadline = time.monotonic() + 8
		while time.monotonic() < deadline:
			if (
				run_git(self.target, "branch", "--show-current") == "background-burst"
				and run_git(self.target, "rev-parse", "HEAD") == expected
			):
				break
			time.sleep(0.05)
		else:
			worker_log = workspace_sync._state_directory(self.source) / "worker.log"
			detail = worker_log.read_text(encoding="utf-8") if worker_log.is_file() else "no log"
			self.fail(f"background synchronization did not converge: {detail}")
		self.assert_preserved_files()

	def test_linked_worktrees_share_one_queue_and_select_the_latest_source(self) -> None:
		workspace_sync.configure(self.source, self.target, trust_target=False)
		linked = self.root / "linked"
		with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
			run_git(self.source, "worktree", "add", "-b", "linked-feature", str(linked))
			write(linked / "tracked.txt", "linked worktree\n")
			run_git(linked, "add", "tracked.txt")
			run_git(linked, "commit", "-m", "Linked worktree state")

		self.assertEqual(
			workspace_sync._state_directory(self.source),
			workspace_sync._state_directory(linked),
		)
		request_path = workspace_sync._state_directory(self.source) / "request.json"
		request = json.loads(request_path.read_text(encoding="utf-8"))
		self.assertEqual(str(linked), request["source"])
		self.assertTrue(workspace_sync.run_worker(self.source))
		self.assertEqual("linked-feature", run_git(self.target, "branch", "--show-current"))
		self.assertEqual("linked worktree\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))

		with mock.patch.dict(os.environ, {"NAL_WINDOWS_SYNC_NO_SPAWN": "1"}):
			write(self.source / "tracked.txt", "main worktree newer\n")
			run_git(self.source, "add", "tracked.txt")
			run_git(self.source, "commit", "-m", "Main worktree state")
		self.assertTrue(workspace_sync.run_worker(linked))
		self.assertEqual("main", run_git(self.target, "branch", "--show-current"))
		self.assertEqual("main worktree newer\n", (self.target / "tracked.txt").read_text(encoding="utf-8"))
		self.assert_preserved_files()


if __name__ == "__main__":
	unittest.main()
