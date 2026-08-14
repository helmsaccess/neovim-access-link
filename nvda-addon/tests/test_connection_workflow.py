from __future__ import annotations

import builtins
from enum import Enum
import importlib.util
import pathlib
import sys
import types
import unittest


PLUGIN_ROOT = pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink"
PACKAGE_NAME = "nvim_nvda_connection_workflow_test_package"


class ClaimTransitionKind(Enum):
	PASS_THROUGH = "passThrough"
	INVENTORY_PENDING = "inventoryPending"
	LOCAL = "local"
	REMOTE = "remote"
	AUTOMATIC = "automatic"


class DiscoverySelectionKind(Enum):
	STALE = "stale"
	ERROR = "error"
	EMPTY = "empty"
	FALLBACK = "fallback"
	CLAIM_MISSING = "claimMissing"
	SELECT = "select"
	CHOOSE = "choose"


def load_workflow_module():
	package = types.ModuleType(PACKAGE_NAME)
	package.__path__ = [str(PLUGIN_ROOT)]
	sys.modules[PACKAGE_NAME] = package
	core_package = types.ModuleType(f"{PACKAGE_NAME}.core")
	core_package.__path__ = []
	sys.modules[core_package.__name__] = core_package
	profiles_module = types.ModuleType(f"{PACKAGE_NAME}.core.connection_profiles")
	profiles_module.parse_profile = lambda value: types.SimpleNamespace(**value)
	profiles_module.parse_profiles = lambda values: tuple(types.SimpleNamespace(**value) for value in values)
	sys.modules[profiles_module.__name__] = profiles_module
	targets_module = types.ModuleType(f"{PACKAGE_NAME}.core.connection_targets")
	targets_module.LOCAL_WINDOWS_TCP = "localWindowsTcp"
	targets_module.local_windows_target = lambda label: types.SimpleNamespace(
		kind="localWindowsTcp", identifier="local-windows", label=label
	)
	targets_module.remote_ssh_target = lambda identifier, label: types.SimpleNamespace(
		kind="remoteSsh", identifier=identifier, label=label
	)
	sys.modules[targets_module.__name__] = targets_module
	claim_module = types.ModuleType(f"{PACKAGE_NAME}.session_claim")
	claim_module.ClaimTransitionKind = ClaimTransitionKind
	claim_module.DiscoverySelectionKind = DiscoverySelectionKind
	sys.modules[claim_module.__name__] = claim_module

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.initTranslation = lambda: None
	sys.modules["addonHandler"] = addon_handler
	ui_module = types.ModuleType("ui")
	ui_module.messages = []
	ui_module.message = ui_module.messages.append
	sys.modules["ui"] = ui_module
	log_module = types.ModuleType("logHandler")
	log_module.log = types.SimpleNamespace(info=lambda *_args: None, exception=lambda *_args: None)
	sys.modules["logHandler"] = log_module
	builtins._ = lambda text: text

	module_name = f"{PACKAGE_NAME}.connection_workflow"
	spec = importlib.util.spec_from_file_location(module_name, PLUGIN_ROOT / "connection_workflow.py")
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load connection workflow")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


WORKFLOW_MODULE = load_workflow_module()
ConnectionWorkflow = WORKFLOW_MODULE.ConnectionWorkflow


class _Diagnostics:
	def __init__(self) -> None:
		self.entries = []

	def record(self, category, **fields) -> None:
		self.entries.append((category, fields))


class _Gate:
	def __init__(self) -> None:
		self.focused = "terminal-1"
		self.manual_enabled = False
		self.authenticated = False
		self.nvim_active = False
		self.bound_terminal = None
		self.disable_calls = 0

	def disable(self) -> None:
		self.disable_calls += 1
		self.manual_enabled = False
		self.authenticated = False
		self.nvim_active = False
		self.bound_terminal = None


class _Instances:
	def __init__(self) -> None:
		self.items = []
		self.detached = []

	def list(self):
		return list(self.items)

	def detach(self, instance_id):
		instance = next(item for item in self.items if item.identifier == instance_id)
		self.items.remove(instance)
		self.detached.append(instance_id)
		return instance, instance.client


class _Coordinator:
	def __init__(self) -> None:
		self.gate = _Gate()
		self.instances = _Instances()
		self.connected = False
		self.calls = []

	def discard_focus_context(self):
		self.calls.append("discardFocus")

	def clear_runtime_tracking(self):
		self.calls.append("clearRuntime")


