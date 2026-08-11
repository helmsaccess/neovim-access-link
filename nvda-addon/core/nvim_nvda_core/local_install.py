"""Atomic per-user installation of the bundled Neovim plugin on Windows."""

from __future__ import annotations

import os
import pathlib
import shutil
import stat
import uuid

from .ssh_install import InstallResult


def _is_normal_directory(path: pathlib.Path) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISDIR(value.st_mode) and not bool(
        getattr(value, "st_file_attributes", 0) & reparse_attribute
    )


def default_local_plugin_directory(environment: dict[str, str] | None = None) -> pathlib.Path:
    values = os.environ if environment is None else environment
    root = values.get("LOCALAPPDATA", "")
    if not isinstance(root, str) or not root or "\0" in root:
        raise ValueError("LOCALAPPDATA is unavailable")
    return (
        pathlib.Path(root) / "nvim-data" / "site" / "pack"
        / "nvim-nvda" / "start" / "nvim-nvda"
    )


class LocalPluginInstaller:
    def install(self, source: pathlib.Path, destination: pathlib.Path | None = None) -> InstallResult:
        try:
            destination = destination or default_local_plugin_directory()
        except ValueError as error:
            return InstallResult(False, "local Neovim data directory is unavailable", str(error))
        source = pathlib.Path(source)
        destination = pathlib.Path(destination)
        if not self._valid_source(source):
            return InstallResult(False, "bundled local Neovim plugin is unavailable")
        if os.path.lexists(destination) and not _is_normal_directory(destination):
            return InstallResult(False, "local Neovim plugin target is not a directory")
        parent = destination.parent
        temporary = parent / f".{destination.name}.new-{uuid.uuid4().hex}"
        backup = parent / f".{destination.name}.old-{uuid.uuid4().hex}"
        moved_existing = False
        try:
            parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, temporary, symlinks=False)
            if os.path.lexists(destination):
                os.replace(destination, backup)
                moved_existing = True
            os.replace(temporary, destination)
            if moved_existing:
                shutil.rmtree(backup)
            return InstallResult(
                True, "Local Neovim plugin installed",
                f"installed Neovim plugin: {destination}",
            )
        except OSError as error:
            try:
                if moved_existing and os.path.lexists(backup) and not os.path.lexists(destination):
                    os.replace(backup, destination)
            except OSError:
                pass
            return InstallResult(False, "local Neovim plugin installation failed", str(error))
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
            if os.path.lexists(destination):
                shutil.rmtree(backup, ignore_errors=True)

    def uninstall(self, destination: pathlib.Path | None = None) -> InstallResult:
        try:
            destination = destination or default_local_plugin_directory()
        except ValueError as error:
            return InstallResult(False, "local Neovim data directory is unavailable", str(error))
        destination = pathlib.Path(destination)
        if os.path.lexists(destination) and not _is_normal_directory(destination):
            return InstallResult(False, "local Neovim plugin target is not a directory")
        try:
            if os.path.lexists(destination):
                shutil.rmtree(destination)
            # The installer owns these two package directories, but remove them
            # only while empty so unrelated files are never lost.
            for directory in (destination.parent, destination.parent.parent):
                try:
                    directory.rmdir()
                except FileNotFoundError:
                    pass
                except OSError:
                    break
            return InstallResult(
                True, "Local Neovim plugin removed",
                f"removed Neovim plugin: {destination}",
            )
        except OSError as error:
            return InstallResult(False, "local Neovim plugin removal failed", str(error))

    @staticmethod
    def _valid_source(source: pathlib.Path) -> bool:
        try:
            return (
                source.is_dir()
                and (source / "plugin" / "nvim_nvda.lua").is_file()
                and (source / "lua" / "nvim_nvda" / "init.lua").is_file()
                and not any(path.is_symlink() for path in source.rglob("*"))
            )
        except OSError:
            return False
