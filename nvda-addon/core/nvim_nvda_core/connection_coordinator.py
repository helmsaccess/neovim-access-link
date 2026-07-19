"""Shared connection ownership independent of NVDA plugin inheritance."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .connection_instances import ConnectionInstanceManager


class ConnectionCoordinator:
    """Own connection instances and their cross-terminal runtime tracking."""

    def __init__(self, instance_manager: ConnectionInstanceManager | None = None) -> None:
        self.instances = instance_manager or ConnectionInstanceManager()
        self.active_client: Any | None = None
        self.last_connection_state: str | None = None
        self.connected = False
        self.remembered_terminal_bindings: set[Any] = set()
        self.remember_offer_instances: set[str] = set()
        self.authenticated_instances: set[str] = set()
        self.terminal_passthrough: dict[str, bool] = {}
        self.active_instance_id: str | None = None
        self.runtime_states: dict[str, dict[str, Any]] = {}
        self.pending_full_states: dict[str, dict[str, Any]] = {}

    def clear_runtime_tracking(self) -> None:
        """Forget tracked runtime state after callers have stopped owned clients."""
        self.active_client = None
        self.connected = False
        self.remembered_terminal_bindings.clear()
        self.remember_offer_instances.clear()
        self.authenticated_instances.clear()
        self.terminal_passthrough.clear()
        self.active_instance_id = None
        self.runtime_states.clear()
        self.pending_full_states.clear()

    def switch_runtime(
        self,
        instance_id: str,
        active_runtime: dict[str, Any],
        create_runtime: Callable[[], dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Store the previous instance runtime and activate one isolated runtime."""
        if instance_id == self.active_instance_id:
            return None
        if self.active_instance_id is not None:
            self.runtime_states[self.active_instance_id] = active_runtime
        runtime = self.runtime_states.pop(instance_id, None) or create_runtime()
        self.active_instance_id = instance_id
        return runtime

    def drop_runtime(
        self,
        instance_id: str,
        create_runtime: Callable[[], dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Forget one instance and return a blank runtime when it was active."""
        self.runtime_states.pop(instance_id, None)
        if self.active_instance_id != instance_id:
            return None
        runtime = create_runtime()
        self.active_instance_id = None
        return runtime
