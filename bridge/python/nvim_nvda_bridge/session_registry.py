"""Discover private Neovim RPC sockets registered by the installed plugin."""

from __future__ import annotations

import json
import math
import os
import pathlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RegisteredSession:
    identifier: str
    pid: int
    socket: str
    name: str
    cwd: str
    started_monotonic: int
    started_unix: int = 0
    claimed_monotonic: int = 0
    claim_sequence: int = 0


def _json_integer(value: Any, *, positive: bool) -> int | None:
    """Accept JSON integers even when Lua encoded a large value with an exponent."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        return None
    normalized = int(value)
    if normalized < (1 if positive else 0):
        return None
    return normalized


def registry_directory() -> pathlib.Path:
    configured = os.environ.get("XDG_RUNTIME_DIR")
    if configured:
        runtime = pathlib.Path(configured)
    else:
        # sshd does not consistently preserve XDG_RUNTIME_DIR for a remote
        # command (`ssh host command`), although the interactive Neovim that
        # created the registry received it from PAM.  Recover the standard
        # systemd/logind path, but only when it belongs to this user.
        system_runtime = pathlib.Path(f"/run/user/{os.getuid()}")
        try:
            if not system_runtime.is_dir() or system_runtime.stat().st_uid != os.getuid():
                raise OSError("unsafe runtime directory")
            runtime = system_runtime
        except OSError:
            runtime = pathlib.Path(f"/tmp/nvim-nvda-{os.getuid()}")
    return runtime / "nvim-nvda" / "sessions"


def list_sessions(directory: pathlib.Path | None = None) -> list[RegisteredSession]:
    directory = registry_directory() if directory is None else directory
    candidates: list[RegisteredSession] = []
    try:
        entries = list(directory.glob("*.json"))
    except OSError as error:
        raise RuntimeError(f"cannot read Neovim session registry: {error}") from error
    for entry in entries:
        try:
            data: Any = json.loads(entry.read_text(encoding="utf-8"))
            version = data.get("version")
            pid = data.get("pid")
            socket_path = data.get("socket")
            started = data.get("startedMonotonic", 0)
            started_unix = data.get("startedUnix", 0)
            claimed = data.get("claimedMonotonic", 0)
            claim_sequence = data.get("claimSequence", 0)
            name = data.get("name", "")
            cwd = data.get("cwd", "")
            if version != 2 or not isinstance(pid, int) or not isinstance(socket_path, str) or not socket_path:
                continue
            started = _json_integer(started, positive=True)
            if started is None:
                continue
            started_unix = _json_integer(started_unix, positive=False)
            if started_unix is None:
                started_unix = 0
            claimed = _json_integer(claimed, positive=False)
            if claimed is None:
                claimed = 0
            claim_sequence = _json_integer(claim_sequence, positive=False)
            if claim_sequence is None:
                claim_sequence = 0
            if not isinstance(name, str):
                name = ""
            if not isinstance(cwd, str):
                cwd = ""
            os.kill(pid, 0)
            if not pathlib.Path(socket_path).exists():
                continue
            candidates.append(RegisteredSession(
                identifier=str(pid), pid=pid, socket=socket_path,
                name=name, cwd=cwd, started_monotonic=started, started_unix=started_unix,
                claimed_monotonic=claimed, claim_sequence=claim_sequence,
            ))
        except (OSError, ValueError, AttributeError):
            continue
    return sorted(candidates, key=lambda item: (item.started_monotonic, item.pid), reverse=True)


def discover_socket(directory: pathlib.Path | None = None, selector: str = "") -> str:
    sessions = list_sessions(directory)
    if not sessions:
        raise RuntimeError("no registered Neovim accessibility session found")
    if selector:
        matches = [session for session in sessions if session.identifier == selector or session.name == selector]
        if not matches:
            raise RuntimeError(f"registered Neovim accessibility session not found: {selector}")
        if len(matches) > 1:
            raise RuntimeError(f"ambiguous Neovim accessibility session name: {selector}")
        return matches[0].socket
    # A hard ambiguity error would make every session unusable as soon as a
    # detached tmux window contains another Neovim. Prefer the newest current
    # registry entry when the caller did not provide an explicit session.
    return sessions[0].socket
