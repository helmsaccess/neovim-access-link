"""Strict validation for bounded, read-only text exploration controls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .clipboard import valid_request_id


MAX_EXPLORATION_TEXT_BYTES = 16 * 1024
EXPLORATION_ACTIONS = frozenset({
    "characterLeft", "characterRight", "lineUp", "lineDown", "wordPrevious", "wordNext",
})
EXPLORATION_UNITS = frozenset({"character", "line", "word"})
_REQUEST_FIELDS = frozenset({
    "requestId", "explorationId", "actionIndex", "action", "count", "bufferId", "windowId",
    "tabpageId", "changedtick", "modeRaw", "cursorLine", "cursorByteColumn", "cursorVirtualColumn",
})
_END_FIELDS = frozenset({"requestId", "explorationId"})
_NONNEGATIVE_REQUEST_FIELDS = (
    "bufferId", "windowId", "tabpageId", "changedtick", "cursorByteColumn", "cursorVirtualColumn",
)
_RESULT_ONLY_FIELDS = frozenset({
    "requestId", "explorationId", "actionIndex", "action", "unit", "ok", "resultCode", "text",
    "line", "byteColumn", "characterColumn", "virtualColumn",
})
_SUCCESS_CODES = frozenset({"moved", "boundary"})
_FAILURE_CODES = frozenset({
    "invalidOrStaleRequest", "outOfOrder", "scanLimit", "textTooLarge",
})


def _positive_integer(value: Any) -> bool:
    return valid_request_id(value) and value > 0


def _nonnegative_integer(value: Any) -> bool:
    return valid_request_id(value)


def _valid_text(value: Any) -> bool:
    if not isinstance(value, str) or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_EXPLORATION_TEXT_BYTES
    except UnicodeEncodeError:
        return False


def valid_explore_text_request(payload: Any) -> bool:
    """Accept one exact virtual-cursor step with a canonical real origin."""
    return (
        isinstance(payload, Mapping)
        and frozenset(payload) == _REQUEST_FIELDS
        and _positive_integer(payload.get("requestId"))
        and _positive_integer(payload.get("explorationId"))
        and _positive_integer(payload.get("actionIndex"))
        and payload.get("action") in EXPLORATION_ACTIONS
        and _positive_integer(payload.get("count"))
        and payload.get("count") <= 64
        and all(_nonnegative_integer(payload.get(field)) for field in _NONNEGATIVE_REQUEST_FIELDS)
        and _positive_integer(payload.get("cursorLine"))
        and isinstance(payload.get("modeRaw"), str)
        and 0 < len(payload.get("modeRaw")) <= 16
    )


def valid_end_exploration_request(payload: Any) -> bool:
    """Accept only the correlation identifiers needed to discard virtual state."""
    return (
        isinstance(payload, Mapping)
        and frozenset(payload) == _END_FIELDS
        and _positive_integer(payload.get("requestId"))
        and _positive_integer(payload.get("explorationId"))
    )


def valid_explore_text_result(payload: Any) -> bool:
    """Validate result correlation and bounded text while allowing a state snapshot."""
    if not isinstance(payload, Mapping):
        return False
    if not all(_positive_integer(payload.get(field)) for field in (
        "requestId", "explorationId", "actionIndex",
    )):
        return False
    if payload.get("action") not in EXPLORATION_ACTIONS or not isinstance(payload.get("ok"), bool):
        return False
    result_code = payload.get("resultCode")
    if payload.get("ok") is False:
        return result_code in _FAILURE_CODES
    return (
        result_code in _SUCCESS_CODES
        and payload.get("unit") in EXPLORATION_UNITS
        and _valid_text(payload.get("text"))
        and _positive_integer(payload.get("line"))
        and all(_nonnegative_integer(payload.get(field)) for field in (
            "byteColumn", "characterColumn", "virtualColumn",
        ))
    )


def exploration_result_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical editor state without ephemeral exploration data."""
    return {key: value for key, value in payload.items() if key not in _RESULT_ONLY_FIELDS}
