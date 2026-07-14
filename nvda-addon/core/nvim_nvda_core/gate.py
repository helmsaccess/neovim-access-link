"""Fail-open decision gate for session-scoped terminal suppression."""

from __future__ import annotations

from dataclasses import dataclass
import threading


@dataclass(frozen=True)
class TerminalIdentity:
    process_id: int
    window_handle: int
    frontend_kind: str = "window"
    runtime_id: tuple[int, ...] = ()


class SessionGate:
    def __init__(self, enabled_frontends=frozenset({"windowsTerminal"})) -> None:
        self.enabled_frontends = frozenset(enabled_frontends)
        self.manual_enabled = False
        self.authenticated = False
        self.nvim_active = False
        self.terminal_passthrough = False
        self.focused: TerminalIdentity | None = None
        self.bound_terminal: TerminalIdentity | None = None
        self._lock = threading.RLock()

    @property
    def suppression_active(self) -> bool:
        with self._lock:
            return (
                self.manual_enabled
                and self.authenticated
                and self.nvim_active
                and not self.terminal_passthrough
                and self.focused is not None
                and self.focused == self.bound_terminal
                and self.focused.frontend_kind in self.enabled_frontends
            )

    def disconnect(self) -> None:
        with self._lock:
            self.authenticated = False
            self.nvim_active = False
            self.terminal_passthrough = False
            self.bound_terminal = None

    def disable(self) -> None:
        with self._lock:
            self.manual_enabled = False
            self.disconnect()

    def should_suppress(self, identity: TerminalIdentity) -> bool:
        return self.suppression_active and identity == self.bound_terminal
