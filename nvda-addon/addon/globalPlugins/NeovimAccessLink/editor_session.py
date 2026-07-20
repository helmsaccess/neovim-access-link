"""Per-instance editor runtime transitions independent of NVDA plugin inheritance."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from .core.braille import BraillePlan, plan_braille as build_braille_plan
from .core.clipboard import clipboard_result_state, valid_clipboard_text, valid_request_id
from .core.connection_coordinator import ConnectionCoordinator, PendingControlRequest
from .core.gate import TerminalIdentity
from .core.speech import SpeechAction, SpeechPlanner
from .core.terminal_control import terminal_control_result_state


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


@dataclass(frozen=True)
class BrailleRoutePlan:
	rejection_reason: str | None
	buffer_id: int | None = None
	window_id: int | None = None
	line: int | None = None
	byte_column: int | None = None
	changedtick: int | None = None

	@property
	def ready(self) -> bool:
		return self.rejection_reason is None

	def payload(self) -> dict[str, int]:
		if not self.ready:
			raise ValueError("a rejected Braille route has no payload")
		values = {
			"bufferId": self.buffer_id,
			"windowId": self.window_id,
			"line": self.line,
			"byteColumn": self.byte_column,
			"changedtick": self.changedtick,
		}
		if not all(isinstance(value, int) and not isinstance(value, bool) for value in values.values()):
			raise ValueError("a ready Braille route requires complete integer state")
		return values


class ControlReplyKind(Enum):
	ACCEPTED = "accepted"
	INVALID_REQUEST_ID = "invalidRequestId"
	STALE_OR_UNBOUND = "staleOrUnbound"


@dataclass(frozen=True)
class PendingRequestPlan:
	request_id: int
	discarded_request_ids: tuple[int, ...]


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
	) -> None:
		self._coordinator = coordinator
		self._newPlanner = new_planner
		self._maxPendingClipboardRequests = max_pending_clipboard_requests
		self._maxPendingTerminalControlRequests = max_pending_terminal_control_requests

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
		}

	def switch_instance(self, instance_id: str) -> bool:
		return self._coordinator.switch_runtime(instance_id, self.new_runtime)

	def drop_instance(self, instance_id: str) -> bool:
		return self._coordinator.drop_runtime(instance_id, self.new_runtime)

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

		if payload is not None:
			self._coordinator.current_state = payload
			transport = payload.get("_transport")
			if isinstance(transport, dict) and isinstance(transport.get("capabilities"), list):
				self._coordinator.transport_capabilities = frozenset(
					value for value in transport["capabilities"] if isinstance(value, str)
				)

		if event_type == "menuSelectionChanged" and payload is not None:
			item = payload.get("item", {})
			documentation = item.get("documentation", "") if isinstance(item, dict) else ""
			self._coordinator.menu_documentation = documentation if isinstance(documentation, str) else ""
		elif event_type == "menuClosed":
			self._coordinator.menu_documentation = ""

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
		)

	def plan_event(
		self,
		event: Mapping[str, Any],
		*,
		focus_announcement: str,
		plan_speech: bool,
		allow_focus_context_cue: bool,
	) -> EditorEventPlan:
		"""Apply one event and return NVDA-neutral presentation decisions."""
		transition = self.apply_event(event)
		payload_value = event.get("payload")
		payload = payload_value if isinstance(payload_value, dict) else None
		terminal_passthrough = bool(
			payload is not None and payload.get("buftype") == "terminal" and payload.get("mode") == "terminal"
		)
		mode_cue = self._plan_mode_cue(
			transition,
			payload,
			allow_focus_context_cue=allow_focus_context_cue,
		)
		speech_actions = (
			tuple(
				self._coordinator.planner.plan(
					dict(event),
					focus_announcement=focus_announcement,
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

	def reset_typed_echo(self) -> None:
		self._coordinator.typed_word = []
		self._coordinator.typed_position = None

	def mark_disconnected(self) -> None:
		"""Open connection state immediately when called by a network callback."""
		self._coordinator.connected = False

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

	def plan_braille(self, *, report_spelling: bool) -> BrailleSessionPlan:
		"""Return an isolated Braille plan for the active canonical editor state."""
		state = dict(self._coordinator.current_state)
		state["reportSpellingBraille"] = bool(report_spelling)
		line = state.get("lineText")
		return BrailleSessionPlan(
			plan=build_braille_plan(state),
			source_line=line if isinstance(line, str) else "",
		)

	def plan_braille_route(self, byte_column: int) -> BrailleRoutePlan:
		"""Validate a semantic cursor route without performing transport I/O."""
		state = self._coordinator.current_state
		transport_value = state.get("_transport", {})
		transport = transport_value if isinstance(transport_value, dict) else {}
		capability_values = transport.get("capabilities")
		capabilities = (
			frozenset(value for value in capability_values if isinstance(value, str))
			if isinstance(capability_values, list)
			else self._coordinator.transport_capabilities
		)
		if "cursorRouting" not in capabilities:
			return BrailleRoutePlan("capabilityMissing")
		cursor_value = state.get("cursor", {})
		cursor = cursor_value if isinstance(cursor_value, dict) else {}
		values = (
			state.get("bufferId"),
			state.get("windowId"),
			cursor.get("line"),
			byte_column,
			state.get("changedtick"),
		)
		if self._coordinator.active_client is None or not all(
			isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values
		):
			return BrailleRoutePlan("incompleteState", byte_column=byte_column)
		return BrailleRoutePlan(
			None,
			buffer_id=values[0],
			window_id=values[1],
			line=values[2],
			byte_column=values[3],
			changedtick=values[4],
		)

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
