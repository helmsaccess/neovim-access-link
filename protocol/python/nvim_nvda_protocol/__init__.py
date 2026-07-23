"""NVDA-independent protocol core for structured Neovim accessibility."""

from .codec import FrameDecoder, ProtocolError, encode_frame
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
    "COPY_TEXT_SOURCES",
    "ExponentialBackoff",
    "EXPLORATION_ACTIONS",
    "EXPLORATION_UNITS",
    "FrameDecoder",
    "InvalidByteColumn",
    "MessageFactory",
    "MAX_CLIPBOARD_TEXT_BYTES",
    "MAX_EXPLORATION_TEXT_BYTES",
    "LocalTcpClient",
    "NvimRpcEndpoint",
    "NvimRpcSource",
    "ProtocolError",
    "SessionTracker",
    "SshStdioClient",
    "cursor_text",
    "clipboard_result_state",
    "encode_frame",
    "exploration_result_state",
    "utf16_column",
    "terminal_control_result_state",
    "valid_clipboard_text",
    "valid_copy_text_request",
    "valid_end_exploration_request",
    "valid_explore_text_request",
    "valid_explore_text_result",
    "valid_paste_text_request",
    "valid_request_id",
    "valid_set_register_request",
    "valid_leave_terminal_input_request",
]
