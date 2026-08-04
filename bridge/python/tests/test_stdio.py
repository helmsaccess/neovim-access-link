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

	def test_braille_line_control_is_validated_and_capability_gated(self) -> None:
		payload = {
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"changedtick": 4,
			"modeRaw": "n",
			"direction": "next",
			"targetColumn": "preferred",
			"preferredVirtualColumn": 79,
		}
		controls: list[tuple[str, dict]] = []
		frames = b"".join(
			encode_frame(MessageFactory().create("moveBrailleLine", value))
			for value in (payload, {**payload, "modeRaw": "c"})
		)
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["brailleLineNavigation"]},
			io.BytesIO(frames),
			io.BytesIO(),
			on_control=lambda kind, value: controls.append((kind, value)),
			heartbeat_seconds=10.0,
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([("moveBrailleLine", payload)], controls)
		transport.stop()

	def test_repeated_braille_routing_action_is_validated_and_capability_gated(self) -> None:
		payload = {
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"byteColumn": 4,
			"changedtick": 5,
			"modeRaw": "n",
			"action": "changeLine",
			"lineStart": "beginning",
		}
		controls: list[tuple[str, dict]] = []
		frames = b"".join(
			encode_frame(MessageFactory().create("brailleRouteAction", value))
			for value in (payload, {**payload, "action": "dd"})
		)
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["brailleRoutingActions"]},
			io.BytesIO(frames),
			io.BytesIO(),
			on_control=lambda kind, value: controls.append((kind, value)),
			heartbeat_seconds=10.0,
		)
		self.assertIn(
			"brailleRoutingActions",
			transport._state_with_capabilities()["_transport"]["capabilities"],
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([("brailleRouteAction", payload)], controls)
		transport.stop()

		transport = StdioTransport(
			lambda: {"pluginCapabilities": []},
			io.BytesIO(),
			io.BytesIO(),
			heartbeat_seconds=10.0,
		)
		self.assertNotIn(
			"brailleRoutingActions",
			transport._state_with_capabilities()["_transport"]["capabilities"],
		)

	def test_braille_exploration_controls_are_independent_validated_and_gated(self) -> None:
		step = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "lineDown",
			"count": 1,
			"bufferId": 3,
			"windowId": 4,
			"tabpageId": 5,
			"changedtick": 6,
			"modeRaw": "n",
			"cursorLine": 7,
			"cursorByteColumn": 0,
			"cursorVirtualColumn": 0,
			"desiredVirtualColumn": 79,
			"targetColumn": "preferred",
		}
		controls = b"".join(
			(
				encode_frame(MessageFactory().create("brailleExploreLineRequest", step)),
				encode_frame(
					MessageFactory().create(
						"endBrailleExplorationRequest",
						{"requestId": 2, "explorationId": 2},
					)
				),
				encode_frame(
					MessageFactory().create(
						"brailleExploreLineRequest",
						{**step, "action": "wordNext"},
					)
				),
			)
		)
		dispatched = []
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["brailleExploration"]},
			io.BytesIO(controls),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual(
			["brailleExploreLineRequest", "endBrailleExplorationRequest"],
			[kind for kind, _payload in dispatched],
		)
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

	def test_developer_context_controls_are_validated_and_capability_gated(self) -> None:
		payload = {
			"requestId": 1,
			"bufferId": 2,
			"windowId": 3,
			"tabpageId": 4,
			"changedtick": 5,
			"line": 6,
			"byteColumn": 7,
		}
		controls = b"".join(
			(
				encode_frame(MessageFactory().create("callableContextRequest", payload)),
				encode_frame(MessageFactory().create("diagnosticContextRequest", payload)),
				encode_frame(
					MessageFactory().create(
						"callableContextRequest",
						{**payload, "extra": True},
					)
				),
			)
		)
		dispatched = []
		transport = StdioTransport(
			lambda: {
				"pluginCapabilities": [
					"callableContextQuery",
					"diagnosticContextQuery",
					"diagnosticCursorSummary",
				],
			},
			io.BytesIO(controls),
			io.BytesIO(),
			on_control=lambda kind, value: dispatched.append((kind, value)),
			heartbeat_seconds=10.0,
		)
		capabilities = transport._state_with_capabilities()["_transport"]["capabilities"]
		self.assertIn("callableContextQuery", capabilities)
		self.assertIn("diagnosticContextQuery", capabilities)
		self.assertIn("diagnosticCursorSummary", capabilities)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual(
			["callableContextRequest", "diagnosticContextRequest"],
			[kind for kind, _payload in dispatched],
		)
		transport.stop()

		dispatched.clear()
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["callableContextQuery"]},
			io.BytesIO(
				encode_frame(
					MessageFactory().create("diagnosticContextRequest", payload),
				)
			),
			io.BytesIO(),
			on_control=lambda kind, value: dispatched.append((kind, value)),
			heartbeat_seconds=10.0,
		)
		self.assertNotIn(
			"diagnosticContextQuery",
			transport._state_with_capabilities()["_transport"]["capabilities"],
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([], dispatched)
		transport.stop()

	def test_active_parameter_capability_is_forwarded_only_when_advertised(self) -> None:
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["activeParameterHints"]},
			io.BytesIO(),
			io.BytesIO(),
			heartbeat_seconds=10.0,
		)
		self.assertIn(
			"activeParameterHints",
			transport._state_with_capabilities()["_transport"]["capabilities"],
		)
		self.assertNotIn(
			"activeParameterHints",
			transport._state_with_capabilities({"pluginCapabilities": []})["_transport"][
				"capabilities"
			],
		)

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

	def test_numbered_choice_accept_is_exact_and_capability_gated(self) -> None:
		request = {
			"requestId": 8,
			"choiceKind": "spellSuggestions",
			"choiceId": 7,
			"itemIndex": 1,
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
		}
		controls = b"".join(
			(
				encode_frame(MessageFactory().create("acceptNumberedChoiceRequest", request)),
				encode_frame(
					MessageFactory().create(
						"acceptNumberedChoiceRequest",
						{**request, "itemIndex": -1},
					)
				),
			)
		)
		dispatched = []
		transport = StdioTransport(
			lambda: {"pluginCapabilities": ["numberedChoices"]},
			io.BytesIO(controls),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
		)
		self.assertIn(
			"numberedChoices",
			transport._state_with_capabilities()["_transport"]["capabilities"],
		)
		transport.start()
		self.assertTrue(transport.closed.wait(1.0))
		self.assertEqual([("acceptNumberedChoiceRequest", request)], dispatched)
		transport.stop()

		dispatched.clear()
		transport = StdioTransport(
			lambda: {},
			io.BytesIO(
				encode_frame(
					MessageFactory().create("acceptNumberedChoiceRequest", request),
				)
			),
			io.BytesIO(),
			on_control=lambda kind, payload: dispatched.append((kind, payload)),
			heartbeat_seconds=10.0,
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
