"""Discover private Neovim RPC sockets registered by the installed plugin."""

from __future__ import annotations

import json
import math
import os
import pathlib
import stat
from dataclasses import dataclass
from typing import Any

REGISTRY_ENTRY_MAX_BYTES = 65_536
REGISTRY_MAX_ENTRIES = 256


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
    session_nonce: str = ""


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


def registry_directories() -> tuple[pathlib.Path, ...]:
    """Return every private runtime location an interactive Neovim may use."""
    runtimes: list[pathlib.Path] = []

    def add(runtime: pathlib.Path) -> None:
        if runtime not in runtimes:
            runtimes.append(runtime)

    configured = os.environ.get("XDG_RUNTIME_DIR")
    if configured:
        add(pathlib.Path(configured))
    # sshd does not consistently preserve XDG_RUNTIME_DIR for a remote
    # command (`ssh host command`), although the interactive Neovim that
    # created the registry may have received it from PAM. Conversely, a
    # long-running Neovim may have started without it while the later bridge
    # command sees /run/user/UID. Search both valid outcomes.
    system_runtime = pathlib.Path(f"/run/user/{os.getuid()}")
    try:
        if system_runtime.is_dir() and system_runtime.stat().st_uid == os.getuid():
            add(system_runtime)
    except OSError:
        pass
    add(pathlib.Path(f"/tmp/nvim-nvda-{os.getuid()}"))
    return tuple(runtime / "nvim-nvda" / "sessions" for runtime in runtimes)


def registry_directory() -> pathlib.Path:
    """Return the preferred registry directory for compatibility callers."""
    return registry_directories()[0]


def _is_private_registry_directory(directory: pathlib.Path) -> bool:
    """Only scan an existing per-user directory with no group/world access."""
    try:
        value = directory.stat()
        return (
            stat.S_ISDIR(value.st_mode)
            and value.st_uid == os.getuid()
            and stat.S_IMODE(value.st_mode) & 0o077 == 0
        )
    except OSError:
        return False


def _process_start_ticks(pid: int) -> int:
    value = pathlib.Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    remainder = value[value.rfind(")") + 2:].split()
    return int(remainder[19])  # Linux /proc field 22; remainder starts at field 3.


def _discard(entry: pathlib.Path, data: dict[str, Any]) -> None:
    """Remove one nonce-owned stale record and its equally unique socket."""
    try:
        entry.unlink()
    except OSError:
        pass
    pid, nonce, socket_value = data.get("pid"), data.get("sessionNonce"), data.get("socket")
    expected = entry.parent.parent / f"nvim-{pid}-{nonce}.sock"
    if (
        data.get("ownsSocket") is True and isinstance(socket_value, str)
        and pathlib.Path(socket_value) == expected
    ):
        try:
            expected.unlink()
        except OSError:
            pass


def _owns_registry_entry(entry: pathlib.Path, pid: int, version: int, nonce: Any) -> bool:
    """A schema-3 nonce filename cannot be replaced by a reused PID."""
    return (
        version == 3 and isinstance(nonce, str)
        and entry.name == f"{pid}-{nonce}.json"
    )


def _read_registry_entry(entry: pathlib.Path) -> Any:
    with entry.open("rb") as source:
        payload = source.read(REGISTRY_ENTRY_MAX_BYTES + 1)
    if len(payload) > REGISTRY_ENTRY_MAX_BYTES:
        raise ValueError("registry entry is too large")
    return json.loads(payload.decode("utf-8"))


def list_sessions(
    directory: pathlib.Path | None = None, *,
    process_start_reader=_process_start_ticks,
) -> list[RegisteredSession]:
    explicit_directory = directory is not None
    directories = (directory,) if directory is not None else registry_directories()
    candidates: list[RegisteredSession] = []
    entries: list[pathlib.Path] = []
    for candidate_directory in directories:
        if not explicit_directory and not _is_private_registry_directory(candidate_directory):
            continue
        try:
            for entry in candidate_directory.glob("*.json"):
                entries.append(entry)
                if len(entries) >= REGISTRY_MAX_ENTRIES:
                    break
        except OSError as error:
            if explicit_directory:
                raise RuntimeError(f"cannot read Neovim session registry: {error}") from error
        if len(entries) >= REGISTRY_MAX_ENTRIES:
            break
    for entry in entries:
        try:
            data: Any = _read_registry_entry(entry)
            version = data.get("version")
            pid = data.get("pid")
            socket_path = data.get("socket")
            started = data.get("startedMonotonic", 0)
            started_unix = data.get("startedUnix", 0)
            claimed = data.get("claimedMonotonic", 0)
            claim_sequence = data.get("claimSequence", 0)
            name = data.get("name", "")
            cwd = data.get("cwd", "")
            nonce = data.get("sessionNonce")
            pid = _json_integer(pid, positive=True)
            if (
                version != 3 or pid is None
                or not isinstance(socket_path, str) or not socket_path
                or len(socket_path) > 4096
            ):
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
            if not isinstance(name, str) or len(name) > 120:
                name = ""
            if not isinstance(cwd, str) or len(cwd) > 4096:
                cwd = ""
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                if _owns_registry_entry(entry, pid, version, nonce):
                    _discard(entry, data)
                continue
            except (PermissionError, OSError):
                # Access failure is not proof that the process is dead.
                continue
            if not pathlib.Path(socket_path).exists():
                continue
            expected_ticks = _json_integer(data.get("processStartTicks"), positive=True)
            if (
                data.get("transportKind") != "remoteSsh" or expected_ticks is None
                or not isinstance(nonce, str) or len(nonce) != 32
                or any(character not in "0123456789abcdef" for character in nonce)
                or not _owns_registry_entry(entry, pid, version, nonce)
            ):
                continue
            try:
                actual_ticks = process_start_reader(pid)
            except (OSError, ValueError, IndexError):
                continue
            if actual_ticks != expected_ticks:
                _discard(entry, data)
                continue
            candidates.append(RegisteredSession(
                identifier=str(pid), pid=pid, socket=socket_path,
                name=name, cwd=cwd, started_monotonic=started, started_unix=started_unix,
                claimed_monotonic=claimed, claim_sequence=claim_sequence,
                session_nonce=nonce,
            ))
        except (OSError, ValueError, AttributeError):
            continue
    unique = {
        (session.pid, session.session_nonce): session
        for session in candidates
    }
    return sorted(
        unique.values(), key=lambda item: (item.started_monotonic, item.pid), reverse=True,
    )


def discover_session(
    directory: pathlib.Path | None = None, selector: str = "",
) -> RegisteredSession:
    sessions = list_sessions(directory)
    if not sessions:
        raise RuntimeError("no registered Neovim accessibility session found")
    if selector:
        matches = [session for session in sessions if session.identifier == selector or session.name == selector]
        if not matches:
            raise RuntimeError(f"registered Neovim accessibility session not found: {selector}")
        if len(matches) > 1:
            raise RuntimeError(f"ambiguous Neovim accessibility session name: {selector}")
        return matches[0]
    # A hard ambiguity error would make every session unusable as soon as a
    # detached tmux window contains another Neovim. Prefer the newest current
    # registry entry when the caller did not provide an explicit session.
    return sessions[0]
