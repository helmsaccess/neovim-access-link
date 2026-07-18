"""Compose Neovim RPC input with the SSH stdio transport."""

from __future__ import annotations

import threading
from typing import Any

from .stdio import StdioTransport
from nvim_nvda_protocol import (
    NvimRpcEndpoint, NvimRpcSource, clipboard_result_state,
    valid_copy_text_request, valid_paste_text_request,
    terminal_control_result_state, valid_leave_terminal_input_request,
    valid_set_register_request,
)


_COPY_TEXT_LUA = "return require('nvim_nvda').request_copy_text(...)"
_PASTE_TEXT_LUA = "return require('nvim_nvda').request_paste_text(...)"
_SET_REGISTER_LUA = "return require('nvim_nvda').request_set_register(...)"
_LEAVE_TERMINAL_INPUT_LUA = "return require('nvim_nvda').request_leave_terminal_input(...)"


class Bridge:
    def __init__(
        self,
        nvim_socket: str,
        stdio_streams: tuple[Any, Any] | None = None,
        transport: Any | None = None,
        session_nonce: str | None = None,
    ) -> None:
        self._state_lock = threading.Lock()
        self._state: dict[str, Any] = {"connection": {"neovim": "connecting"}}
        if transport is not None and stdio_streams is not None:
            raise ValueError("provide either stdio streams or a test transport")
        if transport is not None:
            self.transport = transport
        elif stdio_streams is not None:
            self.transport = StdioTransport(
                self.full_state, stdio_streams[0], stdio_streams[1], on_control=self._on_client_control
            )
        else:
            raise ValueError("SSH stdio streams are required")
        self.nvim = NvimRpcSource(
            NvimRpcEndpoint.unix(nvim_socket),
            self._on_nvim_event, self._on_nvim_connection,
            session_nonce,
        )

    def start(self) -> None:
        self.transport.start()
        self.nvim.start()

    def stop(self) -> None:
        self.nvim.stop()
        self.transport.stop()

    def full_state(self) -> dict[str, Any]:
        with self._state_lock:
            return dict(self._state)

    def _on_nvim_event(self, event_type: str, payload: dict[str, Any]) -> None:
        published = dict(payload)
        published["connection"] = {"neovim": "connected"}
        if event_type in {"copyTextResult", "pasteTextResult", "setRegisterResult"}:
            state = clipboard_result_state(payload)
        elif event_type == "leaveTerminalInputResult":
            state = terminal_control_result_state(payload)
        else:
            state = dict(payload)
        with self._state_lock:
            self._state = state
            self._state["connection"] = {"neovim": "connected"}
        self.transport.publish(event_type, published)

    def _on_nvim_connection(self, state: str) -> None:
        with self._state_lock:
            self._state["connection"] = {"neovim": state}
        if state != "connecting":
            self.transport.publish("connectionStateChanged", self.full_state())

    def _on_client_control(self, kind: str, payload: dict[str, Any]) -> None:
        if kind == "copyTextRequest":
            if valid_copy_text_request(payload):
                self.nvim.notify("nvim_exec_lua", _COPY_TEXT_LUA, [dict(payload)])
            return
        if kind == "pasteTextRequest":
            if valid_paste_text_request(payload):
                self.nvim.notify("nvim_exec_lua", _PASTE_TEXT_LUA, [dict(payload)])
            return
        if kind == "setRegisterRequest":
            if valid_set_register_request(payload):
                self.nvim.notify("nvim_exec_lua", _SET_REGISTER_LUA, [dict(payload)])
            return
        if kind == "leaveTerminalInputRequest":
            if valid_leave_terminal_input_request(payload):
                self.nvim.notify("nvim_exec_lua", _LEAVE_TERMINAL_INPUT_LUA, [dict(payload)])
            return
        if kind != "routeCursor":
            return
        required = ("bufferId", "windowId", "line", "byteColumn", "changedtick")
        if any(not isinstance(payload.get(field), int) for field in required):
            return
        self.nvim.notify(
            "nvim_exec_lua",
            """
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
            """,
            [payload],
        )
