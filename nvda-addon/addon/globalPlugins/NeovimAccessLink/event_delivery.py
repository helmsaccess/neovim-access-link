"""Correlated inbound transport events and NVDA presentation delivery."""

from __future__ import annotations

from typing import Any

import addonHandler
import braille as nvdaBraille
import config
import speech
import ui
from logHandler import log

from .nvda_braille import (
	capture_structured_viewport,
	restore_structured_viewport,
	StructuredTerminalBrailleOverlay,
)

addonHandler.initTranslation()


class EventDelivery:
	"""Validate instance/focus correlation and deliver planned NVDA output."""

	def __init__(
		self,
		*,
		coordinator: Any,
		editor_session: Any,
		terminal_actions: Any,
		session_claim: Any,
		terminal_focus: Any,
		settings: Any,
		presentation: Any,
		scheduler: Any,
		diagnostics: Any,
		offer_temporary_binding,
	) -> None:
		self._connectionCoordinator = coordinator
		self._editorSessionController = editor_session
		self._terminalActions = terminal_actions
		self._sessionClaimService = session_claim
		self._terminalFocusService = terminal_focus
		self._settingsService = settings
		self._presentation = presentation
		self._scheduler = scheduler
		self._diagnostics = diagnostics
		self._offerTemporaryBinding = offer_temporary_binding
		self._terminalIntegrationService = None

	@property
	def _gate(self):
		return self._connectionCoordinator.gate

	@property
	def _instanceManager(self):
		return self._connectionCoordinator.instances

	def bind_terminal_integration(self, integration) -> None:
		"""Complete the single facade cycle before the runtime is published."""
		if integration is None or self._terminalIntegrationService is not None:
			raise RuntimeError("terminal integration may be bound exactly once")
		self._terminalIntegrationService = integration

	def _queueRuntimeCallback(self, callback, *args, immediate=False):
		return self._scheduler.queue(callback, *args, immediate=immediate)

	def _identityFields(self, identity):
		return self._terminalFocusService.identity_fields(identity)

	def _focusAnnouncement(self):
		return self._settingsService.focus_announcement()

	def _switchInstanceRuntime(self, instance_id):
		self._editorSessionController.switch_instance(instance_id)

	def _discardClipboardRequests(self, *, instance_id=None):
		self._editorSessionController.discard_clipboard_requests(instance_id)

	def _discardTerminalControlRequests(self, *, instance_id=None):
		self._editorSessionController.discard_terminal_control_requests(instance_id)

	def on_managed_event(self, instance_id, event):
		self._queueRuntimeCallback(self.handle_managed_event, instance_id, event)

	def handle_managed_event(self, instance_id, event):
		identity = self._gate.focused
		selected = self._instanceManager.selected_for(identity) if identity else None
		if event.get("type") == "focusContext":
			payload = event.get("payload")
			request_id = payload.get("_focusRequestId") if isinstance(payload, dict) else None
			if (
				not self._connectionCoordinator.matches_focus_context(
					instance_id,
					request_id,
					identity,
				)
				or selected is None
				or selected.identifier != instance_id
				or instance_id not in self._connectionCoordinator.authenticated_instances
			):
				self._diagnostics.record(
					"focusContextIgnored",
					instanceId=instance_id,
					reason="staleOrUnbound",
				)
				return
			self._connectionCoordinator.discard_focus_context(instance_id)
			self._connectionCoordinator.confirm_foreground_instance(
				instance_id,
				identity,
				self._editorSessionController.new_runtime,
			)
			self._diagnostics.record(
				"temporaryTerminalForegroundConfirmed",
				instanceId=instance_id,
				terminal=self._identityFields(identity),
			)
		if selected is None or selected.identifier != instance_id:
			if event.get("type") == "fullState":
				# A modal profile/session chooser can still own NVDA focus when
				# the newly started client delivers its first fullState.  The
				# instance was explicitly bound before it started; defer this
				# authoritative state until its terminal regains focus.
				try:
					self._instanceManager.client_for(instance_id)
				except ValueError:
					return
				self._connectionCoordinator.pending_full_states[instance_id] = event
				self._diagnostics.record(
					"instanceFullStateDeferred",
					instanceId=instance_id,
					reason="terminalNotFocused",
				)
				return
			self._diagnostics.record("instanceEventIgnored", instanceId=instance_id, reason="notSelected")
			return
		if (
			instance_id in self._connectionCoordinator.authenticated_instances
			and event.get("type") != "focusContext"
			and not (
				self._gate.authenticated
				and self._gate.nvim_active
				and self._gate.bound_terminal == identity
				and self._connectionCoordinator.active_instance_id == instance_id
			)
		):
			self._diagnostics.record(
				"instanceEventIgnored",
				instanceId=instance_id,
				reason="foregroundUnconfirmed",
			)
			return
		self._connectionCoordinator.select_instance(
			instance_id,
			identity,
			self._editorSessionController.new_runtime,
		)
		if event.get("type") == "exploreTextResult":
			if not self._terminalIntegrationService.handle_exploration_result(
				instance_id,
				identity,
				event,
			):
				self._diagnostics.record(
					"explorationResultIgnored",
					instanceId=instance_id,
					reason="staleOrUnbound",
				)
			return
		if event.get("type") in {"callableContextResult", "diagnosticContextResult"}:
			if not self._terminalIntegrationService.handle_held_context_result(
				instance_id,
				identity,
				event,
			):
				self._diagnostics.record(
					"developerContextResultIgnored",
					instanceId=instance_id,
					reason="staleOrUnbound",
				)
			return
		if event.get("type") == "brailleExploreLineResult":
			if not self._terminalIntegrationService.handle_braille_exploration_result(
				instance_id,
				identity,
				event,
			):
				self._diagnostics.record(
					"brailleExplorationResultIgnored",
					instanceId=instance_id,
					reason="staleOrUnbound",
				)
			return
		if event.get("type") in {"numberedChoiceOpened", "numberedChoiceClosed"}:
			handled = self._terminalIntegrationService.handle_numbered_choice_event(
				instance_id,
				identity,
				event,
			)
			if not handled:
				self._diagnostics.record(
					"numberedChoiceEventIgnored",
					instanceId=instance_id,
					reason="invalidOrStale",
				)
			elif event.get("type") == "numberedChoiceOpened":
				self._presentation.announce_numbered_choice_opened()
			return
		if event.get("type") in {"copyTextResult", "pasteTextResult", "setRegisterResult"}:
			event = self._terminalActions.handle_clipboard_result(instance_id, identity, event)
			if event is None:
				return
		elif event.get("type") == "leaveTerminalInputResult":
			event = self._terminalActions.handle_terminal_control_result(
				instance_id,
				identity,
				event,
			)
			if event is None:
				return
		first_authenticated_state = (
			event.get("type") == "fullState"
			and instance_id not in self._connectionCoordinator.authenticated_instances
		)
		if event.get("type") == "fullState":
			self._connectionCoordinator.authenticated_instances.add(instance_id)
		self._handleEvent(event, connection_label=selected.context_label)
		if first_authenticated_state and self._connectionCoordinator.is_foreground_instance_confirmed(
			instance_id,
			identity,
		):
			self._presentation.play_connection_sound()
			self._diagnostics.record(
				"connectionEstablished",
				instanceId=instance_id,
				terminal=self._identityFields(identity),
			)
		if event.get("type") == "fullState" and self._sessionClaimService.consume_temporary_binding_offer(
			instance_id
		):
			# Retain the exact authenticated binding in this same main-thread
			# transition. Deferring it would let a later focus event invalidate a
			# successful F12 association before it reaches runtime memory.
			if self._sessionClaimService.is_temporary_binding_remembered(identity):
				self._diagnostics.record(
					"temporaryTerminalBindingRetained",
					instanceId=instance_id,
					terminal=self._identityFields(identity),
				)
				return
			self._offerTemporaryBinding(identity, instance_id)
			return

	def discard_transient_focus_context(self):
		self._captureBrailleExplorationViewport()
		self._terminalIntegrationService.discard_transient_focus_context()
		self._connectionCoordinator.discard_focus_context()
		self._discardClipboardRequests()
		self._discardTerminalControlRequests()

	def _captureBrailleExplorationViewport(self):
		try:
			start_position = capture_structured_viewport(nvdaBraille.handler)
			if start_position is None:
				return False
			return self._editorSessionController.remember_braille_exploration_viewport(
				start_position,
			)
		except Exception as error:
			self._diagnostics.record(
				"brailleViewportCaptureFailed",
				errorType=type(error).__name__,
			)
			return False

	def _restoreBrailleExplorationViewport(self):
		try:
			start_position = self._editorSessionController.braille_exploration_viewport()
			if start_position is None:
				return False
			restored = restore_structured_viewport(nvdaBraille.handler, start_position)
			self._diagnostics.record(
				"brailleViewportRestored",
				restored=restored,
				startPosition=start_position,
			)
			return restored
		except Exception as error:
			self._diagnostics.record(
				"brailleViewportRestoreFailed",
				errorType=type(error).__name__,
			)
			return False

	def on_managed_state(self, instance_id, state):
		# Fail open immediately in the transport callback for the exact active
		# instance. Inactive runtimes are reset on NVDA's main thread below.
		if state == "disconnected" and instance_id == self._connectionCoordinator.active_instance_id:
			self._gate.disconnect()
			self._editorSessionController.mark_disconnected()
		self._queueRuntimeCallback(self._handleManagedState, instance_id, state)

	def _handleManagedState(self, instance_id, state):
		if state == "disconnected":
			self._connectionCoordinator.authenticated_instances.discard(instance_id)
			self._connectionCoordinator.terminal_passthrough.pop(instance_id, None)
			self._connectionCoordinator.pending_full_states.pop(instance_id, None)
			self._connectionCoordinator.discard_focus_context(instance_id)
			self._discardClipboardRequests(instance_id=instance_id)
			self._discardTerminalControlRequests(instance_id=instance_id)
		identity = self._gate.focused
		selected = self._instanceManager.selected_for(identity) if identity else None
		if selected is not None and selected.identifier == instance_id:
			self._switchInstanceRuntime(instance_id)
			self._handleConnectionState(state)
		elif state == "disconnected":
			self._editorSessionController.reset_disconnected_instance(instance_id)

	def fail_open_terminal_event(self, event_name, error):
		"""Drop suppression after a frontend event failure."""
		self._gate.disconnect()
		self._connectionCoordinator.active_client = None
		self._diagnostics.record(
			"terminalEventFailedOpen",
			event=event_name,
			errorType=type(error).__name__,
		)

	def record_network_diagnostic(self, category, fields):
		self._diagnostics.record(category, **fields)
		log.debug("NeovimAccessLink %s %r", category, fields)

	def _handleConnectionState(self, state):
		transition = self._editorSessionController.apply_connection_state(
			state,
			reset_runtime=self._gate.focused is not None,
		)
		self._diagnostics.record("connectionState", previous=transition.previous, state=state)
		if transition.connection_lost and self._gate.focused is not None:
			self._presentation.play_disconnection_sound()
			self._diagnostics.record(
				"connectionLost",
				terminal=self._identityFields(self._gate.focused),
			)
			speech.clearTypedWordBuffer()
			ui.message(_("Neovim connection lost; normal terminal output restored"))
			self._refreshBraille(rebuild=True)

	def _handleEvent(self, event, *, connection_label=None):
		activated = False
		payload = event.get("payload")
		previous_payload = self._editorSessionController.exploration_state()
		word_character, line_word, line_character = self._settingsService.navigation_details(
			exploration=False
		)
		plan = self._editorSessionController.plan_event(
			event,
			focus_announcement=self._focusAnnouncement(),
			plan_speech=self._gate.manual_enabled,
			allow_focus_context_cue=self._gate.manual_enabled,
			connection_label=connection_label,
			word_character=word_character,
			line_word=line_word,
			line_character=line_character,
		)
		transition = plan.transition
		self._terminalIntegrationService.cancel_stale_held_context()
		keyObserverDiagnostics = (
			payload.get("keyObserverDiagnostics", {}) if isinstance(payload, dict) else {}
		)
		if not isinstance(keyObserverDiagnostics, dict):
			keyObserverDiagnostics = {}
		completionAdapterDiagnostics = (
			payload.get("completionAdapterDiagnostics", {}) if isinstance(payload, dict) else {}
		)
		if not isinstance(completionAdapterDiagnostics, dict):
			completionAdapterDiagnostics = {}
		self._diagnostics.record(
			"eventDispatch",
			type=event.get("type"),
			sessionId=event.get("sessionId"),
			sequence=event.get("sequence"),
			mode=payload.get("mode") if isinstance(payload, dict) else None,
			modeRaw=payload.get("modeRaw") if isinstance(payload, dict) else None,
			modeBlocking=(payload.get("modeBlocking") if isinstance(payload, dict) else None),
			bufferId=payload.get("bufferId") if isinstance(payload, dict) else None,
			windowId=payload.get("windowId") if isinstance(payload, dict) else None,
			changedtick=payload.get("changedtick") if isinstance(payload, dict) else None,
			cursor=payload.get("cursor") if isinstance(payload, dict) else None,
			lineText=payload.get("lineText") if isinstance(payload, dict) else None,
			transport=payload.get("_transport") if isinstance(payload, dict) else None,
			preConnectErrorCode=(payload.get("preConnectErrorCode") if isinstance(payload, dict) else None),
			preConnectErrorKind=(payload.get("preConnectErrorKind") if isinstance(payload, dict) else None),
			currentErrorCode=(payload.get("currentErrorCode") if isinstance(payload, dict) else None),
			currentErrorKind=(payload.get("currentErrorKind") if isinstance(payload, dict) else None),
			keyObserverErrorCount=keyObserverDiagnostics.get("observerErrorCount"),
			keyObserverErrorKind=keyObserverDiagnostics.get("observerErrorKind"),
			keyClaimErrorKind=keyObserverDiagnostics.get("claimErrorKind"),
			keyClaimSkippedMode=keyObserverDiagnostics.get("claimSkippedMode"),
			keyClaimConsumed=keyObserverDiagnostics.get("claimKeyConsumed"),
			keyModeAfterClaim=keyObserverDiagnostics.get("modeAfterClaim"),
			keyTranslated=keyObserverDiagnostics.get("translatedKey"),
			keyTypedTranslated=keyObserverDiagnostics.get("translatedTyped"),
			keyByteLength=keyObserverDiagnostics.get("keyByteLength"),
			keyTypedByteLength=keyObserverDiagnostics.get("typedByteLength"),
			keyPromptActive=keyObserverDiagnostics.get("promptActive"),
			keyPromptKind=keyObserverDiagnostics.get("promptKind"),
			keyPromptClass=keyObserverDiagnostics.get("promptClass"),
			keyPromptLength=keyObserverDiagnostics.get("promptLength"),
			completionAdapterActive=completionAdapterDiagnostics.get("activeKind"),
			completionAdapterApi=completionAdapterDiagnostics.get("apiVariant"),
			completionAdapterErrors=completionAdapterDiagnostics.get("errorCount"),
			completionAdapterSlowTicks=completionAdapterDiagnostics.get("slowTickCount"),
			completionAdapterMaximumTickNs=completionAdapterDiagnostics.get("maximumTickNanoseconds"),
		)
		mode = transition.mode
		previous_mode = transition.previous_mode
		event_type = transition.event_type
		terminal_passthrough = plan.terminal_passthrough
		if terminal_passthrough != self._gate.terminal_passthrough:
			# Direct terminal input must fail open before any optional sound or
			# speech is produced for the mode transition.
			self._gate.terminal_passthrough = terminal_passthrough
			self._diagnostics.record(
				"terminalPassthrough",
				enabled=terminal_passthrough,
				bufferId=payload.get("bufferId") if isinstance(payload, dict) else None,
			)
		if plan.mode_cue is not None:
			self._presentation.play_mode_sound(
				plan.mode_cue.mode,
				focus_context=plan.mode_cue.focus_context,
			)
		if transition.reset_typed_echo:
			speech.clearTypedWordBuffer()
		if event_type == "fullState":
			if self._gate.manual_enabled and self._gate.focused is not None:
				self._gate.authenticated = True
				self._gate.nvim_active = True
				self._gate.bound_terminal = self._gate.focused
				activated = True
		if not self._gate.manual_enabled:
			return
		self._playDiagnosticNavigationCue(
			event_type,
			previous_payload,
			payload if isinstance(payload, dict) else {},
		)
		self._presentation.deliver_actions(
			plan.speech_actions,
			event_type=event.get("type"),
			mode=mode,
			previous_mode=previous_mode,
			payload=payload,
			speak_structured_typing=self._speakStructuredTyping,
			allow_braille_messages=not (
				event_type == "focusContext" and self._editorSessionController.braille_exploration_enabled()
			),
		)
		if self._gate.suppression_active:
			# NVDA builds its native terminal regions during gainFocus, before a
			# remembered binding's asynchronous focusContext can authenticate
			# this pane. An incremental update would retain that native region,
			# so physical routing keys would never reach StructuredLineRegion.
			rebuild = activated or event_type == "focusContext"
			self._refreshBraille(
				rebuild=rebuild,
				follow_cursor=(
					not rebuild
					and transition.braille_cursor_moved
					and not self._editorSessionController.braille_exploration_enabled()
				),
			)

	def _playDiagnosticNavigationCue(self, event_type, previous_payload, payload):
		navigation_events = {
			"characterMoved",
			"diagnosticMoved",
			"wordMoved",
			"lineChanged",
			"lineStart",
			"lineEnd",
			"searchMatchChanged",
			"matchingPairMoved",
		}
		if event_type not in navigation_events:
			return
		previous_cursor = previous_payload.get("cursor")
		cursor = payload.get("cursor")
		previous_summary = previous_payload.get("diagnosticSummary")
		summary = payload.get("diagnosticSummary")
		if not all(isinstance(value, dict) for value in (previous_cursor, cursor, previous_summary, summary)):
			return
		position_identity = summary.get("positionIdentity", "")
		# Match VS Code's positional accessibility signal: deliberate cursor
		# navigation emits the cue at every position covered by a diagnostic,
		# not only on the first cell of a range. Text changes and asynchronous
		# DiagnosticChanged refreshes never enter this navigation-only path.
		at_position = bool(position_identity)
		line_changed = cursor.get("line") != previous_cursor.get("line")
		severity = (
			summary.get("positionSeverity")
			if at_position
			else summary.get("lineSeverity")
			if line_changed
			else None
		)
		if severity not in {"error", "warning"}:
			return
		played = self._presentation.play_diagnostic_sound(
			severity,
			at_position=at_position,
		)
		self._diagnostics.record(
			"diagnosticNavigationSound",
			severity=severity,
			scope="position" if at_position else "line",
			played=played,
		)

	def _speakStructuredTyping(self, text, state=None, *, command_line=False):
		keyboard = config.conf["keyboard"]
		speak_characters = int(keyboard["speakTypedCharacters"]) != 0
		speak_words = int(keyboard["speakTypedWords"]) != 0
		actions = self._editorSessionController.plan_structured_typing(
			text,
			state if isinstance(state, dict) else None,
			command_line=command_line,
			speak_characters=speak_characters,
			speak_words=speak_words,
		)
		for action in actions:
			if action.spelling:
				speech.speakSpelling(action.text)
			else:
				speech.speakText(action.text)

	def reset_editor_planning(self):
		self._editorSessionController.reset_planning_state()
		speech.clearTypedWordBuffer()

	def reset_typed_echo(self):
		self._editorSessionController.reset_typed_echo()
		speech.clearTypedWordBuffer()

	def _refreshBraille(self, rebuild, follow_cursor=False):
		try:
			focus = self._terminalFocusService.focused_terminal_object
			if focus is None:
				return
			braille_config = config.conf.get("braille", {})
			try:
				tether = nvdaBraille.handler.getTether()
			except Exception:
				tether = "unknown"
			self._diagnostics.record(
				"brailleRefresh",
				rebuild=bool(rebuild),
				followCursor=bool(follow_cursor),
				enabled=bool(getattr(nvdaBraille.handler, "enabled", False)),
				mode=braille_config.get("mode", "unknown"),
				tether=tether,
				structuredOverlay=isinstance(focus, StructuredTerminalBrailleOverlay),
			)
			if rebuild:
				nvdaBraille.handler.handleGainFocus(focus, shouldAutoTether=False)
				self._restoreBrailleExplorationViewport()
			elif follow_cursor:
				# This is NVDA's public standard caret path. StructuredLineRegion
				# derives from TextInfoRegion so NVDA updates it, restores any
				# manually selected window, and scrolls only as far as necessary
				# to expose the translated cursor cell.
				nvdaBraille.handler.handleCaretMove(focus, shouldAutoTether=False)
			else:
				nvdaBraille.handler.handleUpdate(focus)
		except Exception as error:
			self._diagnostics.record("brailleError", errorType=type(error).__name__, error=str(error))
			log.exception("NeovimAccessLink braille failure")

	def present_exploration(self, action, mode, state):
		self._presentation.deliver_actions(
			(action,),
			event_type="exploreTextResult",
			mode=mode,
			previous_mode=mode,
			payload=state,
			speak_structured_typing=self._speakStructuredTyping,
		)

	def queue_braille_refresh(self, rebuild, follow_cursor=False):
		self._queueRuntimeCallback(self._refreshBraille, rebuild, follow_cursor)
