"""Safe installation of the optional Neovim starter configuration."""

from __future__ import annotations

import datetime
import os
import pathlib
import shutil
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class StarterConfigResult:
    success: bool
    message: str
    configuration_path: str = ""
    backup_paths: tuple[str, ...] = ()
    diagnostics: str = ""


def default_local_config_directory(environment: dict[str, str] | None = None) -> pathlib.Path:
    values = os.environ if environment is None else environment
    root = values.get("LOCALAPPDATA", "")
    if not isinstance(root, str) or not root or "\0" in root:
        raise ValueError("LOCALAPPDATA is unavailable")
    return pathlib.Path(root) / "nvim"


class StarterConfigInstaller:
    def install(
        self,
        source: pathlib.Path,
        config_directory: pathlib.Path | None = None,
    ) -> StarterConfigResult:
        try:
            destination_directory = config_directory or default_local_config_directory()
        except ValueError as error:
            return StarterConfigResult(
                False, "local Neovim configuration directory is unavailable", diagnostics=str(error)
            )
        source = pathlib.Path(source)
        destination_directory = pathlib.Path(destination_directory)
        destination = destination_directory / "init.lua"
        candidates = (destination, destination_directory / "init.vim")
        temporary = destination_directory / f".init.lua.new-{uuid.uuid4().hex}"
        moved: list[tuple[pathlib.Path, pathlib.Path]] = []
        try:
            if not source.is_file() or source.is_symlink():
                return StarterConfigResult(False, "bundled Neovim starter configuration is unavailable")
            if destination_directory.exists() and (
                not destination_directory.is_dir() or destination_directory.is_symlink()
            ):
                return StarterConfigResult(False, "Neovim configuration target is not a normal directory")
            existing = []
            for candidate in candidates:
                if not os.path.lexists(candidate):
                    continue
                if candidate.is_symlink() or not candidate.is_file():
                    return StarterConfigResult(
                        False,
                        "existing Neovim configuration is not a normal file",
                        diagnostics=str(candidate),
                    )
                existing.append(candidate)

            destination_directory.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, temporary)
            for candidate in existing:
                backup = self._backup_path(candidate)
                os.replace(candidate, backup)
                moved.append((candidate, backup))
            os.replace(temporary, destination)
            return StarterConfigResult(
                True,
                "Neovim starter configuration installed",
                str(destination),
                tuple(str(backup) for _candidate, backup in moved),
            )
        except OSError as error:
            rollback_errors = []
            for original, backup in reversed(moved):
                try:
                    if os.path.lexists(original):
                        original.unlink()
                    shutil.copy2(backup, original)
                except OSError as rollback_error:
                    rollback_errors.append(f"{original}: {rollback_error}")
            diagnostics = str(error)
            if rollback_errors:
                diagnostics += "; rollback failed: " + "; ".join(rollback_errors)
            return StarterConfigResult(
                False,
                "Neovim starter configuration installation failed",
                diagnostics=diagnostics,
            )
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

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
