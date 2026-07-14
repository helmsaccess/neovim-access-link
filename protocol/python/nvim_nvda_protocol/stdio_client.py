"""Reconnectable SSH subprocess client for the bridge stdio transport."""

from __future__ import annotations

import os
import subprocess
import threading
from collections.abc import Callable
from typing import Any

from .codec import FrameDecoder, ProtocolError, encode_frame
from .messages import MessageFactory
from .reconnect import ExponentialBackoff
from .session import SessionTracker

STDIO_MARKER = b"NVIM-NVDA-STDIO/2\n"


class SshStdioClient:
    def __init__(self, ssh_target: str, on_event: Callable[[dict[str, Any]], None],
                 on_connection_state: Callable[[str], None],
                 on_diagnostic: Callable[[str, dict[str, Any]], None] | None = None,
                 ssh_port: int = 22, identity_file: str = "", session_id: str = "",
                 password: str = "", askpass_path: str = "") -> None:
        if not ssh_target or ssh_target.startswith("-") or any(ch.isspace() for ch in ssh_target):
            raise ValueError("invalid SSH target")
        self.ssh_target = ssh_target
        if not isinstance(ssh_port, int) or isinstance(ssh_port, bool) or not 1 <= ssh_port <= 65535:
            raise ValueError("invalid SSH port")
        if identity_file and (
            not isinstance(identity_file, str) or identity_file.startswith("-")
            or "\r" in identity_file or "\n" in identity_file or "\0" in identity_file
        ):
            raise ValueError("invalid SSH identity file")
        self.ssh_port = ssh_port
        self.identity_file = identity_file
        if session_id and (not isinstance(session_id, str) or not session_id.isascii() or not session_id.isdigit()):
            raise ValueError("invalid Neovim session id")
        self.session_id = session_id
        if password and (not isinstance(password, str) or "\0" in password):
            raise ValueError("invalid SSH password")
        if password and (not askpass_path or not isinstance(askpass_path, str)):
            raise ValueError("SSH askpass helper is required for password authentication")
        self.password = password
        self.askpass_path = askpass_path
        self.on_event = on_event
        self.on_connection_state = on_connection_state
        self.on_diagnostic = on_diagnostic or (lambda _category, _fields: None)
        self._stop = threading.Event()
        self._process_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._factory = MessageFactory()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="nvim-nvda-ssh-stdio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._process_lock:
            process = self._process
        if process is not None:
            try:
                if process.stdin:
                    process.stdin.close()
            except OSError:
                pass
            try:
                process.terminate()
                process.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                except OSError:
                    pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                raise RuntimeError("SSH stdio client thread did not stop")

    def send_control(self, kind: str, payload: dict[str, Any]) -> bool:
        with self._process_lock:
            process = self._process
        if process is None or process.poll() is not None or process.stdin is None:
            self.on_diagnostic("controlRejected", {"type": kind, "reason": "notConnected"})
            return False
        try:
            frame = encode_frame(self._factory.create(kind, payload))
            with self._write_lock:
                process.stdin.write(frame)
                process.stdin.flush()
            return True
        except (BrokenPipeError, OSError, ValueError):
            return False

    def _run(self) -> None:
        backoff = ExponentialBackoff()
        while not self._stop.is_set():
            self.on_connection_state("connecting")
            command = self._build_command()
            self.on_diagnostic("sshProcessStart", {"target": self.ssh_target})
            try:
                process = subprocess.Popen(
                    command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    env=self._build_environment(),
                )
                with self._process_lock:
                    self._process = process
                threading.Thread(target=self._read_stderr, args=(process,), daemon=True).start()
                self._receive(process)
                self.on_diagnostic("sshProcessExit", {"returnCode": process.wait(timeout=2.0)})
            except (OSError, ProtocolError, subprocess.TimeoutExpired) as error:
                self.on_diagnostic("sshProcessError", {"errorType": type(error).__name__, "error": str(error)})
            finally:
                with self._process_lock:
                    self._process = None
            if not self._stop.is_set():
                self.on_connection_state("disconnected")
                self._stop.wait(backoff.next_delay())

    def _build_command(self) -> list[str]:
        batch_mode = "no" if self.password else "yes"
        command = [
                "ssh.exe", "-T", "-o", f"BatchMode={batch_mode}", "-o", "ConnectTimeout=10",
                "-o", "ClearAllForwardings=yes",
                "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
        ]
        if self.password:
            command.extend((
                "-o", "PreferredAuthentications=keyboard-interactive,password",
                "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1",
            ))
        if self.ssh_port != 22:
            command.extend(("-p", str(self.ssh_port)))
        if self.identity_file:
            command.extend(("-i", self.identity_file))
        remote_command = "$HOME/.local/bin/nvim-nvda-bridge"
        if self.session_id:
            remote_command += f" --session {self.session_id}"
        command.extend((self.ssh_target, remote_command))
        return command

    def _build_environment(self) -> dict[str, str] | None:
        if not self.password:
            return None
        environment = os.environ.copy()
        environment.update({
            "SSH_ASKPASS": self.askpass_path,
            "SSH_ASKPASS_REQUIRE": "force",
            "DISPLAY": environment.get("DISPLAY", "nvim-nvda"),
            "NVIM_NVDA_SSH_PASSWORD": self.password,
        })
        return environment

    def _receive(self, process: subprocess.Popen) -> None:
        assert process.stdout is not None
        prefix = bytearray()
        while not self._stop.is_set() and STDIO_MARKER not in prefix:
            data = process.stdout.read(1)
            if not data:
                raise ConnectionResetError("SSH closed before stdio protocol marker")
            prefix.extend(data)
            if len(prefix) > 65_536:
                raise ProtocolError("stdio marker not found within startup output limit")
        marker_end = prefix.index(STDIO_MARKER) + len(STDIO_MARKER)
        decoder = FrameDecoder()
        tracker = SessionTracker()
        authenticated = False
        pending = bytes(prefix[marker_end:])
        while not self._stop.is_set():
            data = pending or self._read_pipe(process.stdout)
            pending = b""
            if not data:
                raise ConnectionResetError("SSH stdio bridge closed")
            for event in decoder.feed(data):
                disposition = tracker.observe(event)
                if disposition == "accept":
                    if not authenticated:
                        if event["type"] != "fullState":
                            raise ProtocolError("first stdio event must be fullState")
                        authenticated = True
                        self.on_connection_state("connected")
                    if event["type"] != "heartbeat":
                        self.on_event(event)
                elif disposition == "resyncRequired":
                    self.send_control("requestFullState", {})

    @staticmethod
    def _read_pipe(stream) -> bytes:
        read1 = getattr(stream, "read1", None)
        if read1 is not None:
            return read1(65_536)
        return stream.read(65_536)

    def _read_stderr(self, process: subprocess.Popen) -> None:
        if process.stderr is None:
            return
        while not self._stop.is_set():
            line = process.stderr.readline()
            if not line:
                return
            # This is process diagnostics, not editor text.  Use a dedicated
            # field so privacy redaction does not hide actionable SSH/bridge
            # errors such as a missing executable or session selection issue.
            self.on_diagnostic("sshStderr", {
                "stderrLine": line.decode("utf-8", "replace").rstrip()[-1000:],
            })
