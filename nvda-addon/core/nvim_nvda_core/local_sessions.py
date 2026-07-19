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
LOCAL_SESSION_MAX_ENTRIES = 256


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
    session_nonce: str = ""


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
        process_alive: Callable[[int], bool | None] | None = None,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.directory = directory
        self._process_alive = process_alive or self._default_process_alive
        self._monotonic_ns = monotonic_ns

    @staticmethod
    def _discard_entry(entry: pathlib.Path) -> None:
        try:
            entry.unlink()
        except OSError:
            pass

    @staticmethod
    def _default_process_alive(pid: int) -> bool | None:
        if os.name == "nt":
            # Windows process probing is injected by the NVDA integration so
            # this neutral module never declares its own DLL boundary.
            return None
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except (PermissionError, OSError):
            return None

    def list(self) -> list[LocalWindowsSession]:
        directory = self.directory or local_registry_directory()
        try:
            entries = []
            for entry in directory.glob("*.json"):
                entries.append(entry)
                if len(entries) >= LOCAL_SESSION_MAX_ENTRIES:
                    break
        except OSError as error:
            raise RuntimeError(f"cannot read local Neovim session registry: {error}") from error
        sessions = []
        now = self._monotonic_ns()
        for entry in entries:
            try:
                with entry.open("rb") as source:
                    payload = source.read(LOCAL_SESSION_MAX_BYTES + 1)
                if len(payload) > LOCAL_SESSION_MAX_BYTES:
                    continue
                value: Any = json.loads(payload.decode("utf-8"))
                if not isinstance(value, dict) or value.get("version") != 3:
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
                nonce = value.get("sessionNonce")
                owns_entry = (
                    pid is not None
                    and isinstance(nonce, str) and entry.name == f"{pid}-{nonce}.json"
                )
                alive = pid is not None and self._process_alive(pid)
                if owns_entry and alive is False:
                    self._discard_entry(entry)
                if (
                    pid is None or port is None or port > 65535 or started is None
                    or claimed is None or claim_sequence is None
                    or not isinstance(name, str) or not isinstance(cwd, str)
                    or len(name) > 120 or len(cwd) > 4096 or alive is not True
                ):
                    continue
                if (
                    not isinstance(nonce, str) or len(nonce) != 32
                    or any(character not in "0123456789abcdef" for character in nonce)
                    or not owns_entry
                ):
                    continue
                claim_age = -1 if claimed == 0 or claimed > now else (now - claimed) // 1_000_000
                sessions.append(LocalWindowsSession(
                    str(pid), name, cwd, "127.0.0.1", port, pid,
                    started_unix or 0, int(claim_age), claimed, claim_sequence, nonce,
                ))
            except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
                continue
        return sorted(sessions, key=lambda item: (item.started_unix, item.pid), reverse=True)
