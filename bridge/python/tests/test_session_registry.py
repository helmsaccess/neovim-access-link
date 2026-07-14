from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from nvim_nvda_bridge.session_registry import discover_socket, list_sessions, registry_directory


class SessionRegistryTests(unittest.TestCase):
    def test_noninteractive_ssh_recovers_owned_system_runtime_directory(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(pathlib.Path, "is_dir", return_value=True), \
                mock.patch.object(pathlib.Path, "stat", return_value=SimpleNamespace(st_uid=os.getuid())):
            self.assertEqual(
                pathlib.Path(f"/run/user/{os.getuid()}/nvim-nvda/sessions"),
                registry_directory(),
            )

    def test_discovers_only_live_registered_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            socket_path = directory / "nvim.sock"
            socket_path.touch()
            (directory / f"{os.getpid()}.json").write_text(json.dumps({
                "version": 2, "pid": os.getpid(), "socket": str(socket_path),
                "startedMonotonic": 1,
            }), encoding="utf-8")
            (directory / "stale.json").write_text(json.dumps({
                "version": 2, "pid": 999_999_999, "socket": str(socket_path),
                "startedMonotonic": 2,
            }), encoding="utf-8")
            self.assertEqual(str(socket_path), discover_socket(directory))

    def test_selects_newest_live_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            for sequence, name in enumerate(("one", "two"), start=1):
                socket_path = directory / f"{name}.sock"
                socket_path.touch()
                (directory / f"{name}.json").write_text(json.dumps({
                    "version": 2, "pid": os.getpid(), "socket": str(socket_path),
                    "startedMonotonic": sequence,
                }), encoding="utf-8")
            self.assertEqual(str(directory / "two.sock"), discover_socket(directory))

    def test_lists_sessions_and_selects_explicit_id_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            for pid, name, label in ((111, "one", "project"), (222, "two", "project")):
                socket_path = directory / f"{name}.sock"
                socket_path.touch()
                (directory / f"{pid}.json").write_text(json.dumps({
                    "version": 2, "pid": pid, "socket": str(socket_path), "name": label,
                    "cwd": f"/work/{name}", "startedMonotonic": pid,
                    "claimedMonotonic": pid + 1000, "claimSequence": pid,
                }), encoding="utf-8")
            sessions = list_sessions(directory)
            self.assertEqual(["222", "111"], [session.identifier for session in sessions])
            self.assertEqual([1222, 1111], [session.claimed_monotonic for session in sessions])
            self.assertEqual([222, 111], [session.claim_sequence for session in sessions])
            self.assertEqual(str(directory / "one.sock"), discover_socket(directory, "111"))
            with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                discover_socket(directory, "project")
            with self.assertRaisesRegex(RuntimeError, "not found"):
                discover_socket(directory, "missing")

    def test_rejects_previous_registry_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            socket_path = directory / "old.sock"
            socket_path.touch()
            (directory / "old.json").write_text(json.dumps({
                "version": 1, "pid": 123, "socket": str(socket_path),
                "startedMonotonic": 10,
            }), encoding="utf-8")
            self.assertEqual([], list_sessions(directory))

    def test_accepts_large_lua_timestamps_encoded_with_exponents(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            socket_path = directory / "nvim.sock"
            socket_path.touch()
            (directory / "123.json").write_text(json.dumps({
                "version": 2, "pid": 123, "socket": str(socket_path),
                "startedMonotonic": 2.5688576805887e14,
            }), encoding="utf-8")
            sessions = list_sessions(directory)
            self.assertEqual(1, len(sessions))
            self.assertEqual(256_885_768_058_870, sessions[0].started_monotonic)


if __name__ == "__main__":
    unittest.main()
