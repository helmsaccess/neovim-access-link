from __future__ import annotations

import builtins
import importlib.util
import pathlib
import sys
import types
import unittest


PLUGIN_ROOT = pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink"
PACKAGE_NAME = "nvim_nvda_event_delivery_test_package"


def load_delivery_module():
	package = types.ModuleType(PACKAGE_NAME)
	package.__path__ = [str(PLUGIN_ROOT)]
	sys.modules[PACKAGE_NAME] = package

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.initTranslation = lambda: None
	sys.modules["addonHandler"] = addon_handler
	braille_module = types.ModuleType("braille")
	braille_module.handler = object()
	sys.modules["braille"] = braille_module
	config_module = types.ModuleType("config")
	config_module.conf = {"keyboard": {}, "braille": {}}
	sys.modules["config"] = config_module
	speech_module = types.ModuleType("speech")
	speech_module.clearTypedWordBuffer = lambda: None
	speech_module.speakSpelling = lambda *_args, **_kwargs: None
	speech_module.speakText = lambda *_args, **_kwargs: None
	sys.modules["speech"] = speech_module
	ui_module = types.ModuleType("ui")
	ui_module.messages = []
	ui_module.message = ui_module.messages.append
	sys.modules["ui"] = ui_module
	log_module = types.ModuleType("logHandler")
	log_module.log = types.SimpleNamespace(debug=lambda *_args: None, exception=lambda *_args: None)
	sys.modules["logHandler"] = log_module
	nvda_braille = types.ModuleType(f"{PACKAGE_NAME}.nvda_braille")
	nvda_braille.capture_structured_viewport = lambda _handler: None
	nvda_braille.restore_structured_viewport = lambda _handler, _position: False
	nvda_braille.StructuredTerminalBrailleOverlay = type("StructuredTerminalBrailleOverlay", (), {})
	sys.modules[nvda_braille.__name__] = nvda_braille
	builtins._ = lambda text: text

	module_name = f"{PACKAGE_NAME}.event_delivery"
	spec = importlib.util.spec_from_file_location(module_name, PLUGIN_ROOT / "event_delivery.py")
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load event delivery")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


DELIVERY_MODULE = load_delivery_module()
EventDelivery = DELIVERY_MODULE.EventDelivery


class _Diagnostics:
	def __init__(self) -> None:
		self.entries = []

	def record(self, category, **fields) -> None:
		self.entries.append((category, fields))


class _Scheduler:
	def __init__(self) -> None:
		self.calls = []

	def queue(self, callback, *args, immediate=False):
		self.calls.append((callback, args, immediate))
		return True


class _Instances:
	def __init__(self) -> None:
		self.selected = {}
		self.clients = {}

	def selected_for(self, identity):
		return self.selected.get(identity)

	def client_for(self, instance_id):
		if instance_id not in self.clients:
			raise ValueError("unknown instance")
		return self.clients[instance_id]


class _Gate:
	def __init__(self) -> None:
		self.focused = "terminal-1"
		self.authenticated = False
		self.nvim_active = False
		self.bound_terminal = None
		self.manual_enabled = True
		self.disconnect_calls = 0

	@property
	def suppression_active(self):
		return self.authenticated and self.nvim_active and self.bound_terminal == self.focused

	def disconnect(self) -> None:
		self.disconnect_calls += 1
		self.authenticated = False
		self.nvim_active = False
		self.bound_terminal = None


class _Coordinator:
	def __init__(self) -> None:
		self.gate = _Gate()
		self.instances = _Instances()
		self.authenticated_instances = set()
		self.pending_full_states = {}
		self.pending_focus_contexts = {}
		self.terminal_passthrough = {}
		self.active_instance_id = None
		self.active_client = object()
		self.matches = False
		self.foreground_confirmed = False
		self.calls = []

	def matches_focus_context(self, instance_id, request_id, identity):
		return self.matches

	def discard_focus_context(self, instance_id=None):
		self.calls.append(("discardFocus", instance_id))

	def confirm_foreground_instance(self, instance_id, identity, new_runtime):
		self.calls.append(("confirm", instance_id, identity, new_runtime))
		self.foreground_confirmed = True

	def select_instance(self, instance_id, identity, new_runtime):
		self.calls.append(("select", instance_id, identity, new_runtime))
		self.active_instance_id = instance_id

	def is_foreground_instance_confirmed(self, instance_id, identity):
		return self.foreground_confirmed


