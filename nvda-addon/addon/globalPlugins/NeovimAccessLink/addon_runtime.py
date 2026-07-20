"""Ordered ownership and teardown for process-wide add-on services."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AddonRuntime:
	"""Publish and close one fully composed add-on runtime exactly once."""

	def __init__(
		self,
		*,
		registrar: Any,
		integration_service: Any,
		pending_main_thread_calls: set[Any],
		gate: Any,
		profile_switch_action: Any,
		profile_switch_handler: Callable[..., None],
		clear_session_passwords: Callable[[], None],
		coordinator: Any,
		focus_service: Any,
		claim_service: Any,
		ui_manager: Any,
		presentation: Any,
		diagnostics: Any,
	) -> None:
		if registrar is None or integration_service is None:
			raise ValueError("registrar and integration service are required")
		self._registrar = registrar
		self._integrationService = integration_service
		self._pendingMainThreadCalls = pending_main_thread_calls
		self._gate = gate
		self._profileSwitchAction = profile_switch_action
		self._profileSwitchHandler = profile_switch_handler
		self._clearSessionPasswords = clear_session_passwords
		self._coordinator = coordinator
		self._focusService = focus_service
		self._claimService = claim_service
		self._uiManager = ui_manager
		self._presentation = presentation
		self._diagnostics = diagnostics
		self._registrationToken: object | None = None
		self._profileSwitchRegistered = False
		self._started = False
		self._closed = False

	@property
	def closed(self) -> bool:
		return self._closed

	def start(self) -> bool:
		"""Register and publish once, rolling back any partial activation."""
		if self._closed:
			raise RuntimeError("runtime is closed")
		if self._started:
			return False
		try:
			self._profileSwitchAction.register(self._profileSwitchHandler)
			self._profileSwitchRegistered = True
			self._uiManager.register()
			self._registrationToken = self._registrar.publish(self._integrationService)
			self._started = True
		except Exception:
			self.close()
			raise
		return True

	def close(self) -> bool:
		"""Close once, keeping teardown fail-open after an individual failure."""
		if self._closed:
			return False
		self._closed = True
		self._started = False

		token = self._registrationToken
		self._registrationToken = None
		if token is not None:
			self._run_close_step(
				"unpublish",
				lambda: self._registrar.unpublish(self._integrationService, token),
			)
		self._run_close_step("terminalService", self._integrationService.close)
		self._cancel_main_thread_calls()
		self._run_close_step("gate", self._gate.disable)
		if self._profileSwitchRegistered:
			self._profileSwitchRegistered = False
			self._run_close_step(
				"profileSwitch",
				lambda: self._profileSwitchAction.unregister(self._profileSwitchHandler),
			)
		self._run_close_step("passwords", self._clearSessionPasswords)
		self._run_close_step("connectionClaims", self._claimService.invalidate_connection_state)
		self._run_close_step("terminalFocus", self._focusService.clear)
		self._run_close_step("connections", self._stop_owned_connections)
		self._run_close_step("runtimeTracking", self._coordinator.clear_runtime_tracking)
		self._run_close_step("ui", self._uiManager.unregister)
		self._run_close_step("presentation", self._presentation.close)
		self._record("addonStop")
		return True

	def _stop_owned_connections(self) -> None:
		instances = self._coordinator.instances
		if not instances.list():
			return
		instances.stop_all()
		self._record("clientInstancesStopped")

	def _cancel_main_thread_calls(self) -> None:
		for pending in tuple(self._pendingMainThreadCalls):
			self._run_close_step("mainThreadCall", pending.Stop)
		self._pendingMainThreadCalls.clear()

	def _run_close_step(self, step: str, operation: Callable[[], Any]) -> None:
		try:
			operation()
		except Exception as error:
			self._record(
				"runtimeCloseStepError",
				step=step,
				errorType=type(error).__name__,
				error=str(error),
			)

	def _record(self, category: str, **fields: Any) -> None:
		try:
			self._diagnostics.record(category, **fields)
		except Exception:
			pass
