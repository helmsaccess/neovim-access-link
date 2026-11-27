"""Reconnectable Neovim MessagePack-RPC byte source for Unix or loopback TCP."""

from __future__ import annotations

import socket
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import msgpack

from .codec import DEFAULT_MAX_FRAME_BYTES
from .reconnect import ExponentialBackoff

_IO_TIMEOUT_SECONDS = 1.0
_REQUEST_TIMEOUT_SECONDS = 2.0
_READ_BYTES = 65_536
_MAX_PENDING_NOTIFICATIONS = 64


@dataclass(frozen=True)
class NvimRpcEndpoint:
    family: int
    address: str | tuple[str, int]

    @classmethod
    def unix(cls, path: str) -> "NvimRpcEndpoint":
        if not isinstance(path, str) or not path:
            raise ValueError("Neovim Unix socket path is required")
        return cls(socket.AF_UNIX, path)

    @classmethod
    def windows_loopback_tcp(cls, host: str, port: int) -> "NvimRpcEndpoint":
        if host != "127.0.0.1":
            raise ValueError("local Neovim TCP must use 127.0.0.1")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError("invalid local Neovim TCP port")
        return cls(socket.AF_INET, (host, port))


class SessionIdentityError(RuntimeError):
    """The selected registry record does not own the connected RPC endpoint."""


