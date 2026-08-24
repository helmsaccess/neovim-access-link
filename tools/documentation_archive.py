#!/usr/bin/env python3
"""Create the deterministic documentation archive from generated HTML."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

import buildVars  # noqa: E402
from tools.documentation_layout import DOCUMENTS, source_name  # noqa: E402


def expected_sources(source_directory: Path) -> tuple[Path, ...]:
	return tuple(
		source_directory / source_name(document, language)
		for language, documents in DOCUMENTS.items()
		for document in documents
	)


def build(source_directory: Path, output_directory: Path) -> Path:
	"""Write one deterministic ZIP and return its path."""
	sources = expected_sources(source_directory)
	missing = tuple(path for path in sources if not path.is_file())
	if missing:
		raise RuntimeError(f"generated documentation is missing: {missing!r}")
	output = output_directory / (
		f"{buildVars.product_slug()}-{buildVars.artifact_version()}-documentation.zip"
	)
	output.parent.mkdir(parents=True, exist_ok=True)
	staged = output.with_name(f".{output.name}.tmp")
	with zipfile.ZipFile(
		staged,
		"w",
		compression=zipfile.ZIP_DEFLATED,
		compresslevel=9,
	) as archive:
		for source in sources:
			info = zipfile.ZipInfo(source.name, date_time=(1980, 1, 1, 0, 0, 0))
			info.compress_type = zipfile.ZIP_DEFLATED
			info.external_attr = 0o644 << 16
			archive.writestr(info, source.read_bytes(), compresslevel=9)
	staged.replace(output)
	output.chmod(0o644)
	return output


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("source_directory", type=Path)
	parser.add_argument("output_directory", type=Path)
	arguments = parser.parse_args()
	result = build(arguments.source_directory, arguments.output_directory)
	print(f"built {result} ({result.stat().st_size} bytes)")


if __name__ == "__main__":
	main()
