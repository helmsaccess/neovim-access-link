"""Validate fixed semantic Braille line-navigation controls."""

from __future__ import annotations

from typing import Any

from .cursor_routing import MAX_MODE_RAW_BYTES

BRAILLE_LINE_DIRECTIONS = frozenset({"previous", "next"})
BRAILLE_LINE_TARGET_COLUMNS = frozenset({"preferred", "start", "end"})
MAX_VIRTUAL_COLUMN = 2_147_483_647


def _integer(value: Any, *, minimum: int = 0) -> bool:
	return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def valid_move_braille_line_request(payload: Any) -> bool:
	"""Return whether *payload* is one complete, bounded editor-line request."""
	if not isinstance(payload, dict):
		return False
	if set(payload) != {
		"bufferId",
		"windowId",
		"line",
		"changedtick",
		"modeRaw",
		"direction",
		"targetColumn",
		"preferredVirtualColumn",
	}:
		return False
	if not all(
		_integer(payload.get(field), minimum=1 if field == "line" else 0)
		for field in (
			"bufferId",
			"windowId",
			"line",
			"changedtick",
			"preferredVirtualColumn",
		)
	):
		return False
	if payload["preferredVirtualColumn"] > MAX_VIRTUAL_COLUMN:
		return False
	mode_raw = payload.get("modeRaw")
	return (
		isinstance(mode_raw, str)
		and bool(mode_raw)
		and "\0" not in mode_raw
		and len(mode_raw.encode("utf-8")) <= MAX_MODE_RAW_BYTES
		and not mode_raw.startswith(("c", "t"))
		and payload.get("direction") in BRAILLE_LINE_DIRECTIONS
		and payload.get("targetColumn") in BRAILLE_LINE_TARGET_COLUMNS
	)
