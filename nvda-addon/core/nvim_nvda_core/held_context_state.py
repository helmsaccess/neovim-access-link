"""Bounded state for read-only callable and diagnostic inspection."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class HeldContextKind(Enum):
    CALLABLE = "callable"
    DIAGNOSTIC = "diagnostic"


class HeldContextDirection(Enum):
    PREVIOUS_ITEM = "previousItem"
    NEXT_ITEM = "nextItem"
    PREVIOUS_PARAMETER = "previousParameter"
    NEXT_PARAMETER = "nextParameter"


@dataclass(frozen=True)
class HeldContextLocation:
    instance_id: str
    identity: object
    adapter_token: object
    service_generation: object
    buffer_id: int
    window_id: int
    tabpage_id: int
    changedtick: int
    line: int
    byte_column: int

    @classmethod
    def from_state(
        cls,
        instance_id: str,
        identity: object,
        adapter_token: object,
        service_generation: object,
        state: Mapping[str, Any],
    ) -> HeldContextLocation | None:
        cursor = state.get("cursor")
        values = (
            state.get("bufferId"),
            state.get("windowId"),
            state.get("tabpageId"),
            state.get("changedtick"),
            cursor.get("line") if isinstance(cursor, Mapping) else None,
            cursor.get("byteColumn") if isinstance(cursor, Mapping) else None,
        )
        if (
            not instance_id
            or identity is None
            or adapter_token is None
            or service_generation is None
            or not all(
                isinstance(value, int) and not isinstance(value, bool) and value >= 0
                for value in values
            )
            or any(value < 1 for value in values[:3])
            or values[4] < 1
        ):
            return None
        return cls(
            instance_id,
            identity,
            adapter_token,
            service_generation,
            *values,
        )

    def request_payload(self, request_id: int) -> dict[str, int]:
        return {
            "requestId": request_id,
            "bufferId": self.buffer_id,
            "windowId": self.window_id,
            "tabpageId": self.tabpage_id,
            "changedtick": self.changedtick,
            "line": self.line,
            "byteColumn": self.byte_column,
        }

    def matches_state(self, state: Mapping[str, Any]) -> bool:
        cursor = state.get("cursor")
        return (
            isinstance(cursor, Mapping)
            and state.get("bufferId") == self.buffer_id
            and state.get("windowId") == self.window_id
            and state.get("tabpageId") == self.tabpage_id
            and state.get("changedtick") == self.changedtick
            and cursor.get("line") == self.line
            and cursor.get("byteColumn") == self.byte_column
        )


@dataclass(frozen=True)
class HeldContextRequest:
    kind: HeldContextKind
    request_id: int
    payload: Mapping[str, int]

    @property
    def control(self) -> str:
        return (
            "callableContextRequest"
            if self.kind is HeldContextKind.CALLABLE
            else "diagnosticContextRequest"
        )


@dataclass(frozen=True)
class HeldContextPresentation:
    kind: HeldContextKind
    item: Mapping[str, Any]
    item_index: int
    item_count: int
    parameter: str = ""
    parameter_index: int = 0
    parameter_count: int = 0


class HeldContextController:
    """Correlate an inspection request and retain only bounded display state."""

    def __init__(self, next_request_id: Callable[[], int]) -> None:
        self._next_request_id = next_request_id
        self._kind: HeldContextKind | None = None
        self._location: HeldContextLocation | None = None
        self._request_id: int | None = None
        self._items: tuple[Mapping[str, Any], ...] = ()
        self._item_index = 0
        self._parameter_index = 0

    @property
    def location(self) -> HeldContextLocation | None:
        return self._location

    def begin(
        self,
        kind: HeldContextKind,
        location: HeldContextLocation,
    ) -> HeldContextRequest:
        request_id = self._next_request_id()
        self._kind = kind
        self._location = location
        self._request_id = request_id
        self._items = ()
        self._item_index = 0
        self._parameter_index = 0
        return HeldContextRequest(kind, request_id, location.request_payload(request_id))

    def consume(
        self,
        kind: HeldContextKind,
        event: Mapping[str, Any],
    ) -> HeldContextPresentation | None:
        if not self.accepts(kind, event):
            return None
        payload = event["payload"]
        if payload.get("ok") is not True:
            self._items = ()
            return None
        items = payload.get("items")
        if not isinstance(items, list) or not items or len(items) > 100:
            return None
        self._items = tuple(item for item in items if isinstance(item, Mapping))
        if not self._items:
            return None
        selected = payload.get("activeItem")
        parameter = payload.get("activeParameter")
        self._item_index = (
            selected
            if isinstance(selected, int) and not isinstance(selected, bool)
            and 0 <= selected < len(self._items)
            else 0
        )
        self._parameter_index = (
            parameter
            if isinstance(parameter, int) and not isinstance(parameter, bool) and parameter >= 0
            else 0
        )
        return self.current()

    def accepts(
        self,
        kind: HeldContextKind,
        event: Mapping[str, Any],
    ) -> bool:
        payload = event.get("payload")
        return (
            self._kind is kind
            and self._location is not None
            and self._request_id is not None
            and isinstance(payload, Mapping)
            and payload.get("requestId") == self._request_id
            and self._location.matches_state(payload)
        )

    def navigate(self, direction: HeldContextDirection) -> HeldContextPresentation | None:
        if not self._items or self._kind is None:
            return None
        if direction is HeldContextDirection.PREVIOUS_ITEM:
            self._item_index = (self._item_index - 1) % len(self._items)
            self._parameter_index = 0
        elif direction is HeldContextDirection.NEXT_ITEM:
            self._item_index = (self._item_index + 1) % len(self._items)
            self._parameter_index = 0
        else:
            parameters = self._parameters()
            if not parameters:
                return self.current()
            delta = -1 if direction is HeldContextDirection.PREVIOUS_PARAMETER else 1
            self._parameter_index = (self._parameter_index + delta) % len(parameters)
        return self.current()

    def current(self) -> HeldContextPresentation | None:
        if not self._items or self._kind is None:
            return None
        item = self._items[self._item_index]
        parameters = self._parameters()
        parameter_index = min(self._parameter_index, max(0, len(parameters) - 1))
        self._parameter_index = parameter_index
        return HeldContextPresentation(
            self._kind,
            item,
            self._item_index,
            len(self._items),
            parameters[parameter_index] if parameters else "",
            parameter_index,
            len(parameters),
        )

    def cancel(self, adapter_token: object | None = None) -> bool:
        if self._location is None or (
            adapter_token is not None and self._location.adapter_token is not adapter_token
        ):
            return False
        self._kind = None
        self._location = None
        self._request_id = None
        self._items = ()
        self._item_index = 0
        self._parameter_index = 0
        return True

    def _parameters(self) -> tuple[str, ...]:
        if not self._items:
            return ()
        values = self._items[self._item_index].get("parameters")
        if not isinstance(values, list):
            return ()
        return tuple(value for value in values if isinstance(value, str))
