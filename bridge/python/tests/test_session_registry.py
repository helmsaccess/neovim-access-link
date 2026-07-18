from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from nvim_nvda_bridge.session_registry import (
    REGISTRY_MAX_ENTRIES, discover_session, list_sessions, registry_directory,
)


class SessionRegistryTests(unittest.TestCase):
    def test_noninteractive_ssh_recovers_owned_system_runtime_directory(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(pathlib.Path, "is_dir", return_value=True), \
                mock.patch.object(pathlib.Path, "stat", return_value=SimpleNamespace(st_uid=os.getuid())):
            self.assertEqual(
                pathlib.Path(f"/run/user/{os.getuid()}/nvim-nvda/sessions"),
                registry_directory(),
            )

    def test_previous_schema_is_hidden_even_when_pid_and_path_look_live(self) -> None:
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
            self.assertEqual([], list_sessions(directory))

    def test_selects_newest_live_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            for sequence, name in enumerate(("one", "two"), start=1):
                socket_path = directory / f"{name}.sock"
                socket_path.touch()
                nonce = ("a" if name == "one" else "b") * 32
                (directory / f"{os.getpid()}-{nonce}.json").write_text(json.dumps({
                    "version": 3, "transportKind": "remoteSsh", "pid": os.getpid(),
                    "socket": str(socket_path), "processStartTicks": 77,
                    "sessionNonce": nonce,
                    "startedMonotonic": sequence,
                }), encoding="utf-8")
            sessions = list_sessions(
                directory, process_start_reader=lambda _pid: 77,
            )
            self.assertEqual(str(directory / "two.sock"), sessions[0].socket)

    def test_lists_sessions_and_selects_explicit_id_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            for pid, name, label in ((111, "one", "project"), (222, "two", "project")):
                socket_path = directory / f"{name}.sock"
                socket_path.touch()
                nonce = ("a" if pid == 111 else "b") * 32
                (directory / f"{pid}-{nonce}.json").write_text(json.dumps({
                    "version": 3, "transportKind": "remoteSsh", "pid": pid,
                    "socket": str(socket_path), "processStartTicks": pid + 1,
                    "sessionNonce": nonce, "name": label,
                    "cwd": f"/work/{name}", "startedMonotonic": pid,
                    "claimedMonotonic": pid + 1000, "claimSequence": pid,
                }), encoding="utf-8")
            sessions = list_sessions(
                directory, process_start_reader=lambda pid: pid + 1,
            )
            self.assertEqual(["222", "111"], [session.identifier for session in sessions])
            self.assertEqual([1222, 1111], [session.claimed_monotonic for session in sessions])
            self.assertEqual([222, 111], [session.claim_sequence for session in sessions])
            with mock.patch("nvim_nvda_bridge.session_registry.list_sessions", return_value=sessions):
                self.assertEqual(str(directory / "one.sock"), discover_session(directory, "111").socket)
                with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                    discover_session(directory, "project")
                with self.assertRaisesRegex(RuntimeError, "not found"):
                    discover_session(directory, "missing")

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
            nonce = "a" * 32
            (directory / f"123-{nonce}.json").write_text(json.dumps({
                "version": 3, "transportKind": "remoteSsh", "pid": 123,
                "socket": str(socket_path), "processStartTicks": 77,
                "sessionNonce": nonce, "startedMonotonic": 2.5688576805887e14,
            }), encoding="utf-8")
            sessions = list_sessions(
                directory, process_start_reader=lambda _pid: 77,
            )
            self.assertEqual(1, len(sessions))
            self.assertEqual(256_885_768_058_870, sessions[0].started_monotonic)
            self.assertEqual(nonce, sessions[0].session_nonce)

    def test_current_schema_requires_process_and_endpoint_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            socket_path = directory / "nvim.sock"
            socket_path.touch()
            entry = directory / f"123-{'a' * 32}.json"
            entry.write_text(json.dumps({
                "version": 3, "transportKind": "remoteSsh", "pid": 123,
                "socket": str(socket_path), "startedMonotonic": 10,
                "processStartTicks": 77, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            sessions = list_sessions(
                directory, process_start_reader=lambda _pid: 77,
            )
            self.assertEqual(["123"], [session.identifier for session in sessions])
            self.assertEqual([], list_sessions(
                directory, process_start_reader=lambda _pid: 78,
            ))
            self.assertFalse(entry.exists(), "reused PID is pruned")

    def test_live_remote_registry_is_discovered_without_opening_rpc_socket(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            socket_path = directory / "nvim.sock"
            socket_path.touch()
            entry = directory / f"123-{'a' * 32}.json"
            entry.write_text(json.dumps({
                "version": 3, "transportKind": "remoteSsh", "pid": 123,
                "socket": str(socket_path), "startedMonotonic": 10,
                "processStartTicks": 77, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            self.assertEqual(1, len(list_sessions(
                directory, process_start_reader=lambda _pid: 77,
            )))
            self.assertTrue(entry.exists())

    def test_uncertain_process_permission_is_not_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, \
                mock.patch("os.kill", side_effect=PermissionError()):
            directory = pathlib.Path(directory_name)
            entry = directory / f"123-{'a' * 32}.json"
            entry.write_text(json.dumps({
                "version": 3, "transportKind": "remoteSsh", "pid": 123,
                "socket": "/missing", "startedMonotonic": 10,
                "processStartTicks": 77, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            self.assertEqual([], list_sessions(directory))
            self.assertTrue(entry.exists())

    def test_oversized_remote_entry_is_ignored_without_reading_unbounded_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            entry = directory / f"123-{'a' * 32}.json"
            entry.write_bytes(b" " * 70_000)
            self.assertEqual([], list_sessions(directory))
            self.assertTrue(entry.exists())

    def test_scan_count_is_bounded_and_passive(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill"):
            directory = pathlib.Path(directory_name)
            nonce = "a" * 32
            for pid in range(1, REGISTRY_MAX_ENTRIES + 20):
                socket_path = directory / f"{pid}.sock"
                socket_path.touch()
                (directory / f"{pid}-{nonce}.json").write_text(json.dumps({
                    "version": 3, "transportKind": "remoteSsh", "pid": pid,
                    "socket": str(socket_path), "startedMonotonic": pid,
                    "processStartTicks": pid, "sessionNonce": nonce,
                }), encoding="utf-8")
            sessions = list_sessions(
                directory, process_start_reader=lambda pid: pid,
            )
            self.assertEqual(REGISTRY_MAX_ENTRIES, len(sessions))

    def test_boolean_pid_is_rejected_without_process_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name, mock.patch("os.kill") as kill:
            directory = pathlib.Path(directory_name)
            (directory / f"True-{'a' * 32}.json").write_text(json.dumps({
                "version": 3, "transportKind": "remoteSsh", "pid": True,
                "socket": "/tmp/fake", "startedMonotonic": 10,
                "processStartTicks": 1, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            self.assertEqual([], list_sessions(directory))
            kill.assert_not_called()

    def test_dead_session_removes_only_nonce_owned_socket(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name) / "nvim-nvda"
            directory = root / "sessions"
            directory.mkdir(parents=True)
            owned = root / f"nvim-123-{'a' * 32}.sock"
            owned.touch()
            entry = directory / f"123-{'a' * 32}.json"
            entry.write_text(json.dumps({
                "version": 3, "pid": 123, "socket": str(owned),
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
                "ownsSocket": True,
            }), encoding="utf-8")
            with mock.patch("os.kill", side_effect=ProcessLookupError()):
                self.assertEqual([], list_sessions(directory))
            self.assertFalse(entry.exists())
            self.assertFalse(owned.exists())

            foreign = root / "user.sock"
            foreign.touch()
            entry.write_text(json.dumps({
                "version": 3, "pid": 123, "socket": str(foreign),
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
                "ownsSocket": True,
            }), encoding="utf-8")
            with mock.patch("os.kill", side_effect=ProcessLookupError()):
                self.assertEqual([], list_sessions(directory))
            self.assertTrue(foreign.exists(), "nonstandard user socket is never removed")

    def test_mismatched_filename_is_never_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            entry = directory / "123.json"
            entry.write_text(json.dumps({
                "version": 3, "pid": 123, "socket": "/missing",
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            with mock.patch("os.kill", side_effect=ProcessLookupError()):
                self.assertEqual([], list_sessions(directory))
            self.assertTrue(entry.exists(), "only nonce-qualified private records are pruned")


if __name__ == "__main__":
    unittest.main()
