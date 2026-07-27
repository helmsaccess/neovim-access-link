"""Validate the fixed semantic cursor-routing control."""

from __future__ import annotations

from typing import Any

MAX_COMMAND_LINE_BYTES = 16 * 1024
MAX_MODE_RAW_BYTES = 16


def _integer(value: Any, *, minimum: int = 0) -> bool:
	return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _bounded_text(value: Any, maximum: int, *, allow_empty: bool = True) -> bool:
	return (
		isinstance(value, str)
		and (allow_empty or bool(value))
		and "\0" not in value
		and len(value.encode("utf-8")) <= maximum
	)


def _utf8_boundary(text: str, byte_column: int) -> bool:
	encoded = text.encode("utf-8")
	return (
		byte_column <= len(encoded)
		and (byte_column == len(encoded) or encoded[byte_column] & 0xC0 != 0x80)
	)


def valid_route_cursor_request(payload: Any) -> bool:
	"""Return whether *payload* is one complete, bounded routing request."""
	if not isinstance(payload, dict):
		return False
	if not all(_integer(payload.get(field)) for field in (
		"bufferId",
		"windowId",
		"byteColumn",
		"changedtick",
	)):
		return False
	mode_raw = payload.get("modeRaw")
	if not _bounded_text(mode_raw, MAX_MODE_RAW_BYTES, allow_empty=False):
		return False
	target = payload.get("target")
	if target == "editor":
		return (
			not mode_raw.startswith("c")
			and _integer(payload.get("line"), minimum=1)
			and set(payload) == {
				"target",
				"bufferId",
				"windowId",
				"line",
				"byteColumn",
				"changedtick",
				"modeRaw",
			}
		)
	if target == "commandLine":
		command_line = payload.get("commandLine")
		command_type = payload.get("commandLineType")
		return (
			mode_raw.startswith("c")
			and _bounded_text(command_line, MAX_COMMAND_LINE_BYTES)
			and _bounded_text(command_type, 8, allow_empty=False)
			and _utf8_boundary(command_line, payload["byteColumn"])
			and set(payload) == {
				"target",
				"bufferId",
				"windowId",
				"byteColumn",
				"changedtick",
				"modeRaw",
				"commandLine",
				"commandLineType",
			}
		)
	return False
