"""Typed connection targets shared by discovery, installation and runtime clients."""

from __future__ import annotations

from dataclasses import dataclass

REMOTE_SSH = "remoteSsh"
LOCAL_WINDOWS_TCP = "localWindowsTcp"
LOCAL_WINDOWS_TARGET_ID = "local-windows"


@dataclass(frozen=True)
class ConnectionTarget:
    """A transport destination, distinct from an SSH profile or live instance."""

    kind: str
    identifier: str
    name: str
    profile_id: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {REMOTE_SSH, LOCAL_WINDOWS_TCP}:
            raise ValueError("unsupported connection target kind")
        if not self.identifier or not self.name:
            raise ValueError("connection target id and name are required")
        if self.kind == REMOTE_SSH and not self.profile_id:
            raise ValueError("remote SSH target requires a profile id")
        if self.kind == LOCAL_WINDOWS_TCP and self.profile_id:
            raise ValueError("local Windows target must not reference an SSH profile")


def remote_ssh_target(profile_id: str, name: str) -> ConnectionTarget:
    return ConnectionTarget(REMOTE_SSH, profile_id, name, profile_id)


def local_windows_target(name: str = "This computer - local Neovim") -> ConnectionTarget:
    return ConnectionTarget(LOCAL_WINDOWS_TCP, LOCAL_WINDOWS_TARGET_ID, name)
