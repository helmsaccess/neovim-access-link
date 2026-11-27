"""Shared, reproducible construction of the two distributable artifacts."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import venv
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import buildVars

PANDOC_VERSION = "3.1.11.1"
PANDOC_WINDOWS_URL = (
	"https://github.com/jgm/pandoc/releases/download/3.1.11.1/"
	"pandoc-3.1.11.1-windows-x86_64.zip"
)
PANDOC_WINDOWS_SHA256 = "2dbf908b8c9a730f3213896c5a03ac3f91764c2db5cd613da9b4b8cea0b8b9c6"
PANDOC_WINDOWS_MEMBER = "pandoc-3.1.11.1/pandoc.exe"
PANDOC_LINUX_URL = (
	"https://github.com/jgm/pandoc/releases/download/3.1.11.1/"
	"pandoc-3.1.11.1-linux-amd64.tar.gz"
)
PANDOC_LINUX_SHA256 = "07635f6953201ee261bf90e821b8fe36c045e5a6fbae2ae6b1c2127715432942"
PANDOC_LINUX_MEMBER = "pandoc-3.1.11.1/bin/pandoc"


@dataclass(frozen=True)
class SourceSnapshot:
	branch: str
	commit: str


def _run_git(root: Path, *arguments: str) -> str:
	completed = subprocess.run(
		("git", "-C", str(root), *arguments),
		check=False,
		capture_output=True,
		text=True,
	)
	if completed.returncode != 0:
		detail = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
		raise RuntimeError(detail)
	return completed.stdout.strip()


def _clean_source_snapshot(root: Path, branch: str) -> SourceSnapshot:
	commit = _run_git(root, "rev-parse", "--verify", "HEAD^{commit}")
	if _run_git(root, "status", "--porcelain=v1", "--untracked-files=no"):
		raise RuntimeError("the source worktree has changes to versioned files")
	return SourceSnapshot(branch, commit)


def development_source_snapshot(root: Path) -> SourceSnapshot:
	"""Return a clean local development snapshot without a sync dependency."""
	if buildVars.development_build is None:
		raise RuntimeError("Windows development assets require a development build number")
	branch = _run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
	return _clean_source_snapshot(root, branch)


def release_source_snapshot(root: Path) -> SourceSnapshot:
	"""Return one clean main-branch release snapshot."""
	if buildVars.development_build is not None:
		raise RuntimeError("Linux release assets require development_build = None")
	branch = _run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
	if branch != "main":
		raise RuntimeError(f"Linux release assets must be built from main, not {branch!r}")
	return _clean_source_snapshot(root, branch)


def expected_artifact_names() -> frozenset[str]:
	version = buildVars.artifact_version()
	return frozenset(
		{
			f"{buildVars.addon_info['name']}-{version}.nvda-addon",
			f"{buildVars.product_slug()}-{version}-documentation.zip",
		}
	)


def _environment_python(environment: Path) -> Path:
	return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _download_verified(url: str, sha256: str, destination: Path) -> None:
	hash_value = hashlib.sha256()
	request = urllib.request.Request(url, headers={"User-Agent": "NeovimAccessLink-build"})
	try:
		with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
			while chunk := response.read(1024 * 1024):
				hash_value.update(chunk)
				output.write(chunk)
	except OSError as error:
		raise RuntimeError(f"cannot download the pinned Pandoc build: {error}") from error
	actual = hash_value.hexdigest()
	if actual != sha256:
		raise RuntimeError(f"the downloaded Pandoc archive failed SHA-256 verification: {actual}")


def _compatible_local_pandoc() -> Path | None:
	candidate = shutil.which("pandoc")
	if not candidate:
		return None
	try:
		completed = subprocess.run(
			(candidate, "--version"),
			check=False,
			capture_output=True,
			text=True,
			timeout=10,
		)
	except (OSError, subprocess.TimeoutExpired):
		return None
	if completed.returncode != 0:
		return None
	lines = completed.stdout.splitlines()
	if (
		len(lines) < 2
		or lines[0] not in {f"pandoc {PANDOC_VERSION}", f"pandoc.exe {PANDOC_VERSION}"}
		or lines[1] != "Features: +server +lua"
	):
		print(
			f"Ignoring local Pandoc; the build requires the official {PANDOC_VERSION} binary.",
			flush=True,
		)
		return None
	print(f"Using compatible local Pandoc: {candidate}", flush=True)
	return Path(candidate)


def prepare_windows_pandoc(temporary_root: Path) -> Path:
	local_pandoc = _compatible_local_pandoc()
	if local_pandoc is not None:
		return local_pandoc
	archive_path = temporary_root / f"pandoc-{PANDOC_VERSION}-windows-x86_64.zip"
	_download_verified(PANDOC_WINDOWS_URL, PANDOC_WINDOWS_SHA256, archive_path)
	destination = temporary_root / "pandoc" / "bin" / "pandoc.exe"
	destination.parent.mkdir(parents=True)
	try:
		with (
			zipfile.ZipFile(archive_path) as archive,
			archive.open(PANDOC_WINDOWS_MEMBER) as source,
			destination.open("wb") as output,
		):
			shutil.copyfileobj(source, output)
	except (KeyError, OSError, zipfile.BadZipFile) as error:
		raise RuntimeError(f"the verified Pandoc archive is invalid: {error}") from error
	return destination


def prepare_linux_pandoc(temporary_root: Path) -> Path:
	archive_path = temporary_root / f"pandoc-{PANDOC_VERSION}-linux-amd64.tar.gz"
	_download_verified(PANDOC_LINUX_URL, PANDOC_LINUX_SHA256, archive_path)
	destination = temporary_root / "pandoc" / "bin" / "pandoc"
	destination.parent.mkdir(parents=True)
	try:
		with tarfile.open(archive_path, "r:gz") as archive:
			source = archive.extractfile(PANDOC_LINUX_MEMBER)
			if source is None:
				raise RuntimeError("the verified Pandoc archive does not contain its executable")
			with source, destination.open("wb") as output:
				shutil.copyfileobj(source, output)
	except (KeyError, OSError, tarfile.TarError) as error:
		raise RuntimeError(f"the verified Pandoc archive is invalid: {error}") from error
	destination.chmod(0o755)
	return destination


def _publish(staging: Path, outputs: tuple[Path, ...], destination: Path) -> tuple[Path, ...]:
	destination.mkdir(parents=True, exist_ok=True)
	published = []
	for output in outputs:
		if output.parent != staging or not output.is_file():
			raise RuntimeError(f"expected staged artifact is missing: {output}")
		published_path = destination / output.name
		output.replace(published_path)
		published.append(published_path)
	return tuple(published)


def build_distributions(
	root: Path,
	*,
	bash: Path,
	snapshot: Callable[[], object],
	prepare_pandoc: Callable[[Path], Path],
	temporary_prefix: str,
) -> tuple[Path, ...]:
	"""Build and publish the add-on and documentation ZIP from one snapshot."""
	initial_snapshot = snapshot()
	temporary_parent = root / "build"
	temporary_parent.mkdir(parents=True, exist_ok=True)
	with tempfile.TemporaryDirectory(prefix=temporary_prefix, dir=temporary_parent) as temporary:
		temporary_root = Path(temporary)
		environment = temporary_root / "environment"
		documentation = temporary_root / "documentation"
		artifacts = temporary_root / "artifacts"
		artifacts.mkdir()
		pandoc = prepare_pandoc(temporary_root)
		print("Creating a temporary Python environment...", flush=True)
		venv.EnvBuilder(with_pip=True).create(environment)
		python = _environment_python(environment)
		child_environment = os.environ.copy()
		child_environment["PYTHONNOUSERSITE"] = "1"
		print("Installing the pinned build dependencies...", flush=True)
		subprocess.run(
			(
				str(python), "-m", "pip", "--isolated", "install",
				"--disable-pip-version-check", "--no-input", "--no-cache-dir",
				"-r", str(root / "tools" / "requirements-build.txt"),
			),
			cwd=root,
			env=child_environment,
			check=True,
		)
		print("Rendering and validating documentation...", flush=True)
		documentation_environment = child_environment.copy()
		documentation_environment["PYTHON"] = python.as_posix()
		documentation_environment["PANDOC"] = pandoc.as_posix()
		subprocess.run(
			(
				str(bash), "tools/build_documentation.sh", "--output-only",
				documentation.relative_to(root).as_posix(),
			),
			cwd=root,
			env=documentation_environment,
			check=True,
		)
		print(f"Building {buildVars.addon_info['summary']}...", flush=True)
		subprocess.run(
			(
				str(python), "-m", "SCons", "-Q", "addon",
				f"OUTPUT_DIRECTORY={artifacts}",
				f"DOCUMENTATION_DIRECTORY={documentation}",
				f"SCONS_STATE_DIRECTORY={temporary_root / 'scons'}",
			),
			cwd=root,
			env=child_environment,
			check=True,
		)
		subprocess.run(
			(
				str(python), str(root / "tools" / "documentation_archive.py"),
				str(documentation), str(artifacts),
			),
			cwd=root,
			env=child_environment,
			check=True,
		)
		if snapshot() != initial_snapshot:
			raise RuntimeError("the source snapshot changed during the build; retry from the current state")
		outputs = tuple(sorted(path for path in artifacts.iterdir() if path.is_file()))
		if {path.name for path in outputs} != expected_artifact_names():
			raise RuntimeError(
				"the staged distributable artifacts do not have the expected names: "
				f"{outputs!r}"
			)
		published = _publish(artifacts, outputs, root / "dist")
	print(f"{buildVars.addon_info['summary']} build complete. The two artifacts are in: {root / 'dist'}")
	return published
