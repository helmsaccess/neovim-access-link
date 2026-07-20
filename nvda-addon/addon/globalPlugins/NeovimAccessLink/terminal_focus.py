"""State owner for Windows Terminal focus and identity transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .core.connection_coordinator import ConnectionCoordinator
from .core.gate import TerminalIdentity


@dataclass(frozen=True)
class TerminalFocusDecision:
	"""Immutable result of preparing one Windows Terminal focus event."""

	adapter_token: object
	generation: int
	identity: TerminalIdentity | None
	instance_id: str | None
	pending_full_state: dict | None
	suppress_native_speech: bool


class TerminalFocusService:
	"""Own focused frontend state and correlated focus completion."""

	def __init__(
		self,
		coordinator: ConnectionCoordinator,
		*,
		identity_for_object: Callable[[object], TerminalIdentity | None],
		identity_element: Callable[[object, TerminalIdentity], object | None],
		identity_fields: Callable[[TerminalIdentity | None], dict | None],
		record_diagnostic: Callable[..., None],
		discard_transient_context: Callable[[], None],
		activate_remembered_binding: Callable[[TerminalIdentity, str, bool], None],
		handle_pending_full_state: Callable[[str, dict], None],
		reset_typed_echo: Callable[[], None],
		cancel_speech: Callable[[], None],
	):
		self._coordinator = coordinator
		self._identityForObject = identity_for_object
		self._identityElement = identity_element
		self._identityFields = identity_fields
		self._recordDiagnostic = record_diagnostic
		self._discardTransientContext = discard_transient_context
		self._activateRememberedBinding = activate_remembered_binding
		self._handlePendingFullState = handle_pending_full_state
		self._resetTypedEcho = reset_typed_echo
		self._cancelSpeech = cancel_speech
		self._focusedTerminalObject = None
		self._identityElements: dict[TerminalIdentity, object] = {}
		self._focusedAppModule = None
		self._focusedAdapterToken = None
		self._generation = 0

	@property
	def focused_terminal_object(self) -> object | None:
		return self._focusedTerminalObject

	@focused_terminal_object.setter
	def focused_terminal_object(self, value: object | None) -> None:
		# Compatibility for existing internal tests while ownership stays here.
		self._focusedTerminalObject = value

	@property
	def focused_app_module(self) -> object | None:
		return self._focusedAppModule

	@property
	def focused_adapter_token(self) -> object | None:
		return self._focusedAdapterToken

	def identity(self, obj: object) -> TerminalIdentity | None:
		return self._identityForObject(obj)

	def identity_fields(self, identity: TerminalIdentity | None) -> dict | None:
		return self._identityFields(identity)

	def known_element(self, identity: TerminalIdentity) -> object | None:
		return self._identityElements.get(identity)

	def forget_identity(self, identity: TerminalIdentity) -> None:
		self._identityElements.pop(identity, None)

	def clear(self) -> None:
		self._identityElements.clear()
		self._focusedTerminalObject = None
		self._focusedAppModule = None
		self._focusedAdapterToken = None

	def prepare_focus(
		self,
		obj: object,
		adapter_token: object,
		app_module: object | None = None,
	) -> TerminalFocusDecision:
		"""Prepare shared state before the AppModule runs native focus handling."""
		if adapter_token is None:
			raise ValueError("adapter token is required")
		gate = self._coordinator.gate
		previous = gate.focused
		identity = self.identity(obj)
		if previous != identity:
			self._discardTransientContext()
			gate.disconnect()
			self._recordDiagnostic(
				"terminalFocusIdentityChanged",
				previous=self.identity_fields(previous),
				current=self.identity_fields(identity),
			)
		gate.focused = identity
		if identity is not None:
			element = self._identityElement(obj, identity)
			if element is not None:
				self._identityElements[identity] = element
		self._focusedTerminalObject = obj if identity is not None else None
		self._focusedAppModule = app_module
		self._focusedAdapterToken = adapter_token
		self._generation += 1
		instance = self._coordinator.instances.selected_for(identity) if identity else None
		pending_full_state = (
			self._coordinator.pending_full_states.get(instance.identifier) if instance is not None else None
		)
		if identity in self._coordinator.remembered_terminal_bindings:
			if instance is None:
				self._coordinator.remembered_terminal_bindings.discard(identity)
			else:
				self._activateRememberedBinding(identity, instance.identifier, previous != identity)
		return TerminalFocusDecision(
			adapter_token=adapter_token,
			generation=self._generation,
			identity=identity,
			instance_id=instance.identifier if instance is not None else None,
			pending_full_state=pending_full_state,
			suppress_native_speech=(identity is not None and gate.should_suppress(identity))
			or pending_full_state is not None,
		)

	def finish_focus(self, decision: TerminalFocusDecision) -> None:
		"""Complete prepared focus after the AppModule initialized native LiveText."""
		if not isinstance(decision, TerminalFocusDecision):
			raise ValueError("terminal focus decision is required")
		if (
			decision.adapter_token is not self._focusedAdapterToken
			or decision.generation != self._generation
			or decision.identity != self._coordinator.gate.focused
		):
			self._recordDiagnostic("staleTerminalFocusCompletionIgnored")
			return
		if decision.suppress_native_speech:
			self._cancelSpeech()
			self._recordDiagnostic(
				"terminalFocusAnnouncementSuppressed",
				terminal=self.identity_fields(decision.identity),
			)
		if decision.pending_full_state is None or decision.instance_id is None:
			return
		if self._coordinator.pending_full_states.get(decision.instance_id) is not decision.pending_full_state:
			self._recordDiagnostic(
				"terminalFocusPendingStateChanged",
				instanceId=decision.instance_id,
			)
			return
		self._coordinator.pending_full_states.pop(decision.instance_id, None)
		self._recordDiagnostic("instanceFullStateResumed", instanceId=decision.instance_id)
		self._handlePendingFullState(decision.instance_id, decision.pending_full_state)

	def refresh_for_action(
		self,
		obj: object,
		app_module: object | None = None,
		adapter_token: object | None = None,
	) -> TerminalIdentity | None:
		"""Refresh focus when an action does not receive a new gainFocus event."""
		gate = self._coordinator.gate
		identity = self.identity(obj)
		previous = gate.focused
		gate.focused = identity
		if identity is not None:
			element = self._identityElement(obj, identity)
			if element is not None:
				self._identityElements[identity] = element
		self._focusedTerminalObject = obj if identity is not None else None
		self._focusedAppModule = app_module if identity is not None else None
		self._focusedAdapterToken = adapter_token if identity is not None else None
		self._recordDiagnostic(
			"terminalActionFocusRefreshed",
			previous=self.identity_fields(previous),
			current=self.identity_fields(identity),
		)
		return identity

	def lose_focus(self, adapter_token: object) -> None:
		if (
			adapter_token is not None
			and self._focusedAdapterToken is not None
			and adapter_token is not self._focusedAdapterToken
		):
			self._recordDiagnostic("staleAppModuleLoseFocusIgnored")
			return
		gate = self._coordinator.gate
		previous = gate.focused
		gate.disconnect()
		gate.focused = None
		self._discardTransientContext()
		self._focusedTerminalObject = None
		self._focusedAppModule = None
		self._focusedAdapterToken = None
		self._resetTypedEcho()
		if previous is not None:
			self._recordDiagnostic(
				"terminalApplicationLostFocus",
				previous=self.identity_fields(previous),
			)

	def should_suppress(self, obj: object) -> bool:
		identity = self.identity(obj)
		return identity is not None and self._coordinator.gate.should_suppress(identity)
