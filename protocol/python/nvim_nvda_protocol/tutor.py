"""Strictly scope Neovim Tutor exercise state to genuine Tutor buffers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


TUTOR_EXERCISE_STATUSES = frozenset({"correct", "incorrect"})


def tutor_public_state(payload: Mapping[str, Any]) -> dict[str, Any]:
	"""Retain the bounded exercise status only for Neovim's Tutor filetype."""
	if "tutorExerciseStatus" not in payload:
		return payload if isinstance(payload, dict) else dict(payload)
	status = payload.get("tutorExerciseStatus")
	if payload.get("filetype") == "tutor" and status in TUTOR_EXERCISE_STATUSES:
		return payload if isinstance(payload, dict) else dict(payload)
	state = dict(payload)
	state.pop("tutorExerciseStatus", None)
	return state


def valid_tutor_exercise_changed(payload: Any) -> bool:
	"""Accept one assessment transition only in an exact Tutor context."""
	return (
		isinstance(payload, Mapping)
		and payload.get("filetype") == "tutor"
		and payload.get("tutorExerciseStatus") in TUTOR_EXERCISE_STATUSES
	)
