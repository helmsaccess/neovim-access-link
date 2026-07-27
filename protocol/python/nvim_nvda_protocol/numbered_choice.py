"""Strict validation for bounded numbered-choice events and controls."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .clipboard import valid_request_id


MAX_NUMBERED_CHOICE_ITEMS = 128
MAX_NUMBERED_CHOICE_ITEM_BYTES = 4 * 1024
NUMBERED_CHOICE_KINDS = frozenset({"spellSuggestions"})
_OPEN_ONLY_FIELDS = frozenset({"choiceKind", "choiceId", "items"})
_ACCEPT_FIELDS = frozenset({
    "requestId", "choiceKind", "choiceId", "itemIndex", "bufferId", "windowId",
    "tabpageId", "changedtick",
})


def _positive_integer(value: Any) -> bool:
    return valid_request_id(value) and value > 0


def _nonnegative_integer(value: Any) -> bool:
    return valid_request_id(value)


def _valid_item(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_NUMBERED_CHOICE_ITEM_BYTES
    except UnicodeEncodeError:
        return False


def valid_numbered_choice_opened(payload: Any) -> bool:
    """Validate a bounded choice list while allowing canonical editor state."""
    if not isinstance(payload, Mapping):
        return False
    items = payload.get("items")
    return (
        payload.get("choiceKind") in NUMBERED_CHOICE_KINDS
        and _positive_integer(payload.get("choiceId"))
        and isinstance(items, Sequence)
        and not isinstance(items, (str, bytes, bytearray))
        and 1 <= len(items) <= MAX_NUMBERED_CHOICE_ITEMS
        and all(_valid_item(item) for item in items)
        and all(_nonnegative_integer(payload.get(field)) for field in (
            "bufferId", "windowId", "tabpageId", "changedtick",
        ))
    )


def valid_numbered_choice_closed(payload: Any) -> bool:
    """Validate the identity of a closed numbered-choice prompt."""
    return (
        isinstance(payload, Mapping)
        and payload.get("choiceKind") in NUMBERED_CHOICE_KINDS
        and _positive_integer(payload.get("choiceId"))
        and all(_nonnegative_integer(payload.get(field)) for field in (
            "bufferId", "windowId", "tabpageId", "changedtick",
        ))
    )


def valid_accept_numbered_choice_request(payload: Any) -> bool:
    """Accept only one exact zero-based item from one exact editor context."""
    return (
        isinstance(payload, Mapping)
        and frozenset(payload) == _ACCEPT_FIELDS
        and payload.get("choiceKind") in NUMBERED_CHOICE_KINDS
        and _positive_integer(payload.get("requestId"))
        and _positive_integer(payload.get("choiceId"))
        and all(_nonnegative_integer(payload.get(field)) for field in (
            "itemIndex", "bufferId", "windowId", "tabpageId", "changedtick",
        ))
        and payload.get("itemIndex") < MAX_NUMBERED_CHOICE_ITEMS
    )


def numbered_choice_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical editor state without the prompt's item data."""
    return {key: value for key, value in payload.items() if key not in _OPEN_ONLY_FIELDS}
