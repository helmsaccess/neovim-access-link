from __future__ import annotations

import builtins
from enum import Enum
import importlib.util
import pathlib
import sys
import types
import unittest


PLUGIN_ROOT = pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink"
PACKAGE_NAME = "nvim_nvda_terminal_actions_test_package"


class ControlReplyKind(Enum):
	ACCEPTED = "accepted"
	INVALID_REQUEST_ID = "invalidRequestId"
	STALE_OR_UNBOUND = "staleOrUnbound"


class ControlRequestRejection(Enum):
	CAPABILITY_MISSING = "capabilityMissing"
	VISUAL_SELECTION_REQUIRED = "visualSelectionRequired"
	PASTE_MODE_UNAVAILABLE = "pasteModeUnavailable"
	BUFFER_NOT_EDITABLE = "bufferNotEditable"
	NOT_DIRECT_TERMINAL = "notDirectTerminal"
	INCOMPLETE_STATE = "incompleteState"


def load_actions_module():
	package = types.ModuleType(PACKAGE_NAME)
	package.__path__ = [str(PLUGIN_ROOT)]
	sys.modules[PACKAGE_NAME] = package
	core_package = types.ModuleType(f"{PACKAGE_NAME}.core")
	core_package.__path__ = []
	sys.modules[core_package.__name__] = core_package
	clipboard_module = types.ModuleType(f"{PACKAGE_NAME}.core.clipboard")
	clipboard_module.MAX_CLIPBOARD_TEXT_BYTES = 256 * 1024
	clipboard_module.valid_clipboard_text = lambda text: (
		isinstance(text, str) and bool(text) and "\0" not in text and len(text.encode()) <= 256 * 1024
	)
	sys.modules[clipboard_module.__name__] = clipboard_module
	editor_module = types.ModuleType(f"{PACKAGE_NAME}.editor_session")
	editor_module.ControlReplyKind = ControlReplyKind
	editor_module.ControlRequestRejection = ControlRequestRejection
	sys.modules[editor_module.__name__] = editor_module

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.initTranslation = lambda: None
	sys.modules["addonHandler"] = addon_handler
	api_module = types.ModuleType("api")
	api_module.clipboard = ""
	api_module.copyToClip = lambda text: setattr(api_module, "clipboard", text) or True
	api_module.getClipData = lambda: api_module.clipboard
	sys.modules["api"] = api_module
	speech_module = types.ModuleType("speech")
	speech_module.__path__ = []
	speech_module.calls = []
	speech_module.speakText = lambda *args, **kwargs: speech_module.calls.append((args, kwargs))
	sys.modules["speech"] = speech_module
	priorities_module = types.ModuleType("speech.priorities")
	priorities_module.SpeechPriority = types.SimpleNamespace(NOW="now", NEXT="next")
	sys.modules[priorities_module.__name__] = priorities_module
	tones_module = types.ModuleType("tones")
	tones_module.calls = []
	tones_module.beep = lambda *args: tones_module.calls.append(args)
	sys.modules["tones"] = tones_module
	ui_module = types.ModuleType("ui")
	ui_module.messages = []
	ui_module.message = ui_module.messages.append
	sys.modules["ui"] = ui_module
	builtins._ = lambda text: text

	module_name = f"{PACKAGE_NAME}.terminal_actions"
	spec = importlib.util.spec_from_file_location(module_name, PLUGIN_ROOT / "terminal_actions.py")
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load terminal actions")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


ACTIONS_MODULE = load_actions_module()
TerminalActions = ACTIONS_MODULE.TerminalActions


class _Diagnostics:
	def __init__(self) -> None:
		self.entries = []

	def record(self, category, **fields) -> None:
		self.entries.append((category, fields))

	def report(self, header, *, product_name):
		return f"{product_name}: {header}"


class _Dispatcher:
	def __init__(self) -> None:
		self.calls = []
		self.accepted = True

	def submit(self, client, kind, payload, *, on_result):
		self.calls.append((client, kind, payload, on_result))
		return self.accepted