class NvimRpcSource:
    def __init__(
        self,
        endpoint: NvimRpcEndpoint,
        on_event: Callable[[str, dict[str, Any]], None],
        on_connection_state: Callable[[str], None],
        expected_session_nonce: str | None = None,
    ) -> None:
        if not isinstance(endpoint, NvimRpcEndpoint):
            raise ValueError("typed Neovim RPC endpoint is required")
        self.endpoint = endpoint
        self.on_event = on_event
        self.on_connection_state = on_connection_state
        if expected_session_nonce is not None and (
            not isinstance(expected_session_nonce, str)
            or len(expected_session_nonce) != 32
            or any(character not in "0123456789abcdef" for character in expected_session_nonce)
        ):
            raise ValueError("invalid expected Neovim session nonce")
        self.expected_session_nonce = expected_session_nonce
        self._stop = threading.Event()
        self._socket_lock = threading.Lock()
        self._socket: socket.socket | None = None
        self._ready = False
        self._thread: threading.Thread | None = None
        self._request_id = 0
        self._send_lock = threading.Lock()
        self._unpacker = self._new_unpacker()
        self._pending_notifications: deque[tuple[str, list[Any]]] = deque()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="nvim-nvda-rpc", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._socket_lock:
            connection = self._socket
            self._socket = None
            self._ready = False
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                raise RuntimeError("Neovim RPC thread did not stop")

    @staticmethod
    def _new_unpacker() -> msgpack.Unpacker:
        return msgpack.Unpacker(
            raw=False, strict_map_key=True, max_buffer_size=DEFAULT_MAX_FRAME_BYTES + _READ_BYTES,
        )

    def _run(self) -> None:
        backoff = ExponentialBackoff()
        while not self._stop.is_set():
            identity_rejected = False
            connection = None
            self.on_connection_state("connecting")
            try:
                connection = socket.socket(self.endpoint.family, socket.SOCK_STREAM)
                connection.settimeout(_IO_TIMEOUT_SECONDS)
                connection.connect(self.endpoint.address)
                with self._socket_lock:
                    if self._stop.is_set():
                        raise EOFError("stopped")
                    self._socket = connection
                self._unpacker = self._new_unpacker()
                self._pending_notifications.clear()
                info = self._request("nvim_get_api_info")
                if not isinstance(info, list) or len(info) != 2 or type(info[0]) is not int or info[0] < 1:
                    raise RuntimeError("invalid Neovim RPC channel information")
                channel = info[0]
                self._verify_session_identity()
                self._request(
                    "nvim_exec_lua",
                    "local p=require('nvim_nvda'); p.setup(); p.register_channel(...)",
                    [channel],
                )
                with self._socket_lock:
                    if self._stop.is_set():
                        raise EOFError("stopped")
                    self._ready = True
                backoff.reset()
                self.on_connection_state("connected")
                self._notifications_loop()
            except SessionIdentityError:
                # A mismatch is definitive for this selected registry record.
                # Reopening the same endpoint would add load without ever
                # making the unauthenticated session safe to use.
                identity_rejected = True
            except (OSError, EOFError, RuntimeError, ValueError, msgpack.UnpackException):
                pass
            finally:
                with self._socket_lock:
                    self._socket = None
                    self._ready = False
                if connection is not None:
                    connection.close()
            if not self._stop.is_set():
                self.on_connection_state("disconnected")
                if identity_rejected:
                    break
                self._stop.wait(backoff.next_delay())

    def _verify_session_identity(self) -> None:
        """Authenticate the selected registry entry on this permanent channel."""
        if self.expected_session_nonce is None:
            return
        actual = self._request(
            "nvim_exec_lua",
            "return require('nvim_nvda.session').identity()",
            [],
        )
        if actual != self.expected_session_nonce:
            raise SessionIdentityError("Neovim session identity mismatch")

    def _send(self, message: list[Any], connection: socket.socket | None = None) -> None:
        if connection is None:
            connection = self._socket
        if connection is None:
            raise EOFError("Neovim RPC socket is not connected")
        encoded = msgpack.packb(message, use_bin_type=True)
        with self._send_lock:
            connection.sendall(encoded)

    def notify(self, method: str, *parameters: Any) -> bool:
        with self._socket_lock:
            connection = self._socket if self._ready else None
        if connection is None:
            return False
        try:
            self._send([2, method, list(parameters)], connection)
        except (OSError, EOFError):
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return False
        return True

    def _request(self, method: str, *parameters: Any) -> Any:
        deadline = time.monotonic() + _REQUEST_TIMEOUT_SECONDS
        self._request_id += 1
        request_id = self._request_id
        self._send([0, request_id, method, list(parameters)])
        while not self._stop.is_set() and time.monotonic() < deadline:
            for message in self._messages():
                if message[0] == 2:
                    if len(self._pending_notifications) >= _MAX_PENDING_NOTIFICATIONS:
                        raise RuntimeError("too many notifications during Neovim RPC setup")
                    self._pending_notifications.append((message[1], message[2]))
                elif message[0] == 1 and message[1] == request_id:
                    if message[2] is not None:
                        raise RuntimeError(str(message[2]))
                    return message[3]
            self._feed()
        raise TimeoutError("Neovim RPC request did not complete")

    def _messages(self) -> Iterator[list[Any]]:
        for message in self._unpacker:
            if not isinstance(message, list) or not message or type(message[0]) is not int:
                raise RuntimeError("invalid Neovim RPC message")
            kind = message[0]
            if kind == 2 and len(message) == 3 and isinstance(message[1], str) and isinstance(message[2], list):
                yield message
            elif kind in (0, 1) and len(message) == 4 and type(message[1]) is int:
                yield message
            else:
                raise RuntimeError("invalid Neovim RPC message")

    def _feed(self) -> None:
        connection = self._socket
        if connection is None:
            raise EOFError("Neovim RPC socket is not connected")
        data = connection.recv(_READ_BYTES)
        if not data:
            raise EOFError("Neovim RPC socket closed")
        self._unpacker.feed(data)

    def _notifications_loop(self) -> None:
        while not self._stop.is_set():
            if self._pending_notifications:
                method, parameters = self._pending_notifications.popleft()
                self._dispatch(method, parameters)
                continue
            for message in self._messages():
                if message[0] == 2:
                    self._dispatch(message[1], message[2])
            try:
                self._feed()
            except TimeoutError:
                continue

    def _dispatch(self, method: str, parameters: list[Any]) -> None:
        if method != "nvim_nvda_event" or len(parameters) != 1 or not isinstance(parameters[0], dict):
            return
        event = parameters[0]
        event_type = event.get("type")
        payload = event.get("payload")
        if isinstance(event_type, str) and isinstance(payload, dict):
            self.on_event(event_type, payload)
