"""Direct local Windows Neovim client over an IPv4 loopback RPC socket."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from .codec import ProtocolError, encode_frame
from .braille_navigation import valid_move_braille_line_request
from .braille_exploration import (
	valid_braille_explore_line_request,
	valid_braille_explore_line_result,
	valid_end_braille_exploration_request,
)
from .braille_routing_actions import valid_braille_route_action_request
from .clipboard import (
	clipboard_result_state,
	valid_copy_text_request,
	valid_paste_text_request,
	valid_set_register_request,
)
from .cursor_routing import valid_route_cursor_request
from .developer_context import (
	developer_context_result_state,
	valid_callable_context_result,
	valid_context_request,
	valid_diagnostic_context_result,
)
from .exploration import (
	exploration_result_state,
	valid_end_exploration_request,
	valid_explore_text_request,
	valid_explore_text_result,
)
from .messages import MessageFactory
from .numbered_choice import (
	numbered_choice_state,
	valid_accept_numbered_choice_request,
	valid_numbered_choice_closed,
	valid_numbered_choice_opened,
)
from .nvim_rpc import NvimRpcEndpoint, NvimRpcSource
from .terminal_control import (
	terminal_control_result_state,
	valid_leave_terminal_input_request,
)


_ROUTE_CURSOR_LUA = "return require('nvim_nvda').request_route_cursor(...)"
_BRAILLE_ROUTE_ACTION_LUA = "return require('nvim_nvda').request_braille_route_action(...)"
_MOVE_BRAILLE_LINE_LUA = "return require('nvim_nvda').request_move_braille_line(...)"
_BRAILLE_EXPLORE_LINE_LUA = "return require('nvim_nvda').request_braille_explore_line(...)"
_END_BRAILLE_EXPLORATION_LUA = (
	"return require('nvim_nvda').request_end_braille_exploration(...)"
)

_COPY_TEXT_LUA = "return require('nvim_nvda').request_copy_text(...)"
_PASTE_TEXT_LUA = "return require('nvim_nvda').request_paste_text(...)"
_SET_REGISTER_LUA = "return require('nvim_nvda').request_set_register(...)"
_LEAVE_TERMINAL_INPUT_LUA = "return require('nvim_nvda').request_leave_terminal_input(...)"
_EXPLORE_TEXT_LUA = "return require('nvim_nvda').request_explore_text(...)"
_END_EXPLORATION_LUA = "return require('nvim_nvda').request_end_exploration(...)"
_CALLABLE_CONTEXT_LUA = "return require('nvim_nvda').request_callable_context(...)"
_DIAGNOSTIC_CONTEXT_LUA = "return require('nvim_nvda').request_diagnostic_context(...)"


class LocalTcpClient:
	capabilities = (
		"resync",
		"semanticEvents",
		"cursorRouting",
		"accessibleMenus",
		"focusContext",
		"clipboardTransfer",
		"terminalControl",
	)

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
		self._active_numbered_choice: dict[str, Any] | None = None
		self._authenticated = False
		self._source = source_factory(
			self.endpoint,
			self._on_nvim_event,
			self._on_nvim_connection,
			session_nonce,
		)

	def start(self) -> None:
		self.on_diagnostic(
			"localTcpStart",
			{
				"host": self.endpoint.address[0],
				"port": self.endpoint.address[1],
			},
		)
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
		if kind == "requestFocusContext":
			request_id = payload.get("requestId") if isinstance(payload, dict) else None
			if not self._valid_request_id(request_id):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			with self._state_lock:
				state = dict(self._state) if self._state is not None else None
			if state is None:
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "notConnected"})
				return False
			state["_focusRequestId"] = request_id
			return self._publish("focusContext", state)
		if kind == "copyTextRequest":
			if not valid_copy_text_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _COPY_TEXT_LUA, [dict(payload)])
		if kind == "pasteTextRequest":
			if not valid_paste_text_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _PASTE_TEXT_LUA, [dict(payload)])
		if kind == "setRegisterRequest":
			if not valid_set_register_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _SET_REGISTER_LUA, [dict(payload)])
		if kind == "leaveTerminalInputRequest":
			if not valid_leave_terminal_input_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify(
				"nvim_exec_lua",
				_LEAVE_TERMINAL_INPUT_LUA,
				[dict(payload)],
			)
		if kind == "exploreTextRequest":
			if not self._supports_plugin_capability("exploration"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_explore_text_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _EXPLORE_TEXT_LUA, [dict(payload)])
		if kind == "endExplorationRequest":
			if not self._supports_plugin_capability("exploration"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_end_exploration_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _END_EXPLORATION_LUA, [dict(payload)])
		if kind == "callableContextRequest":
			if not self._supports_plugin_capability("callableContextQuery"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_context_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _CALLABLE_CONTEXT_LUA, [dict(payload)])
		if kind == "diagnosticContextRequest":
			if not self._supports_plugin_capability("diagnosticContextQuery"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_context_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify(
				"nvim_exec_lua",
				_DIAGNOSTIC_CONTEXT_LUA,
				[dict(payload)],
			)
		if kind == "brailleExploreLineRequest":
			if not self._supports_plugin_capability("brailleExploration"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_braille_explore_line_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify(
				"nvim_exec_lua",
				_BRAILLE_EXPLORE_LINE_LUA,
				[dict(payload)],
			)
		if kind == "endBrailleExplorationRequest":
			if not self._supports_plugin_capability("brailleExploration"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_end_braille_exploration_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify(
				"nvim_exec_lua",
				_END_BRAILLE_EXPLORATION_LUA,
				[dict(payload)],
			)
		if kind == "acceptNumberedChoiceRequest":
			if not self._supports_plugin_capability("numberedChoices"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_accept_numbered_choice_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			with self._state_lock:
				choice = (
					dict(self._active_numbered_choice)
					if self._active_numbered_choice is not None
					else None
				)
			if not self._matches_numbered_choice(payload, choice):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "staleState"})
				return False
			return self._source.notify("nvim_input", f"{payload['itemIndex'] + 1}\r")
		if kind == "moveBrailleLine":
			if not self._supports_plugin_capability("brailleLineNavigation"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_move_braille_line_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify("nvim_exec_lua", _MOVE_BRAILLE_LINE_LUA, [dict(payload)])
		if kind == "brailleRouteAction":
			if not self._supports_plugin_capability("brailleRoutingActions"):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "capabilityMissing"})
				return False
			if not valid_braille_route_action_request(payload):
				self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
				return False
			return self._source.notify(
				"nvim_exec_lua",
				_BRAILLE_ROUTE_ACTION_LUA,
				[dict(payload)],
			)
		if kind != "routeCursor" or not valid_route_cursor_request(payload):
			self.on_diagnostic("controlRejected", {"type": kind, "reason": "invalidControl"})
			return False
		return self._source.notify("nvim_exec_lua", _ROUTE_CURSOR_LUA, [dict(payload)])

	@staticmethod
	def _valid_request_id(value: Any) -> bool:
		return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2_147_483_647

	def _on_nvim_event(self, event_type: str, payload: dict[str, Any]) -> None:
		if (event_type == "callableContextResult" and not valid_callable_context_result(payload)) or (
			event_type == "diagnosticContextResult" and not valid_diagnostic_context_result(payload)
		):
			self.on_diagnostic(
				"localEventRejected",
				{
					"type": event_type,
					"errorType": "ProtocolError",
					"error": "invalid developer context result",
				},
			)
			return
		if event_type == "exploreTextResult" and not valid_explore_text_result(payload):
			self.on_diagnostic(
				"localEventRejected",
				{
					"type": event_type,
					"errorType": "ProtocolError",
					"error": "invalid exploration result",
				},
			)
			return
		if (
			event_type == "brailleExploreLineResult"
			and not valid_braille_explore_line_result(payload)
		):
			self.on_diagnostic(
				"localEventRejected",
				{
					"type": event_type,
					"errorType": "ProtocolError",
					"error": "invalid Braille exploration result",
				},
			)
			return
		if event_type == "numberedChoiceOpened" and not valid_numbered_choice_opened(payload):
			self.on_diagnostic(
				"localEventRejected",
				{"type": event_type, "errorType": "ProtocolError", "error": "invalid numbered choice"},
			)
			return
		if event_type == "numberedChoiceClosed" and not valid_numbered_choice_closed(payload):
			self.on_diagnostic(
				"localEventRejected",
				{"type": event_type, "errorType": "ProtocolError", "error": "invalid numbered choice"},
			)
			return
		state = dict(payload)
		event = self._validated_event(event_type, state)
		if event is None:
			return
		if event_type in {"copyTextResult", "pasteTextResult", "setRegisterResult"}:
			state = clipboard_result_state(state)
		elif event_type == "leaveTerminalInputResult":
			state = terminal_control_result_state(state)
		elif event_type in {"exploreTextResult", "brailleExploreLineResult"}:
			state = exploration_result_state(state)
		elif event_type in {"callableContextResult", "diagnosticContextResult"}:
			state = developer_context_result_state(state)
		elif event_type in {"numberedChoiceOpened", "numberedChoiceClosed"}:
			state = numbered_choice_state(state)
		with self._state_lock:
			self._state = state
			if event_type == "numberedChoiceOpened":
				self._active_numbered_choice = dict(payload)
			elif (
				event_type == "numberedChoiceClosed"
				and self._active_numbered_choice is not None
				and payload.get("choiceId") == self._active_numbered_choice.get("choiceId")
			):
				self._active_numbered_choice = None
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
		self,
		event_type: str,
		payload: dict[str, Any],
	) -> dict[str, Any] | None:
		value = dict(payload)
		if event_type == "fullState":
			capabilities = list(self.capabilities)
			if self._payload_supports(value, "exploration"):
				capabilities.append("exploration")
			if self._payload_supports(value, "numberedChoices"):
				capabilities.append("numberedChoices")
			if self._payload_supports(value, "brailleLineNavigation"):
				capabilities.append("brailleLineNavigation")
			if self._payload_supports(value, "brailleExploration"):
				capabilities.append("brailleExploration")
			if self._payload_supports(value, "brailleRoutingActions"):
				capabilities.append("brailleRoutingActions")
			if self._payload_supports(value, "callableContextQuery"):
				capabilities.append("callableContextQuery")
			if self._payload_supports(value, "diagnosticContextQuery"):
				capabilities.append("diagnosticContextQuery")
			if self._payload_supports(value, "diagnosticCursorSummary"):
				capabilities.append("diagnosticCursorSummary")
			value["_transport"] = {
				"capabilities": capabilities,
				"kind": "windows-loopback-tcp",
			}
		try:
			event = self._factory.create(event_type, value)
			encode_frame(event)  # Reuse v2 type and resource validation without SSH framing.
		except (ProtocolError, TypeError, ValueError) as error:
			self.on_diagnostic(
				"localEventRejected",
				{
					"type": event_type,
					"errorType": type(error).__name__,
					"error": str(error),
				},
			)
			return None
		return event

	def _supports_plugin_capability(self, capability: str) -> bool:
		with self._state_lock:
			state = self._state
			return state is not None and self._payload_supports(state, capability)

	@staticmethod
	def _payload_supports(payload: dict[str, Any], capability: str) -> bool:
		capabilities = payload.get("pluginCapabilities")
		return isinstance(capabilities, list) and capability in capabilities

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

	def _on_nvim_connection(self, state: str) -> None:
		if state == "connected":
			# Authentication for the accessibility layer begins with fullState,
			# matching the SSH client rather than the raw RPC socket state.
			return
		if state == "disconnected":
			self._authenticated = False
			with self._state_lock:
				self._state = None
				self._active_numbered_choice = None
		self.on_connection_state(state)
