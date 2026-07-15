from __future__ import annotations

import contextlib
import io
import json
import sys
import threading
import unittest
from unittest import mock

from nvim_nvda_bridge.__main__ import main
from nvim_nvda_bridge.session_registry import RegisteredSession


class BridgeCliTests(unittest.TestCase):
    def test_auto_discovered_nonce_is_bound_to_bridge_channel(self) -> None:
        session = RegisteredSession(
            identifier="42", pid=42, socket="/run/user/1/nvim.sock",
            name="project", cwd="/work/project", started_monotonic=10,
            session_nonce="a" * 32,
        )
        bridge = mock.Mock()
        bridge.transport.closed = threading.Event()
        bridge.start.side_effect = bridge.transport.closed.set
        with mock.patch.object(sys, "argv", ["nvim-nvda-bridge"]), \
                mock.patch("nvim_nvda_bridge.__main__.discover_session", return_value=session), \
                mock.patch("nvim_nvda_bridge.__main__.Bridge", return_value=bridge) as bridge_type, \
                mock.patch("nvim_nvda_bridge.__main__.signal.signal"):
            self.assertEqual(0, main())
        bridge_type.assert_called_once_with(
            session.socket,
            stdio_streams=(sys.stdin.buffer, sys.stdout.buffer),
            session_nonce=session.session_nonce,
        )
        bridge.start.assert_called_once_with()
        bridge.stop.assert_called_once_with()

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
