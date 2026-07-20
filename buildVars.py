"""Single source of truth for product identity and release metadata."""

from __future__ import annotations

import re
import subprocess


product_version = "0.95.0"
# Set to ``None`` only for a user-approved release artifact.
development_build: int | None = 17
release_channel = "beta"

addon_info = {
    "name": "NeovimAccessLink",
    "summary": "Neovim Access Link",
    "description": (
        "Structured, low-latency Neovim navigation for local Windows and "
        "remote Linux sessions."
    ),
    "author": "Emanuel Helms <emanuel@helmsaccess.de>",
    "minimumNVDAVersion": "2026.1",
    "lastTestedNVDAVersion": "2026.1.1",
}


def store_version() -> str:
    """Return the normal numeric product version exposed to the NVDA Store."""
    if re.fullmatch(r"\d+\.\d+\.\d+", product_version) is None:
        raise ValueError("product_version must contain three numeric components")
    return product_version


def _git_value(*arguments: str) -> str:
    try:
        return subprocess.run(
            ("git", *arguments), check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _metadata_identifier(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z-]+", ".", value).strip(".")
    return value or "source"


def development_version(*, include_metadata: bool = True) -> str:
    """Return the branch-local SemVer identifier used outside the Store manifest."""
    if not isinstance(development_build, int) or development_build < 1:
        raise ValueError("development_build must be a positive integer for development artifacts")
    value = f"{store_version()}-dev.{development_build}"
    if not include_metadata:
        return value
    branch = _git_value("branch", "--show-current")
    commit = _git_value("rev-parse", "--short=8", "HEAD")
    metadata = [item for item in (_metadata_identifier(branch), commit) if item]
    return f"{value}+{'.'.join(metadata)}" if metadata else value


def artifact_version() -> str:
    """Return the unique traceable version for packages and diagnostics."""
    return store_version() if development_build is None else development_version()


def product_slug() -> str:
    """Return a filesystem-safe slug derived from the visible product name."""
    words = re.findall(r"[A-Za-z0-9]+", addon_info["summary"])
    if not words:
        raise ValueError("summary must contain at least one ASCII word")
    return "-".join(word.lower() for word in words)


def manifest() -> dict[str, str]:
    """Return all scalar fields required by an NVDA add-on manifest."""
    return {**addon_info, "version": store_version()}
