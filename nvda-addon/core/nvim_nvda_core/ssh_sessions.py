"""List remote Neovim accessibility sessions through OpenSSH."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RemoteSession:
    identifier: str
    name: str
    cwd: str
    started_unix: int = 0
    claim_age_ms: int = -1
    claim_sequence: int = 0


class SshSessionLister:
    def __init__(self, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self._runner = runner

    def list(self, target: str, port: int = 22, identity_file: str = "",
             password: str = "", askpass_path: str = "") -> list[RemoteSession]:
        if not target or target.startswith("-") or any(character.isspace() for character in target):
            raise ValueError("invalid SSH target")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError("invalid SSH port")
        if identity_file and (
            not isinstance(identity_file, str) or identity_file.startswith("-")
            or "\r" in identity_file or "\n" in identity_file or "\0" in identity_file
        ):
            raise ValueError("invalid SSH identity file")
        if password and not askpass_path:
            raise ValueError("SSH askpass helper is required")
        command = [
            "ssh.exe", "-T", "-o", f"BatchMode={'no' if password else 'yes'}",
            "-o", "ConnectTimeout=10", "-o", "ClearAllForwardings=yes",
        ]
        if password:
            command.extend((
                "-o", "PreferredAuthentications=keyboard-interactive,password",
                "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1",
            ))
        if port != 22:
            command.extend(("-p", str(port)))
        if identity_file:
            command.extend(("-i", identity_file))
        command.extend((target, "$HOME/.local/bin/nvim-nvda-bridge --list-sessions"))
        environment = None
        if password:
            environment = os.environ.copy()
            environment.update({
                "SSH_ASKPASS": askpass_path, "SSH_ASKPASS_REQUIRE": "force",
                "DISPLAY": environment.get("DISPLAY", "nvim-nvda"),
                "NVIM_NVDA_SSH_PASSWORD": password,
            })
        result = self._runner(
            command, capture_output=True, timeout=15, env=environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            stderr = bytes(result.stderr or b"").decode("utf-8", "replace")[-2000:]
            raise RuntimeError(f"SSH session listing failed: {stderr}")
        try:
            values: Any = json.loads(bytes(result.stdout or b"").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("remote session list is not valid JSON") from error
        if not isinstance(values, list):
            raise RuntimeError("remote session list must be an array")
        sessions = []
        for value in values:
            if not isinstance(value, dict):
                continue
            identifier, name, cwd = value.get("id"), value.get("name"), value.get("cwd", "")
            started_unix = value.get("startedUnix", 0)
            claim_age_ms = value.get("claimAgeMs", -1)
            claim_sequence = value.get("claimSequence", 0)
            if not isinstance(identifier, str) or not identifier.isascii() or not identifier.isdigit():
                continue
            if not isinstance(name, str) or not isinstance(cwd, str):
                continue
            if isinstance(started_unix, bool) or not isinstance(started_unix, int) or started_unix < 0:
                started_unix = 0
            if (
                isinstance(claim_age_ms, bool) or not isinstance(claim_age_ms, int)
                or claim_age_ms < -1
            ):
                claim_age_ms = -1
            if (
                isinstance(claim_sequence, bool) or not isinstance(claim_sequence, int)
                or claim_sequence < 0
            ):
                claim_sequence = 0
            sessions.append(RemoteSession(
                identifier, name, cwd, started_unix, claim_age_ms, claim_sequence,
            ))
        return sessions
