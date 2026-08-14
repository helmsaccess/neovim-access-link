"""Automatic runtime terminal binding retention and state refresh."""

from __future__ import annotations

from typing import Any

import addonHandler
import ui

from .session_claim import (
	RememberedBindingActivationKind,
	RememberedStateRequestKind,
	TemporaryBindingOfferKind,
)

addonHandler.initTranslation()

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
	) -> None:
		if not callable(dispatch_control):
			raise ValueError("control dispatch callback is required")
		self._connectionCoordinator = coordinator
		self._sessionClaimService = session_claim
		self._terminalFocusService = terminal_focus
		self._dispatchControl = dispatch_control
		self._scheduler = scheduler
		self._diagnostics = diagnostics

	def _identityFields(self, identity):
		return self._terminalFocusService.identity_fields(identity)

	def _scheduleMainThreadCall(self, delay_ms, callback, *args):
		return self._scheduler.later(delay_ms, callback, *args)

	def offer_temporary_binding(self, identity, instance_id):
		offer = self._sessionClaimService.remember_temporary_binding(identity, instance_id)
		if offer.kind == TemporaryBindingOfferKind.FOCUS_CHANGED:
			self._diagnostics.record(
				"temporaryTerminalBindingRememberIgnored",
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
		self._diagnostics.record(
			"temporaryTerminalBindingRemembered",
			instanceId=instance_id,
			transportKind=offer.instance.transport_kind,
			terminal=self._identityFields(identity),
		)
		ui.message(_("Connection remembered for this terminal tab until NVDA exits"))

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
		# Closely spaced focus events can schedule overlapping refreshes. The first
		# correlated reply may already confirm the exact binding, so do not turn a
		# stale callback into another request and a duplicate mode cue.
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
