"""Strict validation for held callable and diagnostic inspection controls."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .clipboard import valid_request_id


MAX_CONTEXT_TEXT_BYTES = 16 * 1024
MAX_CONTEXT_ITEMS = 100
MAX_CONTEXT_TOTAL_TEXT_BYTES = 256 * 1024
_REQUEST_FIELDS = frozenset({
    "requestId",
    "bufferId",
    "windowId",
    "tabpageId",
    "changedtick",
    "line",
    "byteColumn",
})
_RESULT_ONLY_FIELDS = frozenset({
    "requestId",
    "ok",
    "resultCode",
    "items",
    "activeItem",
    "activeParameter",
})
_RESULT_CODES = frozenset({
    "ok",
    "noResult",
    "invalidOrStaleRequest",
    "requestFailed",
})
_SEVERITIES = frozenset({"error", "warning", "information", "hint"})


def _positive_integer(value: Any) -> bool:
    return valid_request_id(value) and value > 0


def _nonnegative_integer(value: Any) -> bool:
    return valid_request_id(value)


def _bounded_text(value: Any) -> bool:
    if not isinstance(value, str) or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_CONTEXT_TEXT_BYTES
    except UnicodeEncodeError:
        return False


def valid_context_request(payload: Any) -> bool:
    """Accept one exact, immutable editor location."""
    return (
        isinstance(payload, Mapping)
        and frozenset(payload) == _REQUEST_FIELDS
        and _positive_integer(payload.get("requestId"))
        and all(_positive_integer(payload.get(field)) for field in ("bufferId", "windowId", "tabpageId"))
        and all(_nonnegative_integer(payload.get(field)) for field in ("changedtick", "byteColumn"))
        and _positive_integer(payload.get("line"))
    )


def _valid_callable_item(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    if frozenset(value) != {"signature", "parameters", "documentation"}:
        return False
    parameters = value.get("parameters")
    return (
        _bounded_text(value.get("signature"))
        and _bounded_text(value.get("documentation"))
        and isinstance(parameters, Sequence)
        and not isinstance(parameters, (str, bytes, bytearray))
        and len(parameters) <= MAX_CONTEXT_ITEMS
        and all(_bounded_text(parameter) for parameter in parameters)
    )


def _valid_diagnostic_item(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    required = {
        "message",
        "severity",
        "source",
        "code",
        "line",
        "byteColumn",
        "endLine",
        "endByteColumn",
        "atCursor",
    }
    if frozenset(value) != required:
        return False
    code = value.get("code")
    line = value.get("line")
    byte_column = value.get("byteColumn")
    end_line = value.get("endLine")
    end_byte_column = value.get("endByteColumn")
    return (
        _bounded_text(value.get("message"))
        and value.get("severity") in _SEVERITIES
        and _bounded_text(value.get("source"))
        and (
            code is None
            or (
                isinstance(code, int)
                and not isinstance(code, bool)
                and -(2**31) <= code <= 2**31 - 1
            )
            or _bounded_text(code)
        )
        and _positive_integer(line)
        and _nonnegative_integer(byte_column)
        and _positive_integer(end_line)
        and _nonnegative_integer(end_byte_column)
        and (end_line > line or (end_line == line and end_byte_column >= byte_column))
        and isinstance(value.get("atCursor"), bool)
    )


def _text_bytes(value: Any) -> int:
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, Mapping):
        return sum(_text_bytes(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return sum(_text_bytes(item) for item in value)
    return 0


def _valid_result(payload: Any, item_validator, *, callable_result: bool) -> bool:
    if not isinstance(payload, Mapping):
        return False
    request = {field: payload.get(field) for field in _REQUEST_FIELDS}
    if not valid_context_request(request) or not isinstance(payload.get("ok"), bool):
        return False
    result_code = payload.get("resultCode")
    if result_code not in _RESULT_CODES:
        return False
    items = payload.get("items")
    if (
        not isinstance(items, Sequence)
        or isinstance(items, (str, bytes, bytearray))
        or len(items) > MAX_CONTEXT_ITEMS
        or not all(item_validator(item) for item in items)
        or _text_bytes(items) > MAX_CONTEXT_TOTAL_TEXT_BYTES
    ):
        return False
    active_item = payload.get("activeItem")
    active_parameter = payload.get("activeParameter")
    if not _nonnegative_integer(active_item) or not _nonnegative_integer(active_parameter):
        return False
    if payload.get("ok"):
        if result_code != "ok" or len(items) == 0 or active_item >= len(items):
            return False
        if not callable_result:
            return active_parameter == 0
        parameters = items[active_item].get("parameters")
        return active_parameter < max(1, len(parameters))
    return result_code != "ok" and len(items) == 0 and active_item == 0 and active_parameter == 0


def valid_callable_context_result(payload: Any) -> bool:
    """Validate one bounded callable-context response plus its state snapshot."""
    return _valid_result(payload, _valid_callable_item, callable_result=True)


def valid_diagnostic_context_result(payload: Any) -> bool:
    """Validate one bounded diagnostic-context response plus its state snapshot."""
    return _valid_result(payload, _valid_diagnostic_item, callable_result=False)


def developer_context_result_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical editor state without ephemeral inspection data."""
    return {key: value for key, value in payload.items() if key not in _RESULT_ONLY_FIELDS}
