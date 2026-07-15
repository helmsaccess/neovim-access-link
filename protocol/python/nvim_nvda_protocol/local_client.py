"""Direct local Windows Neovim client over an IPv4 loopback RPC socket."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from .codec import ProtocolError, encode_frame
from .messages import MessageFactory
from .nvim_rpc import NvimRpcEndpoint, NvimRpcSource


_ROUTE_CURSOR_LUA = """
  local p = ...
  if vim.api.nvim_get_current_buf() ~= p.bufferId then return false end
  if vim.api.nvim_get_current_win() ~= p.windowId then return false end
  if vim.api.nvim_buf_get_changedtick(p.bufferId) ~= p.changedtick then return false end
  if p.line < 1 or p.line > vim.api.nvim_buf_line_count(p.bufferId) then return false end
  local line = vim.api.nvim_buf_get_lines(p.bufferId, p.line - 1, p.line, true)[1] or ''
  if p.byteColumn < 0 or p.byteColumn > #line then return false end
  if p.byteColumn < #line then
    local byte = string.byte(line, p.byteColumn + 1)
    if byte >= 0x80 and byte < 0xC0 then return false end
  end
  vim.api.nvim_win_set_cursor(p.windowId, { p.line, p.byteColumn })
  return true
"""


class LocalTcpClient:
    capabilities = ("resync", "semanticEvents", "cursorRouting", "accessibleMenus")

    def __init__(
        self,
        host: str,
        port: int,
        on_event: Callable[[dict[str, Any]], None],
        on_connection_state: Callable[[str], None],
        on_diagnostic: Callable[[str, dict[str, Any]], None] | None = None,
        source_factory: Callable[..., Any] = NvimRpcSource,
        session_nonce: str | None = None,
    ) -> None:
        self.endpoint = NvimRpcEndpoint.windows_loopback_tcp(host, port)
        self.on_event = on_event
        self.on_connection_state = on_connection_state
        self.on_diagnostic = on_diagnostic or (lambda _category, _fields: None)
        self._factory = MessageFactory()
        self._state_lock = threading.Lock()
        self._state: dict[str, Any] | None = None
        self._authenticated = False
        self._source = source_factory(
            self.endpoint, self._on_nvim_event, self._on_nvim_connection,
            session_nonce,
        )

    def start(self) -> None:
        self.on_diagnostic("localTcpStart", {
            "host": self.endpoint.address[0], "port": self.endpoint.address[1],
        })
        self._source.start()

    def stop(self) -> None:
        self._source.stop()

    def send_control(self, kind: str, payload: dict[str, Any]) -> bool:
        if kind == "requestFullState":
            with self._state_lock:
                state = dict(self._state) if self._state is not None else None
            if state is None:
                self.on_diagnostic("controlRejected", {"type": kind, "reason": "notConnected"})
                return False
            return self._publish("fullState", state)
        if kind != "routeCursor" or not self._valid_cursor_payload(payload):
            self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
            return False
        return self._source.notify("nvim_exec_lua", _ROUTE_CURSOR_LUA, [dict(payload)])

    @staticmethod
    def _valid_cursor_payload(payload: dict[str, Any]) -> bool:
        required = ("bufferId", "windowId", "line", "byteColumn", "changedtick")
        return isinstance(payload, dict) and all(
            isinstance(payload.get(field), int) and not isinstance(payload.get(field), bool)
            for field in required
        )

    def _on_nvim_event(self, event_type: str, payload: dict[str, Any]) -> None:
        state = dict(payload)
        event = self._validated_event(event_type, state)
        if event is None:
            return
        with self._state_lock:
            self._state = state
        if event_type == "fullState" and not self._authenticated:
            self._authenticated = True
            self.on_connection_state("connected")
        self.on_event(event)

    def _publish(self, event_type: str, payload: dict[str, Any]) -> bool:
        event = self._validated_event(event_type, payload)
        if event is None:
            return False
        self.on_event(event)
        return True

    def _validated_event(
        self, event_type: str, payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        value = dict(payload)
        if event_type == "fullState":
            value["_transport"] = {
                "capabilities": list(self.capabilities),
                "kind": "windows-loopback-tcp",
            }
        try:
            event = self._factory.create(event_type, value)
            encode_frame(event)  # Reuse v2 type and resource validation without SSH framing.
        except (ProtocolError, TypeError, ValueError) as error:
            self.on_diagnostic("localEventRejected", {
                "type": event_type, "errorType": type(error).__name__, "error": str(error),
            })
            return None
        return event

    def _on_nvim_connection(self, state: str) -> None:
        if state == "connected":
            # Authentication for the accessibility layer begins with fullState,
            # matching the SSH client rather than the raw RPC socket state.
            return
        if state == "disconnected":
            self._authenticated = False
            with self._state_lock:
                self._state = None
        self.on_connection_state(state)
