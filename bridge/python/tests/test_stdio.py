from __future__ import annotations

import io
import os
import time
import unittest

from nvim_nvda_bridge.stdio import STDIO_MARKER, StdioTransport
from nvim_nvda_protocol import FrameDecoder, MessageFactory, encode_frame


class StdioTransportTests(unittest.TestCase):
    def test_marker_full_state_event_and_eof(self) -> None:
        output = io.BytesIO()
        read_fd, write_fd = os.pipe()
        input_stream = os.fdopen(read_fd, "rb", buffering=0)
        transport = StdioTransport(
            lambda: {"lineText": "hello"}, input_stream, output, heartbeat_seconds=10.0
        )
        transport.start()
        transport.publish("connectionStateChanged", {"connection": {"neovim": "connected"}})
        transport.publish("fullState", {"lineText": "hello", "connection": {"neovim": "connected"}})
        os.close(write_fd)
        self.assertTrue(transport.closed.wait(1.0))
        raw = output.getvalue()
        self.assertTrue(raw.startswith(STDIO_MARKER))
        messages = FrameDecoder().feed(raw[len(STDIO_MARKER):])
        self.assertEqual(["fullState"], [message["type"] for message in messages])
        self.assertEqual("ssh-stdio", messages[0]["payload"]["_transport"]["kind"])
        transport.stop()

    def test_route_control_is_dispatched(self) -> None:
        controls: list[tuple[str, dict]] = []
        control = MessageFactory().create("routeCursor", {"line": 2})
        transport = StdioTransport(
            lambda: {}, io.BytesIO(encode_frame(control)), io.BytesIO(),
            on_control=lambda kind, payload: controls.append((kind, payload)), heartbeat_seconds=10.0,
        )
        transport.start()
        self.assertTrue(transport.closed.wait(1.0))
        self.assertEqual([("routeCursor", {"line": 2})], controls)
        transport.stop()


if __name__ == "__main__":
    unittest.main()
