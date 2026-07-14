"""Discover local Windows Neovim sessions registered by the Lua plugin."""

from __future__ import annotations

import json
import math
import os
import pathlib
import time
from dataclasses import dataclass
from typing import Any, Callable

LOCAL_SESSION_MAX_BYTES = 65_536


@dataclass(frozen=True)
class LocalWindowsSession:
    identifier: str
    name: str
    cwd: str
    host: str
    port: int
    pid: int
    started_unix: int = 0
    claim_age_ms: int = -1
    claimed_monotonic_ns: int = 0
    claim_sequence: int = 0


def local_registry_directory(environment: dict[str, str] | None = None) -> pathlib.Path:
    values = os.environ if environment is None else environment
    root = values.get("LOCALAPPDATA", "")
    if not isinstance(root, str) or not root or "\0" in root:
        raise RuntimeError("LOCALAPPDATA is unavailable for local Neovim discovery")
    return pathlib.Path(root) / "nvim-nvda" / "sessions"


def _integer(value: Any, *, positive: bool) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        return None
    result = int(value)
    if result < (1 if positive else 0):
        return None
    return result


class LocalSessionLister:
    def __init__(
        self,
        directory: pathlib.Path | None = None,
        process_alive: Callable[[int], bool] | None = None,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.directory = directory
        self._process_alive = process_alive or self._default_process_alive
        self._monotonic_ns = monotonic_ns

    @staticmethod
    def _default_process_alive(pid: int) -> bool:
        if os.name == "nt":
            # os.kill(pid, 0) does not have POSIX probe semantics on every
            # supported Windows Python build. Query the process handle without
            # ever requesting termination rights.
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
                kernel32.OpenProcess.restype = wintypes.HANDLE
                kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
                kernel32.GetExitCodeProcess.restype = wintypes.BOOL
                kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
                kernel32.CloseHandle.restype = wintypes.BOOL
                handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                if not handle:
                    return False
                try:
                    exit_code = wintypes.DWORD()
                    return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and (
                        exit_code.value == 259  # STILL_ACTIVE
                    )
                finally:
                    kernel32.CloseHandle(handle)
            except (AttributeError, OSError, TypeError, ValueError):
                return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def list(self) -> list[LocalWindowsSession]:
        directory = self.directory or local_registry_directory()
        try:
            entries = list(directory.glob("*.json"))
        except OSError as error:
            raise RuntimeError(f"cannot read local Neovim session registry: {error}") from error
        sessions = []
        now = self._monotonic_ns()
        for entry in entries:
            try:
                if entry.stat().st_size > LOCAL_SESSION_MAX_BYTES:
                    continue
                value: Any = json.loads(entry.read_text(encoding="utf-8"))
                if not isinstance(value, dict) or value.get("version") != 2:
                    continue
                if value.get("transportKind") != "localWindowsTcp" or value.get("host") != "127.0.0.1":
                    continue
                pid = _integer(value.get("pid"), positive=True)
                port = _integer(value.get("port"), positive=True)
                started = _integer(value.get("startedMonotonic"), positive=True)
                claimed = _integer(value.get("claimedMonotonic", 0), positive=False)
                claim_sequence = _integer(value.get("claimSequence", 0), positive=False)
                started_unix = _integer(value.get("startedUnix", 0), positive=False)
                name, cwd = value.get("name", ""), value.get("cwd", "")
                if (
                    pid is None or port is None or port > 65535 or started is None
                    or claimed is None or claim_sequence is None
                    or not isinstance(name, str) or not isinstance(cwd, str)
                    or len(name) > 120 or len(cwd) > 4096 or not self._process_alive(pid)
                ):
                    continue
                claim_age = -1 if claimed == 0 or claimed > now else (now - claimed) // 1_000_000
                sessions.append(LocalWindowsSession(
                    str(pid), name, cwd, "127.0.0.1", port, pid,
                    started_unix or 0, int(claim_age), claimed, claim_sequence,
                ))
            except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
                continue
        return sorted(sessions, key=lambda item: (item.started_unix, item.pid), reverse=True)
