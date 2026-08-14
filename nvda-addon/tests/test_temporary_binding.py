from __future__ import annotations

import builtins
from enum import Enum
import importlib.util
import pathlib
import sys
import types
import unittest


PLUGIN_ROOT = pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink"
PACKAGE_NAME = "nvim_nvda_temporary_binding_test_package"


class RememberedBindingActivationKind(Enum):
	STALE = "stale"
	ALREADY_ACTIVE = "alreadyActive"
	ACTIVATE = "activate"


class RememberedStateRequestKind(Enum):
	STALE = "stale"
	SKIP = "skip"
	PENDING = "pending"
	FOCUS_CONTEXT = "focusContext"
	FULL_STATE = "fullState"


class TemporaryBindingOfferKind(Enum):
	FOCUS_CHANGED = "focusChanged"
	UNAVAILABLE = "unavailable"
	STALE = "stale"
	OFFER = "offer"


def load_workflow_module():
	package = types.ModuleType(PACKAGE_NAME)
	package.__path__ = [str(PLUGIN_ROOT)]
	sys.modules[PACKAGE_NAME] = package
	claim_module = types.ModuleType(f"{PACKAGE_NAME}.session_claim")
	claim_module.RememberedBindingActivationKind = RememberedBindingActivationKind
	claim_module.RememberedStateRequestKind = RememberedStateRequestKind
	claim_module.TemporaryBindingOfferKind = TemporaryBindingOfferKind
	sys.modules[claim_module.__name__] = claim_module

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.initTranslation = lambda: None
	sys.modules["addonHandler"] = addon_handler
	api_module = types.ModuleType("api")
	api_module.getFocusObject = lambda: None
	api_module.getDesktopObject = lambda: types.SimpleNamespace(objectWithFocus=lambda: None)
	sys.modules["api"] = api_module
	ui_module = types.ModuleType("ui")
	ui_module.messages = []
	ui_module.message = ui_module.messages.append
	sys.modules["ui"] = ui_module
	builtins._ = lambda text: text

	module_name = f"{PACKAGE_NAME}.temporary_binding"
	spec = importlib.util.spec_from_file_location(module_name, PLUGIN_ROOT / "temporary_binding.py")
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the temporary binding workflow")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


WORKFLOW_MODULE = load_workflow_module()
TemporaryBindingWorkflow = WORKFLOW_MODULE.TemporaryBindingWorkflow


class _Diagnostics:
	def __init__(self) -> None:
		self.entries = []

	def record(self, category, **fields) -> None:
		self.entries.append((category, fields))


class _Scheduler:
	def __init__(self) -> None:
		self.calls = []

	def later(self, delay, callback, *args):
		self.calls.append((delay, callback, args))
		return self.calls[-1]


class _Instances:
	def __init__(self) -> None:
		self.selected = {}

	def selected_for(self, identity):
		return self.selected.get(identity)


class _Coordinator:
	def __init__(self) -> None:
		self.gate = types.SimpleNamespace(
			focused=None,
			bound_terminal=None,
			authenticated=False,
			nvim_active=False,
			disconnect=lambda: None,
		)
		self.instances = _Instances()
		self.active_instance_id = None
		self.foreground_confirmed = False
		self.matches = True
		self.discarded = []

	def is_foreground_instance_confirmed(self, instance_id, identity):
		return self.foreground_confirmed

	def matches_focus_context(self, instance_id, request_id, identity):
		return self.matches

	def discard_focus_context(self, instance_id):
		self.discarded.append(instance_id)


class _SessionClaim:
	def __init__(self) -> None:
		self.instance = types.SimpleNamespace(
			identifier="connection-1",
			label="Work",
			transport_kind="remoteSsh",
		)
		self.offer_kind = TemporaryBindingOfferKind.OFFER
		self.activation_kind = RememberedBindingActivationKind.STALE
		self.state_request = types.SimpleNamespace(
			kind=RememberedStateRequestKind.STALE,
			client=None,
			request_id=0,
		)
		self.calls = []
		self.remembered = False
		self.reactivation = True

	def _offer(self):
		return types.SimpleNamespace(kind=self.offer_kind, instance=self.instance)

	def arm_temporary_binding_reactivation(self, identity, instance_id):
		self.calls.append(("arm", identity, instance_id))
		return self._offer()

	def prepare_temporary_binding_offer(self, identity, instance_id):
		self.calls.append(("prepare", identity, instance_id))
		return self._offer()

	def remember_temporary_binding(self, identity, instance_id):
		self.calls.append(("remember", identity, instance_id))
		self.remembered = True
		return self._offer()

	def consume_temporary_binding_reactivation(self, identity, instance_id):
		self.calls.append(("consume", identity, instance_id))
		self.reactivation = False

	def is_temporary_binding_remembered(self, identity):
		return self.remembered

	def has_temporary_binding_reactivation(self, identity, instance_id):
		return self.reactivation

	def activate_remembered_binding(self, identity, instance_id, *, focus_regained=False):
		self.calls.append(("activate", identity, instance_id, focus_regained))
		return types.SimpleNamespace(kind=self.activation_kind)

	def plan_remembered_state_request(self, identity, instance_id):
		self.calls.append(("planState", identity, instance_id))
		return self.state_request


