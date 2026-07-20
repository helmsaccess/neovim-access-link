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
		unregister_profile_switch: Callable[[], None],
		clear_session_passwords: Callable[[], None],
		stop_connections: Callable[[], None],
		instance_manager: Any,
		coordinator: Any,
		focus_service: Any,
		editor_session: Any,
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
		self._unregisterProfileSwitch = unregister_profile_switch
		self._clearSessionPasswords = clear_session_passwords
		self._stopConnections = stop_connections
		self._instanceManager = instance_manager
		self._coordinator = coordinator
		self._focusService = focus_service
		self._editorSession = editor_session
		self._claimService = claim_service
		self._uiManager = ui_manager
		self._presentation = presentation
		self._diagnostics = diagnostics
		self._registrationToken: object | None = None
		self._profileSwitchRegistered = False
		self._closed = False

	@property
	def closed(self) -> bool:
		return self._closed

	def mark_profile_switch_registered(self) -> None:
		if self._closed:
			raise RuntimeError("runtime is closed")
		self._profileSwitchRegistered = True

	def publish(self) -> None:
		"""Publish only after every process-wide registration has completed."""
		if self._closed:
			raise RuntimeError("runtime is closed")
		if self._registrationToken is None:
			self._registrationToken = self._registrar.publish(self._integrationService)

	def close(self) -> bool:
		"""Close once, keeping teardown fail-open after an individual failure."""
		if self._closed:
			return False
		self._closed = True

		token = self._registrationToken
		self._registrationToken = None
		self._run_close_step(
			"unpublish",
			lambda: self._registrar.unpublish(self._integrationService, token),
		)
		self._run_close_step("terminalService", self._integrationService.close)
		self._cancel_main_thread_calls()
		self._run_close_step("gate", self._gate.disable)
		if self._profileSwitchRegistered:
			self._profileSwitchRegistered = False
			self._run_close_step("profileSwitch", self._unregisterProfileSwitch)
		self._run_close_step("passwords", self._clearSessionPasswords)
		self._run_close_step("connections", self._stopConnections)
		self._run_close_step("instances", self._instanceManager.stop_all)
		self._run_close_step("runtimeTracking", self._coordinator.clear_runtime_tracking)
		self._run_close_step("terminalFocus", self._focusService.clear)
		self._run_close_step("focusContext", self._coordinator.discard_focus_context)
		self._run_close_step("clipboardRequests", self._editorSession.discard_clipboard_requests)
		self._run_close_step(
			"terminalControlRequests",
			self._editorSession.discard_terminal_control_requests,
		)
		self._run_close_step("sessionClaim", self._claimService.cancel_pending_authorization)
		self._run_close_step("ui", self._uiManager.unregister)
		self._run_close_step("presentation", self._presentation.close)
		self._record("addonStop")
		return True

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
