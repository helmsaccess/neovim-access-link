"""Narrow public contract for Windows Terminal and structured Braille adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .core.exploration_state import ExplorationAction, ExplorationContext
from .core.gate import TerminalIdentity
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
		control_dispatcher: Any,
		present_exploration: Callable[[object, str | None, Mapping[str, Any]], None],
		exploration_details: Callable[[], tuple[bool, bool, bool]],
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
			present_exploration,
			exploration_details,
			record_diagnostic,
			fail_open_event,
		)
		if not all(callable(callback) for callback in callbacks):
			raise ValueError("terminal integration callbacks are required")
		if control_dispatcher is None or not all(
			callable(getattr(control_dispatcher, name, None)) for name in ("submit", "close")
		):
			raise ValueError("a bounded control dispatcher is required")
		self._focusService = focus_service
		self._claimService = claim_service
		self._editorSession = editor_session
		self._commandActions = dict(command_actions)
		self._copyDiagnosticReport = copy_diagnostic_report
		self._claimFocusedSession = claim_focused_session
		self._sendBrailleRoute = send_braille_route
		self._controlDispatcher = control_dispatcher
		self._presentExploration = present_exploration
		self._explorationDetails = exploration_details
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
		self._editorSession.invalidate_exploration()
		self._controlDispatcher.close()
		return True

	def exploration_script_available(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
		expected_identity: TerminalIdentity | None = None,
	) -> bool:
		"""Authorize dynamic exploration scripts only for the exact active Neovim pane."""
		context = self._exploration_context(focus_obj, app_module, adapter_token)
		return context is not None and (expected_identity is None or context.identity == expected_identity)

	def explore_text(
		self,
		action: ExplorationAction,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> TerminalIdentity | None:
		"""Plan and queue one read-only virtual movement without transport I/O here."""
		if not isinstance(action, ExplorationAction):
			return None
		context = self._exploration_context(focus_obj, app_module, adapter_token)
		if context is None:
			self._editorSession.invalidate_exploration()
			return None
		selected = self._editorSession.exploration_instance()
		if selected is None or selected[0] != context.instance_id:
			self._editorSession.invalidate_exploration()
			return None
		plan = self._editorSession.plan_exploration_step(context, action)
		if not plan.ready or plan.control is None or plan.payload is None:
			self._record("explorationRequestRejected", reason=plan.rejection.value)
			return None
		accepted = self._controlDispatcher.submit(selected[1], plan.control, plan.payload)
		if not accepted:
			self._editorSession.invalidate_exploration()
		self._record(
			"explorationRequestQueued",
			accepted=accepted,
			instanceId=context.instance_id,
			requestId=plan.request_id,
			action=action.value,
		)
		return context.identity if accepted else None

	def release_exploration(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		"""Speak the real cursor unit and queue disposal when the NVDA key is released."""
		context = self._exploration_context(focus_obj, app_module, adapter_token)
		if context is None:
			self.cancel_exploration(adapter_token)
			return False
		selected = self._editorSession.exploration_instance()
		if selected is None or selected[0] != context.instance_id:
			self.cancel_exploration(adapter_token)
			return False
		word_character, line_word, line_character = self._explorationDetails()
		plan = self._editorSession.release_exploration(
			context,
			word_character=word_character,
			line_word=line_word,
			line_character=line_character,
		)
		if not plan.ready:
			return False
		if plan.speech_action is not None:
			self._presentExploration(
				plan.speech_action,
				self._editorSession.exploration_mode(),
				self._editorSession.exploration_state(),
			)
		cleanup = plan.cleanup
		if cleanup is not None and cleanup.control is not None and cleanup.payload is not None:
			self._controlDispatcher.submit(selected[1], cleanup.control, cleanup.payload)
		return True

	def cancel_exploration(self, adapter_token: object | None = None) -> bool:
		"""Discard ephemeral state, ignoring stale AppModule teardown notifications."""
		context = self._editorSession.active_exploration_context()
		if context is None or (adapter_token is not None and context.adapter_token is not adapter_token):
			return False
		self._editorSession.invalidate_exploration()
		return True

	def handle_exploration_result(
		self,
		instance_id: str,
		identity: object,
		event: Mapping[str, Any],
	) -> bool:
		"""Correlate one result and present it only in its still-focused pane."""
		if self._closed or identity is None:
			return False
		focus_obj = self._focusService.focused_terminal_object
		app_module = self._focusService.focused_app_module
		adapter_token = self._focusService.focused_adapter_token
		context = self._exploration_context(focus_obj, app_module, adapter_token)
		if context is None or context.instance_id != instance_id or context.identity != identity:
			return False
		plan = self._editorSession.consume_exploration_result(context, event)
		if not plan.accepted or plan.speech_action is None:
			self._record(
				"explorationResultIgnored",
				instanceId=instance_id,
				reason=plan.rejection.value,
			)
			return False
		self._presentExploration(
			plan.speech_action,
			self._editorSession.exploration_mode(),
			self._editorSession.exploration_state(),
		)
		return True

	def _exploration_context(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> ExplorationContext | None:
		if (
			self._closed
			or focus_obj is None
			or app_module is None
			or adapter_token is None
			or getattr(focus_obj, "appModule", None) is not app_module
			or self._focusService.focused_app_module is not app_module
			or self._focusService.focused_adapter_token is not adapter_token
		):
			return None
		try:
			identity = self._focusService.identity(focus_obj)
			selected = self._editorSession.exploration_instance()
			if (
				identity is None
				or not self._focusService.is_active_neovim_context(focus_obj)
				or selected is None
			):
				return None
			return ExplorationContext(selected[0], identity, adapter_token, self._generation)
		except Exception as error:
			self._fail_open("explorationAuthorization", error)
			return None

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
