#!/usr/bin/env python3
"""Synchronize generated HTML into NVDA's installed add-on documentation layout."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import buildVars  # noqa: E402


SOURCE_DIRECTORY = ROOT / "build" / "docs"
DESTINATION_DIRECTORY = ROOT / "nvda-addon" / "addon" / "doc"
DOCUMENTS = {
    "de": {
        "handbook": "readme.html",
        "quick-guide": "quick-guide.html",
        "developer-documentation": "developer-documentation.html",
        "human-testing": "human-testing.html",
    },
    "en": {
        "handbook": "readme.html",
        "quick-guide": "quick-guide.html",
        "developer-documentation": "developer-documentation.html",
        "human-testing": "human-testing.html",
    },
}


class _HtmlMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.language = ""
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        values = dict(attributes)
        if tag == "html":
            self.language = values.get("lang") or ""
        target = values.get("href")
        if target:
            self.links.append(target)


def _source_name(document: str, language: str) -> str:
    return f"{buildVars.product_slug()}-{document}-{language}.html"


def _rewrite_links(value: str, language: str) -> str:
    replacements = {
        _source_name(document, language): destination
        for document, destination in DOCUMENTS[language].items()
    }
    for source, destination in replacements.items():
        value = re.sub(
            rf'(?<=href="){re.escape(source)}(?=[#?"])',
            destination,
            value,
        )
    return value


def expected_documents(source_directory: Path = SOURCE_DIRECTORY) -> dict[Path, str]:
    expected = {}
    for language, documents in DOCUMENTS.items():
        for document, destination in documents.items():
            source = source_directory / _source_name(document, language)
            if not source.is_file():
                raise RuntimeError(f"generated documentation is missing: {source}")
            expected[Path(language) / destination] = _rewrite_links(
                source.read_text(encoding="utf-8"),
                language,
            )
    return expected


def validate_documents(directory: Path) -> None:
    expected_paths = {
        Path(language) / destination
        for language, documents in DOCUMENTS.items()
        for destination in documents.values()
    }
    actual_paths = {
        path.relative_to(directory)
        for path in directory.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise RuntimeError(
            "installed documentation set differs from the supported set; "
            f"missing={sorted(expected_paths - actual_paths)!r}, "
            f"unexpected={sorted(actual_paths - expected_paths)!r}"
        )
    for relative in sorted(actual_paths):
        parser = _HtmlMetadata()
        parser.feed((directory / relative).read_text(encoding="utf-8"))
        if parser.language != relative.parts[0]:
            raise RuntimeError(f"incorrect HTML language for {relative}: {parser.language!r}")
        for target in parser.links:
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            linked = (directory / relative.parent / parsed.path).resolve()
            if directory.resolve() not in linked.parents or not linked.is_file():
                raise RuntimeError(f"broken installed documentation link in {relative}: {target}")


def synchronize(source_directory: Path, destination_directory: Path, *, check: bool) -> None:
    expected = expected_documents(source_directory)
    stale = []
    for relative, value in expected.items():
        destination = destination_directory / relative
        if not destination.is_file() or destination.read_text(encoding="utf-8") != value:
            stale.append(relative)
        if not check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(value, encoding="utf-8", newline="\n")
    if check and stale:
        raise RuntimeError(
            "installed documentation is stale; run "
            "python3 tools/sync_installed_documentation.py --write: "
            + ", ".join(str(path) for path in stale)
        )
    validate_documents(destination_directory)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--source", type=Path, default=SOURCE_DIRECTORY)
    parser.add_argument("--destination", type=Path, default=DESTINATION_DIRECTORY)
    arguments = parser.parse_args()
    synchronize(arguments.source, arguments.destination, check=arguments.check)


if __name__ == "__main__":
    main()
