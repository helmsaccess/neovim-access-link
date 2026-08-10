"""Strict validation for semantic plugin-manager lifecycle events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PLUGIN_MANAGER_OPERATIONS = frozenset({"install", "update", "clean", "check", "log", "sync"})
PLUGIN_MANAGER_PHASES = frozenset({"started", "finished"})


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
