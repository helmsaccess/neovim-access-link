"""Narrow public contract for Windows Terminal and structured Braille adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
import time
from typing import Any

from .core.braille_exploration_state import BrailleExplorationTogglePlan
from .core.braille_routing_repeats import (
	BrailleRoutingActions,
	BrailleRoutingPressKind,
	BrailleRoutingRepeatController,
)
from .core.exploration_state import ExplorationAction, ExplorationContext
from .core.gate import TerminalIdentity
from .core.held_context_state import (
	HeldContextDirection,
	HeldContextKind,
	HeldContextPresentation,
)
from .core.numbered_choice_state import (
	NumberedChoiceContext,
	NumberedChoiceDirection,
	NumberedChoiceRejection,
)
from .editor_session import BrailleSessionPlan, EditorSessionController


class TerminalCommand(Enum):
	"""Commands that an application-specific adapter may request."""

	TOGGLE_ACCESSIBILITY = "action_toggleNeovimMode"
	TOGGLE_BRAILLE_EXPLORATION = "action_toggleBrailleExplorationMode"
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


@dataclass(frozen=True)
class NumberedChoiceAuthorization:
	"""One-shot contextual activation for one exact native Neovim prompt."""

	context: NumberedChoiceContext


@dataclass(frozen=True)
class _DirectBrailleNextLineIntent:
	"""One event-turn marker distinguishing NVDA's direct line command from scrolling."""

	token: object
	focus_obj: object
	app_module: object
	adapter_token: object
	service_generation: object


