"""Single source of truth for product identity and release metadata."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


product_version = "0.99.0"
# Set to ``None`` only for a user-approved release artifact.
development_build: int | None = 1
release_channel = "beta"
# Store upgrade baseline for the intended channel. For a stable release,
# confirm the previous stable Store version before preparing the release.
manifest_changelog_base_version = "0.96.0"


def _(message: str) -> str:
    """Mark manifest text for gettext extraction without loading translations."""
    return message


addon_info = {
    "name": "NeovimAccessLink",
    # Translators: Add-on display name shown by NVDA.
    "summary": _("Neovim Access Link"),
    # Translators: Add-on description shown by NVDA.
    "description": _(
        "Accessible Neovim integration for NVDA with structured speech, sound, and Braille feedback "
        "for editing, navigation, and spelling suggestions. Supports separate local Windows and "
        "remote SSH sessions across Windows Terminal windows, tabs, and panes."
    ),
    "author": "Emanuel Helms <emanuel@helmsaccess.de>",
    "url": "https://github.com/helmsaccess/neovim-access-link",
    "docFileName": "readme.html",
    "minimumNVDAVersion": "2026.1",
    "lastTestedNVDAVersion": "2026.3.1",
    "updateChannel": release_channel,
}
addon_store_info = {
    "sourceURL": "https://github.com/helmsaccess/neovim-access-link",
    "license": "GPL-2.0-only",
    "licenseURL": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
}

_ROOT = Path(__file__).resolve().parent
_CHANGELOG_HEADINGS = {"de": "Unveröffentlicht", "en": "Unreleased"}
_EMPTY_DEVELOPMENT_CHANGELOG = {
    "de": "Keine unveröffentlichten Änderungen aufgeführt.",
    "en": "No unreleased changes listed.",
}
_PRODUCT_VERSION = r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}"
_RELEASE_HEADING = re.compile(
    rf"##\s+(?:\[({_PRODUCT_VERSION})\][ \t]+-[ \t]+[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}"
    rf"(?:[ \t]+\[YANKED\])?|({_PRODUCT_VERSION})(?:\s+\([^)]*\))?)\s*"
)
_VERSION_LINK = re.compile(rf"\s{{0,3}}\[(?:{_PRODUCT_VERSION}|Unreleased|Unveröffentlicht)\]:\s+.*")


def store_version() -> str:
    """Return the normal numeric product version exposed to the NVDA Store."""
    _version_tuple(product_version)
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


def _release_heading_version(line: str) -> str | None:
    match = _RELEASE_HEADING.fullmatch(line)
    return (match[1] or match[2]) if match else None


def _changelog_section(language: str, heading: str) -> str:
    if language not in _CHANGELOG_HEADINGS:
        raise ValueError(f"unsupported changelog language: {language}")
    path = _ROOT / "docs" / language / "development" / "changelog.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(
        (
            index + 1
            for index, line in enumerate(lines)
            if line.rstrip() == f"## {heading}" or _release_heading_version(line) == heading
        ),
        None,
    )
    if start is None:
        raise ValueError(f"missing {heading!r} section in {path}")
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    value = "\n".join(line for line in lines[start:end] if not _VERSION_LINK.fullmatch(line)).strip()
    if not value:
        if heading == _CHANGELOG_HEADINGS[language]:
            return _EMPTY_DEVELOPMENT_CHANGELOG[language]
        raise ValueError(f"empty {heading!r} section in {path}")
    return value


def changelog(language: str = "en") -> str:
    """Return the current localized product-version changelog section."""
    if language not in _CHANGELOG_HEADINGS:
        raise ValueError(f"unsupported changelog language: {language}")
    heading = (
        _CHANGELOG_HEADINGS[language]
        if development_build is not None
        else product_version
    )
    return _changelog_section(language, heading)


def _version_tuple(value: str) -> tuple[int, int, int]:
    if re.fullmatch(_PRODUCT_VERSION, value) is None:
        raise ValueError(f"invalid product version: {value!r}")
    return tuple(int(part) for part in value.split("."))


def manifest_changelog(language: str = "en") -> str:
    """Return changes since the version currently published in the Add-on Store."""
    if development_build is not None:
        return changelog(language)
    base = _version_tuple(manifest_changelog_base_version)
    current = _version_tuple(store_version())
    if base >= current:
        raise ValueError("manifest changelog base must precede the release version")
    path = _ROOT / "docs" / language / "development" / "changelog.md"
    headings = (
        version
        for line in path.read_text(encoding="utf-8").splitlines()
        if (version := _release_heading_version(line)) is not None
    )
    versions = [
        heading
        for heading in headings
        if base < _version_tuple(heading) <= current
    ]
    if store_version() not in versions:
        raise ValueError(f"missing {store_version()!r} release section in {path}")
    return "\n\n".join(
        f"{version}\n\n{_changelog_section(language, version)}"
        for version in versions
    )


def manifest() -> dict[str, str]:
    """Return all scalar fields required by an NVDA add-on manifest."""
    return {**addon_info, "version": store_version(), "changelog": manifest_changelog()}
