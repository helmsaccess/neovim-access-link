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


class _Coordinator:
	def __init__(self) -> None:
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

	def remember_temporary_binding(self, identity, instance_id):
		self.calls.append(("remember", identity, instance_id))
		return types.SimpleNamespace(kind=self.offer_kind, instance=self.instance)

	def activate_remembered_binding(self, identity, instance_id, *, focus_regained=False):
		self.calls.append(("activate", identity, instance_id, focus_regained))
		return types.SimpleNamespace(kind=self.activation_kind)

	def plan_remembered_state_request(self, identity, instance_id):
		self.calls.append(("planState", identity, instance_id))
		return self.state_request


class _TerminalFocus:
	@staticmethod
	def identity_fields(identity):
		return {"identity": identity}


def make_workflow(*, dispatch=None):
	coordinator = _Coordinator()
	session_claim = _SessionClaim()
	terminal_focus = _TerminalFocus()
	scheduler = _Scheduler()
	diagnostics = _Diagnostics()
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
	)
	return types.SimpleNamespace(
		workflow=workflow,
		coordinator=coordinator,
		session_claim=session_claim,
		scheduler=scheduler,
		diagnostics=diagnostics,
		dispatch_calls=dispatch_calls,
	)


class TemporaryBindingWorkflowTests(unittest.TestCase):
	def setUp(self) -> None:
		WORKFLOW_MODULE.ui.messages.clear()

	def test_successful_binding_is_remembered_immediately_without_scheduled_modal_work(self) -> None:
		fixture = make_workflow()

		fixture.workflow.offer_temporary_binding("terminal-1", "connection-1")

		self.assertEqual(
			[("remember", "terminal-1", "connection-1")],
			fixture.session_claim.calls,
		)
		self.assertEqual([], fixture.scheduler.calls)
		self.assertEqual(1, len(WORKFLOW_MODULE.ui.messages))
		self.assertIn(
			(
				"temporaryTerminalBindingRemembered",
				{
					"instanceId": "connection-1",
					"transportKind": "remoteSsh",
					"terminal": {"identity": "terminal-1"},
				},
			),
			fixture.diagnostics.entries,
		)

	def test_changed_focus_cannot_be_remembered(self) -> None:
		fixture = make_workflow()
		fixture.session_claim.offer_kind = TemporaryBindingOfferKind.FOCUS_CHANGED

		fixture.workflow.offer_temporary_binding("terminal-1", "connection-1")

		self.assertEqual([], WORKFLOW_MODULE.ui.messages)
		self.assertIn(
			(
				"temporaryTerminalBindingRememberIgnored",
				{"instanceId": "connection-1", "reason": "focusChanged"},
			),
			fixture.diagnostics.entries,
		)

	def test_unsupported_terminal_cannot_be_remembered(self) -> None:
		fixture = make_workflow()
		fixture.session_claim.offer_kind = TemporaryBindingOfferKind.UNAVAILABLE

		fixture.workflow.offer_temporary_binding("terminal-1", "connection-1")

		self.assertEqual([], WORKFLOW_MODULE.ui.messages)
		self.assertIn(
			(
				"temporaryTerminalBindingUnavailable",
				{"terminal": {"identity": "terminal-1"}},
			),
			fixture.diagnostics.entries,
		)

	def test_failed_focus_context_dispatch_is_discarded_and_retried(self) -> None:
		fixture = make_workflow(dispatch=lambda on_result: on_result(False, "QueueUnavailable"))
		client = object()
		fixture.session_claim.state_request = types.SimpleNamespace(
			kind=RememberedStateRequestKind.FOCUS_CONTEXT,
			client=client,
			request_id=7,
		)

		fixture.workflow.request_remembered_binding_state("terminal-1", "connection-1")

		self.assertEqual(
			[(client, "requestFocusContext", {"requestId": 7})],
			[(client, kind, payload) for client, kind, payload, _callback in fixture.dispatch_calls],
		)
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