class _Instances:
	def __init__(self, selected) -> None:
		self.selected = selected

	def selected_for(self, identity):
		return self.selected if identity == "terminal-1" else None


class _EditorSession:
	def __init__(self) -> None:
		self.clipboard_plan = types.SimpleNamespace(
			ready=True,
			rejection=None,
			discarded_request_ids=(),
			control="copyTextRequest",
			payload={"requestId": 7},
			request_id=7,
		)
		self.terminal_plan = types.SimpleNamespace(
			ready=True,
			rejection=None,
			discarded_request_ids=(),
			control="leaveTerminalInputRequest",
			payload={"requestId": 8},
			request_id=8,
		)
		self.clipboard_reply = None
		self.finished_clipboard_reply = None
		self.terminal_reply = None
		self.calls = []

	def braille_exploration_enabled(self):
		return False

	def completion_documentation(self):
		return ""

	def validate_clipboard_request(self, kind):
		self.calls.append(("validateClipboard", kind))
		return None

	def plan_clipboard_request(self, instance_id, identity, kind, **kwargs):
		self.calls.append(("planClipboard", instance_id, identity, kind, kwargs))
		return self.clipboard_plan

	def plan_leave_terminal_input_request(self, instance_id, identity):
		self.calls.append(("planTerminal", instance_id, identity))
		return self.terminal_plan

	def cancel_clipboard_request(self, request_id):
		self.calls.append(("cancelClipboard", request_id))

	def cancel_terminal_control_request(self, request_id):
		self.calls.append(("cancelTerminal", request_id))

	def consume_clipboard_reply(self, instance_id, identity, event):
		self.calls.append(("consumeClipboard", instance_id, identity, event))
		return self.clipboard_reply

	def finish_clipboard_reply(self, reply, *, clipboard_written):
		self.calls.append(("finishClipboard", reply, clipboard_written))
		return self.finished_clipboard_reply

	def consume_terminal_control_reply(self, instance_id, identity, event):
		self.calls.append(("consumeTerminal", instance_id, identity, event))
		return self.terminal_reply

	def discard_clipboard_requests(self, instance_id=None):
		self.calls.append(("discardClipboard", instance_id))

	def discard_terminal_control_requests(self, instance_id=None):
		self.calls.append(("discardTerminal", instance_id))


def make_actions():
	client = object()
	instance = types.SimpleNamespace(identifier="connection-1")
	gate = types.SimpleNamespace(
		focused="terminal-1",
		manual_enabled=True,
		authenticated=True,
		nvim_active=True,
		bound_terminal="terminal-1",
		suppression_active=True,
	)
	coordinator = types.SimpleNamespace(
		gate=gate,
		instances=_Instances(instance),
		active_client=client,
		active_instance_id="connection-1",
		connected=True,
	)
	editor = _EditorSession()
	dispatcher = _Dispatcher()
	diagnostics = _Diagnostics()
	presentation = types.SimpleNamespace(feedback_mode=lambda _channel: 0)
	actions = TerminalActions(
		coordinator=coordinator,
		editor_session=editor,
		control_dispatcher=dispatcher,
		presentation=presentation,
		diagnostics=diagnostics,
		addon_version="test-version",
		product_name="test product",
		nvda_version=lambda: "2026.1.1",
	)
	return types.SimpleNamespace(
		actions=actions,
		coordinator=coordinator,
		editor=editor,
		dispatcher=dispatcher,
		diagnostics=diagnostics,
		client=client,
	)


