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
    "FrameDecoder",
    "InvalidByteColumn",
    "MessageFactory",
    "MAX_CLIPBOARD_TEXT_BYTES",
    "LocalTcpClient",
    "NvimRpcEndpoint",
    "NvimRpcSource",
    "ProtocolError",
    "SessionTracker",
    "SshStdioClient",
    "cursor_text",
    "clipboard_result_state",
    "encode_frame",
    "utf16_column",
    "terminal_control_result_state",
    "valid_clipboard_text",
    "valid_copy_text_request",
    "valid_paste_text_request",
    "valid_request_id",
    "valid_set_register_request",
    "valid_leave_terminal_input_request",
]
