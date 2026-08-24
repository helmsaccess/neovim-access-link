"""Map generated documentation into the installed NVDA add-on layout."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import buildVars

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


def source_name(document: str, language: str) -> str:
	return f"{buildVars.product_slug()}-{document}-{language}.html"


def _rewrite_links(value: str, language: str) -> str:
	replacements = {
		source_name(document, language): destination
		for document, destination in DOCUMENTS[language].items()
	}
	for source, destination in replacements.items():
		value = re.sub(
			rf'(?<=href="){re.escape(source)}(?=[#?"])',
			destination,
			value,
		)
	return value


def expected_documents(source_directory: Path) -> dict[Path, str]:
	expected = {}
	for language, documents in DOCUMENTS.items():
		for document, destination in documents.items():
			source = source_directory / source_name(document, language)
			if not source.is_file():
				raise RuntimeError(f"generated documentation is missing: {source}")
			expected[Path(language) / destination] = _rewrite_links(
				source.read_text(encoding="utf-8"),
				language,
			)
	return expected


def validate_installed_documents(directory: Path) -> None:
	expected_paths = {
		Path(language) / destination
		for language, documents in DOCUMENTS.items()
		for destination in documents.values()
	}
	actual_paths = {path.relative_to(directory) for path in directory.rglob("*") if path.is_file()}
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


def install_generated_documentation(source_directory: Path, destination_directory: Path) -> None:
	for relative, value in expected_documents(source_directory).items():
		destination = destination_directory / relative
		destination.parent.mkdir(parents=True, exist_ok=True)
		destination.write_text(value, encoding="utf-8", newline="\n")
	validate_installed_documents(destination_directory)
