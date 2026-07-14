"""Length-prefixed MessagePack framing with strict resource limits."""

from __future__ import annotations

import struct
from collections.abc import Mapping
from typing import Any

import msgpack

PROTOCOL_VERSION = 2
DEFAULT_MAX_FRAME_BYTES = 1_048_576
_HEADER = struct.Struct(">I")
_REQUIRED = frozenset(
    {"protocolVersion", "sessionId", "sequence", "timestampMonotonic", "type", "payload"}
)


class ProtocolError(ValueError):
    """Raised for malformed, incompatible, or oversized protocol data."""


def _validate(message: Mapping[str, Any]) -> None:
    missing = _REQUIRED.difference(message)
    if missing:
        raise ProtocolError(f"missing required fields: {', '.join(sorted(missing))}")
    if message["protocolVersion"] != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version: {message['protocolVersion']!r}")
    if not isinstance(message["sessionId"], str) or not message["sessionId"]:
        raise ProtocolError("sessionId must be a non-empty string")
    if not isinstance(message["sequence"], int) or message["sequence"] < 0:
        raise ProtocolError("sequence must be a non-negative integer")
    if not isinstance(message["timestampMonotonic"], int) or message["timestampMonotonic"] < 0:
        raise ProtocolError("timestampMonotonic must be a non-negative integer")
    if not isinstance(message["type"], str) or not message["type"]:
        raise ProtocolError("type must be a non-empty string")
    if not isinstance(message["payload"], Mapping):
        raise ProtocolError("payload must be a map")


def encode_frame(message: Mapping[str, Any], max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> bytes:
    """Validate and encode one message with a four-byte network-order length."""
    _validate(message)
    payload = msgpack.packb(dict(message), use_bin_type=True)
    if len(payload) > max_frame_bytes:
        raise ProtocolError(f"frame exceeds {max_frame_bytes} bytes")
    return _HEADER.pack(len(payload)) + payload


class FrameDecoder:
    """Incrementally decode arbitrarily chunked framed messages."""

    def __init__(self, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> None:
        self._buffer = bytearray()
        self._max_frame_bytes = max_frame_bytes

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        self._buffer.extend(data)
        messages: list[dict[str, Any]] = []
        while len(self._buffer) >= _HEADER.size:
            (size,) = _HEADER.unpack_from(self._buffer)
            if size > self._max_frame_bytes:
                self._buffer.clear()
                raise ProtocolError(f"declared frame exceeds {self._max_frame_bytes} bytes")
            end = _HEADER.size + size
            if len(self._buffer) < end:
                break
            raw = bytes(self._buffer[_HEADER.size:end])
            del self._buffer[:end]
            try:
                decoded = msgpack.unpackb(raw, raw=False, strict_map_key=True)
            except (ValueError, msgpack.UnpackException) as error:
                raise ProtocolError("invalid MessagePack payload") from error
            if not isinstance(decoded, dict):
                raise ProtocolError("top-level value must be a map")
            _validate(decoded)
            messages.append(decoded)
        return messages
