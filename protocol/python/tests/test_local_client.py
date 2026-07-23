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
			"127.0.0.1",
			45678,
			events.append,
			states.append,
			lambda category, fields: diagnostics.append((category, fields)),
			source_factory,
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

	def test_focus_context_control_correlates_cached_state(self) -> None:
		client, source, events, _states, diagnostics = self.make_client()
		source.on_event("fullState", {"mode": "insert", "bufferName": "example.txt"})
		self.assertTrue(client.send_control("requestFocusContext", {"requestId": 7}))
		self.assertEqual("focusContext", events[-1]["type"])
		self.assertEqual(7, events[-1]["payload"]["_focusRequestId"])
		self.assertEqual("example.txt", events[-1]["payload"]["bufferName"])
		for value in (True, -1, 2_147_483_648, None):
			self.assertFalse(client.send_control("requestFocusContext", {"requestId": value}))
		self.assertEqual(4, sum(category == "controlRejected" for category, _ in diagnostics))

	def test_cursor_control_is_validated_before_rpc_notification(self) -> None:
		client, source, _events, _states, diagnostics = self.make_client()
		self.assertFalse(client.send_control("routeCursor", {"line": 1}))
		payload = {
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"byteColumn": 4,
			"changedtick": 5,
		}
		self.assertTrue(client.send_control("routeCursor", payload))
		self.assertEqual("nvim_exec_lua", source.notifications[0][0])
		self.assertEqual([payload], source.notifications[0][1][1])
		self.assertEqual("controlRejected", diagnostics[0][0])

	def test_clipboard_controls_are_fixed_validated_rpc_calls(self) -> None:
		client, source, _events, _states, diagnostics = self.make_client()
		state = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
			"modeRaw": "n",
			"requestId": 5,
		}
		self.assertTrue(
			client.send_control(
				"copyTextRequest",
				{
					**state,
					"source": "yankRegister",
				},
			)
		)
		self.assertTrue(
			client.send_control(
				"pasteTextRequest",
				{
					**state,
					"text": "local text",
				},
			)
		)
		self.assertTrue(
			client.send_control(
				"setRegisterRequest",
				{
					**state,
					"text": "new current register",
				},
			)
		)
		self.assertFalse(
			client.send_control(
				"copyTextRequest",
				{
					**state,
					"source": "arbitraryRegister",
				},
			)
		)
		self.assertEqual(
			["nvim_exec_lua", "nvim_exec_lua", "nvim_exec_lua"],
			[notification[0] for notification in source.notifications],
		)
		self.assertIn("request_copy_text", source.notifications[0][1][0])
		self.assertIn("request_paste_text", source.notifications[1][1][0])
		self.assertIn("request_set_register", source.notifications[2][1][0])
		self.assertEqual("controlRejected", diagnostics[-1][0])

	def test_terminal_control_is_a_fixed_validated_rpc_call(self) -> None:
		client, source, _events, _states, diagnostics = self.make_client()
		payload = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"modeRaw": "t",
			"requestId": 5,
		}
		self.assertTrue(client.send_control("leaveTerminalInputRequest", payload))
		self.assertFalse(
			client.send_control(
				"leaveTerminalInputRequest",
				{
					**payload,
					"modeRaw": "n",
				},
			)
		)
		self.assertEqual("nvim_exec_lua", source.notifications[0][0])
		self.assertIn("request_leave_terminal_input", source.notifications[0][1][0])
		self.assertEqual("controlRejected", diagnostics[-1][0])

	def test_terminal_control_result_fields_never_enter_cached_full_state(self) -> None:
		client, source, events, _states, _diagnostics = self.make_client()
		source.on_event("fullState", {"mode": "terminal", "bufferId": 1})
		source.on_event(
			"leaveTerminalInputResult",
			{
				"mode": "terminalNormal",
				"bufferId": 1,
				"requestId": 7,
				"ok": True,
				"resultCode": "ok",
			},
		)
		self.assertTrue(client.send_control("requestFullState", {}))
		self.assertEqual("terminalNormal", events[-1]["payload"]["mode"])
		self.assertNotIn("requestId", events[-1]["payload"])
		self.assertNotIn("resultCode", events[-1]["payload"])

	def test_exploration_controls_are_fixed_validated_rpc_calls(self) -> None:
		client, source, _events, _states, diagnostics = self.make_client()
		source.on_event("fullState", {"pluginCapabilities": ["exploration"]})
		payload = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "characterRight",
			"count": 1,
			"bufferId": 3,
			"windowId": 4,
			"tabpageId": 5,
			"changedtick": 6,
			"modeRaw": "n",
			"cursorLine": 7,
			"cursorByteColumn": 0,
			"cursorVirtualColumn": 0,
		}
		self.assertTrue(client.send_control("exploreTextRequest", payload))
		self.assertTrue(
			client.send_control(
				"endExplorationRequest",
				{
					"requestId": 2,
					"explorationId": 2,
				},
			)
		)
		self.assertFalse(
			client.send_control(
				"exploreTextRequest",
				{
					**payload,
					"action": "executeLua",
				},
			)
		)
		self.assertIn("request_explore_text", source.notifications[0][1][0])
		self.assertIn("request_end_exploration", source.notifications[1][1][0])
		self.assertEqual("controlRejected", diagnostics[-1][0])

	def test_exploration_is_not_advertised_or_dispatched_without_plugin_support(self) -> None:
		client, source, events, _states, diagnostics = self.make_client()
		source.on_event("fullState", {"mode": "normal"})
		self.assertNotIn("exploration", events[-1]["payload"]["_transport"]["capabilities"])
		self.assertFalse(
			client.send_control(
				"exploreTextRequest",
				{
					"requestId": 1,
					"explorationId": 2,
					"actionIndex": 1,
					"action": "characterRight",
					"count": 1,
					"bufferId": 3,
					"windowId": 4,
					"tabpageId": 5,
					"changedtick": 6,
					"modeRaw": "n",
					"cursorLine": 7,
					"cursorByteColumn": 0,
					"cursorVirtualColumn": 0,
				},
			)
		)
		self.assertEqual([], source.notifications)
		self.assertEqual("capabilityMissing", diagnostics[-1][1]["reason"])

	def test_exploration_result_is_validated_and_never_pollutes_cached_state(self) -> None:
		client, source, events, _states, diagnostics = self.make_client()
		source.on_event(
			"fullState",
			{
				"mode": "normal",
				"bufferId": 1,
				"pluginCapabilities": ["exploration"],
			},
		)
		result = {
			"mode": "normal",
			"bufferId": 1,
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "characterRight",
			"unit": "character",
			"ok": True,
			"resultCode": "moved",
			"text": "b",
			"line": 1,
			"byteColumn": 1,
			"characterColumn": 1,
			"virtualColumn": 1,
		}
		source.on_event("exploreTextResult", result)
		self.assertEqual("b", events[-1]["payload"]["text"])
		self.assertTrue(client.send_control("requestFullState", {}))
		self.assertEqual("normal", events[-1]["payload"]["mode"])
		self.assertNotIn("text", events[-1]["payload"])
		self.assertNotIn("explorationId", events[-1]["payload"])
		source.on_event("exploreTextResult", {**result, "text": "x" * (16 * 1024 + 1)})
		self.assertEqual("localEventRejected", diagnostics[-1][0])

	def test_clipboard_result_text_never_enters_cached_full_state(self) -> None:
		client, source, events, _states, _diagnostics = self.make_client()
		source.on_event("fullState", {"mode": "visualCharacter", "bufferId": 1})
		source.on_event(
			"copyTextResult",
			{
				"mode": "visualCharacter",
				"bufferId": 1,
				"requestId": 7,
				"ok": True,
				"resultCode": "copied",
				"clipboardText": "private text",
			},
		)
		self.assertEqual("private text", events[-1]["payload"]["clipboardText"])
		self.assertTrue(client.send_control("requestFullState", {}))
		self.assertNotIn("clipboardText", events[-1]["payload"])
		self.assertNotIn("requestId", events[-1]["payload"])

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
