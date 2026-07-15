"""Single source of truth for product identity and release metadata.

The layout deliberately follows NVDA's official Add-on Template convention.
The user owns ``product_version`` and ``release_channel``; coding agents only
advance ``build_number`` when installable content changes.
"""

from __future__ import annotations

import re


product_version = "0.89"
build_number = 16
release_channel = "beta"

addon_info = {
    "name": "nvimNvdaAccess",
    "summary": "Neovim Access Link",
    "description": (
        "Structured, low-latency Neovim navigation for local Windows and "
        "remote Linux sessions."
    ),
    "author": "Emanuel Helms <emanuel@helmsaccess.de>",
    "minimumNVDAVersion": "2026.1",
    "lastTestedNVDAVersion": "2026.1.1",
}


def version() -> str:
    """Return the strictly orderable, Add-on Store-compatible build version."""
    if re.fullmatch(r"\d+\.\d+", product_version) is None:
        raise ValueError("product_version must contain two numeric components")
    if not isinstance(build_number, int) or build_number < 1:
        raise ValueError("build_number must be a positive integer")
    return f"{product_version}.{build_number}"


def product_slug() -> str:
    """Return a filesystem-safe slug derived from the visible product name."""
    words = re.findall(r"[A-Za-z0-9]+", addon_info["summary"])
    if not words:
        raise ValueError("summary must contain at least one ASCII word")
    return "-".join(word.lower() for word in words)


def manifest() -> dict[str, str]:
    """Return all scalar fields required by an NVDA add-on manifest."""
    return {**addon_info, "version": version()}
