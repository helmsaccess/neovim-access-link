"""Narrow public contract for Windows Terminal and structured Braille adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .editor_session import BrailleSessionPlan, EditorSessionController


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
	"""Expose only operations required by application and Braille adapters."""

	def __init__(
		self,
		focus_service: Any,
		claim_service: Any,
		editor_session: EditorSessionController,
		*,
		command_actions: Mapping[TerminalCommand, Callable[[object], None]],
		copy_diagnostic_report: Callable[[object], None],
		claim_focused_session: Callable[..., None],
		send_braille_route: Callable[[dict[str, Any]], bool],
		record_diagnostic: Callable[..., None],
		fail_open_event: Callable[[str, Exception], None],
	):
		if focus_service is None or claim_service is None or editor_session is None:
			raise ValueError("focus service, claim service, and editor session are required")
		if set(command_actions) != set(TerminalCommand) or not all(
			callable(action) for action in command_actions.values()
		):
			raise ValueError("one callable is required for every terminal command")
		callbacks = (
			copy_diagnostic_report,
			claim_focused_session,
			send_braille_route,
			record_diagnostic,
			fail_open_event,
		)
		if not all(callable(callback) for callback in callbacks):
			raise ValueError("terminal integration callbacks are required")
		self._focusService = focus_service
		self._claimService = claim_service
		self._editorSession = editor_session
		self._commandActions = dict(command_actions)
		self._copyDiagnosticReport = copy_diagnostic_report
		self._claimFocusedSession = claim_focused_session
		self._sendBrailleRoute = send_braille_route
		self._recordDiagnostic = record_diagnostic
		self._failOpenEvent = fail_open_event
		self._generation = object()
		self._closed = False

	@property
	def closed(self) -> bool:
		return self._closed

	def close(self) -> bool:
		"""Invalidate the published service before shared runtime teardown."""
		if self._closed:
			return False
		self._closed = True
		self._generation = object()
		self._claimService.cancel_pending_authorization()
		return True

	def _record(self, category: str, **fields: Any) -> None:
		if self._closed:
			return
		try:
			self._recordDiagnostic(category, **fields)
		except Exception:
			pass

	def _fail_open(self, event_name: str, error: Exception) -> None:
		if self._closed:
			return
		try:
			self._failOpenEvent(event_name, error)
		except Exception:
			# A secondary fail-open failure must not escape into NVDA's event path.
			pass

	def supports_braille_overlay(self, obj: object) -> bool:
		if self._closed:
			return False
		try:
			return self._focusService.identity(obj) is not None
		except Exception as error:
			self._fail_open("chooseNVDAObjectOverlayClasses", error)
			return False

	def prepare_focus(self, obj: object, adapter_token: object, app_module: object) -> object | None:
		if self._closed:
			return None
		try:
			return self._focusService.prepare_focus(obj, adapter_token, app_module)
		except Exception as error:
			self._fail_open("gainFocus", error)
			return None

	def finish_focus(self, decision: object) -> None:
		if self._closed:
			return
		try:
			self._focusService.finish_focus(decision)
		except Exception as error:
			self._fail_open("gainFocusCompletion", error)

	def abandon_focus(self, decision: object) -> None:
		"""Fail open a prepared focus event after the published service changed."""
		if self._closed:
			return
		self._fail_open("staleTerminalFocusService", RuntimeError("terminal service changed"))

	def lose_focus(self, adapter_token: object) -> None:
		if self._closed:
			return
		try:
			self._focusService.lose_focus(adapter_token)
		except Exception as error:
			self._fail_open("appModuleLoseFocus", error)

	def should_use_native_event(self, obj: object, event_name: str) -> bool:
		if self._closed:
			return True
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
		if self._closed or not isinstance(command, TerminalCommand):
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
		self._commandActions[command](gesture)
		return True

	def copy_diagnostic_report(self, gesture: object) -> None:
		if self._closed:
			return
		self._copyDiagnosticReport(gesture)

	def authorize_session_claim(
		self,
		focus_obj: object,
		app_module: object,
	) -> SessionClaimAuthorization | None:
		if self._closed:
			return None
		if getattr(focus_obj, "appModule", None) is not app_module:
			return None
		try:
			identity = self._focusService.identity(focus_obj)
			if identity is None:
				return None
			generation = self._claimService.authorize(identity)
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
			self._closed
			or not isinstance(authorization, SessionClaimAuthorization)
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
		self._claimFocusedSession(
			None,
			forward_gesture=False,
			expected_identity=authorization.identity,
			claim_generation=authorization.generation,
		)
		return True

	def cancel_session_claim(self, authorization: SessionClaimAuthorization) -> bool:
		if (
			self._closed
			or not isinstance(authorization, SessionClaimAuthorization)
			or authorization.service_generation is not self._generation
		):
			return False
		return self._claimService.cancel(
			authorization.identity,
			authorization.generation,
		)

	def should_suppress_braille(self, obj: object) -> bool:
		if self._closed:
			return False
		try:
			return self._focusService.should_suppress(obj)
		except Exception as error:
			self._fail_open("brailleSuppression", error)
			return False

	def braille_plan(self, obj: object, *, report_spelling: bool) -> BrailleSessionPlan | None:
		if not self.should_suppress_braille(obj):
			return None
		try:
			return self._editorSession.plan_braille(report_spelling=report_spelling)
		except Exception as error:
			self._fail_open("braillePlan", error)
			return None

	def suppress_terminal_live_text(self, obj: object, line_count: int) -> bool:
		if not self.should_suppress_braille(obj):
			return False
		self._record("terminalLiveTextSuppressed", lineCount=line_count)
		return True

	def record_braille_route_rejection(self, reason: str, braille_pos: int) -> None:
		if self._closed:
			return
		self._record("brailleRouteRejected", reason=reason, braillePos=braille_pos)

	def route_braille_cursor(self, obj: object, byte_column: int) -> bool:
		if not self.should_suppress_braille(obj):
			return False
		try:
			plan = self._editorSession.plan_braille_route(byte_column)
			if not plan.ready:
				fields = {"byteColumn": byte_column} if plan.rejection_reason == "incompleteState" else {}
				self._record("brailleRouteRejected", reason=plan.rejection_reason, **fields)
				return False
			payload = plan.payload()
			accepted = self._sendBrailleRoute(payload)
			self._record("brailleRoute", accepted=accepted, **payload)
			return bool(accepted)
		except Exception as error:
			self._fail_open("brailleRoute", error)
			return False
