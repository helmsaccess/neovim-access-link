"""Strict validation for semantic plugin-manager lifecycle events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PLUGIN_MANAGER_OPERATIONS = frozenset({"install", "update", "clean", "check", "log", "sync"})
PLUGIN_MANAGER_PHASES = frozenset({"started", "finished"})
MAX_PLUGIN_MANAGER_OVERVIEW_BYTES = 2048


def valid_plugin_manager_operation(payload: Any) -> bool:
	"""Accept one fixed, data-free lifecycle transition."""
	return (
		isinstance(payload, Mapping)
		and payload.get("pluginManagerKind") == "lazyNvim"
		and payload.get("pluginManagerOperation") in PLUGIN_MANAGER_OPERATIONS
		and payload.get("pluginManagerPhase") in PLUGIN_MANAGER_PHASES
	)


def plugin_manager_operation_state(payload: Mapping[str, Any]) -> dict[str, Any]:
	"""Remove one-shot lifecycle fields before updating canonical state."""
	return {
		key: value for key, value in payload.items()
		if key not in {"pluginManagerKind", "pluginManagerOperation", "pluginManagerPhase"}
	}


def plugin_manager_overview_state(payload: Mapping[str, Any]) -> dict[str, Any]:
	"""Keep a bounded Lazy overview only on the exact public Lazy buffer identity."""
	state = dict(payload)
	overview = state.get("pluginManagerOverview")
	if overview is None:
		return state
	try:
		overview_bytes = len(overview.encode("utf-8")) if isinstance(overview, str) else 0
	except UnicodeEncodeError:
		overview_bytes = 0
	if not (
		state.get("buftype") == "nofile"
		and state.get("filetype") == "lazy"
		and isinstance(overview, str)
		and 0 < overview_bytes <= MAX_PLUGIN_MANAGER_OVERVIEW_BYTES
	):
		state.pop("pluginManagerOverview", None)
	return state
