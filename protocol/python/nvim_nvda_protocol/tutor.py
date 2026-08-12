"""Strictly scope Neovim Tutor exercise state to genuine Tutor buffers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


TUTOR_EXERCISE_STATUSES = frozenset({"correct", "incorrect"})


def tutor_public_state(payload: Mapping[str, Any]) -> dict[str, Any]:
	"""Retain the bounded exercise status only for Neovim's Tutor filetype."""
	state = dict(payload)
	if not (
		state.get("filetype") == "tutor"
		and state.get("tutorExerciseStatus") in TUTOR_EXERCISE_STATUSES
	):
		state.pop("tutorExerciseStatus", None)
	return state