class _TerminalFocus:
	def __init__(self) -> None:
		self.focused_app_module = object()
		self.focused_adapter_token = object()
		self.recover_result = False
		self.recover_calls = []

	@staticmethod
	def identity_fields(identity):
		return {"identity": identity}

	@staticmethod
	def identity(obj):
		return getattr(obj, "identity", None)

	def recover_after_modal(self, *args):
		self.recover_calls.append(args)
		return self.recover_result


class _Dialogs:
	def __init__(self) -> None:
		self.calls = []

	def confirm(self, **kwargs) -> None:
		self.calls.append(kwargs)


def make_workflow(*, prompt_answer=None, dispatch=None):
	coordinator = _Coordinator()
	session_claim = _SessionClaim()
	terminal_focus = _TerminalFocus()
	scheduler = _Scheduler()
	diagnostics = _Diagnostics()
	dialogs = _Dialogs()
	saved_answers = []
	dispatch_calls = []

	def dispatch_control(client, kind, payload, *, on_result):
		dispatch_calls.append((client, kind, payload, on_result))
		if dispatch is not None:
			dispatch(on_result)

	workflow = TemporaryBindingWorkflow(
		coordinator=coordinator,
		session_claim=session_claim,
		terminal_focus=terminal_focus,
		dispatch_control=dispatch_control,
		scheduler=scheduler,
		diagnostics=diagnostics,
		dialogs=dialogs,
		prompt_answer=lambda: prompt_answer,
		remember_prompt_answer=saved_answers.append,
	)
	return types.SimpleNamespace(
		workflow=workflow,
		coordinator=coordinator,
		session_claim=session_claim,
		terminal_focus=terminal_focus,
		scheduler=scheduler,
		diagnostics=diagnostics,
		dialogs=dialogs,
		saved_answers=saved_answers,
		dispatch_calls=dispatch_calls,
	)


