from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = (
	pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink" / "addon_runtime.py"
)


def load_runtime():
	spec = importlib.util.spec_from_file_location("nvim_nvda_addon_runtime_test", MODULE_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the add-on runtime")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module.AddonRuntime


class _Diagnostics:
	def __init__(self, calls: list) -> None:
		self.calls = calls

	def record(self, category, **fields) -> None:
		self.calls.append((category, fields))


class _Service:
	def __init__(self, calls: list, name: str, *, fail: str = "") -> None:
		self.calls = calls
		self.name = name
		self.fail = fail

	def close(self) -> None:
		self.calls.append(self.name)
		if self.fail == "close":
			raise RuntimeError(f"{self.name} failed")

	def disable(self) -> None:
		self.calls.append(self.name)

	def clear(self) -> None:
		self.calls.append(self.name)

	def invalidate_connection_state(self) -> None:
		self.calls.append(self.name)

	def register(self) -> None:
		self.calls.append(f"{self.name}Register")
		if self.fail == "register":
			raise RuntimeError(f"{self.name} failed")

	def unregister(self) -> None:
		self.calls.append(self.name)


class _ProfileSwitch:
	def __init__(self, calls: list, *, fail_register: bool = False) -> None:
		self.calls = calls
		self.fail_register = fail_register

	def register(self, handler) -> None:
		self.calls.append(("profileRegister", handler))
		if self.fail_register:
			raise RuntimeError("profile failed")

	def unregister(self, handler) -> None:
		self.calls.append(("profileSwitch", handler))


class _Registrar:
	def __init__(self, calls: list, *, fail_publish: bool = False) -> None:
		self.calls = calls
		self.fail_publish = fail_publish
		self.token = object()

	def publish(self, service):
		self.calls.append(("publish", service))
		if self.fail_publish:
			raise RuntimeError("publish failed")
		return self.token

	def unpublish(self, service, token) -> None:
		self.calls.append(("unpublish", service, token))


def make_runtime(*, failure: str = ""):
	AddonRuntime = load_runtime()
	calls: list = []
	handler = object()
	service = _Service(calls, "terminalService")
	registrar = _Registrar(calls, fail_publish=failure == "publish")
	profile = _ProfileSwitch(calls, fail_register=failure == "profile")
	ui_manager = _Service(calls, "ui", fail="register" if failure == "ui" else "")
	return (
		AddonRuntime(
			registrar=registrar,
			integration_service=service,
			control_dispatcher=_Service(calls, "controlDispatcher"),
			scheduler=_Service(calls, "scheduler"),
			client_stopper=_Service(calls, "clientStopper"),
			gate=_Service(calls, "gate"),
			profile_switch_action=profile,
			profile_switch_handler=handler,
			clear_session_passwords=lambda: calls.append("passwords"),
			stop_connections=lambda: calls.append("connections"),
			focus_service=_Service(calls, "terminalFocus"),
			claim_service=_Service(calls, "connectionClaims"),
			ui_manager=ui_manager,
			presentation=_Service(calls, "presentation"),
			diagnostics=_Diagnostics(calls),
		),
		calls,
		service,
		registrar,
		handler,
	)


class AddonRuntimeTests(unittest.TestCase):
	def test_start_publishes_late_and_close_is_ordered_and_idempotent(self) -> None:
		runtime, calls, service, registrar, handler = make_runtime()

		self.assertTrue(runtime.start())
		self.assertFalse(runtime.start())
		self.assertTrue(runtime.close())
		self.assertFalse(runtime.close())

		self.assertEqual(
			[
				("profileRegister", handler),
				"uiRegister",
				("publish", service),
				("unpublish", service, registrar.token),
				"terminalService",
				"controlDispatcher",
				"scheduler",
				"gate",
				("profileSwitch", handler),
				"passwords",
				"connectionClaims",
				"terminalFocus",
				"connections",
				"clientStopper",
				"ui",
				"presentation",
				("addonStop", {}),
			],
			calls,
		)

	def test_each_partial_start_failure_rolls_back_and_closes_runtime(self) -> None:
		for failure in ("profile", "ui", "publish"):
			with self.subTest(failure=failure):
				runtime, calls, service, _registrar, handler = make_runtime(failure=failure)
				with self.assertRaisesRegex(RuntimeError, rf"{failure} failed"):
					runtime.start()
				self.assertTrue(runtime.closed)
				self.assertEqual(1, calls.count("terminalService"))
				self.assertEqual(1, calls.count("ui"))
				self.assertEqual(1, calls.count("presentation"))
				self.assertNotIn(("unpublish", service, _registrar.token), calls)
				self.assertEqual(failure != "profile", ("profileSwitch", handler) in calls)
				with self.assertRaisesRegex(RuntimeError, "runtime is closed"):
					runtime.start()

	def test_close_continues_after_a_failed_step_and_records_it(self) -> None:
		runtime, calls, _service, _registrar, _handler = make_runtime()
		runtime._stopConnections = lambda: (_ for _ in ()).throw(RuntimeError("stop failed"))

		self.assertTrue(runtime.close())

		self.assertIn("clientStopper", calls)
		self.assertIn("ui", calls)
		self.assertIn("presentation", calls)
		self.assertIn(
			(
				"runtimeCloseStepError",
				{"step": "connections", "errorType": "RuntimeError", "error": "stop failed"},
			),
			calls,
		)

	def test_required_lifetime_ports_are_validated(self) -> None:
		AddonRuntime = load_runtime()
		with self.assertRaisesRegex(ValueError, "required"):
			AddonRuntime(
				registrar=None,
				integration_service=object(),
				control_dispatcher=object(),
				scheduler=object(),
				client_stopper=object(),
				gate=object(),
				profile_switch_action=object(),
				profile_switch_handler=lambda: None,
				clear_session_passwords=lambda: None,
				stop_connections=lambda: None,
				focus_service=object(),
				claim_service=object(),
				ui_manager=object(),
				presentation=object(),
				diagnostics=object(),
			)


if __name__ == "__main__":
	unittest.main()
