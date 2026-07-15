from __future__ import annotations

import unittest

from nvim_nvda_protocol import LocalTcpClient


class FakeSource:
    def __init__(self, endpoint, on_event, on_state, expected_session_nonce=None):
        self.endpoint = endpoint
        self.on_event = on_event
        self.on_state = on_state
        self.expected_session_nonce = expected_session_nonce
        self.started = 0
        self.stopped = 0
        self.notifications = []

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def notify(self, method, *parameters):
        self.notifications.append((method, parameters))
        return True


class LocalTcpClientTests(unittest.TestCase):
    def make_client(self, session_nonce="a" * 32):
        events, states, diagnostics, sources = [], [], [], []

        def source_factory(*arguments):
            source = FakeSource(*arguments)
            sources.append(source)
            return source

        client = LocalTcpClient(
            "127.0.0.1", 45678, events.append, states.append,
            lambda category, fields: diagnostics.append((category, fields)), source_factory,
            session_nonce,
        )
        return client, sources[0], events, states, diagnostics

    def test_selected_registry_nonce_reaches_permanent_rpc_source(self) -> None:
        _client, source, _events, _states, _diagnostics = self.make_client("b" * 32)
        self.assertEqual("b" * 32, source.expected_session_nonce)

    def test_rejects_non_loopback_and_invalid_ports(self) -> None:
        for host, port in (("localhost", 1234), ("0.0.0.0", 1234), ("127.0.0.1", 0)):
            with self.subTest(host=host, port=port), self.assertRaises(ValueError):
                LocalTcpClient(host, port, lambda _event: None, lambda _state: None)

    def test_first_full_state_authenticates_and_marks_transport(self) -> None:
        client, source, events, states, _diagnostics = self.make_client()
        client.start()
        source.on_state("connecting")
        source.on_state("connected")
        source.on_event("fullState", {"mode": "normal"})
        self.assertEqual(1, source.started)
        self.assertEqual(["connecting", "connected"], states)
        self.assertEqual("fullState", events[0]["type"])
        self.assertEqual("windows-loopback-tcp", events[0]["payload"]["_transport"]["kind"])
        self.assertNotIn("heartbeat", events[0]["payload"]["_transport"]["capabilities"])

    def test_invalid_full_state_neither_authenticates_nor_enters_cache(self) -> None:
        client, source, events, states, diagnostics = self.make_client()
        source.on_event("fullState", {"mode": object()})
        self.assertEqual([], events)
        self.assertEqual([], states)
        self.assertFalse(client.send_control("requestFullState", {}))
        self.assertEqual("localEventRejected", diagnostics[0][0])

    def test_full_state_control_republishes_cached_state(self) -> None:
        client, source, events, _states, _diagnostics = self.make_client()
        self.assertFalse(client.send_control("requestFullState", {}))
        source.on_event("fullState", {"mode": "insert"})
        self.assertTrue(client.send_control("requestFullState", {}))
        self.assertEqual([0, 1], [event["sequence"] for event in events])

    def test_cursor_control_is_validated_before_rpc_notification(self) -> None:
        client, source, _events, _states, diagnostics = self.make_client()
        self.assertFalse(client.send_control("routeCursor", {"line": 1}))
        payload = {
            "bufferId": 1, "windowId": 2, "line": 3, "byteColumn": 4, "changedtick": 5,
        }
        self.assertTrue(client.send_control("routeCursor", payload))
        self.assertEqual("nvim_exec_lua", source.notifications[0][0])
        self.assertEqual([payload], source.notifications[0][1][1])
        self.assertEqual("controlRejected", diagnostics[0][0])

    def test_disconnect_clears_cached_state_and_stop_is_delegated(self) -> None:
        client, source, _events, states, _diagnostics = self.make_client()
        source.on_event("fullState", {"mode": "normal"})
        source.on_state("disconnected")
        self.assertFalse(client.send_control("requestFullState", {}))
        client.stop()
        self.assertEqual(1, source.stopped)
        self.assertEqual(["connected", "disconnected"], states)


if __name__ == "__main__":
    unittest.main()
