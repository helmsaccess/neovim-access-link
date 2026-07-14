"""Validated SSH connection profiles without assumptions about local usernames."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@dataclass(frozen=True)
class ConnectionProfile:
    identifier: str
    name: str
    host: str
    user: str = ""
    port: int = 22
    identity_file: str = ""
    authentication: str = "openSsh"

    @property
    def ssh_target(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.identifier, "name": self.name, "host": self.host,
            "user": self.user, "port": self.port, "identityFile": self.identity_file,
            "authentication": self.authentication,
        }


def parse_profile(value: Any) -> ConnectionProfile:
    if not isinstance(value, dict):
        raise ValueError("connection profile must be an object")
    identifier = value.get("id", "")
    name = value.get("name", "")
    host = value.get("host", "")
    user = value.get("user", "")
    port = value.get("port", 22)
    identity_file = value.get("identityFile", "")
    authentication = value.get("authentication", "openSsh")
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        raise ValueError("invalid connection profile id")
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise ValueError("invalid connection profile name")
    if not _safe_atom(host) or "@" in host:
        raise ValueError("invalid SSH host")
    if user and (not _safe_atom(user) or "@" in user):
        raise ValueError("invalid SSH user")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("invalid SSH port")
    if identity_file and (
        not isinstance(identity_file, str) or identity_file.startswith("-")
        or "\r" in identity_file or "\n" in identity_file or "\0" in identity_file
    ):
        raise ValueError("invalid SSH identity file")
    if authentication not in {"openSsh", "password"}:
        raise ValueError("unsupported SSH authentication")
    return ConnectionProfile(
        identifier, name.strip(), host, user, port, identity_file, authentication,
    )


def parse_profiles(values: Any) -> list[ConnectionProfile]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("connections must be a list")
    profiles = [parse_profile(value) for value in values]
    identifiers = [profile.identifier for profile in profiles]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate connection profile id")
    return profiles


def unique_profile_id(name: str, existing: set[str]) -> str:
    base = re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-._") or "connection"
    base = base[:56]
    candidate = base
    number = 2
    while candidate in existing:
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def save_profile(values: Any, profile: Any, original_id: str = "") -> list[ConnectionProfile]:
    profiles = parse_profiles(values)
    parsed = parse_profile(profile)
    ids = {item.identifier for item in profiles}
    if original_id:
        for index, item in enumerate(profiles):
            if item.identifier == original_id:
                if parsed.identifier != original_id and parsed.identifier in ids:
                    raise ValueError("duplicate connection profile id")
                profiles[index] = parsed
                return profiles
        raise ValueError("connection profile to edit does not exist")
    if parsed.identifier in ids:
        raise ValueError("duplicate connection profile id")
    profiles.append(parsed)
    return profiles


def remove_profile(values: Any, identifier: str) -> list[ConnectionProfile]:
    profiles = parse_profiles(values)
    remaining = [profile for profile in profiles if profile.identifier != identifier]
    if len(remaining) == len(profiles):
        raise ValueError("connection profile to remove does not exist")
    return remaining


def _safe_atom(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and not value.startswith("-") and not any(
        character.isspace() or ord(character) < 32 for character in value
    )
