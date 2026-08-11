"""Safe transfer of a complete Neovim configuration from Windows to Linux."""

from __future__ import annotations

import datetime
import io
import os
import pathlib
import shutil
import stat
import tarfile
import uuid
from dataclasses import dataclass


CONFIGURATION_UNCHANGED = "unchanged"
CONFIGURATION_STARTER = "starter"
CONFIGURATION_COPY_LOCAL = "copyLocal"
CONFIGURATION_MODES = frozenset(
    (CONFIGURATION_UNCHANGED, CONFIGURATION_STARTER, CONFIGURATION_COPY_LOCAL)
)
MAX_CONFIG_FILES = 4096
MAX_CONFIG_ENTRIES = 8192
MAX_CONFIG_BYTES = 32 * 1024 * 1024
MAX_CONFIG_ARCHIVE_BYTES = 40 * 1024 * 1024


@dataclass(frozen=True)
class ConfigArchiveResult:
    success: bool
    message: str
    payload: bytes = b""
    source_path: str = ""
    file_count: int = 0
    byte_count: int = 0
    diagnostics: str = ""


@dataclass(frozen=True)
class ImportedConfigResult:
    success: bool
    message: str
    configuration_path: str = ""
    backup_paths: tuple[str, ...] = ()
    diagnostics: str = ""


def _is_reparse_point(value: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(value, "st_file_attributes", 0) & attribute)


def _is_normal_directory(path: pathlib.Path) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    return stat.S_ISDIR(value.st_mode) and not _is_reparse_point(value)


class LocalConfigArchiveBuilder:
    """Create a bounded archive without following links or preserving Windows modes."""

    def build(self, source: pathlib.Path) -> ConfigArchiveResult:
        source = pathlib.Path(source)
        if not _is_normal_directory(source):
            return ConfigArchiveResult(
                False,
                "local Neovim configuration is not a normal directory",
                source_path=str(source),
            )
        entries: list[tuple[pathlib.Path, pathlib.PurePosixPath, os.stat_result]] = []
        try:
            self._collect(source, pathlib.PurePosixPath(), entries)
            if len(entries) > MAX_CONFIG_ENTRIES:
                raise ValueError(f"configuration contains more than {MAX_CONFIG_ENTRIES} entries")
            names = {relative.as_posix() for _path, relative, value in entries if stat.S_ISREG(value.st_mode)}
            if not names.intersection(("init.lua", "init.vim")):
                return ConfigArchiveResult(
                    False,
                    "local Neovim configuration has no init.lua or init.vim",
                    source_path=str(source),
                )
            file_entries = [entry for entry in entries if stat.S_ISREG(entry[2].st_mode)]
            if len(file_entries) > MAX_CONFIG_FILES:
                raise ValueError(f"configuration contains more than {MAX_CONFIG_FILES} files")
            total_bytes = sum(value.st_size for _path, _relative, value in file_entries)
            if total_bytes > MAX_CONFIG_BYTES:
                raise ValueError(f"configuration exceeds {MAX_CONFIG_BYTES} uncompressed bytes")
            payload = self._archive(entries)
            if payload.getbuffer().nbytes > MAX_CONFIG_ARCHIVE_BYTES:
                raise ValueError("compressed configuration archive exceeds the supported limit")
            return ConfigArchiveResult(
                True,
                "local Neovim configuration archived",
                payload.getvalue(),
                str(source),
                len(file_entries),
                total_bytes,
            )
        except (OSError, ValueError, tarfile.TarError) as error:
            return ConfigArchiveResult(
                False,
                "local Neovim configuration could not be archived safely",
                source_path=str(source),
                diagnostics=str(error),
            )

    def _collect(
        self,
        directory: pathlib.Path,
        relative_directory: pathlib.PurePosixPath,
        entries: list[tuple[pathlib.Path, pathlib.PurePosixPath, os.stat_result]],
    ) -> None:
        with os.scandir(directory) as scanned:
            children = sorted(scanned, key=lambda entry: entry.name.casefold())
        for child in children:
            relative = relative_directory / child.name
            value = child.stat(follow_symlinks=False)
            if child.is_symlink() or _is_reparse_point(value):
                raise ValueError(f"configuration contains a link or reparse point: {relative}")
            if stat.S_ISDIR(value.st_mode):
                entries.append((pathlib.Path(child.path), relative, value))
                self._collect(pathlib.Path(child.path), relative, entries)
            elif stat.S_ISREG(value.st_mode):
                entries.append((pathlib.Path(child.path), relative, value))
            else:
                raise ValueError(f"configuration contains an unsupported file type: {relative}")

    @staticmethod
    def _archive(
        entries: list[tuple[pathlib.Path, pathlib.PurePosixPath, os.stat_result]],
    ) -> io.BytesIO:
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
            for path, relative, value in entries:
                information = tarfile.TarInfo(relative.as_posix())
                information.uid = 0
                information.gid = 0
                information.uname = ""
                information.gname = ""
                information.mtime = 0
                if stat.S_ISDIR(value.st_mode):
                    information.type = tarfile.DIRTYPE
                    information.mode = 0o700
                    archive.addfile(information)
                    continue
                content = path.read_bytes()
                current = path.lstat()
                if (
                    not stat.S_ISREG(current.st_mode)
                    or _is_reparse_point(current)
                    or current.st_size != value.st_size
                    or current.st_mtime_ns != value.st_mtime_ns
                ):
                    raise ValueError(f"configuration changed while it was archived: {relative}")
                information.size = len(content)
                information.mode = 0o600
                archive.addfile(information, io.BytesIO(content))
        payload.seek(0)
        return payload


