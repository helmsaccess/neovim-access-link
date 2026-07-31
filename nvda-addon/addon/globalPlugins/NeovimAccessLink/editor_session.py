"""Per-instance editor runtime transitions independent of NVDA plugin inheritance."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Any

from .core.braille import (
	BraillePlan,
	plan_braille as build_braille_plan,
	plan_command_line_braille as build_command_line_braille_plan,
)
from .core.braille_exploration_state import (
	BrailleExplorationController,
	BrailleExplorationRejection,
	BrailleExplorationRequestPlan,
	BrailleExplorationResultPlan,
	BrailleExplorationTogglePlan,
)
from .core.clipboard import clipboard_result_state, valid_clipboard_text, valid_request_id
from .core.connection_coordinator import ConnectionCoordinator, PendingControlRequest
from .core.exploration_state import (
	ExplorationAction,
	ExplorationContext,
	ExplorationController,
	ExplorationReleasePlan,
	ExplorationRequestPlan,
	ExplorationResultPlan,
)
from .core.gate import TerminalIdentity
from .core.held_context_state import (
	HeldContextController,
	HeldContextDirection,
	HeldContextKind,
	HeldContextLocation,
	HeldContextPresentation,
	HeldContextRequest,
)
from .core.numbered_choice_state import (
	NumberedChoiceAcceptPlan,
	NumberedChoiceContext,
	NumberedChoiceController,
	NumberedChoiceDirection,
	NumberedChoicePresentation,
	NumberedChoiceRejection,
)
from .core.speech import SpeechAction, SpeechPlanner
from .core.terminal_control import terminal_control_result_state
from .core.text import InvalidByteColumn, cursor_text


def mode_sound_kind(mode: str | None) -> str | None:
	"""Map canonical editor modes to the three neutral mode-cue kinds."""
	if mode in {"insert", "terminal"}:
		return "insert"
	if mode in {"normal", "terminalNormal"}:
		return "normal"
	if mode == "commandLine":
		return "commandLine"
	return None


@dataclass(frozen=True)
class EditorEventTransition:
	"""State facts required by the NVDA presentation boundary after one event."""

	event_type: str | None
	previous_mode: str | None
	mode: str | None
	previous_buffer_id: int | None
	buffer_id: int | None
	previous_buftype: str | None
	reset_typed_echo: bool
	braille_cursor_moved: bool


@dataclass(frozen=True)
class ConnectionStateTransition:
	previous: str | None
	current: str
	connection_lost: bool


@dataclass(frozen=True)
class StructuredTypingAction:
	text: str
	spelling: bool


@dataclass(frozen=True)
class ModeCuePlan:
	mode: str
	focus_context: bool = False


@dataclass(frozen=True)
class EditorEventPlan:
	transition: EditorEventTransition
	terminal_passthrough: bool
	mode_cue: ModeCuePlan | None
	speech_actions: tuple[SpeechAction, ...]


@dataclass(frozen=True)
class BrailleSessionPlan:
	plan: BraillePlan
	source_line: str
	numbered_choice: bool = False
	preserve_viewport: bool = False


@dataclass(frozen=True)
class BrailleRoutePlan:
	rejection_reason: str | None
	target: str | None = None
	buffer_id: int | None = None
	window_id: int | None = None
	line: int | None = None
	byte_column: int | None = None
	changedtick: int | None = None
	mode_raw: str | None = None
	command_line: str | None = None
	command_line_type: str | None = None
	character: str | None = None

	@property
	def ready(self) -> bool:
		return self.rejection_reason is None

	def payload(self) -> dict[str, int | str]:
		if not self.ready:
			raise ValueError("a rejected Braille route has no payload")
		values = {
			"bufferId": self.buffer_id,
			"windowId": self.window_id,
			"byteColumn": self.byte_column,
			"changedtick": self.changedtick,
		}
		if not all(isinstance(value, int) and not isinstance(value, bool) for value in values.values()):
			raise ValueError("a ready Braille route requires complete integer state")
		if not isinstance(self.mode_raw, str) or not self.mode_raw:
			raise ValueError("a ready Braille route requires a raw mode")
		payload: dict[str, int | str] = {
			"target": self.target or "",
			**values,
			"modeRaw": self.mode_raw,
		}
		if self.target == "editor":
			if not isinstance(self.line, int) or isinstance(self.line, bool):
				raise ValueError("an editor Braille route requires a line")
			payload["line"] = self.line
		elif self.target == "commandLine":
			if not isinstance(self.command_line, str) or not isinstance(self.command_line_type, str):
				raise ValueError("a command-line Braille route requires structured command state")
			payload["commandLine"] = self.command_line
			payload["commandLineType"] = self.command_line_type
		else:
			raise ValueError("a ready Braille route requires a fixed target")
		return payload


@dataclass(frozen=True)
class BrailleRoutingActionPlan:
	rejection_reason: str | None
	buffer_id: int | None = None
	window_id: int | None = None
	line: int | None = None
	byte_column: int | None = None
	changedtick: int | None = None
	mode_raw: str | None = None
	action: str | None = None
	line_start: str | None = None

	@property
	def ready(self) -> bool:
		return self.rejection_reason is None

	def payload(self) -> dict[str, int | str]:
		if not self.ready:
			raise ValueError("a rejected repeated Braille routing action has no payload")
		values = {
			"bufferId": self.buffer_id,
			"windowId": self.window_id,
			"line": self.line,
			"byteColumn": self.byte_column,
			"changedtick": self.changedtick,
		}
		if not all(isinstance(value, int) and not isinstance(value, bool) for value in values.values()):
			raise ValueError("a ready repeated Braille routing action requires complete state")
		if not isinstance(self.mode_raw, str) or self.mode_raw[:1] not in {"n", "i"}:
			raise ValueError("a ready repeated Braille routing action requires normal or insert mode")
		if self.action not in {"changeWord", "deleteWord", "changeLine", "deleteLine"}:
			raise ValueError("a ready repeated Braille routing action requires a fixed action")
		payload: dict[str, int | str] = {
			**values,
			"modeRaw": self.mode_raw,
			"action": self.action,
		}
		if self.action in {"changeLine", "deleteLine"}:
			if self.line_start not in {"routing", "indentation", "beginning"}:
				raise ValueError("a line action requires a fixed line start")
			payload["lineStart"] = self.line_start
		return payload


@dataclass(frozen=True)
class BrailleLineNavigationPlan:
	rejection_reason: str | None
	direction: str | None = None
	buffer_id: int | None = None
	window_id: int | None = None
	line: int | None = None
	changedtick: int | None = None
	mode_raw: str | None = None
	preferred_virtual_column: int | None = None
	target_column: str | None = None

	@property
	def ready(self) -> bool:
		return self.rejection_reason is None

	def payload(self) -> dict[str, int | str]:
		if not self.ready:
			raise ValueError("a rejected Braille line navigation has no payload")
		values = {
			"bufferId": self.buffer_id,
			"windowId": self.window_id,
			"line": self.line,
			"changedtick": self.changedtick,
			"preferredVirtualColumn": self.preferred_virtual_column,
		}
		if not all(isinstance(value, int) and not isinstance(value, bool) for value in values.values()):
			raise ValueError("a ready Braille line navigation requires complete integer state")
		if self.direction not in {"previous", "next"}:
			raise ValueError("a ready Braille line navigation requires a fixed direction")
		if self.target_column not in {"preferred", "start", "end"}:
			raise ValueError("a ready Braille line navigation requires a fixed target column")
		if not isinstance(self.mode_raw, str) or not self.mode_raw:
			raise ValueError("a ready Braille line navigation requires a raw mode")
		return {
			**values,
			"direction": self.direction,
			"targetColumn": self.target_column,
			"modeRaw": self.mode_raw,
		}


class ControlReplyKind(Enum):
	ACCEPTED = "accepted"
	INVALID_REQUEST_ID = "invalidRequestId"
	STALE_OR_UNBOUND = "staleOrUnbound"


class ControlRequestRejection(Enum):
	CAPABILITY_MISSING = "capabilityMissing"
	INCOMPLETE_STATE = "incompleteState"
	VISUAL_SELECTION_REQUIRED = "visualSelectionRequired"
	PASTE_MODE_UNAVAILABLE = "pasteModeUnavailable"
	BUFFER_NOT_EDITABLE = "bufferNotEditable"
	NOT_DIRECT_TERMINAL = "notDirectTerminal"


@dataclass(frozen=True)
class PendingRequestPlan:
	request_id: int
	discarded_request_ids: tuple[int, ...]


@dataclass(frozen=True)
class OutboundControlPlan:
	rejection: ControlRequestRejection | None
	control: str | None = None
	request_id: int | None = None
	discarded_request_ids: tuple[int, ...] = ()
	payload: Mapping[str, Any] | None = None

	@property
	def ready(self) -> bool:
		return self.rejection is None


@dataclass(frozen=True)
class ClipboardReply:
	kind: ControlReplyKind
	request_id: int | None = None
	event_type: str | None = None
	ok: bool = False
	result_code: str = "invalidResult"
	clipboard_text: str | None = None
	safe_payload: Mapping[str, Any] | None = None
	safe_event: Mapping[str, Any] | None = None

	@property
	def requires_clipboard_write(self) -> bool:
		return (
			self.kind == ControlReplyKind.ACCEPTED
			and self.event_type == "copyTextResult"
			and self.ok
			and self.clipboard_text is not None
		)


@dataclass(frozen=True)
class TerminalControlReply:
	kind: ControlReplyKind
	request_id: int | None = None
	ok: bool = False
	result_code: str = "invalidResult"
	safe_event: Mapping[str, Any] | None = None


class EditorSessionController:
	"""Own mutation of the active editor runtime selected by the coordinator."""

	def __init__(
		self,
		coordinator: ConnectionCoordinator,
		*,
		new_planner: Callable[[], SpeechPlanner],
		max_pending_clipboard_requests: int = 32,
		max_pending_terminal_control_requests: int = 16,
		translate: Callable[[str], str] | None = None,
	) -> None:
		self._coordinator = coordinator
		self._newPlanner = new_planner
		self._translate = translate or (lambda message: message)
		self._maxPendingClipboardRequests = max_pending_clipboard_requests
		self._maxPendingTerminalControlRequests = max_pending_terminal_control_requests
		self._explorationRequestId = 0
		self._exploration = ExplorationController(
			self._next_exploration_request_id,
			translate=translate,
		)

	def new_runtime(self) -> dict[str, Any]:
		"""Return one isolated runtime in the coordinator's stable storage format."""
		return {
			"planner": self._newPlanner(),
			"currentState": {},
			"lastMode": None,
			"typedWord": [],
			"typedPosition": None,
			"menuDocumentation": "",
			"connected": False,
			"lastConnectionState": None,
			"transportCapabilities": frozenset(),
			"extensionState": {
				"brailleExploration": BrailleExplorationController(
					lambda: self._coordinator.next_request_id("brailleExploration"),
				),
				"numberedChoice": NumberedChoiceController(),
				"heldContext": HeldContextController(
					lambda: self._coordinator.next_request_id("developerContext"),
				),
			},
		}

	def switch_instance(self, instance_id: str) -> bool:
		changed = self._coordinator.switch_runtime(instance_id, self.new_runtime)
		if changed:
			self._exploration.invalidate()
		return changed

	def drop_instance(self, instance_id: str) -> bool:
		changed = self._coordinator.drop_runtime(instance_id, self.new_runtime)
		if changed:
			self._exploration.invalidate()
		return changed

	def exploration_available(self) -> bool:
		"""Return whether the selected authenticated runtime advertises exploration."""
		return (
			self._coordinator.active_client is not None
			and self._coordinator.active_instance_id is not None
			and self._coordinator.connected
			and "exploration" in self._coordinator.transport_capabilities
		)

	def exploration_instance(self) -> tuple[str, object] | None:
		"""Return the selected instance and client without performing transport I/O."""
		if not self.exploration_available():
			return None
		return self._coordinator.active_instance_id, self._coordinator.active_client

	def held_context_instance(self, kind: HeldContextKind) -> tuple[str, object] | None:
		capability = "callableContextQuery" if kind is HeldContextKind.CALLABLE else "diagnosticContextQuery"
		if (
			self._coordinator.active_client is None
			or self._coordinator.active_instance_id is None
			or not self._coordinator.connected
			or capability not in self._coordinator.transport_capabilities
		):
			return None
		return self._coordinator.active_instance_id, self._coordinator.active_client

	def begin_held_context(
		self,
		kind: HeldContextKind,
		identity: object,
		adapter_token: object,
		service_generation: object,
	) -> HeldContextRequest | None:
		selected = self.held_context_instance(kind)
		controller = self._active_held_context()
		if selected is None or controller is None:
			return None
		location = HeldContextLocation.from_state(
			selected[0],
			identity,
			adapter_token,
			service_generation,
			self._coordinator.current_state,
		)
		return controller.begin(kind, location) if location is not None else None

	def consume_held_context(
		self,
		kind: HeldContextKind,
		event: Mapping[str, Any],
	) -> HeldContextPresentation | None:
		controller = self._active_held_context()
		if controller is None or not self.held_context_result_is_current(kind, event):
			return None
		return controller.consume(kind, event)

	def held_context_result_is_current(
		self,
		kind: HeldContextKind,
		event: Mapping[str, Any],
	) -> bool:
		controller = self._active_held_context()
		return (
			controller is not None
			and controller.location is not None
			and controller.location.matches_state(self._coordinator.current_state)
			and controller.accepts(kind, event)
		)

	def navigate_held_context(
		self,
		direction: HeldContextDirection,
	) -> HeldContextPresentation | None:
		controller = self._active_held_context()
		return controller.navigate(direction) if controller is not None else None

	def active_held_context_location(self) -> HeldContextLocation | None:
		controller = self._active_held_context()
		return controller.location if controller is not None else None

	def held_context_matches_current_state(self) -> bool:
		controller = self._active_held_context()
		return (
			controller is not None
			and controller.location is not None
			and controller.location.matches_state(self._coordinator.current_state)
		)

	def invalidate_held_context(self) -> bool:
		controller = self._active_held_context()
		return controller.cancel() if controller is not None else False

	def _active_held_context(self) -> HeldContextController | None:
		if self._coordinator.active_instance_id is None:
			return None
		controller = self._coordinator.runtime_extension_state.get("heldContext")
		return controller if isinstance(controller, HeldContextController) else None

	def braille_route_instance(self) -> tuple[str, object] | None:
		"""Return the selected routable instance without performing transport I/O."""
		if (
			self._coordinator.active_client is None
			or self._coordinator.active_instance_id is None
			or not self._coordinator.connected
			or "cursorRouting" not in self._coordinator.transport_capabilities
		):
			return None
		return self._coordinator.active_instance_id, self._coordinator.active_client

	def braille_line_navigation_instance(self) -> tuple[str, object] | None:
		"""Return the selected line-navigable instance without transport I/O."""
		if (
			self._coordinator.active_client is None
			or self._coordinator.active_instance_id is None
			or not self._coordinator.connected
			or "brailleLineNavigation" not in self._coordinator.transport_capabilities
		):
			return None
		return self._coordinator.active_instance_id, self._coordinator.active_client

	def braille_exploration_instance(self) -> tuple[str, object] | None:
		"""Return the selected Braille-explorable instance without transport I/O."""
		if (
			self._coordinator.active_client is None
			or self._coordinator.active_instance_id is None
			or not self._coordinator.connected
			or "brailleExploration" not in self._coordinator.transport_capabilities
		):
			return None
		return self._coordinator.active_instance_id, self._coordinator.active_client

	def braille_exploration_enabled(self) -> bool:
		controller = self._active_braille_exploration()
		return controller is not None and controller.enabled

	def toggle_braille_exploration(self) -> BrailleExplorationTogglePlan:
		controller = self._active_braille_exploration()
		if controller is None:
			return BrailleExplorationTogglePlan(
				BrailleExplorationRejection.INCOMPLETE_STATE,
				False,
			)
		plan = controller.toggle(
			self._coordinator.current_state,
			capabilities=self._coordinator.transport_capabilities,
		)
		if plan.changed:
			# A viewport belongs to one continuous activation. Switching away
			# preserves it through the instance runtime; explicitly toggling the
			# mode starts or ends a different reading context.
			self._coordinator.runtime_extension_state.pop("brailleViewport", None)
		return plan

	def disable_braille_exploration(self) -> BrailleExplorationTogglePlan:
		controller = self._active_braille_exploration()
		if controller is None:
			return BrailleExplorationTogglePlan(
				BrailleExplorationRejection.DISABLED,
				False,
			)
		plan = controller.disable()
		self._coordinator.runtime_extension_state.pop("brailleViewport", None)
		return plan

	def plan_braille_exploration_step(
		self,
		direction: str,
		*,
		target_column: str = "preferred",
	) -> BrailleExplorationRequestPlan:
		controller = self._active_braille_exploration()
		if controller is None:
			return BrailleExplorationRequestPlan(BrailleExplorationRejection.DISABLED)
		return controller.plan_step(
			self._coordinator.current_state,
			direction,
			capabilities=self._coordinator.transport_capabilities,
			target_column=target_column,
		)

	def consume_braille_exploration_result(
		self,
		event: Mapping[str, Any],
	) -> BrailleExplorationResultPlan:
		controller = self._active_braille_exploration()
		if controller is None:
			return BrailleExplorationResultPlan(BrailleExplorationRejection.DISABLED)
		return controller.consume_result(
			self._coordinator.current_state,
			event,
		)

	def fail_braille_exploration_request(self, request_id: int) -> bool:
		controller = self._active_braille_exploration()
		return controller is not None and controller.fail_request(request_id)

	def remember_braille_exploration_viewport(self, start_position: int) -> bool:
		"""Store NVDA's public Braille-window offset in the selected instance runtime."""
		controller = self._active_braille_exploration()
		if (
			controller is None
			or not controller.enabled
			or not isinstance(start_position, int)
			or isinstance(start_position, bool)
			or start_position < 0
		):
			return False
		context = self._braille_viewport_context()
		if context is None:
			return False
		self._coordinator.runtime_extension_state["brailleViewport"] = (
			*context,
			start_position,
		)
		return True

	def braille_exploration_viewport(self) -> int | None:
		"""Return the selected instance's saved Braille-window offset."""
		controller = self._active_braille_exploration()
		if controller is None or not controller.enabled:
			return None
		viewport = self._coordinator.runtime_extension_state.get("brailleViewport")
		context = self._braille_viewport_context()
		if (
			not isinstance(viewport, tuple)
			or len(viewport) != 4
			or context is None
			or viewport[:3] != context
		):
			self._coordinator.runtime_extension_state.pop("brailleViewport", None)
			return None
		start_position = viewport[3]
		if not isinstance(start_position, int) or isinstance(start_position, bool) or start_position < 0:
			self._coordinator.runtime_extension_state.pop("brailleViewport", None)
			return None
		return start_position

	def _braille_viewport_context(self) -> tuple[int, int, int] | None:
		state = self._coordinator.current_state
		context = (
			state.get("bufferId"),
			state.get("windowId"),
			state.get("tabpageId"),
		)
		if not all(
			isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in context
		):
			return None
		return context

	def _active_braille_exploration(self) -> BrailleExplorationController | None:
		if self._coordinator.active_instance_id is None:
			return None
		controller = self._coordinator.runtime_extension_state.get("brailleExploration")
		return controller if isinstance(controller, BrailleExplorationController) else None

	def plan_exploration_step(
		self,
		context: ExplorationContext,
		action: ExplorationAction,
	) -> ExplorationRequestPlan:
		return self._exploration.plan_step(
			context,
			self._coordinator.current_state,
			action,
			capabilities=self._coordinator.transport_capabilities,
		)

	def consume_exploration_result(
		self,
		context: ExplorationContext,
		event: Mapping[str, Any],
	) -> ExplorationResultPlan:
		return self._exploration.consume_result(
			context,
			event,
			state=self._coordinator.current_state,
		)

	def release_exploration(
		self,
		context: ExplorationContext,
		*,
		word_character: bool,
		line_word: bool,
		line_character: bool,
	) -> ExplorationReleasePlan:
		return self._exploration.release(
			context,
			self._coordinator.current_state,
			word_character=word_character,
			line_word=line_word,
			line_character=line_character,
		)

	def invalidate_exploration(self) -> None:
		self._exploration.invalidate()

	def fail_exploration_request(self, request_id: int) -> bool:
		return self._exploration.fail_request(request_id)

	def active_exploration_context(self) -> ExplorationContext | None:
		return self._exploration.active_context

	def exploration_braille_display_active(self) -> bool:
		return self._exploration.braille_display_active

	def exploration_mode(self) -> str | None:
		return self._string_field(self._coordinator.current_state, "mode")

	def exploration_state(self) -> Mapping[str, Any]:
		return MappingProxyType(dict(self._coordinator.current_state))

	def _next_exploration_request_id(self) -> int:
		self._explorationRequestId = (
			1 if self._explorationRequestId >= 2_147_483_647 else self._explorationRequestId + 1
		)
		return self._explorationRequestId

	def handle_numbered_choice_event(
		self,
		context: NumberedChoiceContext,
		event: Mapping[str, Any],
	) -> bool:
		controller = self._active_numbered_choice()
		if controller is None:
			return False
		event_type = event.get("type")
		if event_type == "numberedChoiceOpened":
			return controller.open(
				context,
				event,
				capabilities=self._coordinator.transport_capabilities,
			)
		if event_type == "numberedChoiceClosed":
			return controller.close(context, event)
		return False

	def numbered_choice_available(self, context: NumberedChoiceContext) -> bool:
		controller = self._active_numbered_choice()
		return (
			controller is not None
			and "numberedChoices" in self._coordinator.transport_capabilities
			and controller.available(context)
		)

	def numbered_choice_instance(self) -> tuple[str, object] | None:
		if (
			self._coordinator.active_client is None
			or self._coordinator.active_instance_id is None
			or not self._coordinator.connected
			or "numberedChoices" not in self._coordinator.transport_capabilities
		):
			return None
		return self._coordinator.active_instance_id, self._coordinator.active_client

	def navigate_numbered_choice(
		self,
		context: NumberedChoiceContext,
		direction: NumberedChoiceDirection,
	) -> NumberedChoicePresentation:
		controller = self._active_numbered_choice()
		if controller is None:
			return NumberedChoicePresentation(NumberedChoiceRejection.NO_ACTIVE_CHOICE)
		return controller.navigate(context, direction)

	def plan_numbered_choice_accept(
		self,
		context: NumberedChoiceContext,
	) -> NumberedChoiceAcceptPlan:
		controller = self._active_numbered_choice()
		if controller is None:
			return NumberedChoiceAcceptPlan(NumberedChoiceRejection.NO_ACTIVE_CHOICE)
		return controller.accept_plan(
			context,
			self._coordinator.next_request_id("numberedChoice"),
		)

	def discard_numbered_choice_selection(
		self,
		context: NumberedChoiceContext | None = None,
	) -> bool:
		controller = self._active_numbered_choice()
		return controller is not None and controller.discard_selection(context)

	def active_numbered_choice_context(self) -> NumberedChoiceContext | None:
		controller = self._active_numbered_choice()
		return controller.active_context if controller is not None else None

	def invalidate_numbered_choice(self) -> None:
		controller = self._active_numbered_choice()
		if controller is not None:
			controller.invalidate()

	def _active_numbered_choice(self) -> NumberedChoiceController | None:
		if self._coordinator.active_instance_id is None:
			return None
		controller = self._coordinator.runtime_extension_state.get("numberedChoice")
		return controller if isinstance(controller, NumberedChoiceController) else None

	def apply_event(self, event: Mapping[str, Any]) -> EditorEventTransition:
		"""Apply canonical state changes and return presentation-relevant facts."""
		previous_state = self._coordinator.current_state
		previous_mode = self._coordinator.last_mode
		previous_buffer_id = self._integer_field(previous_state, "bufferId")
		previous_buftype = self._string_field(previous_state, "buftype")
		event_type_value = event.get("type")
		event_type = event_type_value if isinstance(event_type_value, str) else None
		payload_value = event.get("payload")
		payload = payload_value if isinstance(payload_value, dict) else None
		mode = self._string_field(payload, "mode")
		buffer_id = self._integer_field(payload, "bufferId")
		braille_cursor_moved = payload is not None and self._braille_cursor_signature(
			previous_state
		) != self._braille_cursor_signature(payload)

		if payload is not None:
			self._coordinator.current_state = payload
			transport = payload.get("_transport")
			if isinstance(transport, dict) and isinstance(transport.get("capabilities"), list):
				self._coordinator.transport_capabilities = frozenset(
					value for value in transport["capabilities"] if isinstance(value, str)
				)

		if event_type in {"menuSelectionChanged", "menuItemUpdated"} and payload is not None:
			item = payload.get("item", {})
			documentation = item.get("documentation", "") if isinstance(item, dict) else ""
			self._coordinator.menu_documentation = documentation if isinstance(documentation, str) else ""
		elif event_type == "menuClosed":
			self._coordinator.menu_documentation = ""
		if event_type == "hoverChanged" and payload is not None:
			documentation = payload.get("documentation", "")
			self._coordinator.runtime_extension_state["lspHoverDocumentation"] = (
				documentation if isinstance(documentation, str) else ""
			)
		elif event_type == "hoverClosed":
			self._coordinator.runtime_extension_state.pop("lspHoverDocumentation", None)

		reset_typed_echo = event_type == "fullState" or (
			event_type == "modeChanged" and mode != previous_mode
		)
		if reset_typed_echo:
			self.reset_typed_echo()
		if mode is not None:
			self._coordinator.last_mode = mode
		if event_type == "fullState":
			self._coordinator.connected = True
			self._coordinator.last_connection_state = "connected"

		return EditorEventTransition(
			event_type=event_type,
			previous_mode=previous_mode,
			mode=mode,
			previous_buffer_id=previous_buffer_id,
			buffer_id=buffer_id,
			previous_buftype=previous_buftype,
			reset_typed_echo=reset_typed_echo,
			braille_cursor_moved=braille_cursor_moved,
		)

	@staticmethod
	def _braille_cursor_signature(state: Mapping[str, Any] | None) -> tuple[object, ...] | None:
		if not isinstance(state, Mapping):
			return None
		cursor = state.get("cursor")
		cursor = cursor if isinstance(cursor, Mapping) else {}
		return (
			state.get("modeRaw"),
			cursor.get("line"),
			cursor.get("byteColumn"),
			cursor.get("virtualColumn"),
			state.get("commandLineType"),
			state.get("commandLinePosition"),
		)

	def plan_event(
		self,
		event: Mapping[str, Any],
		*,
		focus_announcement: str,
		plan_speech: bool,
		allow_focus_context_cue: bool,
		connection_label: str | None = None,
		word_character: bool = True,
		line_word: bool = False,
		line_character: bool = True,
	) -> EditorEventPlan:
		"""Apply one event and return NVDA-neutral presentation decisions."""
		planned_event = self._with_connection_label(event, connection_label)
		transition = self.apply_event(planned_event)
		payload_value = planned_event.get("payload")
		payload = payload_value if isinstance(payload_value, dict) else None
		terminal_passthrough = bool(
			payload is not None and payload.get("buftype") == "terminal" and payload.get("mode") == "terminal"
		)
		if payload is not None and self._coordinator.active_instance_id is not None:
			self._coordinator.terminal_passthrough[self._coordinator.active_instance_id] = (
				terminal_passthrough
			)
		mode_cue = self._plan_mode_cue(
			transition,
			payload,
			allow_focus_context_cue=allow_focus_context_cue,
		)
		speech_actions = (
			tuple(
				self._coordinator.planner.plan(
					dict(planned_event),
					focus_announcement=focus_announcement,
					word_character=word_character,
					line_word=line_word,
					line_character=line_character,
				)
			)
			if plan_speech
			else ()
		)
		return EditorEventPlan(
			transition=transition,
			terminal_passthrough=terminal_passthrough,
			mode_cue=mode_cue,
			speech_actions=speech_actions,
		)

	@staticmethod
	def _with_connection_label(
		event: Mapping[str, Any],
		connection_label: str | None,
	) -> Mapping[str, Any]:
		if event.get("type") not in {"focusContext", "contextChanged"}:
			return event
		payload = event.get("payload")
		if not isinstance(payload, dict) or connection_label is None:
			return event
		return {
			**event,
			"payload": {
				**payload,
				"_connectionLabel": connection_label,
			},
		}

	def reset_typed_echo(self) -> None:
		self._coordinator.typed_word = []
		self._coordinator.typed_position = None

	def reset_planning_state(self) -> None:
		"""Reset the active semantic planner and its structured typing state."""
		self.disable_braille_exploration()
		self._coordinator.planner.reset()
		self.reset_typed_echo()

	def completion_documentation(self) -> str:
		"""Return the current instance's validated completion or hover documentation."""
		hover = self._coordinator.runtime_extension_state.get("lspHoverDocumentation", "")
		if isinstance(hover, str) and hover:
			return hover
		return self._coordinator.menu_documentation

	def mark_disconnected(self) -> None:
		"""Open connection state immediately when called by a network callback."""
		self._exploration.invalidate()
		self.disable_braille_exploration()
		self.invalidate_numbered_choice()
		self._coordinator.connected = False

	def reset_disconnected_instance(self, instance_id: str) -> bool:
		"""Reset one disconnected runtime without activating another session."""
		if not instance_id:
			return False
		if self._coordinator.active_instance_id == instance_id:
			self.apply_connection_state("disconnected", reset_runtime=True)
			self.mark_disconnected()
			return True
		runtime = self._coordinator.runtime_states.get(instance_id)
		if not isinstance(runtime, dict):
			return False
		runtime["connected"] = False
		runtime["lastConnectionState"] = "disconnected"
		runtime["typedWord"] = []
		runtime["typedPosition"] = None
		planner = runtime.get("planner")
		if callable(getattr(planner, "reset", None)):
			planner.reset()
		extension_state = runtime.get("extensionState")
		if isinstance(extension_state, dict):
			braille_exploration = extension_state.get("brailleExploration")
			if isinstance(braille_exploration, BrailleExplorationController):
				braille_exploration.disable()
			numbered_choice = extension_state.get("numberedChoice")
			if isinstance(numbered_choice, NumberedChoiceController):
				numbered_choice.invalidate()
		return True

	def apply_connection_state(
		self,
		state: str,
		*,
		reset_runtime: bool,
	) -> ConnectionStateTransition:
		previous = self._coordinator.last_connection_state
		self._coordinator.last_connection_state = state
		connection_lost = state == "disconnected" and previous == "connected"
		if connection_lost and reset_runtime:
			self._exploration.invalidate()
			self.disable_braille_exploration()
			self.invalidate_numbered_choice()
			self._coordinator.planner.reset()
			self.reset_typed_echo()
		return ConnectionStateTransition(previous, state, connection_lost)

	def plan_structured_typing(
		self,
		text: str,
		state: Mapping[str, Any] | None,
		*,
		command_line: bool,
		speak_characters: bool,
		speak_words: bool,
	) -> tuple[StructuredTypingAction, ...]:
		"""Mutate isolated typing state and return ordered NVDA-neutral actions."""
		cursor_value = state.get("cursor", {}) if state is not None else {}
		cursor = cursor_value if isinstance(cursor_value, dict) else {}
		line = cursor.get("line")
		byte_column = (
			state.get("commandLinePosition")
			if command_line and state is not None
			else cursor.get(
				"byteColumn",
			)
		)
		buffer_id = state.get("bufferId") if state is not None else None
		byte_length = len(text.encode("utf-8")) if "\n" not in text else None
		start = (
			byte_column - byte_length if isinstance(byte_column, int) and byte_length is not None else None
		)
		identity = ("commandLine", buffer_id) if command_line else (buffer_id, line)
		typed_position = self._coordinator.typed_position
		if typed_position is not None and isinstance(start, int) and isinstance(byte_column, int):
			previous_identity, previous_end = typed_position
			if previous_identity == identity and start < previous_end <= byte_column:
				overlap = previous_end - start
				encoded = text.encode("utf-8")
				try:
					text = encoded[overlap:].decode("utf-8")
					start = previous_end
				except UnicodeDecodeError:
					# A malformed overlap must never cause older text to be guessed.
					self._coordinator.typed_word = []
		if typed_position is not None:
			previous_identity, previous_end = typed_position
			if identity != previous_identity or start != previous_end:
				self._coordinator.typed_word = []

		actions = []
		for character in text:
			if unicodedata.category(character)[:1] in {"L", "M", "N"}:
				self._coordinator.typed_word.append(character)
			else:
				if self._coordinator.typed_word and speak_words:
					actions.append(StructuredTypingAction("".join(self._coordinator.typed_word), False))
				self._coordinator.typed_word = []
			if speak_characters:
				actions.append(StructuredTypingAction(character, True))
		self._coordinator.typed_position = (identity, byte_column) if isinstance(byte_column, int) else None
		return tuple(actions)

	def plan_braille(
		self,
		*,
		report_spelling: bool,
		follow_speech_exploration: bool = False,
	) -> BrailleSessionPlan:
		"""Return an isolated Braille plan for the active canonical editor state."""
		braille_exploration = self._active_braille_exploration()
		braille_exploration_enabled = braille_exploration is not None and braille_exploration.enabled
		numbered_choice = self._active_numbered_choice()
		choice_text = numbered_choice.display_text() if numbered_choice is not None else None
		if choice_text is not None:
			return BrailleSessionPlan(
				plan=BraillePlan(
					choice_text,
					0,
					None,
					None,
					tuple(range(len(choice_text) + 1)),
					tuple(None for _ in choice_text),
				),
				source_line="",
				numbered_choice=True,
			)
		if braille_exploration_enabled:
			display_state = braille_exploration.display_state(self._coordinator.current_state)
		elif follow_speech_exploration:
			display_state = self._exploration.display_state(self._coordinator.current_state)
		else:
			display_state = self._coordinator.current_state
		state = dict(display_state)
		if braille_exploration_enabled:
			display_cursor = state.get("cursor")
			real_state = self._coordinator.current_state
			real_cursor = real_state.get("cursor")
			real_cursor_visible = (
				isinstance(display_cursor, dict)
				and isinstance(real_cursor, dict)
				and display_cursor.get("line") == real_cursor.get("line")
				and state.get("lineText") == real_state.get("lineText")
			)
			state["brailleCursorVisible"] = real_cursor_visible
			if real_cursor_visible:
				state["cursor"] = dict(real_cursor)
		state["reportSpellingBraille"] = bool(report_spelling)
		if state.get("mode") == "commandLine" or str(state.get("modeRaw", "")).startswith("c"):
			command_line = state.get("commandLine")
			return BrailleSessionPlan(
				plan=build_command_line_braille_plan(state),
				source_line=command_line if isinstance(command_line, str) else "",
				preserve_viewport=braille_exploration_enabled,
			)
		line = state.get("lineText")
		return BrailleSessionPlan(
			plan=build_braille_plan(state, translate=self._translate),
			source_line=line if isinstance(line, str) else "",
			preserve_viewport=braille_exploration_enabled,
		)

	def plan_braille_route(
		self,
		byte_column: int,
		*,
		follow_speech_exploration: bool = False,
	) -> BrailleRoutePlan:
		"""Validate a semantic cursor route without performing transport I/O."""
		braille_exploration = self._active_braille_exploration()
		braille_exploration_enabled = braille_exploration is not None and braille_exploration.enabled
		if braille_exploration_enabled:
			state = braille_exploration.routing_state(self._coordinator.current_state)
			if state is None:
				return BrailleRoutePlan("staleExplorationState", byte_column=byte_column)
		elif follow_speech_exploration:
			state = self._exploration.display_state(self._coordinator.current_state)
		else:
			state = self._coordinator.current_state
		transport_value = self._coordinator.current_state.get("_transport", {})
		transport = transport_value if isinstance(transport_value, dict) else {}
		capability_values = transport.get("capabilities")
		capabilities = (
			frozenset(value for value in capability_values if isinstance(value, str))
			if isinstance(capability_values, list)
			else self._coordinator.transport_capabilities
		)
		if "cursorRouting" not in capabilities:
			return BrailleRoutePlan("capabilityMissing")
		common_values = (
			state.get("bufferId"),
			state.get("windowId"),
			byte_column,
			state.get("changedtick"),
		)
		mode_raw = state.get("modeRaw")
		if (
			self._coordinator.active_client is None
			or not all(
				isinstance(value, int) and not isinstance(value, bool) and value >= 0
				for value in common_values
			)
			or not isinstance(mode_raw, str)
			or not mode_raw
		):
			return BrailleRoutePlan("incompleteState", byte_column=byte_column)
		if braille_exploration_enabled and mode_raw.startswith(("c", "t")):
			return BrailleRoutePlan("modeUnavailable", byte_column=byte_column)
		command_line_mode = state.get("mode") == "commandLine" or mode_raw.startswith("c")
		if command_line_mode:
			command_line = state.get("commandLine")
			command_line_type = state.get("commandLineType")
			if not isinstance(command_line, str) or not isinstance(command_line_type, str):
				return BrailleRoutePlan("incompleteState", byte_column=byte_column)
			try:
				character = cursor_text(command_line, byte_column).character
			except InvalidByteColumn:
				return BrailleRoutePlan("incompleteState", byte_column=byte_column)
			return BrailleRoutePlan(
				None,
				target="commandLine",
				buffer_id=common_values[0],
				window_id=common_values[1],
				byte_column=common_values[2],
				changedtick=common_values[3],
				mode_raw=mode_raw,
				command_line=command_line,
				command_line_type=command_line_type,
				character=character,
			)

		cursor_value = state.get("cursor", {})
		cursor = cursor_value if isinstance(cursor_value, dict) else {}
		line = cursor.get("line")
		if not isinstance(line, int) or isinstance(line, bool) or line < 1:
			return BrailleRoutePlan("incompleteState", byte_column=byte_column)
		line_text = state.get("lineText")
		try:
			character = cursor_text(line_text, byte_column).character if isinstance(line_text, str) else None
		except InvalidByteColumn:
			return BrailleRoutePlan("incompleteState", byte_column=byte_column)
		return BrailleRoutePlan(
			None,
			target="editor",
			buffer_id=common_values[0],
			window_id=common_values[1],
			line=line,
			byte_column=common_values[2],
			changedtick=common_values[3],
			mode_raw=mode_raw,
			character=character,
		)

	def plan_braille_routing_action(
		self,
		byte_column: int,
		action: str,
		*,
		line_start: str = "routing",
	) -> BrailleRoutingActionPlan:
		"""Validate a fixed word or line edit at one semantic routing position."""
		if action not in {"changeWord", "deleteWord", "changeLine", "deleteLine"}:
			return BrailleRoutingActionPlan("invalidAction", action=action)
		if line_start not in {"routing", "indentation", "beginning"}:
			return BrailleRoutingActionPlan(
				"invalidLineStart",
				action=action,
				line_start=line_start,
			)
		if "brailleRoutingActions" not in self._coordinator.transport_capabilities:
			return BrailleRoutingActionPlan(
				"capabilityMissing",
				action=action,
				line_start=line_start,
			)
		route = self.plan_braille_route(byte_column)
		if not route.ready:
			return BrailleRoutingActionPlan(
				route.rejection_reason,
				action=action,
				line_start=line_start,
			)
		if route.target != "editor" or route.mode_raw is None or route.mode_raw[:1] not in {"n", "i"}:
			return BrailleRoutingActionPlan(
				"modeUnavailable",
				action=action,
				line_start=line_start,
			)
		return BrailleRoutingActionPlan(
			None,
			buffer_id=route.buffer_id,
			window_id=route.window_id,
			line=route.line,
			byte_column=route.byte_column,
			changedtick=route.changedtick,
			mode_raw=route.mode_raw,
			action=action,
			line_start=line_start,
		)

	def plan_braille_line_navigation(
		self,
		direction: str,
		*,
		target_column: str = "preferred",
	) -> BrailleLineNavigationPlan:
		"""Validate one editor-cursor line move without performing transport I/O."""
		if direction not in {"previous", "next"}:
			return BrailleLineNavigationPlan("invalidDirection", direction=direction)
		if target_column not in {"preferred", "start", "end"}:
			return BrailleLineNavigationPlan(
				"invalidTargetColumn",
				direction=direction,
				target_column=target_column,
			)
		state = self._coordinator.current_state
		transport_value = state.get("_transport", {})
		transport = transport_value if isinstance(transport_value, dict) else {}
		capability_values = transport.get("capabilities")
		capabilities = (
			frozenset(value for value in capability_values if isinstance(value, str))
			if isinstance(capability_values, list)
			else self._coordinator.transport_capabilities
		)
		if "brailleLineNavigation" not in capabilities:
			return BrailleLineNavigationPlan("capabilityMissing", direction=direction)
		cursor_value = state.get("cursor", {})
		cursor = cursor_value if isinstance(cursor_value, dict) else {}
		preferred = cursor.get("preferredVirtualColumn", cursor.get("virtualColumn"))
		values = (
			state.get("bufferId"),
			state.get("windowId"),
			cursor.get("line"),
			state.get("changedtick"),
			preferred,
			state.get("lineCount"),
		)
		mode_raw = state.get("modeRaw")
		if (
			self._coordinator.active_client is None
			or not all(
				isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values
			)
			or values[2] < 1
			or values[4] > 2_147_483_647
			or values[5] < 1
			or not isinstance(mode_raw, str)
			or not mode_raw
			or mode_raw.startswith(("c", "t"))
		):
			return BrailleLineNavigationPlan("incompleteState", direction=direction)
		target_line = values[2] + (-1 if direction == "previous" else 1)
		if target_line < 1 or target_line > values[5]:
			return BrailleLineNavigationPlan("boundary", direction=direction)
		return BrailleLineNavigationPlan(
			None,
			direction=direction,
			buffer_id=values[0],
			window_id=values[1],
			line=values[2],
			changedtick=values[3],
			mode_raw=mode_raw,
			preferred_virtual_column=values[4],
			target_column=target_column,
		)

	def plan_clipboard_request(
		self,
		instance_id: str,
		identity: TerminalIdentity,
		control: str,
		*,
		source: str | None = None,
	) -> OutboundControlPlan:
		"""Validate and correlate one fixed clipboard control without sending it."""
		rejection = self.validate_clipboard_request(control, source=source)
		if rejection is not None:
			return OutboundControlPlan(rejection)
		state = self._coordinator.current_state
		base_payload = self._clipboard_request_state(state)
		if base_payload is None:
			return OutboundControlPlan(ControlRequestRejection.INCOMPLETE_STATE)
		pending = self.remember_clipboard_request(instance_id, identity, control)
		payload = {**base_payload, "requestId": pending.request_id}
		if control == "copyTextRequest":
			payload["source"] = source
		return OutboundControlPlan(
			None,
			control=control,
			request_id=pending.request_id,
			discarded_request_ids=pending.discarded_request_ids,
			payload=MappingProxyType(payload),
		)

	def validate_clipboard_request(
		self,
		control: str,
		*,
		source: str | None = None,
	) -> ControlRequestRejection | None:
		"""Return the bounded reason why a clipboard action cannot run."""
		if control not in {"copyTextRequest", "pasteTextRequest", "setRegisterRequest"}:
			raise ValueError("unsupported clipboard control")
		if "clipboardTransfer" not in self._coordinator.transport_capabilities:
			return ControlRequestRejection.CAPABILITY_MISSING
		state = self._coordinator.current_state
		if self._clipboard_request_state(state) is None:
			return ControlRequestRejection.INCOMPLETE_STATE
		if control == "copyTextRequest":
			if source not in {"visualSelection", "yankRegister"}:
				raise ValueError("unsupported copy source")
			if source == "visualSelection" and state.get("modeRaw") not in {"v", "V", "\x16"}:
				return ControlRequestRejection.VISUAL_SELECTION_REQUIRED
		if control == "pasteTextRequest":
			if state.get("mode") not in {"normal", "insert"} or state.get("modeBlocking") is True:
				return ControlRequestRejection.PASTE_MODE_UNAVAILABLE
			if (
				state.get("buftype", "") != ""
				or state.get("modifiable") is not True
				or state.get("readonly") is True
				or state.get("fileManager")
			):
				return ControlRequestRejection.BUFFER_NOT_EDITABLE
		return None

	def plan_leave_terminal_input_request(
		self,
		instance_id: str,
		identity: TerminalIdentity,
	) -> OutboundControlPlan:
		"""Validate and correlate the fixed terminal-mode escape control."""
		if "terminalControl" not in self._coordinator.transport_capabilities:
			return OutboundControlPlan(ControlRequestRejection.CAPABILITY_MISSING)
		state = self._coordinator.current_state
		if (
			state.get("buftype") != "terminal"
			or state.get("mode") != "terminal"
			or state.get("modeRaw") != "t"
			or state.get("modeBlocking") is True
		):
			return OutboundControlPlan(ControlRequestRejection.NOT_DIRECT_TERMINAL)
		values = {
			"bufferId": state.get("bufferId"),
			"windowId": state.get("windowId"),
			"tabpageId": state.get("tabpageId"),
		}
		if not all(self._is_integer(value) for value in values.values()):
			return OutboundControlPlan(ControlRequestRejection.INCOMPLETE_STATE)
		pending = self.remember_terminal_control_request(
			instance_id,
			identity,
			"leaveTerminalInputRequest",
		)
		return OutboundControlPlan(
			None,
			control="leaveTerminalInputRequest",
			request_id=pending.request_id,
			discarded_request_ids=pending.discarded_request_ids,
			payload=MappingProxyType(
				{
					**values,
					"modeRaw": state.get("modeRaw"),
					"requestId": pending.request_id,
				}
			),
		)

	@classmethod
	def _clipboard_request_state(cls, state: Mapping[str, Any]) -> dict[str, Any] | None:
		values = {
			"bufferId": state.get("bufferId"),
			"windowId": state.get("windowId"),
			"tabpageId": state.get("tabpageId"),
			"changedtick": state.get("changedtick"),
		}
		mode_raw = state.get("modeRaw")
		if not all(cls._is_integer(value) for value in values.values()) or not isinstance(
			mode_raw,
			str,
		):
			return None
		return {**values, "modeRaw": mode_raw}

	@staticmethod
	def _is_integer(value: Any) -> bool:
		return isinstance(value, int) and not isinstance(value, bool)

	def remember_clipboard_request(
		self,
		instance_id: str,
		identity: TerminalIdentity,
		control: str,
	) -> PendingRequestPlan:
		return self._remember_request(
			"clipboard",
			instance_id,
			identity,
			control,
			self._maxPendingClipboardRequests,
		)

	def remember_terminal_control_request(
		self,
		instance_id: str,
		identity: TerminalIdentity,
		control: str,
	) -> PendingRequestPlan:
		return self._remember_request(
			"terminalControl",
			instance_id,
			identity,
			control,
			self._maxPendingTerminalControlRequests,
		)

	def cancel_clipboard_request(self, request_id: int) -> None:
		self._coordinator.take_pending_request("clipboard", request_id)

	def cancel_terminal_control_request(self, request_id: int) -> None:
		self._coordinator.take_pending_request("terminalControl", request_id)

	def discard_clipboard_requests(self, instance_id: str | None = None) -> None:
		self._coordinator.discard_pending_requests("clipboard", instance_id)

	def discard_terminal_control_requests(self, instance_id: str | None = None) -> None:
		self._coordinator.discard_pending_requests("terminalControl", instance_id)

	def consume_clipboard_reply(
		self,
		instance_id: str,
		identity: TerminalIdentity,
		event: Mapping[str, Any],
	) -> ClipboardReply:
		payload_value = event.get("payload")
		payload = payload_value if isinstance(payload_value, dict) else None
		event_type_value = event.get("type")
		event_type = event_type_value if isinstance(event_type_value, str) else None
		request_id = payload.get("requestId") if payload is not None else None
		if not valid_request_id(request_id):
			return ClipboardReply(ControlReplyKind.INVALID_REQUEST_ID)
		pending = self._coordinator.take_pending_request("clipboard", request_id)
		expected_control = {
			"copyTextResult": "copyTextRequest",
			"pasteTextResult": "pasteTextRequest",
			"setRegisterResult": "setRegisterRequest",
		}.get(event_type)
		expected = (
			PendingControlRequest(instance_id, identity, expected_control)
			if expected_control is not None
			else None
		)
		if pending != expected:
			return ClipboardReply(
				ControlReplyKind.STALE_OR_UNBOUND,
				request_id=request_id,
				event_type=event_type,
			)

		safe_payload = dict(payload)
		clipboard_text = safe_payload.pop("clipboardText", None)
		safe_payload.pop("text", None)
		ok = payload.get("ok") is True
		result_code = payload.get("resultCode")
		if not isinstance(result_code, str) or len(result_code) > 64:
			ok = False
			result_code = "invalidResult"
		if event_type == "copyTextResult" and ok and not valid_clipboard_text(clipboard_text):
			ok = False
			result_code = "invalidText"
		return ClipboardReply(
			ControlReplyKind.ACCEPTED,
			request_id=request_id,
			event_type=event_type,
			ok=ok,
			result_code=result_code,
			clipboard_text=clipboard_text if isinstance(clipboard_text, str) else None,
			safe_payload=safe_payload,
			safe_event={**event, "payload": clipboard_result_state(safe_payload)},
		)

	@staticmethod
	def finish_clipboard_reply(reply: ClipboardReply, *, clipboard_written: bool) -> ClipboardReply:
		if reply.requires_clipboard_write and not clipboard_written:
			return replace(reply, ok=False, result_code="clipboardWriteFailed")
		return reply

	def consume_terminal_control_reply(
		self,
		instance_id: str,
		identity: TerminalIdentity,
		event: Mapping[str, Any],
	) -> TerminalControlReply:
		payload_value = event.get("payload")
		payload = payload_value if isinstance(payload_value, dict) else None
		request_id = payload.get("requestId") if payload is not None else None
		if not valid_request_id(request_id):
			return TerminalControlReply(ControlReplyKind.INVALID_REQUEST_ID)
		pending = self._coordinator.take_pending_request("terminalControl", request_id)
		if pending != PendingControlRequest(instance_id, identity, "leaveTerminalInputRequest"):
			return TerminalControlReply(
				ControlReplyKind.STALE_OR_UNBOUND,
				request_id=request_id,
			)
		ok = payload.get("ok") is True
		result_code = payload.get("resultCode")
		if not isinstance(result_code, str) or len(result_code) > 64:
			ok = False
			result_code = "invalidResult"
		return TerminalControlReply(
			ControlReplyKind.ACCEPTED,
			request_id=request_id,
			ok=ok,
			result_code=result_code,
			safe_event={**event, "payload": terminal_control_result_state(payload)},
		)

	def _remember_request(
		self,
		channel: str,
		instance_id: str,
		identity: TerminalIdentity,
		control: str,
		max_pending: int,
	) -> PendingRequestPlan:
		request_id = self._coordinator.next_request_id(channel)
		discarded = self._coordinator.remember_pending_request(
			channel,
			request_id,
			PendingControlRequest(instance_id, identity, control),
			max_pending,
		)
		return PendingRequestPlan(request_id, discarded)

	@classmethod
	def _plan_mode_cue(
		cls,
		transition: EditorEventTransition,
		payload: Mapping[str, Any] | None,
		*,
		allow_focus_context_cue: bool,
	) -> ModeCuePlan | None:
		mode = transition.mode
		previous_mode = transition.previous_mode
		mode_sound = mode_sound_kind(mode)
		previous_mode_sound = mode_sound_kind(previous_mode)
		if transition.event_type == "focusContext" and allow_focus_context_cue and mode_sound is not None:
			return ModeCuePlan(mode, focus_context=True)
		if (
			transition.event_type == "messageReceived"
			and payload is not None
			and payload.get("commandLineReturn") is True
			and mode_sound is not None
		):
			return ModeCuePlan(mode)
		if (
			transition.event_type in {"commandLineChanged", "modeChanged"}
			and mode_sound == "commandLine"
			and previous_mode != "commandLine"
		):
			return ModeCuePlan(mode)
		if (
			transition.event_type in {"modeChanged", "contextChanged"}
			and mode_sound == "insert"
			and previous_mode_sound != "insert"
		):
			return ModeCuePlan(mode)
		if (
			transition.event_type in {"modeChanged", "contextChanged"}
			and mode_sound == "normal"
			and (
				previous_mode_sound == "insert"
				or (previous_mode == "commandLine" and transition.previous_buftype == "terminal")
			)
		):
			return ModeCuePlan(mode)
		if (
			transition.event_type in {"modeChanged", "contextChanged"}
			and mode == "terminalNormal"
			and (previous_mode != "terminalNormal" or transition.previous_buffer_id != transition.buffer_id)
		):
			return ModeCuePlan(mode)
		return None

	@staticmethod
	def _integer_field(value: Mapping[str, Any] | None, name: str) -> int | None:
		field = value.get(name) if value is not None else None
		return field if isinstance(field, int) and not isinstance(field, bool) else None

	@staticmethod
	def _string_field(value: Mapping[str, Any] | None, name: str) -> str | None:
		field = value.get(name) if value is not None else None
		return field if isinstance(field, str) else None
