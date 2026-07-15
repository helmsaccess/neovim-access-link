from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from nvim_nvda_core import LocalSessionLister, local_registry_directory
from nvim_nvda_core.local_sessions import LOCAL_SESSION_MAX_ENTRIES


class LocalSessionListerTests(unittest.TestCase):
    def test_registry_path_uses_local_app_data(self) -> None:
        self.assertEqual(
            pathlib.Path(r"C:\Users\ExampleUser\AppData\Local") / "nvim-nvda" / "sessions",
            local_registry_directory({"LOCALAPPDATA": r"C:\Users\ExampleUser\AppData\Local"}),
        )
        with self.assertRaisesRegex(RuntimeError, "LOCALAPPDATA"):
            local_registry_directory({})

    def test_lists_only_live_exact_loopback_sessions_and_computes_claim_age(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            valid = {
                "version": 3, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 45678, "name": "Docs", "cwd": r"C:\work",
                "startedMonotonic": 10, "startedUnix": 100,
                "claimedMonotonic": 2_000_000_000, "claimSequence": 3,
                "sessionNonce": "a" * 32,
            }
            (directory / f"42-{'a' * 32}.json").write_text(json.dumps(valid), encoding="utf-8")
            (directory / "lan.json").write_text(json.dumps({
                **valid, "pid": 43, "host": "0.0.0.0",
            }), encoding="utf-8")
            sessions = LocalSessionLister(
                directory, process_alive=lambda pid: pid in {42, 43},
                monotonic_ns=lambda: 2_250_000_000,
            ).list()
            self.assertEqual(1, len(sessions))
            self.assertEqual(("42", "Docs", "127.0.0.1", 45678, 250), (
                sessions[0].identifier, sessions[0].name, sessions[0].host,
                sessions[0].port, sessions[0].claim_age_ms,
            ))
            self.assertEqual(2_000_000_000, sessions[0].claimed_monotonic_ns)
            self.assertEqual(3, sessions[0].claim_sequence)
            self.assertEqual("a" * 32, sessions[0].session_nonce)

    def test_rejects_stale_malformed_and_oversized_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            base = {
                "version": 3, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10,
            }
            (directory / "stale.json").write_text(json.dumps(base), encoding="utf-8")
            (directory / "bad.json").write_text("not json", encoding="utf-8")
            (directory / "large.json").write_text(" " * 70_000, encoding="utf-8")
            self.assertEqual([], LocalSessionLister(
                directory, process_alive=lambda _pid: False,
            ).list())

    def test_current_registry_carries_nonce_without_contacting_neovim(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            value = {
                "version": 3, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
            }
            entry = directory / f"42-{'a' * 32}.json"
            entry.write_text(json.dumps(value), encoding="utf-8")
            probes = []
            sessions = LocalSessionLister(
                directory, process_alive=lambda _pid: probes.append("pid") or True,
            ).list()
            self.assertEqual(1, len(sessions))
            self.assertEqual("a" * 32, sessions[0].session_nonce)
            self.assertEqual(["pid"], probes)
            self.assertTrue(entry.exists())

    def test_dead_well_named_entry_is_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            value = {
                "version": 3, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
            }
            entry = directory / f"42-{'a' * 32}.json"
            entry.write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual([], LocalSessionLister(
                directory, process_alive=lambda _pid: False,
            ).list())
            self.assertFalse(entry.exists(), "definitively dead process is pruned")

    def test_uncertain_process_access_is_hidden_but_not_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            entry = directory / f"42-{'a' * 32}.json"
            entry.write_text(json.dumps({
                "version": 3, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            self.assertEqual([], LocalSessionLister(
                directory, process_alive=lambda _pid: None,
            ).list())
            self.assertTrue(entry.exists())

    def test_previous_schema_is_hidden_even_with_live_reused_pid(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            entry = directory / "42.json"
            entry.write_text(json.dumps({
                "version": 2, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10,
            }), encoding="utf-8")
            self.assertEqual([], LocalSessionLister(
                directory, process_alive=lambda _pid: True,
            ).list())
            self.assertTrue(entry.exists(), "legacy uncertainty is non-destructive")

    def test_current_schema_mismatched_filename_is_never_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            entry = directory / "42.json"
            entry.write_text(json.dumps({
                "version": 3, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10, "sessionNonce": "a" * 32,
            }), encoding="utf-8")
            self.assertEqual([], LocalSessionLister(
                directory, process_alive=lambda _pid: False,
            ).list())
            self.assertTrue(entry.exists(), "a reused PID filename is not owned")

    def test_local_registry_scan_is_bounded_and_passive(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            nonce = "a" * 32
            for pid in range(1, LOCAL_SESSION_MAX_ENTRIES + 20):
                (directory / f"{pid}-{nonce}.json").write_text(json.dumps({
                    "version": 3, "transportKind": "localWindowsTcp", "pid": pid,
                    "host": "127.0.0.1", "port": 10_000 + pid,
                    "name": "", "cwd": "", "startedMonotonic": pid,
                    "sessionNonce": nonce,
                }), encoding="utf-8")
            sessions = LocalSessionLister(
                directory, process_alive=lambda _pid: True,
            ).list()
            self.assertEqual(LOCAL_SESSION_MAX_ENTRIES, len(sessions))


if __name__ == "__main__":
    unittest.main()
