"""Narrow public contract for Windows Terminal and structured Braille adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TerminalCommand(Enum):
	"""Commands that an application-specific adapter may request."""

	TOGGLE_ACCESSIBILITY = "action_toggleNeovimMode"
	READ_COMPLETION_DOCUMENTATION = "action_readCompletionDocumentation"
	COPY_VISUAL_SELECTION = "action_copyNeovimSelection"
	COPY_LAST_YANK = "action_copyLastNeovimYank"
	PASTE_WINDOWS_CLIPBOARD = "action_pasteWindowsClipboard"
	SET_REGISTER_FROM_WINDOWS_CLIPBOARD = "action_setNeovimRegisterFromWindowsClipboard"
	LEAVE_DIRECT_TERMINAL_INPUT = "action_leaveDirectTerminalInput"
	START_CONNECTION = "action_startConnectionInstance"
	DISCONNECT_CONNECTION = "action_disconnectConnectionInstance"
	FORGET_TEMPORARY_BINDING = "action_forgetTemporaryTerminalBinding"


@dataclass(frozen=True)
class SessionClaimAuthorization:
	"""One-shot authorization for the exact focused terminal and service generation."""

	identity: object
	generation: int
	service_generation: object


class TerminalIntegrationService:
	"""Expose only operations required by application and Braille adapters.

	The existing runtime remains the implementation owner during this migration
	phase. Keeping every forwarding operation here makes later ownership moves
	explicit without publishing the NVDA GlobalPlugin itself.
	"""

	def __init__(self, runtime: Any, focus_service: Any):
		if runtime is None or focus_service is None:
			raise ValueError("runtime and focus service are required")
		self._runtime = runtime
		self._focusService = focus_service
		self._generation = object()

	def _record(self, category: str, **fields: Any) -> None:
		try:
			self._runtime._diagnostics.record(category, **fields)
		except Exception:
			pass

	def _fail_open(self, event_name: str, error: Exception) -> None:
		try:
			self._runtime._failOpenTerminalEvent(event_name, error)
		except Exception:
			# _failOpenTerminalEvent opens the gate before recording diagnostics.
			# A secondary diagnostics failure must not escape into NVDA's event path.
			pass

	def supports_braille_overlay(self, obj: object) -> bool:
		try:
			return self._focusService.identity(obj) is not None
		except Exception as error:
			self._fail_open("chooseNVDAObjectOverlayClasses", error)
			return False

	def prepare_focus(self, obj: object, adapter_token: object, app_module: object) -> object | None:
		try:
			return self._focusService.prepare_focus(obj, adapter_token, app_module)
		except Exception as error:
			self._fail_open("gainFocus", error)
			return None

	def finish_focus(self, decision: object) -> None:
		try:
			self._focusService.finish_focus(decision)
		except Exception as error:
			self._fail_open("gainFocusCompletion", error)

	def abandon_focus(self, decision: object) -> None:
		"""Fail open a prepared focus event after the published service changed."""
		self._fail_open("staleTerminalFocusService", RuntimeError("terminal service changed"))

	def lose_focus(self, adapter_token: object) -> None:
		try:
			self._focusService.lose_focus(adapter_token)
		except Exception as error:
			self._fail_open("appModuleLoseFocus", error)

	def should_use_native_event(self, obj: object, event_name: str) -> bool:
		try:
			return not self._focusService.should_suppress(obj)
		except Exception as error:
			self._fail_open(event_name, error)
			return True

	def dispatch_command(
		self,
		command: TerminalCommand,
		gesture: object,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		"""Authorize and run one fixed command, returning whether it was handled."""
		if not isinstance(command, TerminalCommand):
			self._record("configuredGesturePassedThrough", action="unknown")
			return False
		try:
			if getattr(focus_obj, "appModule", None) is not app_module:
				self._record("configuredGesturePassedThrough", action=command.value)
				return False
			if self._focusService.identity(focus_obj) is None:
				self._record("configuredGesturePassedThrough", action=command.value)
				return False
			self._focusService.refresh_for_action(
				focus_obj,
				app_module,
				adapter_token,
			)
		except Exception as error:
			self._record(
				"configuredGestureFocusFailed",
				action=command.value,
				errorType=type(error).__name__,
			)
			self._record("configuredGesturePassedThrough", action=command.value)
			return False
		self._command_actions()[command](gesture)
		return True

	def _command_actions(self):
		"""Return the explicit command allowlist using current runtime methods."""
		return {
			TerminalCommand.TOGGLE_ACCESSIBILITY: self._runtime.action_toggleNeovimMode,
			TerminalCommand.READ_COMPLETION_DOCUMENTATION: (self._runtime.action_readCompletionDocumentation),
			TerminalCommand.COPY_VISUAL_SELECTION: self._runtime.action_copyNeovimSelection,
			TerminalCommand.COPY_LAST_YANK: self._runtime.action_copyLastNeovimYank,
			TerminalCommand.PASTE_WINDOWS_CLIPBOARD: self._runtime.action_pasteWindowsClipboard,
			TerminalCommand.SET_REGISTER_FROM_WINDOWS_CLIPBOARD: (
				self._runtime.action_setNeovimRegisterFromWindowsClipboard
			),
			TerminalCommand.LEAVE_DIRECT_TERMINAL_INPUT: (self._runtime.action_leaveDirectTerminalInput),
			TerminalCommand.START_CONNECTION: self._runtime.action_startConnectionInstance,
			TerminalCommand.DISCONNECT_CONNECTION: (self._runtime.action_disconnectConnectionInstance),
			TerminalCommand.FORGET_TEMPORARY_BINDING: (self._runtime.action_forgetTemporaryTerminalBinding),
		}

	def copy_diagnostic_report(self, gesture: object) -> None:
		self._runtime.action_copyDiagnosticReport(gesture)

	def authorize_session_claim(
		self,
		focus_obj: object,
		app_module: object,
	) -> SessionClaimAuthorization | None:
		if getattr(focus_obj, "appModule", None) is not app_module:
			return None
		try:
			gate = self._runtime._gate
			if not gate.manual_enabled or gate.focused is None:
				return None
			identity = self._focusService.identity(focus_obj)
			if identity is None or identity != gate.focused:
				return None
			generation = self._runtime._captureObservedSessionClaim(identity)
			if generation is None:
				return None
			self._record(
				"sessionClaimGestureCaptured",
				source="decideExecuteGesture",
				terminal=self._focusService.identity_fields(identity),
				generation=generation,
			)
			return SessionClaimAuthorization(identity, generation, self._generation)
		except Exception as error:
			self._fail_open("sessionClaimAuthorization", error)
			return None

	def complete_session_claim(
		self,
		authorization: SessionClaimAuthorization,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		if (
			not isinstance(authorization, SessionClaimAuthorization)
			or authorization.service_generation is not self._generation
		):
			return False
		if getattr(focus_obj, "appModule", None) is not app_module:
			self.cancel_session_claim(authorization)
			return False
		try:
			identity = self._focusService.refresh_for_action(
				focus_obj,
				app_module,
				adapter_token,
			)
		except Exception as error:
			self.cancel_session_claim(authorization)
			self._fail_open("sessionClaimFocus", error)
			return False
		if identity != authorization.identity:
			self.cancel_session_claim(authorization)
			return False
		self._runtime.action_claimFocusedNeovimSession(
			None,
			forward_gesture=False,
			expected_identity=authorization.identity,
			claim_generation=authorization.generation,
		)
		return True

	def cancel_session_claim(self, authorization: SessionClaimAuthorization) -> bool:
		if (
			not isinstance(authorization, SessionClaimAuthorization)
			or authorization.service_generation is not self._generation
		):
			return False
		return self._runtime._cancelObservedSessionClaim(
			authorization.identity,
			authorization.generation,
		)

	def should_suppress_braille(self, obj: object) -> bool:
		try:
			return self._focusService.should_suppress(obj)
		except Exception as error:
			self._fail_open("brailleSuppression", error)
			return False

	def braille_state(self, obj: object) -> dict:
		if not self.should_suppress_braille(obj):
			return {}
		try:
			return dict(self._runtime._currentState)
		except Exception as error:
			self._fail_open("brailleState", error)
			return {}

	def suppress_terminal_live_text(self, obj: object, line_count: int) -> bool:
		if not self.should_suppress_braille(obj):
			return False
		self._record("terminalLiveTextSuppressed", lineCount=line_count)
		return True

	def record_braille_route_rejection(self, reason: str, braille_pos: int) -> None:
		self._record("brailleRouteRejected", reason=reason, braillePos=braille_pos)

	def route_braille_cursor(self, obj: object, byte_column: int) -> bool:
		if not self.should_suppress_braille(obj):
			return False
		try:
			self._runtime._routeBrailleCursor(byte_column)
			return True
		except Exception as error:
			self._fail_open("brailleRoute", error)
			return False
