"""Validation for the fixed, bounded embedded-terminal control."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .clipboard import valid_request_id


_EXPECTED_ID_FIELDS = ("bufferId", "windowId", "tabpageId")
_RESULT_ONLY_FIELDS = frozenset({"requestId", "ok", "resultCode"})


def valid_leave_terminal_input_request(payload: Any) -> bool:
    """Accept only an exact Terminal-mode identity snapshot.

    ``changedtick`` is deliberately absent: terminal jobs may change their
    buffer between the key gesture and RPC handling, while this action changes
    mode only and never consumes buffer text.
    """
    return (
        isinstance(payload, Mapping)
        and valid_request_id(payload.get("requestId"))
        and all(
            isinstance(payload.get(field), int)
            and not isinstance(payload.get(field), bool)
            and payload.get(field) >= 0
            for field in _EXPECTED_ID_FIELDS
        )
        and payload.get("modeRaw") == "t"
    )


def terminal_control_result_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical editor state without one-shot correlation fields."""
    return {key: value for key, value in payload.items() if key not in _RESULT_ONLY_FIELDS}