class _SessionClaim:
	def __init__(self) -> None:
		self.calls = []
		self.authorization = None
		self.accepted = False
		self.transition = types.SimpleNamespace(
			kind=ClaimTransitionKind.PASS_THROUGH,
			identity="terminal-1",
			target_id="",
			explicit_target=False,
		)
		self.disconnect_result = types.SimpleNamespace(instance=None, error_type="", error="")

	def cancel_pending_authorization(self):
		self.calls.append("cancelAuthorization")

	def authorize(self, identity):
		self.calls.append(("authorize", identity))
		return self.authorization

	def accept(self, identity, generation):
		self.calls.append(("accept", identity, generation))
		return self.accepted

	def consume_transition(self, identity):
		self.calls.append(("consume", identity))
		return self.transition

	def invalidate_connection_state(self):
		self.calls.append("invalidate")

	def disconnect_connection(self, identity):
		self.calls.append(("disconnect", identity))
		return self.disconnect_result

	def forget_temporary_binding(self, identity):
		self.calls.append(("forget", identity))
		return True

	def request_temporary_binding_offer(self, instance_id):
		self.calls.append(("offer", instance_id))


class _Scheduler:
	def __init__(self) -> None:
		self.calls = []

	def later(self, delay, callback, *args):
		self.calls.append((delay, callback, args))
		return self.calls[-1]


class _EventDelivery:
	def __init__(self) -> None:
		self.calls = []

	def reset_editor_planning(self):
		self.calls.append("resetPlanning")

	def queue_braille_refresh(self, **kwargs):
		self.calls.append(("braille", kwargs))


class _TerminalFocus:
	def __init__(self) -> None:
		self.forgotten = []
		self.sweeps = 0

	@staticmethod
	def identity_fields(identity):
		return {"identity": identity}

	def forget_identity(self, identity):
		self.forgotten.append(identity)

	def ensure_lifecycle_sweep(self):
		self.sweeps += 1


class _Dialogs:
	def __init__(self) -> None:
		self.passwords = []
		self.password_result = None

	def password(self, profile_name):
		self.passwords.append(profile_name)
		return self.password_result


def make_workflow():
	coordinator = _Coordinator()
	session_claim = _SessionClaim()
	scheduler = _Scheduler()
	event_delivery = _EventDelivery()
	terminal_focus = _TerminalFocus()
	diagnostics = _Diagnostics()
	dialogs = _Dialogs()
	terminal_actions = types.SimpleNamespace(
		calls=[], discard_requests=lambda: terminal_actions.calls.append(True)
	)
	control_dispatcher = types.SimpleNamespace(
		calls=[], discard_client=lambda client: control_dispatcher.calls.append(client)
	)
	client_stopper = types.SimpleNamespace(
		calls=[],
		accepted=True,
		submit=lambda instance_id, client: (
			client_stopper.calls.append((instance_id, client)) or client_stopper.accepted
		),
	)
	settings = types.SimpleNamespace(
		snapshot=lambda: {"connections": []},
		connection_profile_by_id=lambda _identifier: None,
	)
	workflow = ConnectionWorkflow(
		coordinator=coordinator,
		editor_session=object(),
		session_claim=session_claim,
		terminal_focus=terminal_focus,
		terminal_actions=terminal_actions,
		event_delivery=event_delivery,
		settings=settings,
		presentation=object(),
		control_dispatcher=control_dispatcher,
		dispatch_control=lambda *_args, **_kwargs: None,
		client_stopper=client_stopper,
		temporary_bindings=object(),
		scheduler=scheduler,
		diagnostics=diagnostics,
		dialogs=dialogs,
		claim_key_name="F12",
		package_dir="package",
	)
	return types.SimpleNamespace(
		workflow=workflow,
		coordinator=coordinator,
		session_claim=session_claim,
		scheduler=scheduler,
		event_delivery=event_delivery,
		terminal_focus=terminal_focus,
		diagnostics=diagnostics,
		dialogs=dialogs,
		terminal_actions=terminal_actions,
		control_dispatcher=control_dispatcher,
		client_stopper=client_stopper,
	)


