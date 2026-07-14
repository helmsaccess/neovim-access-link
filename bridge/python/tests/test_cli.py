from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from unittest import mock

from nvim_nvda_bridge.__main__ import main
from nvim_nvda_bridge.session_registry import RegisteredSession


class BridgeCliTests(unittest.TestCase):
    def test_lists_current_registry_sessions_as_json(self) -> None:
        session = RegisteredSession(
            identifier="42", pid=42, socket="/run/user/1/nvim.sock",
            name="project", cwd="/work/project", started_monotonic=10, started_unix=20,
        )
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["nvim-nvda-bridge", "--list-sessions"]), \
                mock.patch("nvim_nvda_bridge.__main__.list_sessions", return_value=[session]), \
                contextlib.redirect_stdout(output):
            self.assertEqual(0, main())
        self.assertEqual([{
            "id": "42", "name": "project", "cwd": "/work/project",
            "pid": 42, "startedUnix": 20, "claimSequence": 0, "claimAgeMs": -1,
        }], json.loads(output.getvalue()))

    def test_removed_transport_options_are_rejected(self) -> None:
        for option in ("--stdio", "--token-file", "--host", "--port"):
            with self.subTest(option=option), \
                    mock.patch.object(sys, "argv", ["nvim-nvda-bridge", option]), \
                    contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit):
                main()


if __name__ == "__main__":
    unittest.main()
