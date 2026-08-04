"""Strict validation for automatic LSP parameter announcements."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .clipboard import valid_request_id


MAX_CALL_NAME_BYTES = 512
MAX_SIGNATURE_BYTES = 2048
MAX_PARAMETER_BYTES = 512
MAX_SIGNATURE_ITEMS = 100
_HINT_REASONS = frozenset({"callEntered", "signatureChanged", "parameterChanged"})


def _positive_integer(value: Any, maximum: int = 2_147_483_647) -> bool:
	return (
		valid_request_id(value)
		and value > 0
		and value <= maximum
	)


def _nonnegative_integer(value: Any) -> bool:
	return valid_request_id(value)


def _bounded_text(value: Any, maximum: int, *, empty: bool = True) -> bool:
	if not isinstance(value, str) or "\0" in value or (not empty and not value):
		return False
	try:
		return len(value.encode("utf-8")) <= maximum
	except UnicodeEncodeError:
		return False


def valid_active_parameter_changed(payload: Any) -> bool:
	"""Accept one bounded insertion-time parameter transition from the plugin."""
	if not isinstance(payload, Mapping):
		return False
	cursor = payload.get("cursor")
	capabilities = payload.get("pluginCapabilities")
	signature_index = payload.get("signatureIndex")
	signature_count = payload.get("signatureCount")
	parameter_index = payload.get("activeParameter")
	parameter_count = payload.get("parameterCount")
	return (
		isinstance(capabilities, list)
		and "activeParameterHints" in capabilities
		and payload.get("mode") == "insert"
		and isinstance(payload.get("modeRaw"), str)
		and payload["modeRaw"].startswith("i")
		and _positive_integer(payload.get("bufferId"))
		and _positive_integer(payload.get("windowId"))
		and _nonnegative_integer(payload.get("changedtick"))
		and isinstance(cursor, Mapping)
		and _positive_integer(cursor.get("line"))
		and _nonnegative_integer(cursor.get("byteColumn"))
		and _bounded_text(payload.get("callName"), MAX_CALL_NAME_BYTES, empty=False)
		and _positive_integer(payload.get("callStartLine"))
		and _nonnegative_integer(payload.get("callStartByteColumn"))
		and _bounded_text(payload.get("signature"), MAX_SIGNATURE_BYTES, empty=False)
		and _positive_integer(signature_index, MAX_SIGNATURE_ITEMS)
		and _positive_integer(signature_count, MAX_SIGNATURE_ITEMS)
		and signature_index <= signature_count
		and _positive_integer(parameter_index, MAX_SIGNATURE_ITEMS)
		and _positive_integer(parameter_count, MAX_SIGNATURE_ITEMS)
		and parameter_index <= parameter_count
		and _bounded_text(payload.get("parameter"), MAX_PARAMETER_BYTES)
		and payload.get("hintReason") in _HINT_REASONS
	)
