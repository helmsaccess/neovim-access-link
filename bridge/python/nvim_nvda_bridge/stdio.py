"""SSH-friendly framed transport over standard input and output."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any, BinaryIO

from nvim_nvda_protocol import (
    FrameDecoder, MessageFactory, ProtocolError, encode_frame,
    valid_copy_text_request, valid_paste_text_request,
    valid_set_register_request, valid_leave_terminal_input_request,
)


STDIO_MARKER = b"NVIM-NVDA-STDIO/2\n"


class StdioTransport:
    """Expose one bridge session through pipes owned by an SSH process."""

    capabilities = (
        "heartbeat", "resync", "semanticEvents", "cursorRouting", "accessibleMenus",
        "focusContext", "clipboardTransfer", "terminalControl",
    )

    def __init__(
        self,
        full_state: Callable[[], dict[str, Any]],
        input_stream: BinaryIO,
        output_stream: BinaryIO,
        on_control: Callable[[str, dict[str, Any]], None] | None = None,
        heartbeat_seconds: float = 1.0,
    ) -> None:
        self._full_state = full_state
        self._input = input_stream
        self._output = output_stream
        self.on_control = on_control or (lambda _kind, _payload: None)
        self.heartbeat_seconds = heartbeat_seconds
        self.closed = threading.Event()
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._factory = MessageFactory()
        self._session_ready = threading.Event()
        self._reader: threading.Thread | None = None
        self._heartbeat: threading.Thread | None = None

    def start(self) -> None:
        with self._write_lock:
            self._output.write(STDIO_MARKER)
            self._output.flush()
        self._reader = threading.Thread(target=self._read_controls, name="nvim-nvda-stdio-reader", daemon=True)
        self._heartbeat = threading.Thread(target=self._send_heartbeats, name="nvim-nvda-stdio-heartbeat", daemon=True)
        self._reader.start()
        self._heartbeat.start()

    def publish(self, event_type: str, payload: dict[str, Any]) -> bool:
        if self._stop.is_set():
            return False
        if not self._session_ready.is_set():
            if event_type != "fullState":
                return False
            self._session_ready.set()
        if event_type == "fullState":
            payload = self._state_with_capabilities(payload)
        try:
            frame = encode_frame(self._factory.create(event_type, payload))
            with self._write_lock:
                self._output.write(frame)
                self._output.flush()
        except (BrokenPipeError, OSError, ValueError):
            self.closed.set()
            self._stop.set()
            return False
        return True

    def stop(self) -> None:
        self._stop.set()
        self.closed.set()
        if self._heartbeat is not None:
            self._heartbeat.join(timeout=2.0)
        # A blocked stdin read is a daemon thread and ends with this short-lived
        # process. Closing fd 0 wakes real pipes, but BytesIO used by tests has
        # already reached EOF and needs no special handling.
        try:
            if hasattr(self._input, "fileno"):
                os.close(self._input.fileno())
        except (OSError, ValueError):
            pass
        if self._reader is not None:
            self._reader.join(timeout=0.2)
        try:
            self._input.close()
        except OSError:
            pass

    def _read_controls(self) -> None:
        decoder = FrameDecoder()
        try:
            while not self._stop.is_set():
                read1 = getattr(self._input, "read1", None)
                data = read1(65536) if read1 is not None else self._input.read(65536)
                if not data:
                    break
                for control in decoder.feed(data):
                    kind = control["type"]
                    if kind == "requestFullState":
                        self.publish("fullState", self._full_state())
                    elif kind == "requestFocusContext":
                        payload = control.get("payload", {})
                        request_id = payload.get("requestId") if isinstance(payload, dict) else None
                        if self._valid_request_id(request_id):
                            state = dict(self._full_state())
                            state["_focusRequestId"] = request_id
                            self.publish("focusContext", state)
                    elif kind == "routeCursor":
                        self.on_control(kind, dict(control["payload"]))
                    elif kind == "copyTextRequest" and valid_copy_text_request(control.get("payload")):
                        self.on_control(kind, dict(control["payload"]))
                    elif kind == "pasteTextRequest" and valid_paste_text_request(control.get("payload")):
                        self.on_control(kind, dict(control["payload"]))
                    elif kind == "setRegisterRequest" and valid_set_register_request(control.get("payload")):
                        self.on_control(kind, dict(control["payload"]))
                    elif (
                        kind == "leaveTerminalInputRequest"
                        and valid_leave_terminal_input_request(control.get("payload"))
                    ):
                        self.on_control(kind, dict(control["payload"]))
        except (OSError, ProtocolError):
            pass
        finally:
            self.closed.set()
            self._stop.set()

    def _send_heartbeats(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            if self._session_ready.is_set() and not self.publish("heartbeat", {}):
                return

    def _state_with_capabilities(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        result = dict(self._full_state() if state is None else state)
        result["_transport"] = {"capabilities": list(self.capabilities), "kind": "ssh-stdio"}
        return result

    @staticmethod
    def _valid_request_id(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2_147_483_647
