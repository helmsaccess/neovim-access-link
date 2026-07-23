"""NVDA-independent lifecycle and presentation plans for virtual exploration."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from .gate import TerminalIdentity
from .speech import Priority, SpeechAction


MAX_EXPLORATION_TEXT_BYTES = 16 * 1024


def _identity(message: str) -> str:
	return message


class ExplorationAction(Enum):
	CHARACTER_LEFT = "characterLeft"
	CHARACTER_RIGHT = "characterRight"
	LINE_UP = "lineUp"
	LINE_DOWN = "lineDown"
	WORD_PREVIOUS = "wordPrevious"
	WORD_NEXT = "wordNext"


class ExplorationUnit(Enum):
	CHARACTER = "character"
	LINE = "line"
	WORD = "word"


class ExplorationRejection(Enum):
	CAPABILITY_MISSING = "capabilityMissing"
	INCOMPLETE_STATE = "incompleteState"
	CONTEXT_CHANGED = "contextChanged"
	NO_ACTIVE_EXPLORATION = "noActiveExploration"
	INVALID_RESULT = "invalidResult"
	STALE_OR_UNBOUND = "staleOrUnbound"


_ACTION_UNITS = {
	ExplorationAction.CHARACTER_LEFT: ExplorationUnit.CHARACTER,
	ExplorationAction.CHARACTER_RIGHT: ExplorationUnit.CHARACTER,
	ExplorationAction.LINE_UP: ExplorationUnit.LINE,
	ExplorationAction.LINE_DOWN: ExplorationUnit.LINE,
	ExplorationAction.WORD_PREVIOUS: ExplorationUnit.WORD,
	ExplorationAction.WORD_NEXT: ExplorationUnit.WORD,
}


@dataclass(frozen=True)
class ExplorationContext:
	instance_id: str
	identity: TerminalIdentity
	adapter_token: object
	service_generation: object


@dataclass(frozen=True)
class ExplorationRequestPlan:
	rejection: ExplorationRejection | None
	control: str | None = None
	request_id: int | None = None
	exploration_id: int | None = None
	action_index: int | None = None
	discarded_request_ids: tuple[int, ...] = ()
	payload: Mapping[str, Any] | None = None

	@property
	def ready(self) -> bool:
		return self.rejection is None


@dataclass(frozen=True)
class ExplorationResultPlan:
	rejection: ExplorationRejection | None
	request_id: int | None = None
	exploration_id: int | None = None
	action_index: int | None = None
	unit: ExplorationUnit | None = None
	result_code: str = "invalidResult"
	speech_action: SpeechAction | None = None

	@property
	def accepted(self) -> bool:
		return self.rejection is None


@dataclass(frozen=True)
class ExplorationReleasePlan:
	rejection: ExplorationRejection | None
	speech_action: SpeechAction | None = None
	cleanup: ExplorationRequestPlan | None = None

	@property
	def ready(self) -> bool:
		return self.rejection is None


@dataclass(frozen=True)
class _Origin:
	buffer_id: int
	window_id: int
	tabpage_id: int
	changedtick: int
	mode_raw: str
	cursor_line: int
	cursor_byte_column: int
	cursor_virtual_column: int

	def payload(self) -> dict[str, int | str]:
		return {
			"bufferId": self.buffer_id,
			"windowId": self.window_id,
			"tabpageId": self.tabpage_id,
			"changedtick": self.changedtick,
			"modeRaw": self.mode_raw,
			"cursorLine": self.cursor_line,
			"cursorByteColumn": self.cursor_byte_column,
			"cursorVirtualColumn": self.cursor_virtual_column,
		}


@dataclass
class _ActiveExploration:
	exploration_id: int
	context: ExplorationContext
	origin: _Origin
	action_index: int = 0
	last_unit: ExplorationUnit | None = None
	virtual_position_at_origin: bool = True


@dataclass(frozen=True)
class _PendingResult:
	context: ExplorationContext
	exploration_id: int
	action_index: int
	action: ExplorationAction
	unit: ExplorationUnit


class ExplorationController:
	"""Correlate one bounded virtual exploration without calling NVDA APIs."""

	def __init__(
		self,
		next_request_id: Callable[[], int],
		*,
		translate: Callable[[str], str] | None = None,
		max_pending_requests: int = 32,
	) -> None:
		if not callable(next_request_id):
			raise TypeError("next_request_id must be callable")
		if max_pending_requests < 1:
			raise ValueError("max_pending_requests must be positive")
		self._nextRequestId = next_request_id
		self._translate = translate or _identity
		self._maxPendingRequests = max_pending_requests
		self._nextExplorationId = 0
		self._active: _ActiveExploration | None = None
		self._pending: OrderedDict[int, _PendingResult] = OrderedDict()

	@property
	def active(self) -> bool:
		return self._active is not None

	@property
	def active_context(self) -> ExplorationContext | None:
		return self._active.context if self._active is not None else None

	@property
	def last_unit(self) -> ExplorationUnit | None:
		return self._active.last_unit if self._active is not None else None

	def plan_step(
		self,
		context: ExplorationContext,
		state: Mapping[str, Any],
		action: ExplorationAction,
		*,
		count: int = 1,
		capabilities: frozenset[str] | set[str] | None = None,
	) -> ExplorationRequestPlan:
		if not isinstance(context, ExplorationContext) or not isinstance(action, ExplorationAction):
			raise TypeError("a validated exploration context and action are required")
		if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 64:
			raise ValueError("exploration count must be from 1 through 64")
		if capabilities is not None and "exploration" not in capabilities:
			return ExplorationRequestPlan(ExplorationRejection.CAPABILITY_MISSING)
		origin = self._origin(state)
		if origin is None:
			self.invalidate()
			return ExplorationRequestPlan(ExplorationRejection.INCOMPLETE_STATE)
		if self._active is None:
			self._nextExplorationId = self._bounded_increment(self._nextExplorationId)
			self._active = _ActiveExploration(self._nextExplorationId, context, origin)
		elif self._active.context != context or self._active.origin != origin:
			self.invalidate()
			return ExplorationRequestPlan(ExplorationRejection.CONTEXT_CHANGED)

		active = self._active
		active.action_index = self._bounded_increment(active.action_index)
		active.last_unit = _ACTION_UNITS[action]
		request_id = self._nextRequestId()
		if not self._valid_positive_integer(request_id):
			self.invalidate()
			raise ValueError("next_request_id returned an invalid value")
		pending = _PendingResult(
			context,
			active.exploration_id,
			active.action_index,
			action,
			active.last_unit,
		)
		self._pending[request_id] = pending
		discarded = []
		while len(self._pending) > self._maxPendingRequests:
			discarded_id, _discarded = self._pending.popitem(last=False)
			discarded.append(discarded_id)
		payload = {
			**origin.payload(),
			"requestId": request_id,
			"explorationId": active.exploration_id,
			"actionIndex": active.action_index,
			"action": action.value,
			"count": count,
		}
		return ExplorationRequestPlan(
			None,
			control="exploreTextRequest",
			request_id=request_id,
			exploration_id=active.exploration_id,
			action_index=active.action_index,
			discarded_request_ids=tuple(discarded),
			payload=MappingProxyType(payload),
		)

	def consume_result(
		self,
		context: ExplorationContext,
		event: Mapping[str, Any],
	) -> ExplorationResultPlan:
		if not isinstance(event, Mapping):
			return ExplorationResultPlan(ExplorationRejection.INVALID_RESULT)
		payload = event.get("payload")
		if event.get("type") != "exploreTextResult" or not isinstance(payload, Mapping):
			return ExplorationResultPlan(ExplorationRejection.INVALID_RESULT)
		request_id = payload.get("requestId")
		exploration_id = payload.get("explorationId")
		action_index = payload.get("actionIndex")
		if not all(
			self._valid_positive_integer(value)
			for value in (
				request_id,
				exploration_id,
				action_index,
			)
		):
			return ExplorationResultPlan(ExplorationRejection.INVALID_RESULT)
		pending = self._pending.pop(request_id, None)
		if pending is None or pending.context != context:
			return ExplorationResultPlan(
				ExplorationRejection.STALE_OR_UNBOUND,
				request_id=request_id,
				exploration_id=exploration_id,
				action_index=action_index,
			)
		if (
			self._active is None
			or self._active.context != context
			or self._origin(payload) != self._active.origin
			or pending.exploration_id != exploration_id
			or pending.action_index != action_index
			or self._active.exploration_id != exploration_id
		):
			self.invalidate()
			return ExplorationResultPlan(
				ExplorationRejection.STALE_OR_UNBOUND,
				request_id=request_id,
				exploration_id=exploration_id,
				action_index=action_index,
			)
		if payload.get("action") != pending.action.value or payload.get("unit") != pending.unit.value:
			self.invalidate()
			return ExplorationResultPlan(
				ExplorationRejection.INVALID_RESULT,
				request_id=request_id,
				exploration_id=exploration_id,
				action_index=action_index,
			)
		result_code = payload.get("resultCode")
		text = payload.get("text")
		position_values = (
			payload.get("line"),
			payload.get("byteColumn"),
			payload.get("characterColumn"),
			payload.get("virtualColumn"),
		)
		position_at_origin = payload.get("atOrigin")
		if (
			payload.get("ok") is not True
			or result_code not in {"moved", "boundary"}
			or not isinstance(position_at_origin, bool)
			or not self._valid_result_text(text)
			or not self._valid_positive_integer(position_values[0])
			or not all(self._valid_nonnegative_integer(value) for value in position_values[1:])
		):
			self.invalidate()
			return ExplorationResultPlan(
				ExplorationRejection.INVALID_RESULT,
				request_id=request_id,
				exploration_id=exploration_id,
				action_index=action_index,
			)
		active = self._active
		known_position_at_origin = None
		if pending.unit == ExplorationUnit.CHARACTER:
			known_position_at_origin = (
				position_values[0] == active.origin.cursor_line
				and position_values[1] == active.origin.cursor_byte_column
			)
		elif pending.unit == ExplorationUnit.LINE:
			known_position_at_origin = position_values[0] == active.origin.cursor_line
		if known_position_at_origin is not None and position_at_origin != known_position_at_origin:
			self.invalidate()
			return ExplorationResultPlan(
				ExplorationRejection.INVALID_RESULT,
				request_id=request_id,
				exploration_id=exploration_id,
				action_index=action_index,
			)
		returned_to_origin = (
			not active.virtual_position_at_origin
			and position_at_origin
		)
		active.virtual_position_at_origin = position_at_origin
		return ExplorationResultPlan(
			None,
			request_id=request_id,
			exploration_id=exploration_id,
			action_index=action_index,
			unit=pending.unit,
			result_code=result_code,
			speech_action=self._result_speech(
				pending,
				text,
				result_code,
				returned_to_origin=returned_to_origin,
			),
		)

	def release(
		self,
		context: ExplorationContext,
		state: Mapping[str, Any],
	) -> ExplorationReleasePlan:
		active = self._active
		if active is None:
			return ExplorationReleasePlan(ExplorationRejection.NO_ACTIVE_EXPLORATION)
		if active.context != context or active.origin != self._origin(state):
			self.invalidate()
			return ExplorationReleasePlan(ExplorationRejection.CONTEXT_CHANGED)
		unit = active.last_unit
		if unit is None:
			self.invalidate()
			return ExplorationReleasePlan(ExplorationRejection.NO_ACTIVE_EXPLORATION)
		speech_action = self._release_speech(unit, state)
		request_id = self._nextRequestId()
		if not self._valid_positive_integer(request_id):
			self.invalidate()
			raise ValueError("next_request_id returned an invalid value")
		cleanup = ExplorationRequestPlan(
			None,
			control="endExplorationRequest",
			request_id=request_id,
			exploration_id=active.exploration_id,
			payload=MappingProxyType(
				{
					"requestId": request_id,
					"explorationId": active.exploration_id,
				}
			),
		)
		self.invalidate()
		return ExplorationReleasePlan(None, speech_action=speech_action, cleanup=cleanup)

	def invalidate(self) -> None:
		self._active = None
		self._pending.clear()

	def fail_request(self, request_id: int) -> bool:
		"""Invalidate only when a failed dispatch belongs to the active exploration."""
		pending = self._pending.get(request_id)
		if pending is None or self._active is None or pending.exploration_id != self._active.exploration_id:
			return False
		self.invalidate()
		return True

	@classmethod
	def _origin(cls, state: Mapping[str, Any]) -> _Origin | None:
		if not isinstance(state, Mapping):
			return None
		cursor = state.get("cursor")
		if not isinstance(cursor, Mapping):
			return None
		values = (
			state.get("bufferId"),
			state.get("windowId"),
			state.get("tabpageId"),
			state.get("changedtick"),
			cursor.get("line"),
			cursor.get("byteColumn"),
			cursor.get("virtualColumn"),
		)
		mode_raw = state.get("modeRaw")
		if (
			not all(cls._valid_nonnegative_integer(value) for value in values)
			or values[4] == 0
			or not isinstance(mode_raw, str)
			or not 0 < len(mode_raw) <= 16
		):
			return None
		return _Origin(
			buffer_id=values[0],
			window_id=values[1],
			tabpage_id=values[2],
			changedtick=values[3],
			mode_raw=mode_raw,
			cursor_line=values[4],
			cursor_byte_column=values[5],
			cursor_virtual_column=values[6],
		)

	@staticmethod
	def _valid_nonnegative_integer(value: Any) -> bool:
		return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2_147_483_647

	@classmethod
	def _valid_positive_integer(cls, value: Any) -> bool:
		return cls._valid_nonnegative_integer(value) and value > 0

	@staticmethod
	def _bounded_increment(value: int) -> int:
		return 1 if value >= 2_147_483_647 else value + 1

	@staticmethod
	def _valid_result_text(value: Any) -> bool:
		if not isinstance(value, str) or "\0" in value:
			return False
		try:
			return len(value.encode("utf-8")) <= MAX_EXPLORATION_TEXT_BYTES
		except UnicodeEncodeError:
			return False

	def _result_speech(
		self,
		pending: _PendingResult,
		text: str,
		result_code: str,
		*,
		returned_to_origin: bool = False,
	) -> SpeechAction:
		sound = "explorationOrigin" if returned_to_origin else None
		if sound is None and result_code == "boundary":
			sound = {
				ExplorationAction.CHARACTER_LEFT: "lineStart",
				ExplorationAction.CHARACTER_RIGHT: "lineEnd",
				ExplorationAction.LINE_UP: "fileStart",
				ExplorationAction.LINE_DOWN: "fileEnd",
				ExplorationAction.WORD_PREVIOUS: "fileStart",
				ExplorationAction.WORD_NEXT: "fileEnd",
			}[pending.action]
		spoken = text
		if pending.unit == ExplorationUnit.LINE and not spoken:
			spoken = self._translate("blank")
		return SpeechAction(
			spoken,
			Priority.NAVIGATION,
			interrupt=True,
			sound=sound,
			spelling=pending.unit == ExplorationUnit.CHARACTER and bool(spoken),
			force_symbols=pending.unit == ExplorationUnit.WORD,
		)

	def _release_speech(
		self,
		unit: ExplorationUnit,
		state: Mapping[str, Any],
	) -> SpeechAction | None:
		if unit == ExplorationUnit.LINE:
			line = state.get("lineText")
			if not isinstance(line, str):
				return None
			return SpeechAction(
				line if line else self._translate("blank"),
				Priority.NAVIGATION,
				interrupt=True,
			)
		character = state.get("character")
		character = character if isinstance(character, str) else ""
		if unit == ExplorationUnit.CHARACTER:
			return SpeechAction(
				character,
				Priority.NAVIGATION,
				interrupt=True,
				sound=None if character else "lineEnd",
				spelling=bool(character),
			)
		word = state.get("word")
		text = word if isinstance(word, str) and word else character
		return SpeechAction(
			text,
			Priority.NAVIGATION,
			interrupt=True,
			force_symbols=True,
		)
