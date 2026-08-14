"""Remembered terminal binding confirmation, focus recovery, and state refresh."""

from __future__ import annotations

from typing import Any

import addonHandler
import api
import ui

from .session_claim import (
	RememberedBindingActivationKind,
	RememberedStateRequestKind,
	TemporaryBindingOfferKind,
)

addonHandler.initTranslation()

_TEMPORARY_BINDING_RECOVERY_DELAYS_MS = (50, 150, 350, 750)
_REMEMBERED_STATE_RETRY_DELAYS_MS = (150, 350, 750)


class TemporaryBindingWorkflow:
	"""Own the state machine for one runtime's remembered terminal bindings."""

	def __init__(
		self,
		*,
		coordinator: Any,
		session_claim: Any,
		terminal_focus: Any,
		dispatch_control: Any,
		scheduler: Any,
		diagnostics: Any,
		dialogs: Any,
		prompt_answer: Any,
		remember_prompt_answer: Any,
	) -> None:
		if not all(
			callable(callback) for callback in (dispatch_control, prompt_answer, remember_prompt_answer)
		):
			raise ValueError("control dispatch and prompt callbacks are required")
		self._connectionCoordinator = coordinator
		self._sessionClaimService = session_claim
		self._terminalFocusService = terminal_focus
		self._dispatchControl = dispatch_control
		self._scheduler = scheduler
		self._diagnostics = diagnostics
		self._dialogs = dialogs
		self._promptAnswer = prompt_answer
		self._rememberPromptAnswer = remember_prompt_answer

	@property
	def _gate(self):
		return self._connectionCoordinator.gate

	@property
	def _instanceManager(self):
		return self._connectionCoordinator.instances

	def _identityFields(self, identity):
		return self._terminalFocusService.identity_fields(identity)

	def _scheduleMainThreadCall(self, delay_ms, callback, *args):
		return self._scheduler.later(delay_ms, callback, *args)

	def offer_temporary_binding(self, identity, instance_id):
		try:
			prompt_answer = self._promptAnswer()
		except Exception as error:
			prompt_answer = None
			self._diagnostics.record(
				"temporaryTerminalBindingPromptSettingError",
				errorType=type(error).__name__,
			)
		offer = (
			self._sessionClaimService.arm_temporary_binding_reactivation(identity, instance_id)
			if prompt_answer is None
			else self._sessionClaimService.prepare_temporary_binding_offer(identity, instance_id)
		)
		if offer.kind == TemporaryBindingOfferKind.FOCUS_CHANGED:
			self._diagnostics.record(
				"temporaryTerminalBindingOfferIgnored",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if offer.kind == TemporaryBindingOfferKind.UNAVAILABLE:
			self._diagnostics.record(
				"temporaryTerminalBindingUnavailable",
				terminal=self._identityFields(identity),
			)
			return
		if offer.kind != TemporaryBindingOfferKind.OFFER or offer.instance is None:
			return
		if prompt_answer is not None:
			self._diagnostics.record(
				"temporaryTerminalBindingPromptDecisionApplied",
				decision="remember" if prompt_answer else "doNotRemember",
				instanceId=instance_id,
			)
			self._finishTemporaryBindingDecision(identity, instance_id, prompt_answer)
			return
		app_module = self._terminalFocusService.focused_app_module
		adapter_token = self._terminalFocusService.focused_adapter_token

		def finish(accepted, remember_choice):
			if remember_choice:
				try:
					self._rememberPromptAnswer(accepted)
				except Exception as error:
					self._diagnostics.record(
						"temporaryTerminalBindingPromptDecisionSaveFailed",
						errorType=type(error).__name__,
					)
				else:
					self._diagnostics.record(
						"temporaryTerminalBindingPromptDecisionSaved",
						decision="remember" if accepted else "doNotRemember",
					)
			self._finishTemporaryBindingDecision(
				identity,
				instance_id,
				accepted,
				focus_recovery=(app_module, adapter_token),
			)

		self._dialogs.confirm(
			title=_("Remember temporary terminal connection"),
			message=_(
				"Remember this connection for this Windows Terminal tab until NVDA or "
				"Windows Terminal closes?\n\n{connection}"
			).format(connection=offer.instance.label),
			on_result=finish,
		)

	def _finishTemporaryBindingDecision(
		self,
		identity,
		instance_id,
		accepted,
		*,
		focus_recovery=None,
	):
		if not accepted:
			self._diagnostics.record(
				"temporaryTerminalBindingDeclined",
				instanceId=instance_id,
				terminal=self._identityFields(identity),
			)
		else:
			remembered = self._sessionClaimService.remember_temporary_binding(identity, instance_id)
			if remembered.kind != TemporaryBindingOfferKind.OFFER or remembered.instance is None:
				self._diagnostics.record(
					"temporaryTerminalBindingOfferIgnored",
					instanceId=instance_id,
					reason=remembered.kind.value,
				)
			else:
				self._diagnostics.record(
					"temporaryTerminalBindingRemembered",
					instanceId=instance_id,
					transportKind=remembered.instance.transport_kind,
					terminal=self._identityFields(identity),
				)
				ui.message(_("Connection remembered for this terminal tab until NVDA exits"))
		if focus_recovery is not None:
			app_module, adapter_token = focus_recovery
			self._scheduleTemporaryBindingRecovery(
				identity,
				instance_id,
				app_module,
				adapter_token,
			)

	def _scheduleTemporaryBindingRecovery(
		self,
		identity,
		instance_id,
		app_module,
		adapter_token,
	):
		if app_module is None or adapter_token is None:
			self._sessionClaimService.consume_temporary_binding_reactivation(None, None)
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryStopped",
				instanceId=instance_id,
				reason="adapterUnavailable",
			)
			return
		self._diagnostics.record(
			"temporaryTerminalBindingFocusRecoveryScheduled",
			attempts=len(_TEMPORARY_BINDING_RECOVERY_DELAYS_MS),
			instanceId=instance_id,
		)
		self._scheduleMainThreadCall(
			_TEMPORARY_BINDING_RECOVERY_DELAYS_MS[0],
			self._recoverTemporaryBindingFocus,
			identity,
			instance_id,
			app_module,
			adapter_token,
			0,
		)

	def _recoverTemporaryBindingFocus(
		self,
		identity,
		instance_id,
		app_module,
		adapter_token,
		attempt,
	):
		try:
			focus_obj = api.getFocusObject()
		except Exception as error:
			focus_obj = None
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryFocusError",
				errorType=type(error).__name__,
				instanceId=instance_id,
			)
		focus_identity = self._terminalFocusService.identity(focus_obj) if focus_obj is not None else None
		focus_source = "cached"
		try:
			system_focus_obj = api.getDesktopObject().objectWithFocus()
		except Exception as error:
			system_focus_obj = None
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoverySystemFocusError",
				errorType=type(error).__name__,
				instanceId=instance_id,
			)
		if system_focus_obj is not None:
			focus_obj = system_focus_obj
			focus_identity = self._terminalFocusService.identity(system_focus_obj)
			focus_source = "system"
		if focus_identity is not None and focus_identity != identity:
			selected = self._instanceManager.selected_for(focus_identity)
			self._sessionClaimService.consume_temporary_binding_reactivation(
				focus_identity,
				selected.identifier if selected is not None else None,
			)
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryStopped",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if focus_identity == identity and getattr(focus_obj, "appModule", None) is app_module:
			selected = self._instanceManager.selected_for(identity)
			if selected is None or selected.identifier != instance_id:
				self._sessionClaimService.consume_temporary_binding_reactivation(None, None)
				self._diagnostics.record(
					"temporaryTerminalBindingFocusRecoveryStopped",
					instanceId=instance_id,
					reason="selectionChanged",
				)
				return
			focus_already_current = (
				self._gate.focused == identity
				and self._terminalFocusService.focused_app_module is app_module
				and self._terminalFocusService.focused_adapter_token is adapter_token
			)
			foreground_confirmed = (
				self._gate.bound_terminal == identity
				and self._gate.authenticated
				and self._gate.nvim_active
				and self._connectionCoordinator.active_instance_id == instance_id
			)
			if focus_already_current and foreground_confirmed:
				self._sessionClaimService.consume_temporary_binding_reactivation(
					identity,
					instance_id,
				)
				self._diagnostics.record(
					"temporaryTerminalBindingFocusRecoveryStopped",
					instanceId=instance_id,
					reason="alreadyCurrent",
				)
				return
			# A cached object may lag behind operating-system focus after a modal
			# dialog. Only an exact live object may trigger a new handshake.
			if focus_source == "system":
				allowed = self._sessionClaimService.is_temporary_binding_remembered(
					identity
				) or self._sessionClaimService.has_temporary_binding_reactivation(
					identity,
					instance_id,
				)
				if focus_already_current and allowed:
					# gainFocus can restore the adapter fields before its delayed
					# foreground handshake has run. Retry that exact, idempotent
					# request now instead of mistaking adapter focus for a confirmed
					# Neovim binding. A later scheduled copy observes PENDING.
					self.request_remembered_binding_state(identity, instance_id)
					self._sessionClaimService.consume_temporary_binding_reactivation(
						identity,
						instance_id,
					)
					self._diagnostics.record(
						"temporaryTerminalBindingFocusHandshakeRetried",
						instanceId=instance_id,
						terminal=self._identityFields(identity),
					)
					return
				try:
					recovered = allowed and self._terminalFocusService.recover_after_modal(
						focus_obj,
						identity,
						instance_id,
						app_module,
						adapter_token,
					)
				except Exception as error:
					self._gate.disconnect()
					self._sessionClaimService.consume_temporary_binding_reactivation(None, None)
					self._diagnostics.record(
						"temporaryTerminalBindingFocusRecoveryStopped",
						errorType=type(error).__name__,
						instanceId=instance_id,
						reason="error",
					)
					return
				if not recovered:
					self._diagnostics.record(
						"temporaryTerminalBindingFocusRecoveryStopped",
						instanceId=instance_id,
						reason="authorizationChanged",
					)
					return
				self._diagnostics.record(
					"temporaryTerminalBindingFocusRecovered",
					attempt=attempt + 1,
					focusSource=focus_source,
					instanceId=instance_id,
					terminal=self._identityFields(identity),
				)
				return
		if attempt + 1 < len(_TEMPORARY_BINDING_RECOVERY_DELAYS_MS):
			next_attempt = attempt + 1
			self._scheduleMainThreadCall(
				_TEMPORARY_BINDING_RECOVERY_DELAYS_MS[next_attempt],
				self._recoverTemporaryBindingFocus,
				identity,
				instance_id,
				app_module,
				adapter_token,
				next_attempt,
			)
			return
		self._sessionClaimService.consume_temporary_binding_reactivation(
			identity if focus_identity == identity else None,
			instance_id if focus_identity == identity else None,
		)
		if focus_identity != identity:
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryStopped",
				instanceId=instance_id,
				reason="timeout",
			)

	def activate_remembered_binding(self, identity, instance_id, focus_regained=False):
		activation = self._sessionClaimService.activate_remembered_binding(
			identity,
			instance_id,
			focus_regained=focus_regained,
		)
		if activation.kind != RememberedBindingActivationKind.ACTIVATE:
			return
		# Focus events for Windows Terminal tabs can be followed by transient
		# child-focus events. Let focus settle before accepting a new fullState.
		self._scheduleMainThreadCall(
			100,
			self.request_remembered_binding_state,
			identity,
			instance_id,
		)
		self._diagnostics.record(
			"temporaryTerminalBindingActivated",
			instanceId=instance_id,
			terminal=self._identityFields(identity),
			suppressionImmediate=False,
		)

	def request_remembered_binding_state(self, identity, instance_id, attempt=0):
		# A recovery callback and the normal delayed focus callback can overlap
		# around a modal dialog. The first correlated reply may confirm the exact
		# binding before the second callback runs. Do not turn that stale callback
		# into another focusContext request and a duplicate mode cue.
		if self._connectionCoordinator.is_foreground_instance_confirmed(instance_id, identity):
			self._diagnostics.record(
				"temporaryTerminalBindingStateSkipped",
				instanceId=instance_id,
				reason="alreadyConfirmed",
			)
			return
		request = self._sessionClaimService.plan_remembered_state_request(identity, instance_id)
		if request.kind == RememberedStateRequestKind.SKIP:
			self._diagnostics.record(
				"temporaryTerminalBindingStateSkipped",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if request.kind == RememberedStateRequestKind.PENDING:
			self._diagnostics.record(
				"temporaryTerminalBindingStatePending",
				instanceId=instance_id,
			)
			return
		if request.kind == RememberedStateRequestKind.STALE or request.client is None:
			return
		if request.kind == RememberedStateRequestKind.FOCUS_CONTEXT:
			self._dispatchControl(
				request.client,
				"requestFocusContext",
				{"requestId": request.request_id},
				on_result=lambda accepted, error_type: self._finishRememberedStateDispatch(
					identity,
					instance_id,
					attempt,
					request.kind,
					request.request_id,
					accepted,
					error_type,
				),
			)
			return
		self._dispatchControl(
			request.client,
			"requestFullState",
			{},
			on_result=lambda accepted, error_type: self._finishRememberedStateDispatch(
				identity,
				instance_id,
				attempt,
				request.kind,
				None,
				accepted,
				error_type,
			),
		)

	def _finishRememberedStateDispatch(
		self,
		identity,
		instance_id,
		attempt,
		request_kind,
		request_id,
		accepted,
		error_type,
	):
		focus_context = request_kind == RememberedStateRequestKind.FOCUS_CONTEXT
		if (
			focus_context
			and not accepted
			and isinstance(request_id, int)
			and self._connectionCoordinator.matches_focus_context(instance_id, request_id, identity)
		):
			self._connectionCoordinator.discard_focus_context(instance_id)
		self._diagnostics.record(
			(
				"temporaryTerminalFocusContextRequested"
				if focus_context
				else "temporaryTerminalBindingStateRequested"
			),
			instanceId=instance_id,
			requestId=request_id,
			sent=accepted,
			errorType=error_type,
		)
		if not accepted:
			self._retryRememberedBindingState(identity, instance_id, attempt)

	def _retryRememberedBindingState(self, identity, instance_id, attempt):
		if attempt >= len(_REMEMBERED_STATE_RETRY_DELAYS_MS):
			self._diagnostics.record(
				"temporaryTerminalBindingStateRetryStopped",
				attempts=attempt,
				instanceId=instance_id,
			)
			return
		self._scheduleMainThreadCall(
			_REMEMBERED_STATE_RETRY_DELAYS_MS[attempt],
			self.request_remembered_binding_state,
			identity,
			instance_id,
			attempt + 1,
		)
