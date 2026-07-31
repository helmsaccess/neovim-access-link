"""Compose Neovim RPC input with the SSH stdio transport."""

from __future__ import annotations

import threading
from typing import Any

from .stdio import StdioTransport
from nvim_nvda_protocol import (
    NvimRpcEndpoint, NvimRpcSource, clipboard_result_state,
    exploration_result_state, valid_end_exploration_request,
    valid_explore_text_request, valid_explore_text_result,
    valid_copy_text_request, valid_paste_text_request,
    terminal_control_result_state, valid_leave_terminal_input_request,
    valid_set_register_request,
    numbered_choice_state, valid_accept_numbered_choice_request,
    valid_numbered_choice_closed, valid_numbered_choice_opened,
    valid_route_cursor_request,
    valid_move_braille_line_request,
    valid_braille_explore_line_request, valid_braille_explore_line_result,
    valid_braille_route_action_request,
    valid_end_braille_exploration_request,
    developer_context_result_state,
    valid_callable_context_result,
    valid_context_request,
    valid_diagnostic_context_result,
)


_COPY_TEXT_LUA = "return require('nvim_nvda').request_copy_text(...)"
_PASTE_TEXT_LUA = "return require('nvim_nvda').request_paste_text(...)"
_SET_REGISTER_LUA = "return require('nvim_nvda').request_set_register(...)"
_LEAVE_TERMINAL_INPUT_LUA = "return require('nvim_nvda').request_leave_terminal_input(...)"
_EXPLORE_TEXT_LUA = "return require('nvim_nvda').request_explore_text(...)"
_END_EXPLORATION_LUA = "return require('nvim_nvda').request_end_exploration(...)"
_ROUTE_CURSOR_LUA = "return require('nvim_nvda').request_route_cursor(...)"
_BRAILLE_ROUTE_ACTION_LUA = "return require('nvim_nvda').request_braille_route_action(...)"
_MOVE_BRAILLE_LINE_LUA = "return require('nvim_nvda').request_move_braille_line(...)"
_BRAILLE_EXPLORE_LINE_LUA = "return require('nvim_nvda').request_braille_explore_line(...)"
_END_BRAILLE_EXPLORATION_LUA = (
    "return require('nvim_nvda').request_end_braille_exploration(...)"
)
_CALLABLE_CONTEXT_LUA = "return require('nvim_nvda').request_callable_context(...)"
_DIAGNOSTIC_CONTEXT_LUA = "return require('nvim_nvda').request_diagnostic_context(...)"


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
        self._active_numbered_choice: dict[str, Any] | None = None
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
        if (event_type == "callableContextResult" and not valid_callable_context_result(payload)) or (
            event_type == "diagnosticContextResult" and not valid_diagnostic_context_result(payload)
        ):
            return
        if event_type == "exploreTextResult" and not valid_explore_text_result(payload):
            return
        if (
            event_type == "brailleExploreLineResult"
            and not valid_braille_explore_line_result(payload)
        ):
            return
        if event_type == "numberedChoiceOpened" and not valid_numbered_choice_opened(payload):
            return
        if event_type == "numberedChoiceClosed" and not valid_numbered_choice_closed(payload):
            return
        published = dict(payload)
        published["connection"] = {"neovim": "connected"}
        if event_type in {"copyTextResult", "pasteTextResult", "setRegisterResult"}:
            state = clipboard_result_state(payload)
        elif event_type == "leaveTerminalInputResult":
            state = terminal_control_result_state(payload)
        elif event_type in {"exploreTextResult", "brailleExploreLineResult"}:
            state = exploration_result_state(payload)
        elif event_type in {"callableContextResult", "diagnosticContextResult"}:
            state = developer_context_result_state(payload)
        elif event_type in {"numberedChoiceOpened", "numberedChoiceClosed"}:
            state = numbered_choice_state(payload)
        else:
            state = dict(payload)
        with self._state_lock:
            self._state = state
            self._state["connection"] = {"neovim": "connected"}
            if event_type == "numberedChoiceOpened":
                self._active_numbered_choice = dict(payload)
            elif (
                event_type == "numberedChoiceClosed"
                and self._active_numbered_choice is not None
                and payload.get("choiceId") == self._active_numbered_choice.get("choiceId")
            ):
                self._active_numbered_choice = None
        self.transport.publish(event_type, published)

    def _on_nvim_connection(self, state: str) -> None:
        with self._state_lock:
            self._state["connection"] = {"neovim": state}
            if state == "disconnected":
                self._active_numbered_choice = None
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
        if kind == "exploreTextRequest":
            if valid_explore_text_request(payload):
                self.nvim.notify("nvim_exec_lua", _EXPLORE_TEXT_LUA, [dict(payload)])
            return
        if kind == "endExplorationRequest":
            if valid_end_exploration_request(payload):
                self.nvim.notify("nvim_exec_lua", _END_EXPLORATION_LUA, [dict(payload)])
            return
        if kind == "callableContextRequest":
            if self._supports_plugin_capability("callableContextQuery") and valid_context_request(payload):
                self.nvim.notify("nvim_exec_lua", _CALLABLE_CONTEXT_LUA, [dict(payload)])
            return
        if kind == "diagnosticContextRequest":
            if self._supports_plugin_capability("diagnosticContextQuery") and valid_context_request(payload):
                self.nvim.notify("nvim_exec_lua", _DIAGNOSTIC_CONTEXT_LUA, [dict(payload)])
            return
        if kind == "brailleExploreLineRequest":
            if (
                self._supports_plugin_capability("brailleExploration")
                and valid_braille_explore_line_request(payload)
            ):
                self.nvim.notify("nvim_exec_lua", _BRAILLE_EXPLORE_LINE_LUA, [dict(payload)])
            return
        if kind == "endBrailleExplorationRequest":
            if (
                self._supports_plugin_capability("brailleExploration")
                and valid_end_braille_exploration_request(payload)
            ):
                self.nvim.notify(
                    "nvim_exec_lua",
                    _END_BRAILLE_EXPLORATION_LUA,
                    [dict(payload)],
                )
            return
        if kind == "acceptNumberedChoiceRequest":
            if (
                not self._supports_plugin_capability("numberedChoices")
                or not valid_accept_numbered_choice_request(payload)
            ):
                return
            with self._state_lock:
                choice = (
                    dict(self._active_numbered_choice)
                    if self._active_numbered_choice is not None
                    else None
                )
            if not self._matches_numbered_choice(payload, choice):
                return
            self.nvim.notify("nvim_input", f"{payload['itemIndex'] + 1}\r")
            return
        if kind == "moveBrailleLine":
            if (
                self._supports_plugin_capability("brailleLineNavigation")
                and valid_move_braille_line_request(payload)
            ):
                self.nvim.notify("nvim_exec_lua", _MOVE_BRAILLE_LINE_LUA, [dict(payload)])
            return
        if kind == "brailleRouteAction":
            if (
                self._supports_plugin_capability("brailleRoutingActions")
                and valid_braille_route_action_request(payload)
            ):
                self.nvim.notify("nvim_exec_lua", _BRAILLE_ROUTE_ACTION_LUA, [dict(payload)])
            return
        if kind != "routeCursor":
            return
        if not valid_route_cursor_request(payload):
            return
        self.nvim.notify("nvim_exec_lua", _ROUTE_CURSOR_LUA, [dict(payload)])

    @staticmethod
    def _matches_numbered_choice(
        payload: dict[str, Any],
        choice: dict[str, Any] | None,
    ) -> bool:
        if choice is None:
            return False
        return (
            all(payload.get(field) == choice.get(field) for field in (
                "choiceKind", "choiceId", "bufferId", "windowId", "tabpageId", "changedtick",
            ))
            and payload["itemIndex"] < len(choice.get("items", ()))
        )

    def _supports_plugin_capability(self, capability: str) -> bool:
        with self._state_lock:
            capabilities = self._state.get("pluginCapabilities")
            return isinstance(capabilities, list) and capability in capabilities