class TemporaryBindingWorkflowTests(unittest.TestCase):
	def setUp(self) -> None:
		WORKFLOW_MODULE.ui.messages.clear()
		WORKFLOW_MODULE.api.getFocusObject = lambda: None
		WORKFLOW_MODULE.api.getDesktopObject = lambda: types.SimpleNamespace(objectWithFocus=lambda: None)

	def test_dialog_decision_is_saved_then_revalidated_and_schedules_focus_recovery(self) -> None:
		fixture = make_workflow()
		fixture.workflow.offer_temporary_binding("terminal-1", "connection-1")

		self.assertEqual([("arm", "terminal-1", "connection-1")], fixture.session_claim.calls)
		self.assertEqual(1, len(fixture.dialogs.calls))
		self.assertIn("Work", fixture.dialogs.calls[0]["message"])
		fixture.dialogs.calls[0]["on_result"](True, True)

		self.assertEqual([True], fixture.saved_answers)
		self.assertIn(("remember", "terminal-1", "connection-1"), fixture.session_claim.calls)
		self.assertEqual(1, len(WORKFLOW_MODULE.ui.messages))
		self.assertEqual(50, fixture.scheduler.calls[0][0])
		self.assertEqual("_recoverTemporaryBindingFocus", fixture.scheduler.calls[0][1].__name__)

	def test_configured_decline_bypasses_dialog_and_does_not_arm_reactivation(self) -> None:
		fixture = make_workflow(prompt_answer=False)
		fixture.workflow.offer_temporary_binding("terminal-1", "connection-1")

		self.assertEqual([("prepare", "terminal-1", "connection-1")], fixture.session_claim.calls)
		self.assertEqual([], fixture.dialogs.calls)
		self.assertEqual([], fixture.scheduler.calls)
		self.assertIn(
			("temporaryTerminalBindingDeclined", {
				"instanceId": "connection-1",
				"terminal": {"identity": "terminal-1"},
			}),
			fixture.diagnostics.entries,
		)

	def test_focus_recovery_waits_for_focus_then_uses_live_system_identity(self) -> None:
		fixture = make_workflow()
		app_module = fixture.terminal_focus.focused_app_module
		adapter_token = fixture.terminal_focus.focused_adapter_token
		fixture.workflow._recoverTemporaryBindingFocus(
			"terminal-1",
			"connection-1",
			app_module,
			adapter_token,
			0,
		)
		self.assertEqual(150, fixture.scheduler.calls[-1][0])

		live_focus = types.SimpleNamespace(identity="terminal-1", appModule=app_module)
		WORKFLOW_MODULE.api.getDesktopObject = lambda: types.SimpleNamespace(
			objectWithFocus=lambda: live_focus
		)
		fixture.coordinator.gate.focused = "terminal-1"
		fixture.coordinator.active_instance_id = "connection-1"
		fixture.coordinator.instances.selected["terminal-1"] = fixture.session_claim.instance
		requests = []
		fixture.workflow.request_remembered_binding_state = lambda *args: requests.append(args)
		fixture.workflow._recoverTemporaryBindingFocus(
			"terminal-1",
			"connection-1",
			app_module,
			adapter_token,
			1,
		)

		self.assertEqual([("terminal-1", "connection-1")], requests)
		self.assertIn(("consume", "terminal-1", "connection-1"), fixture.session_claim.calls)
		self.assertIn(
			("temporaryTerminalBindingFocusHandshakeRetried", {
				"instanceId": "connection-1",
				"terminal": {"identity": "terminal-1"},
			}),
			fixture.diagnostics.entries,
		)

	def test_focus_recovery_never_rebinds_a_different_live_terminal(self) -> None:
		fixture = make_workflow()
		app_module = fixture.terminal_focus.focused_app_module
		other = types.SimpleNamespace(identity="terminal-2", appModule=app_module)
		fixture.coordinator.instances.selected["terminal-2"] = types.SimpleNamespace(
			identifier="connection-2"
		)
		WORKFLOW_MODULE.api.getDesktopObject = lambda: types.SimpleNamespace(objectWithFocus=lambda: other)

		fixture.workflow._recoverTemporaryBindingFocus(
			"terminal-1",
			"connection-1",
			app_module,
			fixture.terminal_focus.focused_adapter_token,
			0,
		)

		self.assertIn(("consume", "terminal-2", "connection-2"), fixture.session_claim.calls)
		self.assertEqual([], fixture.terminal_focus.recover_calls)
		self.assertEqual([], fixture.scheduler.calls)

	def test_failed_focus_context_dispatch_is_discarded_and_retried(self) -> None:
		fixture = make_workflow(dispatch=lambda on_result: on_result(False, "QueueUnavailable"))
		client = object()
		fixture.session_claim.state_request = types.SimpleNamespace(
			kind=RememberedStateRequestKind.FOCUS_CONTEXT,
			client=client,
			request_id=7,
		)

		fixture.workflow.request_remembered_binding_state("terminal-1", "connection-1")

		self.assertEqual([(client, "requestFocusContext", {"requestId": 7})], [
			(client, kind, payload)
			for client, kind, payload, _callback in fixture.dispatch_calls
		])
		self.assertEqual(["connection-1"], fixture.coordinator.discarded)
		self.assertEqual(150, fixture.scheduler.calls[0][0])
		self.assertEqual(
			("terminal-1", "connection-1", 1),
			fixture.scheduler.calls[0][2],
		)

	def test_activation_and_confirmed_state_avoid_duplicate_controls(self) -> None:
		fixture = make_workflow()
		fixture.session_claim.activation_kind = RememberedBindingActivationKind.ACTIVATE
		fixture.workflow.activate_remembered_binding(
			"terminal-1",
			"connection-1",
			focus_regained=True,
		)
		self.assertEqual(100, fixture.scheduler.calls[0][0])
		self.assertEqual("request_remembered_binding_state", fixture.scheduler.calls[0][1].__name__)

		fixture.coordinator.foreground_confirmed = True
		fixture.workflow.request_remembered_binding_state("terminal-1", "connection-1")
		self.assertEqual([], fixture.dispatch_calls)
		self.assertFalse(any(call[0] == "planState" for call in fixture.session_claim.calls))


if __name__ == "__main__":
	unittest.main()
