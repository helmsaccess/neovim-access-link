"""Independent state and plans for a persistent virtual Braille cursor."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Any

try:
    from .text import InvalidByteColumn, cursor_text
except ImportError:
    from nvim_nvda_protocol import InvalidByteColumn, cursor_text


MAX_BRAILLE_EXPLORATION_TEXT_BYTES = 16 * 1024

_BUFFER_PRESENTATION_FIELDS = (
    "bufferName",
    "buftype",
    "filetype",
    "lineCount",
    "modifiable",
    "modified",
    "pluginCapabilities",
    "readonly",
    "shiftwidth",
    "tabstop",
    "_transport",
)


class BrailleExplorationRejection(Enum):
    CAPABILITY_MISSING = "capabilityMissing"
    INCOMPLETE_STATE = "incompleteState"
    MODE_UNAVAILABLE = "modeUnavailable"
    DISABLED = "disabled"
    BOUNDARY = "boundary"
    INVALID_RESULT = "invalidResult"
    STALE_OR_UNBOUND = "staleOrUnbound"


@dataclass(frozen=True)
class BrailleExplorationTogglePlan:
    rejection: BrailleExplorationRejection | None
    enabled: bool
    cleanup_control: str | None = None
    cleanup_payload: Mapping[str, Any] | None = None

    @property
    def changed(self) -> bool:
        return self.rejection is None


@dataclass(frozen=True)
class BrailleExplorationRequestPlan:
    rejection: BrailleExplorationRejection | None
    control: str | None = None
    request_id: int | None = None
    discarded_request_ids: tuple[int, ...] = ()
    payload: Mapping[str, Any] | None = None

    @property
    def ready(self) -> bool:
        return self.rejection is None


@dataclass(frozen=True)
class BrailleExplorationResultPlan:
    rejection: BrailleExplorationRejection | None
    request_id: int | None = None
    result_code: str = "invalidResult"
    display_changed: bool = False

    @property
    def accepted(self) -> bool:
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


@dataclass(frozen=True)
class _Pending:
    exploration_id: int
    action_index: int
    action: str
    source_line: int
    target_line: int
    target_column: str
    origin: _Origin


class BrailleExplorationController:
    """Own one read-only Braille cursor without sharing speech exploration state."""

    def __init__(
        self,
        next_request_id: Callable[[], int],
        *,
        max_pending_requests: int = 32,
    ) -> None:
        if not callable(next_request_id):
            raise TypeError("next_request_id must be callable")
        if max_pending_requests < 1:
            raise ValueError("max_pending_requests must be positive")
        self._nextRequestId = next_request_id
        self._maxPendingRequests = max_pending_requests
        self._enabled = False
        self._nextExplorationId = 0
        self._explorationId = 0
        self._actionIndex = 0
        self._acceptedActionIndex = 0
        self._origin: _Origin | None = None
        self._displayState: dict[str, Any] | None = None
        self._plannedLine: int | None = None
        self._desiredVirtualColumn = 0
        self._pending: OrderedDict[int, _Pending] = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def toggle(
        self,
        state: Mapping[str, Any],
        *,
        capabilities: frozenset[str] | set[str],
    ) -> BrailleExplorationTogglePlan:
        if self._enabled:
            cleanup = self._cleanup()
            self._enabled = False
            self._clear_active()
            return BrailleExplorationTogglePlan(
                None,
                False,
                cleanup_control="endBrailleExplorationRequest" if cleanup is not None else None,
                cleanup_payload=cleanup,
            )
        if "brailleExploration" not in capabilities:
            return BrailleExplorationTogglePlan(
                BrailleExplorationRejection.CAPABILITY_MISSING,
                False,
            )
        origin = self._origin_from_state(state)
        if origin is None:
            return BrailleExplorationTogglePlan(
                BrailleExplorationRejection.INCOMPLETE_STATE,
                False,
            )
        if origin.mode_raw.startswith(("c", "t")):
            return BrailleExplorationTogglePlan(
                BrailleExplorationRejection.MODE_UNAVAILABLE,
                False,
            )
        self._enabled = True
        self._start(state, origin)
        return BrailleExplorationTogglePlan(None, True)

    def disable(self) -> BrailleExplorationTogglePlan:
        """Disable the mode during teardown and return optional remote cleanup."""
        if not self._enabled:
            self._clear_active()
            return BrailleExplorationTogglePlan(
                BrailleExplorationRejection.DISABLED,
                False,
            )
        cleanup = self._cleanup()
        self._enabled = False
        self._clear_active()
        return BrailleExplorationTogglePlan(
            None,
            False,
            cleanup_control="endBrailleExplorationRequest" if cleanup is not None else None,
            cleanup_payload=cleanup,
        )

    def display_state(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return the virtual line while enabled, otherwise the canonical state."""
        if not self._enabled:
            return state
        if not self._reconcile(state) or self._displayState is None:
            return state
        return MappingProxyType(dict(self._displayState))

    def routing_state(self, state: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Return a current, routable virtual line without moving its viewport."""
        if not self._enabled:
            return state
        if not self._reconcile(state) or self._displayState is None:
            return None
        origin = self._origin_from_state(state)
        display_cursor = self._displayState.get("cursor")
        line_count = state.get("lineCount")
        if (
            origin is None
            or self._displayState.get("changedtick") != origin.changedtick
            or not isinstance(display_cursor, Mapping)
            or not self._positive_integer(display_cursor.get("line"))
            or not self._positive_integer(line_count)
            or display_cursor["line"] > line_count
        ):
            return None
        display = dict(self._displayState)
        for name in (
            "bufferId",
            "windowId",
            "tabpageId",
            "changedtick",
            "mode",
            "modeRaw",
            "modeBlocking",
            "_transport",
        ):
            if name in state:
                display[name] = state[name]
            else:
                display.pop(name, None)
        return MappingProxyType(display)

    def plan_step(
        self,
        state: Mapping[str, Any],
        direction: str,
        *,
        capabilities: frozenset[str] | set[str],
        target_column: str = "preferred",
    ) -> BrailleExplorationRequestPlan:
        if not self._enabled:
            return BrailleExplorationRequestPlan(BrailleExplorationRejection.DISABLED)
        if "brailleExploration" not in capabilities:
            self._clear_active()
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.CAPABILITY_MISSING,
            )
        if direction not in {"previous", "next"}:
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.INCOMPLETE_STATE,
            )
        if target_column not in {"preferred", "start", "end"}:
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.INCOMPLETE_STATE,
            )
        current_origin = self._origin_from_state(state)
        if current_origin is None:
            self._clear_active()
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.INCOMPLETE_STATE,
            )
        if current_origin.mode_raw.startswith(("c", "t")):
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.MODE_UNAVAILABLE,
            )
        if not self._reconcile(state) or self._origin is None or self._plannedLine is None:
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.MODE_UNAVAILABLE,
            )
        line_count = state.get("lineCount")
        if not self._positive_integer(line_count):
            self._clear_active()
            return BrailleExplorationRequestPlan(
                BrailleExplorationRejection.INCOMPLETE_STATE,
            )
        source_line = self._plannedLine
        target_line = source_line + (-1 if direction == "previous" else 1)
        if target_line < 1 or target_line > line_count:
            return BrailleExplorationRequestPlan(BrailleExplorationRejection.BOUNDARY)
        self._actionIndex = self._bounded_increment(self._actionIndex)
        request_id = self._nextRequestId()
        if not self._positive_integer(request_id):
            self._clear_active()
            raise ValueError("next_request_id returned an invalid value")
        action = "lineUp" if direction == "previous" else "lineDown"
        pending = _Pending(
            self._explorationId,
            self._actionIndex,
            action,
            source_line,
            target_line,
            target_column,
            self._origin,
        )
        self._pending[request_id] = pending
        self._plannedLine = target_line
        discarded = []
        while len(self._pending) > self._maxPendingRequests:
            discarded_id, _discarded = self._pending.popitem(last=False)
            discarded.append(discarded_id)
        payload = {
            **self._origin.payload(),
            "requestId": request_id,
            "explorationId": self._explorationId,
            "actionIndex": self._actionIndex,
            "action": action,
            "count": 1,
            "desiredVirtualColumn": self._desiredVirtualColumn,
            "targetColumn": target_column,
        }
        return BrailleExplorationRequestPlan(
            None,
            control="brailleExploreLineRequest",
            request_id=request_id,
            discarded_request_ids=tuple(discarded),
            payload=MappingProxyType(payload),
        )

    def consume_result(
        self,
        state: Mapping[str, Any],
        event: Mapping[str, Any],
    ) -> BrailleExplorationResultPlan:
        payload = event.get("payload") if isinstance(event, Mapping) else None
        if event.get("type") != "brailleExploreLineResult" or not isinstance(payload, Mapping):
            return BrailleExplorationResultPlan(BrailleExplorationRejection.INVALID_RESULT)
        request_id = payload.get("requestId")
        pending = self._pending.pop(request_id, None)
        if pending is None or not self._enabled:
            return BrailleExplorationResultPlan(
                BrailleExplorationRejection.STALE_OR_UNBOUND,
                request_id=request_id if self._positive_integer(request_id) else None,
            )
        current_origin = self._origin_from_state(state)
        payload_origin = self._origin_from_state(payload)
        if (
            self._origin is None
            or current_origin is None
            or not self._same_context(current_origin, self._origin)
            or payload_origin != current_origin
            or not self._same_exploration_origin(pending.origin, self._origin)
            or payload.get("explorationId") != pending.exploration_id
            or payload.get("actionIndex") != pending.action_index
            or payload.get("action") != pending.action
        ):
            self._clear_active()
            return BrailleExplorationResultPlan(
                BrailleExplorationRejection.STALE_OR_UNBOUND,
                request_id=request_id,
            )
        result_code = payload.get("resultCode")
        result_line = payload.get("line")
        expected_line = pending.target_line if result_code == "moved" else pending.source_line
        if not self._valid_result(payload, expected_line):
            self._clear_active()
            return BrailleExplorationResultPlan(
                BrailleExplorationRejection.INVALID_RESULT,
                request_id=request_id,
            )
        if pending.action_index <= self._acceptedActionIndex:
            return BrailleExplorationResultPlan(
                BrailleExplorationRejection.STALE_OR_UNBOUND,
                request_id=request_id,
            )
        self._acceptedActionIndex = pending.action_index
        self._displayState = self._display_state_from_result(state, payload)
        if result_code == "moved" and pending.target_column != "preferred":
            self._desiredVirtualColumn = payload["virtualColumn"]
        if result_code == "boundary":
            self._plannedLine = result_line
            self._pending.clear()
        return BrailleExplorationResultPlan(
            None,
            request_id=request_id,
            result_code=result_code,
            display_changed=True,
        )

    def fail_request(self, request_id: int) -> bool:
        """Re-anchor after a dispatch failure, without changing the selected mode."""
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return False
        self._clear_active()
        return True

    def _reconcile(self, state: Mapping[str, Any]) -> bool:
        origin = self._origin_from_state(state)
        if origin is None:
            self._clear_active()
            return False
        if self._origin is None or not self._same_context(self._origin, origin):
            self._start(state, origin)
        else:
            if self._origin.changedtick != origin.changedtick:
                self._origin = replace(self._origin, changedtick=origin.changedtick)
            self._refresh_buffer_presentation(state)
            self._refresh_displayed_line(state, origin)
        return True

    def _refresh_buffer_presentation(self, state: Mapping[str, Any]) -> None:
        """Keep buffer-wide rendering facts current without adopting the real cursor."""
        if self._displayState is None:
            return
        for name in _BUFFER_PRESENTATION_FIELDS:
            if name in state:
                self._displayState[name] = state[name]
            else:
                self._displayState.pop(name, None)

    def _refresh_displayed_line(
        self,
        state: Mapping[str, Any],
        real_origin: _Origin,
    ) -> None:
        """Refresh the complete snapshot when the real cursor is on the virtual line."""
        if self._displayState is None:
            return
        display_cursor = self._displayState.get("cursor")
        if (
            not isinstance(display_cursor, Mapping)
            or display_cursor.get("line") != real_origin.cursor_line
            or not self._valid_text(state.get("lineText"))
        ):
            return
        refreshed = dict(state)
        refreshed["cursor"] = dict(display_cursor)
        self._displayState = refreshed

    @staticmethod
    def _same_context(first: _Origin, second: _Origin) -> bool:
        """Compare editor identity without coupling exploration to cursor or text changes."""
        return (
            first.buffer_id,
            first.window_id,
            first.tabpage_id,
        ) == (
            second.buffer_id,
            second.window_id,
            second.tabpage_id,
        )

    @classmethod
    def _same_exploration_origin(cls, first: _Origin, second: _Origin) -> bool:
        """Allow only changedtick to advance within one correlated exploration."""
        return cls._same_context(first, second) and (
            first.mode_raw,
            first.cursor_line,
            first.cursor_byte_column,
            first.cursor_virtual_column,
        ) == (
            second.mode_raw,
            second.cursor_line,
            second.cursor_byte_column,
            second.cursor_virtual_column,
        )

    def _start(self, state: Mapping[str, Any], origin: _Origin) -> None:
        self._nextExplorationId = self._bounded_increment(self._nextExplorationId)
        self._explorationId = self._nextExplorationId
        self._actionIndex = 0
        self._acceptedActionIndex = 0
        self._origin = origin
        self._displayState = dict(state)
        self._plannedLine = origin.cursor_line
        cursor = state.get("cursor")
        preferred = cursor.get("preferredVirtualColumn") if isinstance(cursor, Mapping) else None
        self._desiredVirtualColumn = (
            preferred
            if self._nonnegative_integer(preferred)
            else origin.cursor_virtual_column
        )
        self._pending.clear()

    def _cleanup(self) -> Mapping[str, Any] | None:
        if self._origin is None or self._explorationId < 1 or self._actionIndex < 1:
            return None
        request_id = self._nextRequestId()
        if not self._positive_integer(request_id):
            return None
        return MappingProxyType(
            {
                "requestId": request_id,
                "explorationId": self._explorationId,
            }
        )

    def _clear_active(self) -> None:
        self._explorationId = 0
        self._actionIndex = 0
        self._acceptedActionIndex = 0
        self._origin = None
        self._displayState = None
        self._plannedLine = None
        self._desiredVirtualColumn = 0
        self._pending.clear()

    @classmethod
    def _origin_from_state(cls, state: Mapping[str, Any]) -> _Origin | None:
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
            not all(cls._nonnegative_integer(value) for value in values)
            or values[4] < 1
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

    @classmethod
    def _valid_result(cls, payload: Mapping[str, Any], expected_line: int) -> bool:
        text = payload.get("text")
        byte_column = payload.get("byteColumn")
        character_column = payload.get("characterColumn")
        virtual_column = payload.get("virtualColumn")
        if (
            payload.get("ok") is not True
            or payload.get("resultCode") not in {"moved", "boundary"}
            or payload.get("unit") != "line"
            or payload.get("line") != expected_line
            or not cls._valid_text(text)
            or not all(
                cls._nonnegative_integer(value)
                for value in (byte_column, character_column, virtual_column)
            )
        ):
            return False
        try:
            position = cursor_text(text, byte_column)
        except (InvalidByteColumn, TypeError):
            return False
        return position.character_column == character_column

    def _display_state_from_result(
        self,
        state: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        display = dict(state)
        display["lineText"] = payload["text"]
        display["cursor"] = {
            "line": payload["line"],
            "byteColumn": payload["byteColumn"],
            "characterColumn": payload["characterColumn"],
            "virtualColumn": payload["virtualColumn"],
            "preferredVirtualColumn": self._desiredVirtualColumn,
        }
        display["selection"] = None
        display["spellingErrors"] = []
        display.pop("fileManager", None)
        return display

    @staticmethod
    def _valid_text(value: Any) -> bool:
        if not isinstance(value, str) or "\0" in value:
            return False
        try:
            return len(value.encode("utf-8")) <= MAX_BRAILLE_EXPLORATION_TEXT_BYTES
        except UnicodeEncodeError:
            return False

    @staticmethod
    def _nonnegative_integer(value: Any) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 2_147_483_647
        )

    @classmethod
    def _positive_integer(cls, value: Any) -> bool:
        return cls._nonnegative_integer(value) and value > 0

    @staticmethod
    def _bounded_increment(value: int) -> int:
        return 1 if value >= 2_147_483_647 else value + 1