class ImportedConfigInstaller:
    """Replace one Linux Neovim config directory atomically after full validation."""

    def install(self, archive_path: pathlib.Path, destination: pathlib.Path) -> ImportedConfigResult:
        archive_path = pathlib.Path(archive_path)
        destination = pathlib.Path(destination)
        parent = destination.parent
        staging = parent / f".{destination.name}.new-{uuid.uuid4().hex}"
        backup: pathlib.Path | None = None
        moved_existing = False
        try:
            if not archive_path.is_file() or archive_path.is_symlink():
                return ImportedConfigResult(False, "imported Neovim configuration archive is unavailable")
            if archive_path.stat().st_size > MAX_CONFIG_ARCHIVE_BYTES:
                return ImportedConfigResult(False, "imported Neovim configuration archive is too large")
            if os.path.lexists(destination) and not _is_normal_directory(destination):
                return ImportedConfigResult(False, "Neovim configuration target is not a normal directory")
            parent.mkdir(parents=True, exist_ok=True)
            staging.mkdir(mode=0o700)
            self._extract(archive_path, staging)
            if os.path.lexists(destination):
                backup = self._backup_path(destination)
                os.replace(destination, backup)
                moved_existing = True
            os.replace(staging, destination)
            return ImportedConfigResult(
                True,
                "local Windows Neovim configuration imported",
                str(destination),
                (str(backup),) if backup is not None else (),
            )
        except (OSError, ValueError, tarfile.TarError) as error:
            rollback_error = ""
            if moved_existing and backup is not None and not os.path.lexists(destination):
                try:
                    os.replace(backup, destination)
                except OSError as restore_error:
                    rollback_error = f"; rollback failed: {restore_error}"
            return ImportedConfigResult(
                False,
                "local Windows Neovim configuration import failed",
                diagnostics=f"{error}{rollback_error}",
            )
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def _extract(archive_path: pathlib.Path, staging: pathlib.Path) -> None:
        seen: set[str] = set()
        entries = 0
        files = 0
        total_bytes = 0
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive:
                entries += 1
                if entries > MAX_CONFIG_ENTRIES:
                    raise ValueError("configuration archive contains too many entries")
                relative = pathlib.PurePosixPath(member.name)
                if (
                    not member.name
                    or member.name.startswith("/")
                    or "\\" in member.name
                    or any(part in ("", ".", "..") for part in relative.parts)
                ):
                    raise ValueError(f"invalid configuration archive path: {member.name!r}")
                normalized = relative.as_posix()
                if normalized in seen:
                    raise ValueError(f"duplicate configuration archive path: {normalized}")
                seen.add(normalized)
                target = staging.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                    target.chmod(0o700)
                    continue
                if not member.isfile():
                    raise ValueError(f"unsupported configuration archive entry: {normalized}")
                files += 1
                total_bytes += member.size
                if files > MAX_CONFIG_FILES or total_bytes > MAX_CONFIG_BYTES:
                    raise ValueError("configuration archive exceeds the supported limits")
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"configuration archive file is unreadable: {normalized}")
                with target.open("xb") as destination:
                    shutil.copyfileobj(source, destination)
                target.chmod(0o600)
        if not any((staging / name).is_file() for name in ("init.lua", "init.vim")):
            raise ValueError("configuration archive has no init.lua or init.vim")

    @staticmethod
    def _backup_path(path: pathlib.Path) -> pathlib.Path:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for _attempt in range(100):
            candidate = path.with_name(
                f"{path.name}.neovim-access-link-backup-{timestamp}-{uuid.uuid4().hex[:8]}"
            )
            if not os.path.lexists(candidate):
                return candidate
        raise OSError("could not allocate a unique Neovim configuration backup path")
