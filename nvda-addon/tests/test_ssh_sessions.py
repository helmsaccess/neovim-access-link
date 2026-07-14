from __future__ import annotations

import json
import subprocess
import unittest

from nvim_nvda_core import SshSessionLister


class SshSessionListerTests(unittest.TestCase):
    def test_lists_multiple_sessions_with_profile_options(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps([
                {"id": "12", "name": "project", "cwd": "/work/project", "startedUnix": 42,
                 "claimAgeMs": 275, "claimSequence": 4},
                {"id": "34", "name": "", "cwd": "/work/other"},
            ]).encode(), stderr=b"")
        sessions = SshSessionLister(runner).list(
            "user@host", 2222, r"C:\keys\work key",
        )
        self.assertEqual(["12", "34"], [session.identifier for session in sessions])
        self.assertEqual("", sessions[1].name)
        self.assertEqual("/work/other", sessions[1].cwd)
        self.assertEqual(42, sessions[0].started_unix)
        self.assertEqual(275, sessions[0].claim_age_ms)
        self.assertEqual(4, sessions[0].claim_sequence)
        self.assertEqual(-1, sessions[1].claim_age_ms)
        command = calls[0][0]
        self.assertIn("2222", command)
        self.assertIn(r"C:\keys\work key", command)
        self.assertEqual("$HOME/.local/bin/nvim-nvda-bridge --list-sessions", command[-1])

    def test_password_is_only_in_askpass_environment(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout=b"[]", stderr=b"")
        SshSessionLister(runner).list(
            "user@host", password="secret value", askpass_path=r"C:\addon\askpass.cmd",
        )
        command, kwargs = calls[0]
        self.assertNotIn("secret value", " ".join(command))
        self.assertEqual("secret value", kwargs["env"]["NVIM_NVDA_SSH_PASSWORD"])
        self.assertIn("NumberOfPasswordPrompts=1", command)

    def test_filters_invalid_records_and_rejects_malformed_json(self) -> None:
        valid_runner = lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, stdout=b'[{"id":"1","name":"one"},{"id":"bad id","name":"bad"},7]', stderr=b"",
        )
        self.assertEqual(["1"], [item.identifier for item in SshSessionLister(valid_runner).list("host")])
        bad_runner = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout=b"not-json", stderr=b"")
        with self.assertRaisesRegex(RuntimeError, "valid JSON"):
            SshSessionLister(bad_runner).list("host")

    def test_nonzero_ssh_result_and_invalid_options_fail(self) -> None:
        runner = lambda command, **kwargs: subprocess.CompletedProcess(command, 255, stdout=b"", stderr=b"denied")
        with self.assertRaisesRegex(RuntimeError, "denied"):
            SshSessionLister(runner).list("host")
        for kwargs in ({"port": 0}, {"identity_file": "-bad"}, {"password": "x"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SshSessionLister().list("host", **kwargs)


if __name__ == "__main__":
    unittest.main()
