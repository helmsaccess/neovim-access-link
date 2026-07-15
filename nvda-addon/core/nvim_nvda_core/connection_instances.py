"""Explicit runtime connection instances and terminal bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .connection_targets import ConnectionTarget, REMOTE_SSH, remote_ssh_target


@dataclass(frozen=True)
class ConnectionInstance:
    identifier: str
    target_id: str
    session_id: str
    label: str
    transport_kind: str = REMOTE_SSH

    @property
    def profile_id(self) -> str:
        """Compatibility view for remote-only call sites during target migration."""
        return self.target_id if self.transport_kind == REMOTE_SSH else ""


class ConnectionInstanceManager:
    """Own clients independently; never infer a terminal-to-session mapping."""

    def __init__(self) -> None:
        self._next = 1
        self._instances: dict[str, tuple[ConnectionInstance, Any]] = {}
        self._terminal_bindings: dict[Any, str] = {}

    def add(self, profile_id: str, session_id: str, label: str, client: Any,
            transport_kind: str = REMOTE_SSH) -> ConnectionInstance:
        if transport_kind != REMOTE_SSH:
            raise ValueError("non-SSH instances require add_target")
        return self.add_target(remote_ssh_target(profile_id, label), session_id, label, client)

    def add_target(self, target: ConnectionTarget, session_id: str, label: str,
                   client: Any) -> ConnectionInstance:
        if not isinstance(target, ConnectionTarget):
            raise ValueError("typed connection target is required")
        if not session_id or not label:
            raise ValueError("session and label are required")
        identifier = f"connection-{self._next}"
        self._next += 1
        instance = ConnectionInstance(
            identifier, target.identifier, session_id, label, target.kind,
        )
        self._instances[identifier] = (instance, client)
        try:
            setattr(client, "nvim_nvda_instance_id", identifier)
            client.start()
        except Exception:
            del self._instances[identifier]
            raise
        return instance

    def list(self) -> list[ConnectionInstance]:
        return [value[0] for value in self._instances.values()]

    def bind(self, terminal: Any, instance_id: str) -> ConnectionInstance:
        if terminal is None:
            raise ValueError("terminal identity is required")
        try:
            instance = self._instances[instance_id][0]
        except KeyError as error:
            raise ValueError("unknown connection instance") from error
        self._terminal_bindings[terminal] = instance_id
        return instance

    def selected_for(self, terminal: Any) -> ConnectionInstance | None:
        identifier = self._terminal_bindings.get(terminal)
        value = self._instances.get(identifier) if identifier else None
        return value[0] if value else None

    def bound_terminals_for(self, instance_id: str) -> list[Any]:
        if instance_id not in self._instances:
            raise ValueError("unknown connection instance")
        return [
            terminal for terminal, selected in self._terminal_bindings.items()
            if selected == instance_id
        ]

    def unbind(self, terminal: Any) -> ConnectionInstance | None:
        identifier = self._terminal_bindings.pop(terminal, None)
        value = self._instances.get(identifier) if identifier else None
        return value[0] if value else None

    def client_for(self, instance_id: str) -> Any:
        try:
            return self._instances[instance_id][1]
        except KeyError as error:
            raise ValueError("unknown connection instance") from error

    def remove(self, instance_id: str) -> None:
        _instance, client = self.detach(instance_id)
        client.stop()

    def detach(self, instance_id: str) -> tuple[ConnectionInstance, Any]:
        """Remove ownership without stopping the client, for off-main-thread shutdown."""
        try:
            instance, client = self._instances.pop(instance_id)
        except KeyError as error:
            raise ValueError("unknown connection instance") from error
        for terminal, selected in list(self._terminal_bindings.items()):
            if selected == instance_id:
                del self._terminal_bindings[terminal]
        return instance, client

    def stop_all(self) -> None:
        errors = []
        for identifier in list(self._instances):
            try:
                self.remove(identifier)
            except Exception as error:
                errors.append(error)
        self._terminal_bindings.clear()
        if errors:
            raise RuntimeError(f"{len(errors)} connection clients failed to stop")