class _EditorSession:
	def __init__(self) -> None:
		self.new_runtime = object()
		self.calls = []
		self.connection_transitions = []

	def discard_clipboard_requests(self, instance_id=None):
		self.calls.append(("discardClipboard", instance_id))

	def discard_terminal_control_requests(self, instance_id=None):
		self.calls.append(("discardTerminal", instance_id))

	def mark_disconnected(self):
		self.calls.append(("markDisconnected",))

	def reset_disconnected_instance(self, instance_id):
		self.calls.append(("resetDisconnected", instance_id))

	def switch_instance(self, instance_id):
		self.calls.append(("switch", instance_id))

	def apply_connection_state(self, state, *, reset_runtime):
		self.calls.append(("connectionState", state, reset_runtime))
		return self.connection_transitions.pop(0)


class _Presentation:
	def __init__(self) -> None:
		self.connection_sounds = 0
		self.disconnection_sounds = 0

	def play_connection_sound(self):
		self.connection_sounds += 1

	def play_disconnection_sound(self):
		self.disconnection_sounds += 1


class _Integration:
	def __init__(self) -> None:
		self.calls = []

	def __getattr__(self, name):
		def operation(*args, **kwargs):
			self.calls.append((name, args, kwargs))
			return True

		return operation


def make_delivery():
	coordinator = _Coordinator()
	editor = _EditorSession()
	presentation = _Presentation()
	scheduler = _Scheduler()
	diagnostics = _Diagnostics()
	binding_offers = []
	session_claim = types.SimpleNamespace(
		consume_temporary_binding_offer=lambda _instance_id: False,
		is_temporary_binding_remembered=lambda _identity: False,
	)
	delivery = EventDelivery(
		coordinator=coordinator,
		editor_session=editor,
		terminal_actions=types.SimpleNamespace(),
		session_claim=session_claim,
		terminal_focus=types.SimpleNamespace(identity_fields=lambda identity: {"identity": identity}),
		settings=types.SimpleNamespace(
			focus_announcement=lambda: "", navigation_details=lambda **_k: (0, 0, 0)
		),
		presentation=presentation,
		scheduler=scheduler,
		diagnostics=diagnostics,
		offer_temporary_binding=lambda *args: binding_offers.append(args),
	)
	integration = _Integration()
	delivery.bind_terminal_integration(integration)
	return types.SimpleNamespace(
		delivery=delivery,
		coordinator=coordinator,
		editor=editor,
		presentation=presentation,
		scheduler=scheduler,
		diagnostics=diagnostics,
		integration=integration,
		session_claim=session_claim,
		binding_offers=binding_offers,
	)