class ConnectionWorkflowTests(unittest.TestCase):
	def setUp(self) -> None:
		WORKFLOW_MODULE.ui.messages.clear()

	def test_terminal_integration_is_bound_exactly_once(self) -> None:
		fixture = make_workflow()
		fixture.workflow.bind_terminal_integration(object())
		with self.assertRaisesRegex(RuntimeError, "exactly once"):
			fixture.workflow.bind_terminal_integration(object())

	def test_toggle_failure_disables_gate_and_stops_connections_fail_open(self) -> None:
		fixture = make_workflow()
		stop_calls = []
		fixture.workflow._toggleNeovimMode = lambda: (_ for _ in ()).throw(RuntimeError("toggle"))
		fixture.workflow.stop_connections = lambda: stop_calls.append(True)

		fixture.workflow.toggle_accessibility()

		self.assertEqual(1, fixture.coordinator.gate.disable_calls)
		self.assertEqual([True], stop_calls)
		self.assertIn(
			("toggleError", {"errorType": "RuntimeError", "error": "toggle"}),
			fixture.diagnostics.entries,
		)

	def test_unauthorized_claim_forwards_physical_gesture_exactly_once(self) -> None:
		fixture = make_workflow()
		gesture = types.SimpleNamespace(calls=0)
		gesture.send = lambda: setattr(gesture, "calls", gesture.calls + 1)

		fixture.workflow.claim_focused_session(gesture)

		self.assertEqual(1, gesture.calls)
		self.assertEqual([], fixture.scheduler.calls)
		self.assertIn(
			("sessionClaimIgnored", {"reason": "notAuthorizedOrFocusChanged"}),
			fixture.diagnostics.entries,
		)

	def test_local_claim_enables_manual_mode_and_schedules_only_local_resolution(self) -> None:
		fixture = make_workflow()
		fixture.session_claim.authorization = 3
		fixture.session_claim.accepted = True
		fixture.session_claim.transition = types.SimpleNamespace(
			kind=ClaimTransitionKind.LOCAL,
			identity="terminal-1",
			target_id="",
			explicit_target=True,
		)
		gesture = types.SimpleNamespace(calls=0)
		gesture.send = lambda: setattr(gesture, "calls", gesture.calls + 1)

		fixture.workflow.claim_focused_session(gesture)

		self.assertEqual(1, gesture.calls)
		self.assertTrue(fixture.coordinator.gate.manual_enabled)
		self.assertEqual("resetPlanning", fixture.event_delivery.calls[0])
		delay, callback, args = fixture.scheduler.calls[0]
		self.assertEqual(250, delay)
		self.assertEqual("_beginLocalSessionSelection", callback.__name__)
		self.assertEqual("terminal-1", args[0])

	def test_password_is_cached_only_for_one_runtime_generation(self) -> None:
		fixture = make_workflow()
		profile = types.SimpleNamespace(authentication="password", identifier="work", name="Work")
		fixture.dialogs.password_result = "secret"

		self.assertEqual("secret", fixture.workflow.password_for_profile(profile))
		fixture.dialogs.password_result = "changed"
		self.assertEqual("secret", fixture.workflow.password_for_profile(profile))
		self.assertEqual(["Work"], fixture.dialogs.passwords)
		fixture.workflow.clear_passwords()
		self.assertEqual("changed", fixture.workflow.password_for_profile(profile))

	def test_disconnect_forgets_only_the_selected_terminal_binding(self) -> None:
		fixture = make_workflow()
		instance = types.SimpleNamespace(identifier="connection-1", label="Work")
		fixture.session_claim.disconnect_result = types.SimpleNamespace(
			instance=instance,
			error_type="",
			error="",
		)

		fixture.workflow.disconnect_connection()

		self.assertEqual(["terminal-1"], fixture.terminal_focus.forgotten)
		self.assertIn("Work", WORKFLOW_MODULE.ui.messages[-1])

	def test_stop_connections_transfers_each_detached_client_to_one_stopper(self) -> None:
		fixture = make_workflow()
		first_client = object()
		second_client = object()
		fixture.coordinator.instances.items = [
			types.SimpleNamespace(identifier="connection-1", client=first_client),
			types.SimpleNamespace(identifier="connection-2", client=second_client),
		]
		accepted = iter((True, False))
		fixture.client_stopper.submit = lambda instance_id, client: (
			fixture.client_stopper.calls.append((instance_id, client)) or next(accepted)
		)

		fixture.workflow.stop_connections()

		self.assertEqual(["invalidate"], fixture.session_claim.calls)
		self.assertEqual([first_client, second_client], fixture.control_dispatcher.calls)
		self.assertEqual(
			[("connection-1", first_client), ("connection-2", second_client)],
			fixture.client_stopper.calls,
		)
		self.assertEqual(["discardFocus", "clearRuntime"], fixture.coordinator.calls)
		self.assertEqual([True], fixture.terminal_actions.calls)
		self.assertIn(
			("managedClientStopRejected", {"instanceId": "connection-2"}),
			fixture.diagnostics.entries,
		)
		self.assertIn(("clientInstancesStopped", {"queued": 1}), fixture.diagnostics.entries)


if __name__ == "__main__":
	unittest.main()
