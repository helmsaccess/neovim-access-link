from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from nvim_nvda_core import LocalSessionLister, local_registry_directory


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
                "version": 2, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 45678, "name": "Docs", "cwd": r"C:\work",
                "startedMonotonic": 10, "startedUnix": 100,
                "claimedMonotonic": 2_000_000_000, "claimSequence": 3,
            }
            (directory / "42.json").write_text(json.dumps(valid), encoding="utf-8")
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

    def test_rejects_stale_malformed_and_oversized_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = pathlib.Path(directory_name)
            base = {
                "version": 2, "transportKind": "localWindowsTcp", "pid": 42,
                "host": "127.0.0.1", "port": 1234, "name": "", "cwd": "",
                "startedMonotonic": 10,
            }
            (directory / "stale.json").write_text(json.dumps(base), encoding="utf-8")
            (directory / "bad.json").write_text("not json", encoding="utf-8")
            (directory / "large.json").write_text(" " * 70_000, encoding="utf-8")
            self.assertEqual([], LocalSessionLister(
                directory, process_alive=lambda _pid: False,
            ).list())


if __name__ == "__main__":
    unittest.main()
