"""NVDA-independent protocol core for structured Neovim accessibility."""

from .codec import FrameDecoder, ProtocolError, encode_frame
from .braille_navigation import (
    BRAILLE_LINE_DIRECTIONS,
    MAX_VIRTUAL_COLUMN,
    valid_move_braille_line_request,
)
from .braille_exploration import (
    valid_braille_explore_line_request,
    valid_braille_explore_line_result,
    valid_end_braille_exploration_request,
)
from .braille_routing_actions import (
    LINE_ACTIONS,
    LINE_STARTS,
    WORD_ACTIONS,
    valid_braille_route_action_request,
)
from .clipboard import (
    COPY_TEXT_SOURCES,
    MAX_CLIPBOARD_TEXT_BYTES,
    clipboard_result_state,
    valid_clipboard_text,
    valid_copy_text_request,
    valid_paste_text_request,
    valid_request_id,
    valid_set_register_request,
)
from .cursor_routing import (
    MAX_COMMAND_LINE_BYTES,
    MAX_MODE_RAW_BYTES,
    valid_route_cursor_request,
)
from .exploration import (
    EXPLORATION_ACTIONS,
    EXPLORATION_UNITS,
    MAX_EXPLORATION_TEXT_BYTES,
    exploration_result_state,
    valid_end_exploration_request,
    valid_explore_text_request,
    valid_explore_text_result,
)
from .messages import MessageFactory
from .numbered_choice import (
    MAX_NUMBERED_CHOICE_ITEM_BYTES,
    MAX_NUMBERED_CHOICE_ITEMS,
    NUMBERED_CHOICE_KINDS,
    numbered_choice_state,
    valid_accept_numbered_choice_request,
    valid_numbered_choice_closed,
    valid_numbered_choice_opened,
)
from .local_client import LocalTcpClient
from .nvim_rpc import NvimRpcEndpoint, NvimRpcSource
from .reconnect import ExponentialBackoff
from .session import SessionTracker
from .stdio_client import SshStdioClient
from .terminal_control import (
    terminal_control_result_state, valid_leave_terminal_input_request,
)
from .text import CursorText, InvalidByteColumn, cursor_text, utf16_column

__all__ = [
    "CursorText",
    "BRAILLE_LINE_DIRECTIONS",
    "COPY_TEXT_SOURCES",
    "ExponentialBackoff",
    "EXPLORATION_ACTIONS",
    "EXPLORATION_UNITS",
    "FrameDecoder",
    "InvalidByteColumn",
    "MessageFactory",
    "MAX_CLIPBOARD_TEXT_BYTES",
    "MAX_COMMAND_LINE_BYTES",
    "MAX_EXPLORATION_TEXT_BYTES",
    "MAX_NUMBERED_CHOICE_ITEM_BYTES",
    "MAX_NUMBERED_CHOICE_ITEMS",
    "MAX_MODE_RAW_BYTES",
    "MAX_VIRTUAL_COLUMN",
    "NUMBERED_CHOICE_KINDS",
    "LocalTcpClient",
    "LINE_ACTIONS",
    "LINE_STARTS",
    "NvimRpcEndpoint",
    "NvimRpcSource",
    "ProtocolError",
    "SessionTracker",
    "SshStdioClient",
    "WORD_ACTIONS",
    "cursor_text",
    "clipboard_result_state",
    "encode_frame",
    "exploration_result_state",
    "numbered_choice_state",
    "utf16_column",
    "terminal_control_result_state",
    "valid_clipboard_text",
    "valid_copy_text_request",
    "valid_route_cursor_request",
    "valid_accept_numbered_choice_request",
    "valid_braille_explore_line_request",
    "valid_braille_explore_line_result",
    "valid_braille_route_action_request",
    "valid_end_exploration_request",
    "valid_end_braille_exploration_request",
    "valid_explore_text_request",
    "valid_explore_text_result",
    "valid_paste_text_request",
    "valid_request_id",
    "valid_set_register_request",
    "valid_leave_terminal_input_request",
    "valid_move_braille_line_request",
    "valid_numbered_choice_closed",
    "valid_numbered_choice_opened",
]
