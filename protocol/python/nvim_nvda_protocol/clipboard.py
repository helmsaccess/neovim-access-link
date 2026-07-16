"""Strict validation for the bounded semantic clipboard controls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


MAX_CLIPBOARD_TEXT_BYTES = 256 * 1024
MAX_REQUEST_ID = 2_147_483_647
COPY_TEXT_SOURCES = frozenset({"visualSelection", "yankRegister"})
_EXPECTED_STATE_FIELDS = ("bufferId", "windowId", "tabpageId", "changedtick")
_RESULT_ONLY_FIELDS = frozenset({
    "requestId", "ok", "resultCode", "source", "clipboardText",
    "copiedCharacterCount", "copiedLineCount", "registerType", "insertedBytes",
    "insertedLines", "storedBytes", "storedLineCount", "changedtickBefore",
    "changedtickAfter",
})


def valid_request_id(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= MAX_REQUEST_ID
    )


def valid_expected_state(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping):
        return False
    if any(
        not isinstance(payload.get(field), int)
        or isinstance(payload.get(field), bool)
        or payload.get(field) < 0
        for field in _EXPECTED_STATE_FIELDS
    ):
        return False
    mode_raw = payload.get("modeRaw")
    return isinstance(mode_raw, str) and 0 < len(mode_raw) <= 16


def valid_clipboard_text(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_CLIPBOARD_TEXT_BYTES
    except UnicodeEncodeError:
        return False


def valid_copy_text_request(payload: Any) -> bool:
    return (
        isinstance(payload, Mapping)
        and valid_request_id(payload.get("requestId"))
        and payload.get("source") in COPY_TEXT_SOURCES
        and valid_expected_state(payload)
    )


def valid_paste_text_request(payload: Any) -> bool:
    return (
        isinstance(payload, Mapping)
        and valid_request_id(payload.get("requestId"))
        and valid_expected_state(payload)
        and valid_clipboard_text(payload.get("text"))
    )


def valid_set_register_request(payload: Any) -> bool:
    return valid_paste_text_request(payload)


def clipboard_result_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical editor state without one-shot clipboard fields."""
    return {key: value for key, value in payload.items() if key not in _RESULT_ONLY_FIELDS}
