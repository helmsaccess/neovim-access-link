"""NVDA-independent protocol core for structured Neovim accessibility."""

from .codec import FrameDecoder, ProtocolError, encode_frame
from .messages import MessageFactory
from .local_client import LocalTcpClient
from .nvim_rpc import NvimRpcEndpoint, NvimRpcSource
from .reconnect import ExponentialBackoff
from .session import SessionTracker
from .stdio_client import SshStdioClient
from .text import CursorText, InvalidByteColumn, cursor_text, utf16_column

__all__ = [
    "CursorText",
    "ExponentialBackoff",
    "FrameDecoder",
    "InvalidByteColumn",
    "MessageFactory",
    "LocalTcpClient",
    "NvimRpcEndpoint",
    "NvimRpcSource",
    "ProtocolError",
    "SessionTracker",
    "SshStdioClient",
    "cursor_text",
    "encode_frame",
    "utf16_column",
]
