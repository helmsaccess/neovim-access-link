"""Strict validation for independent read-only Braille exploration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .exploration import (
	valid_end_exploration_request,
	valid_explore_text_request,
	valid_explore_text_result,
)


def valid_braille_explore_line_request(payload: Any) -> bool:
	"""Accept one exact virtual Braille line step with a preferred column."""
	if not isinstance(payload, Mapping):
		return False
	base = {
		key: value
		for key, value in payload.items()
		if key not in {"desiredVirtualColumn", "targetColumn"}
	}
	desired = payload.get("desiredVirtualColumn")
	return (
		frozenset(payload) == frozenset(base) | {"desiredVirtualColumn", "targetColumn"}
		and valid_explore_text_request(base)
		and payload.get("action") in {"lineUp", "lineDown"}
		and payload.get("targetColumn") in {"preferred", "start", "end"}
		and isinstance(desired, int)
		and not isinstance(desired, bool)
		and 0 <= desired <= 2_147_483_647
	)


def valid_end_braille_exploration_request(payload: Any) -> bool:
	"""Accept the fixed cleanup identifiers for the Braille channel."""
	return valid_end_exploration_request(payload)


def valid_braille_explore_line_result(payload: Any) -> bool:
	"""Accept only line-unit results emitted by the Braille channel."""
	return (
		valid_explore_text_result(payload)
		and payload.get("action") in {"lineUp", "lineDown"}
		and (payload.get("ok") is False or payload.get("unit") == "line")
	)