class EventDeliveryTests(unittest.TestCase):
	def setUp(self) -> None:
		DELIVERY_MODULE.ui.messages.clear()

	def test_terminal_integration_is_bound_exactly_once(self) -> None:
		fixture = make_delivery()
		with self.assertRaisesRegex(RuntimeError, "exactly once"):
			fixture.delivery.bind_terminal_integration(object())

	def test_transport_callback_only_queues_the_correlated_event(self) -> None:
		fixture = make_delivery()
		event = {"type": "cursorMoved", "payload": {}}
		fixture.delivery.on_managed_event("connection-1", event)
		self.assertEqual(
			[(fixture.delivery.handle_managed_event, ("connection-1", event), False)],
			fixture.scheduler.calls,
		)

	def test_stale_focus_context_is_rejected_before_state_or_presentation(self) -> None:
		fixture = make_delivery()
		instance = types.SimpleNamespace(identifier="connection-1", context_label="Work")
		fixture.coordinator.instances.selected["terminal-1"] = instance
		fixture.coordinator.authenticated_instances.add("connection-1")
		fixture.delivery._handleEvent = lambda *_args, **_kwargs: self.fail("stale event was delivered")

		fixture.delivery.handle_managed_event(
			"connection-1",
			{"type": "focusContext", "payload": {"_focusRequestId": 7}},
		)

		self.assertNotIn("connection-1", fixture.coordinator.pending_full_states)
		self.assertIn(
			("focusContextIgnored", {"instanceId": "connection-1", "reason": "staleOrUnbound"}),
			fixture.diagnostics.entries,
		)
		self.assertFalse(any(call[0] == "select" for call in fixture.coordinator.calls))

	def test_unfocused_known_full_state_is_deferred_but_unknown_instance_is_dropped(self) -> None:
		fixture = make_delivery()
		fixture.coordinator.instances.clients["connection-1"] = object()
		first = {"type": "fullState", "payload": {"mode": "normal"}}
		fixture.delivery.handle_managed_event("connection-1", first)
		fixture.delivery.handle_managed_event(
			"unknown",
			{"type": "fullState", "payload": {"mode": "insert"}},
		)

		self.assertIs(first, fixture.coordinator.pending_full_states["connection-1"])
		self.assertNotIn("unknown", fixture.coordinator.pending_full_states)

	def test_authenticated_events_require_exact_foreground_confirmation(self) -> None:
		fixture = make_delivery()
		instance = types.SimpleNamespace(identifier="connection-1", context_label="Work")
		fixture.coordinator.instances.selected["terminal-1"] = instance
		fixture.coordinator.authenticated_instances.add("connection-1")
		fixture.delivery._handleEvent = lambda *_args, **_kwargs: self.fail("unconfirmed event delivered")

		fixture.delivery.handle_managed_event(
			"connection-1",
			{"type": "cursorMoved", "payload": {}},
		)

		self.assertIn(
			(
				"instanceEventIgnored",
				{
					"instanceId": "connection-1",
					"reason": "foregroundUnconfirmed",
				},
			),
			fixture.diagnostics.entries,
		)

	def test_valid_focus_context_confirms_before_delivery(self) -> None:
		fixture = make_delivery()
		instance = types.SimpleNamespace(identifier="connection-1", context_label="Work")
		fixture.coordinator.instances.selected["terminal-1"] = instance
		fixture.coordinator.authenticated_instances.add("connection-1")
		fixture.coordinator.matches = True
		delivered = []
		fixture.delivery._handleEvent = lambda event, **kwargs: delivered.append((event, kwargs))
		event = {"type": "focusContext", "payload": {"_focusRequestId": 7}}

		fixture.delivery.handle_managed_event("connection-1", event)

		self.assertEqual(("discardFocus", "connection-1"), fixture.coordinator.calls[0])
		self.assertEqual("confirm", fixture.coordinator.calls[1][0])
		self.assertEqual("select", fixture.coordinator.calls[2][0])
		self.assertEqual([(event, {"connection_label": "Work"})], delivered)

	def test_connection_sound_plays_once_per_authenticated_instance(self) -> None:
		fixture = make_delivery()
		instance = types.SimpleNamespace(identifier="connection-1", context_label="Work")
		fixture.coordinator.instances.selected["terminal-1"] = instance
		fixture.coordinator.foreground_confirmed = True
		fixture.coordinator.active_instance_id = "connection-1"
		fixture.coordinator.gate.authenticated = True
		fixture.coordinator.gate.nvim_active = True
		fixture.coordinator.gate.bound_terminal = "terminal-1"
		fixture.delivery._handleEvent = lambda *_args, **_kwargs: None
		event = {"type": "fullState", "payload": {}}

		fixture.delivery.handle_managed_event("connection-1", event)
		fixture.delivery.handle_managed_event("connection-1", event)

		self.assertEqual(1, fixture.presentation.connection_sounds)
		self.assertEqual({"connection-1"}, fixture.coordinator.authenticated_instances)

	def test_successful_f12_binding_is_retained_in_same_full_state_transition(self) -> None:
		fixture = make_delivery()
		instance = types.SimpleNamespace(identifier="connection-1", context_label="Work")
		fixture.coordinator.instances.selected["terminal-1"] = instance
		fixture.session_claim.consume_temporary_binding_offer = lambda _instance_id: True
		fixture.delivery._handleEvent = lambda *_args, **_kwargs: None

		fixture.delivery.handle_managed_event(
			"connection-1",
			{"type": "fullState", "payload": {}},
		)

		self.assertEqual([("terminal-1", "connection-1")], fixture.binding_offers)
		self.assertEqual([], fixture.scheduler.calls)

	def test_active_disconnect_fails_open_before_queued_cleanup(self) -> None:
		fixture = make_delivery()
		fixture.coordinator.active_instance_id = "connection-1"
		fixture.coordinator.authenticated_instances.add("connection-1")
		fixture.coordinator.terminal_passthrough["connection-1"] = True
		fixture.coordinator.pending_full_states["connection-1"] = {}

		fixture.delivery.on_managed_state("connection-1", "disconnected")

		self.assertEqual(1, fixture.coordinator.gate.disconnect_calls)
		self.assertIn(("markDisconnected",), fixture.editor.calls)
		callback, args, _immediate = fixture.scheduler.calls[0]
		self.assertEqual(fixture.delivery._handleManagedState, callback)
		callback(*args)
		self.assertNotIn("connection-1", fixture.coordinator.authenticated_instances)
		self.assertNotIn("connection-1", fixture.coordinator.terminal_passthrough)
		self.assertNotIn("connection-1", fixture.coordinator.pending_full_states)

	def test_disconnection_cue_plays_only_for_the_real_loss_transition(self) -> None:
		fixture = make_delivery()
		fixture.editor.connection_transitions = [
			types.SimpleNamespace(previous="connected", connection_lost=True),
			types.SimpleNamespace(previous="disconnected", connection_lost=False),
		]
		fixture.delivery._refreshBraille = lambda **_kwargs: None

		fixture.delivery._handleConnectionState("disconnected")
		fixture.delivery._handleConnectionState("disconnected")

		self.assertEqual(1, fixture.presentation.disconnection_sounds)
		self.assertEqual(1, len(DELIVERY_MODULE.ui.messages))


if __name__ == "__main__":
	unittest.main()
