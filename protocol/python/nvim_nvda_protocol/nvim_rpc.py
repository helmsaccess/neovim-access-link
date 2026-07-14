"""Reconnectable Neovim MessagePack-RPC byte source for Unix or loopback TCP."""

from __future__ import annotations

import socket
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import msgpack

from .reconnect import ExponentialBackoff


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


class NvimRpcSource:
    def __init__(
        self,
        endpoint: NvimRpcEndpoint | str,
        on_event: Callable[[str, dict[str, Any]], None],
        on_connection_state: Callable[[str], None],
    ) -> None:
        # A string remains the compatibility shorthand used by the Linux bridge.
        self.endpoint = NvimRpcEndpoint.unix(endpoint) if isinstance(endpoint, str) else endpoint
        if not isinstance(self.endpoint, NvimRpcEndpoint):
            raise ValueError("typed Neovim RPC endpoint is required")
        self.on_event = on_event
        self.on_connection_state = on_connection_state
        self._stop = threading.Event()
        self._socket_lock = threading.Lock()
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._request_id = 0
        self._send_lock = threading.Lock()
        self._unpacker = msgpack.Unpacker(raw=False, strict_map_key=False)
        self._pending_notifications: deque[tuple[str, list[Any]]] = deque()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="nvim-nvda-rpc", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._socket_lock:
            if self._socket is not None:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self._socket.close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                raise RuntimeError("Neovim RPC thread did not stop")

    def _run(self) -> None:
        backoff = ExponentialBackoff()
        while not self._stop.is_set():
            self.on_connection_state("connecting")
            try:
                connection = socket.socket(self.endpoint.family, socket.SOCK_STREAM)
                connection.settimeout(1.0)
                connection.connect(self.endpoint.address)
                connection.settimeout(None)
                with self._socket_lock:
                    self._socket = connection
                self._unpacker = msgpack.Unpacker(raw=False, strict_map_key=False)
                self._pending_notifications.clear()
                channel, _ = self._request("nvim_get_api_info")
                self._request(
                    "nvim_exec_lua",
                    "local p=require('nvim_nvda'); p.setup(); p.register_channel(...)",
                    [channel],
                )
                backoff.reset()
                self.on_connection_state("connected")
                self._notifications_loop()
            except (OSError, EOFError, RuntimeError, msgpack.UnpackException):
                pass
            finally:
                with self._socket_lock:
                    if self._socket is not None:
                        self._socket.close()
                    self._socket = None
            if not self._stop.is_set():
                self.on_connection_state("disconnected")
                self._stop.wait(backoff.next_delay())

    def _send(self, message: list[Any]) -> None:
        assert self._socket is not None
        encoded = msgpack.packb(message, use_bin_type=True)
        with self._send_lock:
            self._socket.sendall(encoded)

    def notify(self, method: str, *parameters: Any) -> bool:
        with self._socket_lock:
            if self._socket is None:
                return False
            try:
                self._send([2, method, list(parameters)])
            except OSError:
                return False
        return True

    def _request(self, method: str, *parameters: Any) -> Any:
        self._request_id += 1
        request_id = self._request_id
        self._send([0, request_id, method, list(parameters)])
        while not self._stop.is_set():
            for message in self._unpacker:
                if message[0] == 2:
                    self._pending_notifications.append((message[1], message[2]))
                elif message[0] == 1 and message[1] == request_id:
                    if message[2] is not None:
                        raise RuntimeError(str(message[2]))
                    return message[3]
            self._feed()
        raise EOFError("stopped")

    def _feed(self) -> None:
        assert self._socket is not None
        data = self._socket.recv(65536)
        if not data:
            raise EOFError("Neovim RPC socket closed")
        self._unpacker.feed(data)

    def _notifications_loop(self) -> None:
        while not self._stop.is_set():
            if self._pending_notifications:
                method, parameters = self._pending_notifications.popleft()
                self._dispatch(method, parameters)
                continue
            for message in self._unpacker:
                if message[0] == 2:
                    self._dispatch(message[1], message[2])
            self._feed()

    def _dispatch(self, method: str, parameters: list[Any]) -> None:
        if method != "nvim_nvda_event" or len(parameters) != 1 or not isinstance(parameters[0], dict):
            return
        event = parameters[0]
        event_type = event.get("type")
        payload = event.get("payload")
        if isinstance(event_type, str) and isinstance(payload, dict):
            self.on_event(event_type, payload)
