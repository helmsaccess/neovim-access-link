from __future__ import annotations

import io
import os
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
		messages = FrameDecoder().feed(raw[len(STDIO_MARKER) :])
		self.assertEqual(["fullState"], [message["type"] for message in messages])
		self.assertEqual("ssh-stdio", messages[0]["payload"]["_transport"]["kind"])
		transport.stop()

	def test_route_control_is_dispatched(self) -> None:
		controls: list[tuple[str, dict]] = []
		control = MessageFactory().create("routeCursor", {"line": 2})
		transport = StdioTransport(
			lambda: {},
			io.BytesIO(encode_frame(control)),
			io.BytesIO(),
			on_control=lambda kind, payload: controls.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([("routeCursor", {"line": 2})], controls)
		transport.stop()

	def test_only_valid_clipboard_controls_are_dispatched(self) -> None:
		state = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
			"modeRaw": "n",
			"requestId": 5,
		}
		controls = b"".join(
			(
				encode_frame(
					MessageFactory().create(
						"copyTextRequest",
						{
							**state,
							"source": "yankRegister",
						},
					)
				),
				encode_frame(
					MessageFactory().create(
						"pasteTextRequest",
						{
							**state,
							"text": "remote text",
						},
					)
				),
				encode_frame(
					MessageFactory().create(
						"setRegisterRequest",
						{
							**state,
							"text": "current register",
						},
					)
				),
				encode_frame(
					MessageFactory().create(
						"copyTextRequest",
						{
							**state,
							"source": "untrusted",
						},
					)
				),
			)
		)
		dispatched: list[tuple[str, dict]] = []
		transport = StdioTransport(
			lambda: {},
			io.BytesIO(controls),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual(
			["copyTextRequest", "pasteTextRequest", "setRegisterRequest"],
			[kind for kind, _payload in dispatched],
		)
		transport.stop()

	def test_only_exact_terminal_control_is_dispatched(self) -> None:
		valid = {
			"requestId": 5,
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"modeRaw": "t",
		}
		controls = b"".join(
			(
				encode_frame(MessageFactory().create("leaveTerminalInputRequest", valid)),
				encode_frame(
					MessageFactory().create(
						"leaveTerminalInputRequest",
						{
							**valid,
							"modeRaw": "n",
						},
					)
				),
			)
		)
		dispatched = []
		transport = StdioTransport(
			lambda: {},
			io.BytesIO(controls),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([("leaveTerminalInputRequest", valid)], dispatched)
		transport.stop()

	def test_only_exact_exploration_controls_are_dispatched(self) -> None:
		step = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "characterLeft",
			"count": 1,
			"bufferId": 3,
			"windowId": 4,
			"tabpageId": 5,
			"changedtick": 6,
			"modeRaw": "n",
			"cursorLine": 7,
			"cursorByteColumn": 1,
			"cursorVirtualColumn": 1,
		}
		controls = b"".join(
			(
				encode_frame(MessageFactory().create("exploreTextRequest", step)),
				encode_frame(
					MessageFactory().create(
						"endExplorationRequest",
						{
							"requestId": 2,
							"explorationId": 2,
						},
					)
				),
				encode_frame(
					MessageFactory().create(
						"exploreTextRequest",
						{
							**step,
							"action": "arbitrary",
						},
					)
				),
			)
		)
		dispatched = []
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["exploration"]},
			io.BytesIO(controls),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual(
			["exploreTextRequest", "endExplorationRequest"], [kind for kind, _payload in dispatched]
		)
		transport.stop()

	def test_exploration_requires_plugin_capability(self) -> None:
		step = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "characterLeft",
			"count": 1,
			"bufferId": 3,
			"windowId": 4,
			"tabpageId": 5,
			"changedtick": 6,
			"modeRaw": "n",
			"cursorLine": 7,
			"cursorByteColumn": 1,
			"cursorVirtualColumn": 1,
		}
		control = encode_frame(MessageFactory().create("exploreTextRequest", step))
		dispatched = []
		transport = StdioTransport(
			lambda: {},
			io.BytesIO(control),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		self.assertNotIn(
			"exploration",
			transport._state_with_capabilities()["_transport"]["capabilities"],
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([], dispatched)
		transport.stop()

	def test_focus_context_control_correlates_cached_state(self) -> None:
		controls = b"".join(
			encode_frame(
				MessageFactory().create(
					"requestFocusContext",
					{"requestId": value},
				)
			)
			for value in (9, True, -1, 2_147_483_648)
		)
		output = io.BytesIO()
		read_fd, write_fd = os.pipe()
		transport = StdioTransport(
			lambda: {"mode": "normal", "bufferName": "example.txt"},
			os.fdopen(read_fd, "rb", buffering=0),
			output,
			heartbeat_seconds=10.0,
		)
		transport.start()
		transport.publish("fullState", {"mode": "normal"})
		os.write(write_fd, controls)
		os.close(write_fd)
		self.assertTrue(transport.closed.wait(1.0))
		messages = FrameDecoder().feed(output.getvalue()[len(STDIO_MARKER) :])
		focus = [message for message in messages if message["type"] == "focusContext"]
		self.assertEqual(1, len(focus))
		self.assertEqual(9, focus[0]["payload"]["_focusRequestId"])
		self.assertEqual("example.txt", focus[0]["payload"]["bufferName"])
		transport.stop()


if __name__ == "__main__":
	unittest.main()
