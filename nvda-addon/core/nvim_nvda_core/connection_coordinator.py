"""Shared connection ownership independent of NVDA plugin inheritance."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .connection_instances import ConnectionInstanceManager
from .gate import SessionGate
from .speech import SpeechPlanner


class ConnectionCoordinator:
    """Own connection instances and their cross-terminal runtime tracking."""

    _REQUEST_ID_LIMIT = 2_147_483_648
    _REQUEST_CHANNELS = frozenset({"focusContext", "clipboard", "terminalControl"})

    def __init__(
        self,
        instance_manager: ConnectionInstanceManager | None = None,
        gate: SessionGate | None = None,
        planner: SpeechPlanner | None = None,
    ) -> None:
        self.instances = instance_manager or ConnectionInstanceManager()
        self.gate = gate or SessionGate()
        self.planner = planner or SpeechPlanner()
        self.current_state: dict[str, Any] = {}
        self.last_mode: str | None = None
        self.typed_word: list[str] = []
        self.typed_position: Any | None = None
        self.menu_documentation = ""
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
        self.pending_focus_contexts: dict[str, Any] = {}
        self.pending_clipboard_requests: dict[int, Any] = {}
        self.pending_terminal_control_requests: dict[int, Any] = {}
        self.transport_capabilities: frozenset[str] = frozenset()
        self._request_ids = {channel: 0 for channel in self._REQUEST_CHANNELS}

    def next_request_id(self, channel: str) -> int:
        """Return the next bounded correlation ID for one allowlisted channel."""
        if channel not in self._REQUEST_CHANNELS:
            raise ValueError("unknown request channel")
        request_id = (self._request_ids[channel] + 1) % self._REQUEST_ID_LIMIT
        self._request_ids[channel] = request_id
        return request_id

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
        self.pending_focus_contexts.clear()
        self.pending_clipboard_requests.clear()
        self.pending_terminal_control_requests.clear()
        self.transport_capabilities = frozenset()

    def switch_runtime(
        self,
        instance_id: str,
        create_runtime: Callable[[], dict[str, Any]],
    ) -> bool:
        """Store the previous instance runtime and activate one isolated runtime."""
        if instance_id == self.active_instance_id:
            return False
        if self.active_instance_id is not None:
            self.runtime_states[self.active_instance_id] = self._capture_runtime()
        runtime = self.runtime_states.pop(instance_id, None) or create_runtime()
        self._activate_runtime(runtime)
        self.active_instance_id = instance_id
        return True

    def drop_runtime(
        self,
        instance_id: str,
        create_runtime: Callable[[], dict[str, Any]],
    ) -> bool:
        """Forget one instance and return a blank runtime when it was active."""
        self.runtime_states.pop(instance_id, None)
        if self.active_instance_id != instance_id:
            return False
        self._activate_runtime(create_runtime())
        self.active_instance_id = None
        return True

    def _capture_runtime(self) -> dict[str, Any]:
        return {
            "planner": self.planner,
            "currentState": self.current_state,
            "lastMode": self.last_mode,
            "typedWord": self.typed_word,
            "typedPosition": self.typed_position,
            "menuDocumentation": self.menu_documentation,
            "connected": self.connected,
            "lastConnectionState": self.last_connection_state,
            "transportCapabilities": self.transport_capabilities,
        }

    def _activate_runtime(self, runtime: dict[str, Any]) -> None:
        self.planner = runtime["planner"]
        self.current_state = runtime["currentState"]
        self.last_mode = runtime["lastMode"]
        self.typed_word = runtime["typedWord"]
        self.typed_position = runtime["typedPosition"]
        self.menu_documentation = runtime["menuDocumentation"]
        self.connected = runtime["connected"]
        self.last_connection_state = runtime["lastConnectionState"]
        self.transport_capabilities = runtime["transportCapabilities"]
