"""Validate fixed semantic actions triggered by repeated Braille routing."""

from __future__ import annotations

from typing import Any

from .cursor_routing import MAX_MODE_RAW_BYTES


WORD_ACTIONS = frozenset({"changeWord", "deleteWord"})
LINE_ACTIONS = frozenset({"changeLine", "deleteLine"})
LINE_STARTS = frozenset({"routing", "indentation", "beginning"})


def _integer(value: Any, *, minimum: int = 0) -> bool:
	return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def valid_braille_route_action_request(payload: Any) -> bool:
	"""Return whether *payload* is one bounded, fixed editor action."""
	if not isinstance(payload, dict):
		return False
	if not all(
		_integer(payload.get(field))
		for field in ("bufferId", "windowId", "byteColumn", "changedtick")
	):
		return False
	if not _integer(payload.get("line"), minimum=1):
		return False
	mode_raw = payload.get("modeRaw")
	if (
		not isinstance(mode_raw, str)
		or not mode_raw
		or "\0" in mode_raw
		or len(mode_raw.encode("utf-8")) > MAX_MODE_RAW_BYTES
		or mode_raw[:1] not in {"n", "i"}
	):
		return False
	action = payload.get("action")
	common = {
		"bufferId",
		"windowId",
		"line",
		"byteColumn",
		"changedtick",
		"modeRaw",
		"action",
	}
	if action in WORD_ACTIONS:
		return set(payload) == common
	if action in LINE_ACTIONS:
		return payload.get("lineStart") in LINE_STARTS and set(payload) == common | {"lineStart"}
	return False