class TerminalActionsTests(unittest.TestCase):
	def setUp(self) -> None:
		ACTIONS_MODULE.ui.messages.clear()
		ACTIONS_MODULE.speech.calls.clear()
		ACTIONS_MODULE.tones.calls.clear()
		ACTIONS_MODULE.api.clipboard = ""

	def test_copy_request_uses_exact_bound_foreground_client(self) -> None:
		fixture = make_actions()
		fixture.actions.copy_selection()

		client, kind, payload, _callback = fixture.dispatcher.calls[0]
		self.assertIs(fixture.client, client)
		self.assertEqual("copyTextRequest", kind)
		self.assertEqual({"requestId": 7}, payload)
		self.assertIn(
			("planClipboard", "connection-1", "terminal-1", "copyTextRequest", {"source": "visualSelection"}),
			fixture.editor.calls,
		)

	def test_unbound_or_unsuppressed_context_fails_open_without_dispatch(self) -> None:
		for field, value in (("authenticated", False), ("suppression_active", False)):
			with self.subTest(field=field):
				fixture = make_actions()
				setattr(fixture.coordinator.gate, field, value)
				fixture.actions.copy_selection()
				self.assertEqual([], fixture.dispatcher.calls)
				self.assertTrue(ACTIONS_MODULE.ui.messages)
				ACTIONS_MODULE.ui.messages.clear()

	def test_queue_rejection_cancels_exact_request_and_reports_failure(self) -> None:
		fixture = make_actions()
		fixture.dispatcher.accepted = False
		fixture.actions.copy_last_yank()

		self.assertIn(("cancelClipboard", 7), fixture.editor.calls)
		self.assertIn(
			(
				"clipboardCopyRequested",
				{
					"requestId": 7,
					"accepted": False,
					"errorType": "QueueUnavailable",
					"source": "yankRegister",
				},
			),
			fixture.diagnostics.entries,
		)

	def test_stale_and_invalid_clipboard_replies_never_reach_canonical_state(self) -> None:
		for kind, reason in (
			(ControlReplyKind.INVALID_REQUEST_ID, "invalidRequestId"),
			(ControlReplyKind.STALE_OR_UNBOUND, "staleOrUnbound"),
		):
			with self.subTest(kind=kind):
				fixture = make_actions()
				fixture.editor.clipboard_reply = types.SimpleNamespace(kind=kind, request_id=7)
				result = fixture.actions.handle_clipboard_result(
					"connection-1",
					"terminal-1",
					{"type": "copyTextResult", "payload": {}},
				)
				self.assertIsNone(result)
				self.assertEqual(reason, fixture.diagnostics.entries[-1][1]["reason"])

	def test_copy_result_writes_clipboard_then_returns_only_safe_event(self) -> None:
		fixture = make_actions()
		reply = types.SimpleNamespace(
			kind=ControlReplyKind.ACCEPTED,
			request_id=7,
			requires_clipboard_write=True,
			clipboard_text="copied text",
		)
		fixture.editor.clipboard_reply = reply
		fixture.editor.finished_clipboard_reply = types.SimpleNamespace(
			event_type="copyTextResult",
			ok=True,
			result_code="ok",
			request_id=7,
			safe_payload={"copiedCharacterCount": 11},
			safe_event={"type": "copyTextResult", "payload": {"lineText": "safe"}},
		)

		result = fixture.actions.handle_clipboard_result(
			"connection-1",
			"terminal-1",
			{"type": "copyTextResult", "payload": {"clipboardText": "untrusted"}},
		)

		self.assertEqual("copied text", ACTIONS_MODULE.api.clipboard)
		self.assertEqual({"type": "copyTextResult", "payload": {"lineText": "safe"}}, result)
		self.assertIn(("finishClipboard", reply, True), fixture.editor.calls)

	def test_leave_terminal_input_is_dispatched_and_queue_failure_cancels_it(self) -> None:
		fixture = make_actions()
		fixture.dispatcher.accepted = False
		fixture.actions.leave_direct_terminal_input()

		_client, kind, payload, _callback = fixture.dispatcher.calls[0]
		self.assertEqual("leaveTerminalInputRequest", kind)
		self.assertEqual({"requestId": 8}, payload)
		self.assertIn(("cancelTerminal", 8), fixture.editor.calls)


if __name__ == "__main__":
	unittest.main()