@dataclass(frozen=True)
class _PendingBrailleRoutingAction:
	"""Revalidatable deferred action for one exact editor instance."""

	token: int
	instance_id: str
	client: object
	byte_column: int
	action: str
	line_start: str


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
		present_braille_route_character: Callable[[str], bool],
		control_dispatcher: Any,
		present_exploration: Callable[[object, str | None, Mapping[str, Any]], None],
		exploration_details: Callable[[], tuple[bool, bool, bool]],
		present_numbered_choice: Callable[[str], bool],
		dismiss_numbered_choice: Callable[[], None],
		present_developer_context: Callable[
			[HeldContextPresentation | None, HeldContextKind, HeldContextDirection | None],
			bool,
		],
		dismiss_developer_context: Callable[[], None],
		refresh_braille: Callable[[], None],
		no_item_selected_message: str,
		record_diagnostic: Callable[..., None],
		fail_open_event: Callable[[str, Exception], None],
		numbered_choice_braille_start: Callable[[], int] | None = None,
		braille_routing_actions: Callable[[], BrailleRoutingActions] | None = None,
		braille_follows_speech_exploration: Callable[[], bool] | None = None,
		routing_repeat_timeout_ms: Callable[[], int] | None = None,
		schedule_later: Callable[[int, Callable[[], None]], object] | None = None,
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
			present_braille_route_character,
			present_exploration,
			exploration_details,
			present_numbered_choice,
			dismiss_numbered_choice,
			present_developer_context,
			dismiss_developer_context,
			refresh_braille,
			record_diagnostic,
			fail_open_event,
		)
		if not all(callable(callback) for callback in callbacks):
			raise ValueError("terminal integration callbacks are required")
		if not isinstance(no_item_selected_message, str) or not no_item_selected_message:
			raise ValueError("a no-selection message is required")
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
		self._presentBrailleRouteCharacter = present_braille_route_character
		self._controlDispatcher = control_dispatcher
		self._presentExploration = present_exploration
		self._explorationDetails = exploration_details
		self._presentNumberedChoice = present_numbered_choice
		self._dismissNumberedChoice = dismiss_numbered_choice
		self._presentDeveloperContext = present_developer_context
		self._dismissDeveloperContext = dismiss_developer_context
		self._refreshBraille = refresh_braille
		self._noItemSelectedMessage = no_item_selected_message
		self._numberedChoiceBrailleStart = numbered_choice_braille_start or (lambda: 1)
		self._brailleRoutingActions = braille_routing_actions or BrailleRoutingActions
		self._brailleFollowsSpeechExploration = braille_follows_speech_exploration or (lambda: False)
		self._routingRepeatTimeoutMs = routing_repeat_timeout_ms or (lambda: 500)
		self._scheduleLater = schedule_later or (lambda _delay, _callback: None)
		self._brailleRoutingRepeats = BrailleRoutingRepeatController()
		self._pendingBrailleRoutingAction: _PendingBrailleRoutingAction | None = None
		self._recordDiagnostic = record_diagnostic
		self._failOpenEvent = fail_open_event
		self._generation = object()
		self._directBrailleNextLineIntent: _DirectBrailleNextLineIntent | None = None
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
		self._directBrailleNextLineIntent = None
		self._claimService.cancel_pending_authorization()
		self._editorSession.invalidate_exploration()
		self._editorSession.disable_braille_exploration()
		self._brailleRoutingRepeats.reset()
		self._pendingBrailleRoutingAction = None
		self._editorSession.invalidate_numbered_choice()
		self._dismissNumberedChoice()
		self._editorSession.invalidate_held_context()
		self._dismissDeveloperContext()
		self._controlDispatcher.close()
		return True

	def toggle_braille_exploration(self) -> BrailleExplorationTogglePlan:
		"""Toggle the independent Braille view and queue its optional remote cleanup."""
		try:
			plan = self._editorSession.toggle_braille_exploration()
			if not plan.changed:
				self._record(
					"brailleExplorationToggleRejected",
					reason=plan.rejection.value,
				)
				return plan
			if plan.cleanup_control is not None and plan.cleanup_payload is not None:
				selected = self._editorSession.braille_exploration_instance()
				if selected is not None:
					self._controlDispatcher.submit(
						selected[1],
						plan.cleanup_control,
						plan.cleanup_payload,
					)
			self._record("brailleExplorationMode", enabled=plan.enabled)
			return plan
		except Exception:
			self._editorSession.disable_braille_exploration()
			raise

	def numbered_choice_script_available(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		context = self._numbered_choice_context(focus_obj, app_module, adapter_token)
		return context is not None and self._editorSession.numbered_choice_available(context)

	def navigate_numbered_choice(
		self,
		direction: NumberedChoiceDirection,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		if not isinstance(direction, NumberedChoiceDirection):
			return False
		context = self._numbered_choice_context(focus_obj, app_module, adapter_token)
		if context is None:
			return False
		plan = self._editorSession.navigate_numbered_choice(context, direction)
		if not plan.ready or plan.text is None:
			self._record("numberedChoiceNavigationRejected", reason=plan.rejection.value)
			return False
		if not self._presentNumberedChoice(plan.text):
			# NVDA can be configured not to show Braille messages. Keep the
			# structured focus-region path as a non-invasive fallback.
			self._refreshBraille()
		return True

	def release_numbered_choice(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		context = self._numbered_choice_context(focus_obj, app_module, adapter_token)
		if context is None:
			return False
		changed = self._editorSession.discard_numbered_choice_selection(context)
		if changed:
			self._dismissNumberedChoice()
			self._refreshBraille()
		return changed

	def cancel_numbered_choice(self, adapter_token: object | None = None) -> bool:
		context = self._editorSession.active_numbered_choice_context()
		if context is None or (adapter_token is not None and context.adapter_token is not adapter_token):
			return False
		self._editorSession.invalidate_numbered_choice()
		self._dismissNumberedChoice()
		self._refreshBraille()
		return True

	def authorize_numbered_choice_accept(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> NumberedChoiceAuthorization | None:
		context = self._numbered_choice_context(focus_obj, app_module, adapter_token)
		if context is None or not self._editorSession.numbered_choice_available(context):
			return None
		return NumberedChoiceAuthorization(context)

	def complete_numbered_choice_accept(
		self,
		authorization: NumberedChoiceAuthorization,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		if self._closed or not isinstance(authorization, NumberedChoiceAuthorization):
			return False
		context = self._numbered_choice_context(focus_obj, app_module, adapter_token)
		if context != authorization.context:
			return False
		plan = self._editorSession.plan_numbered_choice_accept(context)
		if plan.rejection is NumberedChoiceRejection.NO_SELECTED_ITEM:
			self._presentNumberedChoice(self._noItemSelectedMessage)
			return True
		if not plan.ready or plan.payload is None:
			return False
		selected = self._editorSession.numbered_choice_instance()
		if selected is None or selected[0] != context.instance_id:
			return False
		accepted = self._controlDispatcher.submit(
			selected[1],
			"acceptNumberedChoiceRequest",
			plan.payload,
		)
		self._record(
			"numberedChoiceAcceptQueued",
			accepted=accepted,
			instanceId=context.instance_id,
			requestId=plan.payload.get("requestId"),
		)
		if accepted:
			self._editorSession.discard_numbered_choice_selection(context)
			self._dismissNumberedChoice()
			self._refreshBraille()
		return accepted

	def handle_numbered_choice_event(
		self,
		instance_id: str,
		identity: object,
		event: Mapping[str, Any],
	) -> bool:
		if self._closed or identity is None:
			return False
		context = self._numbered_choice_context(
			self._focusService.focused_terminal_object,
			self._focusService.focused_app_module,
			self._focusService.focused_adapter_token,
		)
		if context is None or context.instance_id != instance_id or context.identity != identity:
			return False
		handled = self._editorSession.handle_numbered_choice_event(context, event)
		if handled:
			if self._editorSession.active_numbered_choice_context() is None:
				self._dismissNumberedChoice()
			self._refreshBraille()
		return handled

	def _numbered_choice_context(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> NumberedChoiceContext | None:
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
			selected = self._editorSession.numbered_choice_instance()
			if (
				identity is None
				or not self._focusService.is_active_neovim_context(focus_obj)
				or selected is None
			):
				return None
			return NumberedChoiceContext(selected[0], identity, adapter_token, self._generation)
		except Exception as error:
			self._fail_open("numberedChoiceAuthorization", error)
			return None

	def start_held_context(
		self,
		kind: HeldContextKind,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		if not isinstance(kind, HeldContextKind):
			self._record("developerContextRequestRejected", reason="invalidKind")
			return False
		identity = self._active_identity(focus_obj, app_module, adapter_token)
		if identity is None:
			self._record(
				"developerContextRequestRejected",
				kind=kind.value,
				reason="inactiveContext",
			)
			return False
		if self._editorSession.active_numbered_choice_context() is not None:
			self._record(
				"developerContextRequestRejected",
				kind=kind.value,
				reason="numberedChoiceActive",
			)
			return False
		# A focus or runtime handoff can leave the previous adapter's transient
		# Braille message visible until the next editor event. Starting a newly
		# authorized context owns that handoff and must dismiss the old view now.
		self.cancel_held_context()
		request = self._editorSession.begin_held_context(
			kind,
			identity,
			adapter_token,
			self._generation,
		)
		selected = self._editorSession.held_context_instance(kind)
		if request is None:
			self._record(
				"developerContextRequestRejected",
				kind=kind.value,
				reason="requestUnavailable",
			)
			return False
		if selected is None:
			self._editorSession.invalidate_held_context()
			self._record(
				"developerContextRequestRejected",
				kind=kind.value,
				reason="providerUnavailable",
			)
			return False
		accepted = self._controlDispatcher.submit(
			selected[1],
			request.control,
			dict(request.payload),
		)
		if not accepted:
			self._editorSession.invalidate_held_context()
		else:
			self.cancel_exploration(adapter_token)
		self._record(
			"developerContextRequestQueued",
			accepted=accepted,
			kind=kind.value,
			requestId=request.request_id,
		)
		return accepted

	def navigate_held_context(
		self,
		direction: HeldContextDirection,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		if not isinstance(direction, HeldContextDirection):
			return False
		location = self._editorSession.active_held_context_location()
		identity = self._active_identity(focus_obj, app_module, adapter_token)
		if (
			location is None
			or identity is None
			or location.identity != identity
			or location.adapter_token is not adapter_token
			or location.service_generation is not self._generation
		):
			return False
		presentation = self._editorSession.navigate_held_context(direction)
		return presentation is not None and self._presentDeveloperContext(
			presentation,
			presentation.kind,
			direction,
		)

	def release_held_context(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> bool:
		location = self._editorSession.active_held_context_location()
		identity = self._active_identity(focus_obj, app_module, adapter_token)
		if (
			location is None
			or identity is None
			or location.identity != identity
			or location.adapter_token is not adapter_token
		):
			return False
		return self.cancel_held_context(adapter_token)

	def cancel_held_context(self, adapter_token: object | None = None) -> bool:
		location = self._editorSession.active_held_context_location()
		if location is None or (adapter_token is not None and location.adapter_token is not adapter_token):
			return False
		changed = self._editorSession.invalidate_held_context()
		if changed:
			self._dismissDeveloperContext()
			self._refreshBraille()
		return changed

	def cancel_stale_held_context(self) -> bool:
		"""Dismiss held information after its exact editor location changes."""
		if (
			self._editorSession.active_held_context_location() is None
			or self._editorSession.held_context_matches_current_state()
		):
			return False
		return self.cancel_held_context()

	def handle_held_context_result(
		self,
		instance_id: str,
		identity: object,
		event: Mapping[str, Any],
	) -> bool:
		event_type = event.get("type")
		kind = (
			HeldContextKind.CALLABLE
			if event_type == "callableContextResult"
			else HeldContextKind.DIAGNOSTIC
			if event_type == "diagnosticContextResult"
			else None
		)
		location = self._editorSession.active_held_context_location()
		if (
			self._closed
			or kind is None
			or location is None
			or location.instance_id != instance_id
			or location.identity != identity
			or location.service_generation is not self._generation
		):
			return False
		if not self._editorSession.held_context_result_is_current(kind, event):
			self.cancel_held_context(location.adapter_token)
			return False
		presentation = self._editorSession.consume_held_context(kind, event)
		handled = self._presentDeveloperContext(presentation, kind, None)
		return handled

	def _active_identity(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> object | None:
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
			return (
				identity
				if identity is not None and self._focusService.is_active_neovim_context(focus_obj)
				else None
			)
		except Exception as error:
			self._fail_open("developerContextAuthorization", error)
			return None

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
		restore_braille = (
			self._follow_speech_exploration() and self._editorSession.exploration_braille_display_active()
		)
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
		if restore_braille:
			self._refreshBraille()
		return True

	def cancel_exploration(self, adapter_token: object | None = None) -> bool:
		"""Discard ephemeral state, ignoring stale AppModule teardown notifications."""
		context = self._editorSession.active_exploration_context()
		if context is None or (adapter_token is not None and context.adapter_token is not adapter_token):
			return False
		restore_braille = (
			self._follow_speech_exploration() and self._editorSession.exploration_braille_display_active()
		)
		self._editorSession.invalidate_exploration()
		if restore_braille:
			self._refreshBraille()
		return True

	def discard_transient_focus_context(self) -> None:
		"""Discard input sequences that must never continue in another terminal."""
		self.cancel_exploration()
		self._brailleRoutingRepeats.reset()
		self._pendingBrailleRoutingAction = None
		self._directBrailleNextLineIntent = None
		self._dismissNumberedChoice()
		self.cancel_held_context()

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
		if plan.braille_display_changed and self._follow_speech_exploration():
			self._refreshBraille()
		return True

	def _follow_speech_exploration(self) -> bool:
		try:
			return self._brailleFollowsSpeechExploration() is True
		except Exception as error:
			self._record(
				"brailleExplorationFollowSettingsError",
				errorType=type(error).__name__,
				error=str(error),
			)
			return False

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
		intent = self._directBrailleNextLineIntent
		if intent is not None and intent.adapter_token is adapter_token:
			self._directBrailleNextLineIntent = None
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

	def mark_direct_braille_next_line(
		self,
		focus_obj: object,
		app_module: object,
		adapter_token: object,
	) -> object | None:
		"""Mark one public NVDA direct-next-line command for the exact focused pane."""
		if (
			self._closed
			or focus_obj is None
			or app_module is None
			or adapter_token is None
			or getattr(focus_obj, "appModule", None) is not app_module
			or self._focusService.focused_terminal_object is not focus_obj
			or self._focusService.focused_app_module is not app_module
			or self._focusService.focused_adapter_token is not adapter_token
		):
			return None
		try:
			if not self._focusService.is_active_neovim_context(focus_obj):
				return None
		except Exception as error:
			self._fail_open("brailleNextLineIntent", error)
			return None
		token = object()
		self._directBrailleNextLineIntent = _DirectBrailleNextLineIntent(
			token,
			focus_obj,
			app_module,
			adapter_token,
			self._generation,
		)
		return token

	def consume_direct_braille_next_line(self, focus_obj: object) -> bool:
		"""Consume a still-current direct-next-line marker exactly once."""
		intent = self._directBrailleNextLineIntent
		self._directBrailleNextLineIntent = None
		if (
			self._closed
			or intent is None
			or intent.service_generation is not self._generation
			or intent.focus_obj is not focus_obj
			or self._focusService.focused_terminal_object is not focus_obj
			or self._focusService.focused_app_module is not intent.app_module
			or self._focusService.focused_adapter_token is not intent.adapter_token
		):
			return False
		try:
			return bool(self._focusService.is_active_neovim_context(focus_obj))
		except Exception as error:
			self._fail_open("brailleNextLineIntent", error)
			return False

	def clear_direct_braille_next_line(self, token: object) -> None:
		"""Expire one unconsumed marker after NVDA's current input turn."""
		intent = self._directBrailleNextLineIntent
		if intent is not None and intent.token is token:
			self._directBrailleNextLineIntent = None

	def braille_plan(self, obj: object, *, report_spelling: bool) -> BrailleSessionPlan | None:
		if not self.should_suppress_braille(obj):
			return None
		try:
			return self._editorSession.plan_braille(
				report_spelling=report_spelling,
				follow_speech_exploration=self._follow_speech_exploration(),
			)
		except Exception as error:
			self._fail_open("braillePlan", error)
			return None

	def numbered_choice_braille_start(self) -> int:
		"""Return the configured one-based start cell, falling back safely."""
		try:
			value = self._numberedChoiceBrailleStart()
		except Exception as error:
			self._fail_open("numberedChoiceBrailleStart", error)
			return 1
		return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else 1

	def suppress_terminal_live_text(self, obj: object, line_count: int) -> bool:
		if not self.should_suppress_braille(obj):
			return False
		self._record("terminalLiveTextSuppressed", lineCount=line_count)
		return True

	def record_braille_route_rejection(self, reason: str, braille_pos: int) -> None:
		if self._closed:
			return
		self._record("brailleRouteRejected", reason=reason, braillePos=braille_pos)

	def record_braille_overlay_selected(self) -> None:
		if self._closed:
			return
		self._record("brailleOverlaySelected")

	def record_braille_region_request(self, *, review: bool, suppressed: bool) -> None:
		if self._closed:
			return
		self._record("brailleRegionRequested", review=review, suppressed=suppressed)

	def record_braille_route_attempt(self, braille_pos: int, *, suppressed: bool) -> None:
		if self._closed:
			return
		self._record("brailleRouteAttempt", braillePos=braille_pos, suppressed=suppressed)

	def route_braille_cursor(
		self,
		obj: object,
		byte_column: int,
		*,
		braille_position: int | None = None,
	) -> bool:
		if not self.should_suppress_braille(obj):
			return False
		try:
			follow_speech_exploration = self._follow_speech_exploration()
			plan = self._editorSession.plan_braille_route(
				byte_column,
				follow_speech_exploration=follow_speech_exploration,
			)
			if not plan.ready:
				fields = {"byteColumn": byte_column} if plan.rejection_reason == "incompleteState" else {}
				self._record("brailleRouteRejected", reason=plan.rejection_reason, **fields)
				return False
			instance = self._editorSession.braille_route_instance()
			if instance is None:
				self._record("brailleRouteRejected", reason="incompleteState")
				return False
			payload = plan.payload()
			actions = self._normalized_braille_routing_actions()
			if follow_speech_exploration and self._editorSession.exploration_braille_display_active():
				# Contextual exploration is read-only. A single routing press may
				# adopt the displayed position, but repeated edit actions stay off.
				actions = BrailleRoutingActions()
			probe_action = actions.word_action if actions.word_action != "none" else actions.line_action
			if actions.enabled:
				probe = self._editorSession.plan_braille_routing_action(
					byte_column,
					probe_action,
					line_start=actions.line_start,
				)
				if not probe.ready:
					actions = BrailleRoutingActions()
			identity = (
				instance[0],
				braille_position,
				payload.get("target"),
				payload.get("bufferId"),
				payload.get("windowId"),
				payload.get("line"),
				payload.get("byteColumn"),
				payload.get("changedtick"),
				payload.get("modeRaw"),
			)
			repeat = self._brailleRoutingRepeats.press(
				identity,
				now_ms=int(time.monotonic() * 1000),
				timeout_ms=self._normalized_routing_repeat_timeout(),
				actions=actions,
			)
			if repeat.kind is BrailleRoutingPressKind.WAIT:
				return self._defer_braille_routing_word_action(
					repeat.token,
					repeat.delay_ms,
					instance,
					byte_column,
					actions,
				)
			if repeat.kind in {
				BrailleRoutingPressKind.WORD,
				BrailleRoutingPressKind.LINE,
			}:
				return self._dispatch_braille_routing_action(
					instance,
					byte_column,
					repeat.action,
					line_start=repeat.line_start or actions.line_start,
				)
			self._pendingBrailleRoutingAction = None
			queued = self._controlDispatcher.submit(instance[1], "routeCursor", payload)
			self._record("brailleRoute", queued=queued, instanceId=instance[0], **payload)
			if queued and plan.character:
				self._presentBrailleRouteCharacter(plan.character)
			return bool(queued)
		except Exception as error:
			self._fail_open("brailleRoute", error)
			return False

	def _normalized_braille_routing_actions(self) -> BrailleRoutingActions:
		try:
			actions = self._brailleRoutingActions()
			return actions if isinstance(actions, BrailleRoutingActions) else BrailleRoutingActions()
		except Exception as error:
			self._record(
				"brailleRoutingSettingsError",
				errorType=type(error).__name__,
				error=str(error),
			)
			return BrailleRoutingActions()

	def _normalized_routing_repeat_timeout(self) -> int:
		try:
			value = self._routingRepeatTimeoutMs()
			if isinstance(value, int) and not isinstance(value, bool):
				return max(100, min(value, 20_000))
		except Exception:
			pass
		return 500

	def _defer_braille_routing_word_action(
		self,
		token: int | None,
		delay_ms: int | None,
		instance: tuple[str, object],
		byte_column: int,
		actions: BrailleRoutingActions,
	) -> bool:
		if not isinstance(token, int) or not isinstance(delay_ms, int):
			self._brailleRoutingRepeats.reset()
			return False
		pending: _PendingBrailleRoutingAction | None = None
		if actions.word_action != "none":
			plan = self._editorSession.plan_braille_routing_action(
				byte_column,
				actions.word_action,
				line_start=actions.line_start,
			)
			if plan.ready:
				pending = _PendingBrailleRoutingAction(
					token,
					instance[0],
					instance[1],
					byte_column,
					actions.word_action,
					actions.line_start,
				)
			else:
				self._record(
					"brailleRoutingActionRejected",
					reason=plan.rejection_reason,
					action=actions.word_action,
				)
		self._pendingBrailleRoutingAction = pending
		try:
			self._scheduleLater(delay_ms, lambda: self._complete_braille_routing_repeat(token))
		except Exception as error:
			self._brailleRoutingRepeats.reset()
			self._pendingBrailleRoutingAction = None
			self._fail_open("brailleRoutingSchedule", error)
			return False
		self._record(
			"brailleRoutingRepeat",
			pressCount=2,
			deferred=actions.word_action != "none",
		)
		return True

	def _complete_braille_routing_repeat(self, token: int) -> None:
		if self._closed:
			return
		repeat = self._brailleRoutingRepeats.expire(token)
		pending = self._pendingBrailleRoutingAction
		if pending is not None and pending.token == token:
			self._pendingBrailleRoutingAction = None
		if repeat.kind is not BrailleRoutingPressKind.WORD or pending is None:
			return
		instance = self._editorSession.braille_route_instance()
		if instance is None or instance[0] != pending.instance_id or instance[1] is not pending.client:
			self._record(
				"brailleRoutingActionRejected",
				reason="staleOrUnbound",
				action=pending.action,
			)
			return
		plan = self._editorSession.plan_braille_routing_action(
			pending.byte_column,
			pending.action,
			line_start=pending.line_start,
		)
		if not plan.ready:
			self._record(
				"brailleRoutingActionRejected",
				reason=plan.rejection_reason,
				action=pending.action,
			)
			return
		queued = self._controlDispatcher.submit(
			pending.client,
			"brailleRouteAction",
			plan.payload(),
		)
		self._record(
			"brailleRoutingAction",
			queued=queued,
			pressCount=2,
			action=repeat.action,
		)

	def _dispatch_braille_routing_action(
		self,
		instance: tuple[str, object],
		byte_column: int,
		action: str | None,
		*,
		line_start: str,
	) -> bool:
		self._pendingBrailleRoutingAction = None
		if action is None:
			return False
		plan = self._editorSession.plan_braille_routing_action(
			byte_column,
			action,
			line_start=line_start,
		)
		if not plan.ready:
			self._record(
				"brailleRoutingActionRejected",
				reason=plan.rejection_reason,
				action=action,
			)
			return False
		payload = plan.payload()
		queued = self._controlDispatcher.submit(instance[1], "brailleRouteAction", payload)
		self._record(
			"brailleRoutingAction",
			queued=queued,
			pressCount=3 if action in {"changeLine", "deleteLine"} else 2,
			**payload,
		)
		return bool(queued)

	def navigate_braille_line(
		self,
		obj: object,
		direction: str,
		*,
		target_column: str = "preferred",
	) -> bool:
		"""Queue one validated editor-cursor line move from a Braille region."""
		if not self.should_suppress_braille(obj):
			return False
		try:
			if self._editorSession.braille_exploration_enabled():
				plan = self._editorSession.plan_braille_exploration_step(
					direction,
					target_column=target_column,
				)
				if not plan.ready or plan.control is None or plan.payload is None:
					self._record(
						"brailleExplorationNavigationRejected",
						reason=plan.rejection.value,
						direction=direction,
					)
					return False
				instance = self._editorSession.braille_exploration_instance()
				if instance is None:
					self._record(
						"brailleExplorationNavigationRejected",
						reason="incompleteState",
						direction=direction,
					)
					return False
				queued = self._controlDispatcher.submit(instance[1], plan.control, plan.payload)
				if not queued and plan.request_id is not None:
					self._editorSession.fail_braille_exploration_request(plan.request_id)
				self._record(
					"brailleExplorationNavigation",
					queued=queued,
					instanceId=instance[0],
					direction=direction,
					targetColumn=target_column,
					requestId=plan.request_id,
				)
				return bool(queued)
			plan = self._editorSession.plan_braille_line_navigation(
				direction,
				target_column=target_column,
			)
			if not plan.ready:
				self._record(
					"brailleLineNavigationRejected",
					reason=plan.rejection_reason,
					direction=direction,
				)
				return False
			instance = self._editorSession.braille_line_navigation_instance()
			if instance is None:
				self._record(
					"brailleLineNavigationRejected",
					reason="incompleteState",
					direction=direction,
				)
				return False
			payload = plan.payload()
			queued = self._controlDispatcher.submit(instance[1], "moveBrailleLine", payload)
			self._record(
				"brailleLineNavigation",
				queued=queued,
				instanceId=instance[0],
				**payload,
			)
			return bool(queued)
		except Exception as error:
			self._fail_open("brailleLineNavigation", error)
			return False

	def handle_braille_exploration_result(
		self,
		instance_id: str,
		identity: object,
		event: Mapping[str, Any],
	) -> bool:
		"""Apply one correlated virtual line only to the still-focused Braille pane."""
		if self._closed or identity is None or not self._editorSession.braille_exploration_enabled():
			return False
		focus_obj = self._focusService.focused_terminal_object
		selected = self._editorSession.braille_exploration_instance()
		try:
			active = (
				focus_obj is not None
				and selected is not None
				and selected[0] == instance_id
				and self._focusService.identity(focus_obj) == identity
				and self._focusService.is_active_neovim_context(focus_obj)
			)
		except Exception as error:
			self._fail_open("brailleExplorationAuthorization", error)
			return False
		if not active:
			return False
		plan = self._editorSession.consume_braille_exploration_result(event)
		if not plan.accepted:
			self._record(
				"brailleExplorationResultIgnored",
				instanceId=instance_id,
				reason=plan.rejection.value,
				requestId=plan.request_id,
			)
			return False
		self._record(
			"brailleExplorationResult",
			instanceId=instance_id,
			requestId=plan.request_id,
			resultCode=plan.result_code,
		)
		if plan.display_changed:
			self._refreshBraille()
		return True
