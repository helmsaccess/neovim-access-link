"""Per-instance editor runtime transitions independent of NVDA plugin inheritance."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .core.connection_coordinator import ConnectionCoordinator
from .core.speech import SpeechPlanner


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


class EditorSessionController:
	"""Own mutation of the active editor runtime selected by the coordinator."""

	def __init__(
		self,
		coordinator: ConnectionCoordinator,
		*,
		new_planner: Callable[[], SpeechPlanner],
	) -> None:
		self._coordinator = coordinator
		self._newPlanner = new_planner

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

	@staticmethod
	def _integer_field(value: Mapping[str, Any] | None, name: str) -> int | None:
		field = value.get(name) if value is not None else None
		return field if isinstance(field, int) and not isinstance(field, bool) else None

	@staticmethod
	def _string_field(value: Mapping[str, Any] | None, name: str) -> str | None:
		field = value.get(name) if value is not None else None
		return field if isinstance(field, str) else None
