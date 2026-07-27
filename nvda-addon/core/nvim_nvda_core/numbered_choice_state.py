"""NVDA-independent state for contextual numbered-choice prompts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .gate import TerminalIdentity


MAX_NUMBERED_CHOICE_ITEMS = 128
MAX_NUMBERED_CHOICE_ITEM_BYTES = 4 * 1024


class NumberedChoiceDirection(Enum):
	PREVIOUS = "previous"
	NEXT = "next"


class NumberedChoiceRejection(Enum):
	CAPABILITY_MISSING = "capabilityMissing"
	INVALID_EVENT = "invalidEvent"
	NO_ACTIVE_CHOICE = "noActiveChoice"
	NO_SELECTED_ITEM = "noSelectedItem"
	CONTEXT_CHANGED = "contextChanged"


@dataclass(frozen=True)
class NumberedChoiceContext:
	instance_id: str
	identity: TerminalIdentity
	adapter_token: object
	service_generation: object


@dataclass(frozen=True)
class NumberedChoicePresentation:
	rejection: NumberedChoiceRejection | None
	text: str | None = None

	@property
	def ready(self) -> bool:
		return self.rejection is None and self.text is not None


@dataclass(frozen=True)
class NumberedChoiceAcceptPlan:
	rejection: NumberedChoiceRejection | None
	payload: Mapping[str, Any] | None = None

	@property
	def ready(self) -> bool:
		return self.rejection is None and self.payload is not None


@dataclass
class _ActiveChoice:
	context: NumberedChoiceContext
	kind: str
	choice_id: int
	items: tuple[str, ...]
	buffer_id: int
	window_id: int
	tabpage_id: int
	changedtick: int
	selected_index: int | None = None


class NumberedChoiceController:
	"""Keep one local selection over one validated native Neovim prompt."""

	def __init__(self) -> None:
		self._active: _ActiveChoice | None = None

	@property
	def active_context(self) -> NumberedChoiceContext | None:
		return self._active.context if self._active is not None else None

	def open(
		self,
		context: NumberedChoiceContext,
		event: Mapping[str, Any],
		*,
		capabilities: frozenset[str] | set[str],
	) -> bool:
		if "numberedChoices" not in capabilities:
			self.invalidate()
			return False
		payload = event.get("payload")
		if not isinstance(payload, Mapping) or not self._valid_open_payload(payload):
			self.invalidate()
			return False
		self._active = _ActiveChoice(
			context=context,
			kind=payload["choiceKind"],
			choice_id=payload["choiceId"],
			items=tuple(payload["items"]),
			buffer_id=payload["bufferId"],
			window_id=payload["windowId"],
			tabpage_id=payload["tabpageId"],
			changedtick=payload["changedtick"],
		)
		return True

	def close(self, context: NumberedChoiceContext, event: Mapping[str, Any]) -> bool:
		active = self._active
		payload = event.get("payload")
		if (
			active is None
			or active.context != context
			or not isinstance(payload, Mapping)
			or payload.get("choiceKind") != active.kind
			or payload.get("choiceId") != active.choice_id
			or any(payload.get(field) != expected for field, expected in (
				("bufferId", active.buffer_id),
				("windowId", active.window_id),
				("tabpageId", active.tabpage_id),
			))
		):
			return False
		self.invalidate()
		return True

	def available(self, context: NumberedChoiceContext) -> bool:
		return self._active is not None and self._active.context == context

	def navigate(
		self,
		context: NumberedChoiceContext,
		direction: NumberedChoiceDirection,
	) -> NumberedChoicePresentation:
		active = self._active
		if active is None:
			return NumberedChoicePresentation(NumberedChoiceRejection.NO_ACTIVE_CHOICE)
		if active.context != context:
			return NumberedChoicePresentation(NumberedChoiceRejection.CONTEXT_CHANGED)
		if direction is NumberedChoiceDirection.NEXT:
			active.selected_index = (
				0 if active.selected_index is None else (active.selected_index + 1) % len(active.items)
			)
		elif direction is NumberedChoiceDirection.PREVIOUS:
			active.selected_index = (
				len(active.items) - 1
				if active.selected_index is None
				else (active.selected_index - 1) % len(active.items)
			)
		else:
			raise TypeError("a numbered-choice direction is required")
		return NumberedChoicePresentation(None, active.items[active.selected_index])

	def accept_plan(
		self,
		context: NumberedChoiceContext,
		request_id: int,
	) -> NumberedChoiceAcceptPlan:
		active = self._active
		if active is None:
			return NumberedChoiceAcceptPlan(NumberedChoiceRejection.NO_ACTIVE_CHOICE)
		if active.context != context:
			return NumberedChoiceAcceptPlan(NumberedChoiceRejection.CONTEXT_CHANGED)
		if active.selected_index is None:
			return NumberedChoiceAcceptPlan(NumberedChoiceRejection.NO_SELECTED_ITEM)
		return NumberedChoiceAcceptPlan(None, {
			"requestId": request_id,
			"choiceKind": active.kind,
			"choiceId": active.choice_id,
			"itemIndex": active.selected_index,
			"bufferId": active.buffer_id,
			"windowId": active.window_id,
			"tabpageId": active.tabpage_id,
			"changedtick": active.changedtick,
		})

	def discard_selection(self, context: NumberedChoiceContext | None = None) -> bool:
		if self._active is None or (
			context is not None and self._active.context != context
		):
			return False
		changed = self._active.selected_index is not None
		self._active.selected_index = None
		return changed

	def display_text(self) -> str | None:
		active = self._active
		if active is None or active.selected_index is None:
			return None
		return active.items[active.selected_index]

	def invalidate(self) -> None:
		self._active = None

	@staticmethod
	def _valid_open_payload(payload: Mapping[str, Any]) -> bool:
		items = payload.get("items")
		return (
			payload.get("choiceKind") == "spellSuggestions"
			and NumberedChoiceController._positive_integer(payload.get("choiceId"))
			and isinstance(items, list)
			and 1 <= len(items) <= MAX_NUMBERED_CHOICE_ITEMS
			and all(NumberedChoiceController._valid_item(item) for item in items)
			and all(NumberedChoiceController._nonnegative_integer(payload.get(field)) for field in (
				"bufferId", "windowId", "tabpageId", "changedtick",
			))
		)

	@staticmethod
	def _valid_item(value: Any) -> bool:
		if not isinstance(value, str) or not value or "\0" in value:
			return False
		try:
			return len(value.encode("utf-8")) <= MAX_NUMBERED_CHOICE_ITEM_BYTES
		except UnicodeEncodeError:
			return False

	@staticmethod
	def _positive_integer(value: Any) -> bool:
		return NumberedChoiceController._nonnegative_integer(value) and value > 0

	@staticmethod
	def _nonnegative_integer(value: Any) -> bool:
		return (
			isinstance(value, int)
			and not isinstance(value, bool)
			and 0 <= value <= 2_147_483_647
		)
