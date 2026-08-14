from __future__ import annotations

import threading
import unittest

from nvim_nvda_bridge import Bridge

from nvim_bridge_test_support import RecordingTransport, drain_tui_output


class NvimBridgeMockTests(unittest.TestCase):
	def test_tui_output_drain_is_bounded(self) -> None:
		class ContinuousOutput:
			def read_nonblocking(self, size: int, timeout: float) -> bytes:
				return b"x" * size

		with self.assertRaisesRegex(AssertionError, "byte limit"):
			drain_tui_output(ContinuousOutput(), byte_limit=131072, time_limit=1.0)

	def test_plugin_manager_lifecycle_is_validated_before_publication(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge._active_numbered_choice = None
		bridge.transport = transport
		payload = {
			"pluginManagerKind": "lazyNvim",
			"pluginManagerOperation": "update",
			"pluginManagerPhase": "started",
		}
		bridge._on_nvim_event("pluginManagerOperation", payload)
		self.assertEqual("pluginManagerOperation", transport.events[-1]["type"])
		bridge._on_nvim_event(
			"pluginManagerOperation",
			{**payload, "pluginManagerOperation": "arbitrary"},
		)
		self.assertEqual(1, len(transport.events))
		self.assertNotIn("pluginManagerKind", bridge.full_state())
		self.assertNotIn("pluginManagerOperation", bridge.full_state())

	def test_tutor_transition_is_validated_before_publication(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {"lineText": "previous"}
		bridge._active_numbered_choice = None
		bridge.transport = transport
		payload = {"filetype": "tutor", "tutorExerciseStatus": "correct"}
		bridge._on_nvim_event("tutorExerciseChanged", payload)
		self.assertEqual("tutorExerciseChanged", transport.events[-1]["type"])
		self.assertEqual("correct", bridge.full_state()["tutorExerciseStatus"])
		bridge._on_nvim_event(
			"tutorExerciseChanged",
			{**payload, "tutorExerciseStatus": "arbitrary"},
		)
		bridge._on_nvim_event(
			"tutorExerciseChanged",
			{**payload, "tutorExerciseStatus": []},
		)
		self.assertEqual(1, len(transport.events))
		self.assertEqual("correct", bridge.full_state()["tutorExerciseStatus"])

	def test_active_parameter_transition_is_validated_before_publication(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {"pluginCapabilities": ["activeParameterHints"]}
		bridge._active_numbered_choice = None
		bridge.transport = transport
		payload = {
			"mode": "insert",
			"modeRaw": "i",
			"pluginCapabilities": ["activeParameterHints"],
			"bufferId": 1,
			"windowId": 2,
			"changedtick": 3,
			"cursor": {"line": 4, "byteColumn": 5},
			"callName": "sum",
			"callStartLine": 4,
			"callStartByteColumn": 3,
			"signature": "sum(first, second)",
			"signatureIndex": 1,
			"signatureCount": 1,
			"activeParameter": 1,
			"parameterCount": 2,
			"parameter": "first",
			"hintReason": "callEntered",
		}
		bridge._on_nvim_event("activeParameterChanged", payload)
		self.assertEqual("activeParameterChanged", transport.events[-1]["type"])
		bridge._on_nvim_event("activeParameterChanged", {**payload, "parameterCount": 0})
		self.assertEqual(1, len(transport.events))
		bridge._state = {"pluginCapabilities": []}
		bridge._on_nvim_event("activeParameterChanged", payload)
		self.assertEqual(1, len(transport.events))

	def test_cursor_routing_uses_only_fixed_validated_plugin_entry_point(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		payload = {
			"target": "editor",
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"byteColumn": 4,
			"changedtick": 5,
			"modeRaw": "i",
		}
		bridge._on_client_control("routeCursor", payload)
		bridge._on_client_control("routeCursor", {**payload, "modeRaw": "c"})
		self.assertEqual(1, len(notifications))
		self.assertEqual("nvim_exec_lua", notifications[0][0])
		self.assertIn("request_route_cursor", notifications[0][1][0])
		self.assertEqual([payload], notifications[0][1][1])

	def test_braille_line_navigation_uses_only_fixed_capability_gated_entry_point(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {"pluginCapabilities": ["brailleLineNavigation"]}
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
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
		bridge._on_client_control("moveBrailleLine", payload)
		bridge._on_client_control("moveBrailleLine", {**payload, "modeRaw": "c"})
		bridge._state = {"pluginCapabilities": []}
		bridge._on_client_control("moveBrailleLine", payload)
		self.assertEqual(1, len(notifications))
		self.assertEqual("nvim_exec_lua", notifications[0][0])
		self.assertIn("request_move_braille_line", notifications[0][1][0])
		self.assertEqual([payload], notifications[0][1][1])

	def test_repeated_braille_routing_uses_only_fixed_capability_gated_entry_point(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {"pluginCapabilities": ["brailleRoutingActions"]}
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		payload = {
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"byteColumn": 4,
			"changedtick": 5,
			"modeRaw": "n",
			"action": "deleteLine",
			"lineStart": "routing",
		}
		bridge._on_client_control("brailleRouteAction", payload)
		bridge._on_client_control("brailleRouteAction", {**payload, "action": "dd"})
		bridge._state = {"pluginCapabilities": []}
		bridge._on_client_control("brailleRouteAction", payload)
		self.assertEqual(1, len(notifications))
		self.assertEqual("nvim_exec_lua", notifications[0][0])
		self.assertIn("request_braille_route_action", notifications[0][1][0])
		self.assertEqual([payload], notifications[0][1][1])

	def test_braille_exploration_uses_separate_fixed_capability_gated_entry_points(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {"pluginCapabilities": ["brailleExploration"]}
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		payload = {
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
		bridge._on_client_control("brailleExploreLineRequest", payload)
		bridge._on_client_control(
			"endBrailleExplorationRequest",
			{"requestId": 2, "explorationId": 2},
		)
		bridge._on_client_control("brailleExploreLineRequest", {**payload, "action": "wordNext"})
		bridge._state = {"pluginCapabilities": ["exploration"]}
		bridge._on_client_control("brailleExploreLineRequest", payload)
		self.assertEqual(2, len(notifications))
		self.assertIn("request_braille_explore_line", notifications[0][1][0])
		self.assertIn("request_end_braille_exploration", notifications[1][1][0])

	def test_bridge_publishes_braille_exploration_once_but_never_caches_it(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge.transport = transport
		result = {
			"mode": "normal",
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "lineDown",
			"unit": "line",
			"ok": True,
			"resultCode": "moved",
			"text": "virtual line",
			"line": 2,
			"byteColumn": 0,
			"characterColumn": 0,
			"virtualColumn": 0,
			"atOrigin": False,
		}
		bridge._on_nvim_event("brailleExploreLineResult", result)
		self.assertEqual("virtual line", transport.events[-1]["payload"]["text"])
		self.assertNotIn("text", bridge.full_state())
		self.assertNotIn("explorationId", bridge.full_state())
		bridge._on_nvim_event("brailleExploreLineResult", {**result, "unit": "word"})
		self.assertEqual(1, len(transport.events))

	def test_clipboard_control_uses_only_fixed_plugin_entry_points(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		state = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
			"modeRaw": "n",
			"requestId": 5,
		}
		bridge._on_client_control("copyTextRequest", {**state, "source": "yankRegister"})
		bridge._on_client_control("pasteTextRequest", {**state, "text": "remote text"})
		bridge._on_client_control("setRegisterRequest", {**state, "text": "current register"})
		bridge._on_client_control("pasteTextRequest", {**state, "text": "bad\0text"})
		self.assertEqual(3, len(notifications))
		self.assertTrue(all(method == "nvim_exec_lua" for method, _ in notifications))
		self.assertIn("request_copy_text", notifications[0][1][0])
		self.assertIn("request_paste_text", notifications[1][1][0])
		self.assertIn("request_set_register", notifications[2][1][0])

	def test_terminal_control_uses_only_its_fixed_plugin_entry_point(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		state = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"modeRaw": "t",
			"requestId": 5,
		}
		bridge._on_client_control("leaveTerminalInputRequest", state)
		bridge._on_client_control("leaveTerminalInputRequest", {**state, "modeRaw": "n"})
		self.assertEqual(1, len(notifications))
		self.assertEqual("nvim_exec_lua", notifications[0][0])
		self.assertIn("request_leave_terminal_input", notifications[0][1][0])

	def test_exploration_uses_only_fixed_bounded_plugin_entry_points(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		payload = {
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
		}
		bridge._on_client_control("exploreTextRequest", payload)
		bridge._on_client_control(
			"endExplorationRequest",
			{
				"requestId": 2,
				"explorationId": 2,
			},
		)
		bridge._on_client_control("exploreTextRequest", {**payload, "action": "arbitrary"})
		self.assertEqual(2, len(notifications))
		self.assertIn("request_explore_text", notifications[0][1][0])
		self.assertIn("request_end_exploration", notifications[1][1][0])

	def test_developer_context_uses_only_fixed_capability_gated_entry_points(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {
			"pluginCapabilities": [
				"callableContextQuery",
				"diagnosticContextQuery",
			],
		}
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		payload = {
			"requestId": 1,
			"bufferId": 2,
			"windowId": 3,
			"tabpageId": 4,
			"changedtick": 5,
			"line": 6,
			"byteColumn": 7,
		}
		bridge._on_client_control("callableContextRequest", payload)
		bridge._on_client_control("diagnosticContextRequest", payload)
		bridge._on_client_control("callableContextRequest", {**payload, "line": 0})
		bridge._state = {"pluginCapabilities": []}
		bridge._on_client_control("diagnosticContextRequest", payload)
		self.assertEqual(2, len(notifications))
		self.assertIn("request_callable_context", notifications[0][1][0])
		self.assertIn("request_diagnostic_context", notifications[1][1][0])
		self.assertEqual([payload], notifications[0][1][1])
		self.assertEqual([payload], notifications[1][1][1])

	def test_bridge_publishes_developer_context_once_but_never_caches_it(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge.transport = transport
		request = {
			"requestId": 1,
			"bufferId": 2,
			"windowId": 3,
			"tabpageId": 4,
			"changedtick": 5,
			"line": 6,
			"byteColumn": 7,
		}
		result = {
			**request,
			"ok": True,
			"resultCode": "ok",
			"items": [
				{
					"signature": "calculate_total(price, quantity)",
					"parameters": ["price", "quantity"],
					"documentation": "",
				},
			],
			"activeItem": 0,
			"activeParameter": 0,
		}
		bridge._on_nvim_event("callableContextResult", result)
		self.assertEqual(result["items"], transport.events[-1]["payload"]["items"])
		self.assertNotIn("items", bridge.full_state())
		self.assertNotIn("requestId", bridge.full_state())
		diagnostic = {
			"message": "Undefined name",
			"severity": "error",
			"source": "ruff",
			"code": "F821",
			"line": 6,
			"byteColumn": 7,
			"endLine": 6,
			"endByteColumn": 12,
			"atCursor": True,
		}
		bridge._on_nvim_event(
			"diagnosticContextResult",
			{
				**request,
				"ok": True,
				"resultCode": "ok",
				"items": [diagnostic],
				"activeItem": 0,
				"activeParameter": 0,
			},
		)
		self.assertEqual([diagnostic], transport.events[-1]["payload"]["items"])
		self.assertNotIn("items", bridge.full_state())
		bridge._on_nvim_event("callableContextResult", {**result, "bufferId": 0})
		bridge._on_nvim_event(
			"diagnosticContextResult",
			{
				**request,
				"ok": True,
				"resultCode": "ok",
				"items": [diagnostic],
				"activeItem": 0,
				"activeParameter": 1,
			},
		)
		self.assertEqual(2, len(transport.events))

	def test_bridge_publishes_clipboard_text_once_but_never_caches_it(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge.transport = transport
		bridge._on_nvim_event(
			"copyTextResult",
			{
				"mode": "normal",
				"requestId": 9,
				"ok": True,
				"resultCode": "copied",
				"clipboardText": "private text",
			},
		)
		self.assertEqual("private text", transport.events[-1]["payload"]["clipboardText"])
		self.assertNotIn("clipboardText", bridge.full_state())
		self.assertNotIn("requestId", bridge.full_state())

	def test_bridge_publishes_valid_exploration_once_but_never_caches_it(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge.transport = transport
		result = {
			"mode": "normal",
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "wordNext",
			"unit": "word",
			"ok": True,
			"resultCode": "moved",
			"text": "beta",
			"line": 1,
			"byteColumn": 6,
			"characterColumn": 6,
			"virtualColumn": 6,
			"atOrigin": False,
		}
		bridge._on_nvim_event("exploreTextResult", result)
		self.assertEqual("beta", transport.events[-1]["payload"]["text"])
		self.assertNotIn("text", bridge.full_state())
		self.assertNotIn("explorationId", bridge.full_state())
		bridge._on_nvim_event("exploreTextResult", {**result, "action": "arbitrary"})
		self.assertEqual(1, len(transport.events))

	def test_bridge_accepts_only_the_exact_active_numbered_choice(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {"pluginCapabilities": ["numberedChoices"]}
		bridge.transport = RecordingTransport()
		bridge._active_numbered_choice = {
			"choiceKind": "spellSuggestions",
			"choiceId": 7,
			"items": ["misspelled", "misapplied"],
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
		}
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
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

		bridge._on_client_control("acceptNumberedChoiceRequest", request)
		bridge._on_client_control(
			"acceptNumberedChoiceRequest",
			{**request, "windowId": 9},
		)
		self.assertEqual([("nvim_input", ("2\r",))], notifications)
		bridge._on_nvim_connection("disconnected")
		self.assertIsNone(bridge._active_numbered_choice)


if __name__ == "__main__":
	unittest.main()
