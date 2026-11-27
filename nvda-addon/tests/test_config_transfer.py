from __future__ import annotations

import io
import os
import pathlib
import tarfile
import tempfile
import unittest
from unittest import mock

from nvim_nvda_core import ImportedConfigInstaller, LocalConfigArchiveBuilder


class ConfigTransferTests(unittest.TestCase):
    def make_source(self, root: pathlib.Path) -> pathlib.Path:
        source = root / "windows-config"
        (source / "lua" / "settings").mkdir(parents=True)
        (source / "init.lua").write_text('require("settings")\n', encoding="utf-8")
        (source / "lua" / "settings" / "init.lua").write_text(
            "vim.opt.number = true\n",
            encoding="utf-8",
        )
        (source / "lazy-lock.json").write_text('{"oil.nvim": {}}\n', encoding="utf-8")
        return source

    def test_complete_configuration_round_trips_with_private_non_executable_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            source = self.make_source(root)
            archive = LocalConfigArchiveBuilder().build(source)
            archive_path = root / "config.tar.gz"
            archive_path.write_bytes(archive.payload)
            destination = root / "linux-config" / "nvim"

            imported = ImportedConfigInstaller().install(archive_path, destination)

            self.assertTrue(archive.success, archive.diagnostics)
            self.assertEqual(3, archive.file_count)
            self.assertTrue(imported.success, imported.diagnostics)
            self.assertEqual('require("settings")\n', (destination / "init.lua").read_text())
            self.assertEqual(
                "vim.opt.number = true\n",
                (destination / "lua" / "settings" / "init.lua").read_text(),
            )
            self.assertTrue((destination / "lazy-lock.json").is_file())
            with tarfile.open(fileobj=io.BytesIO(archive.payload), mode="r:gz") as packaged:
                self.assertEqual(0o600, packaged.getmember("init.lua").mode)
                self.assertEqual(0o700, packaged.getmember("lua").mode)

    def test_existing_complete_configuration_directory_is_backed_up(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            source = self.make_source(root)
            archive = LocalConfigArchiveBuilder().build(source)
            archive_path = root / "config.tar.gz"
            archive_path.write_bytes(archive.payload)
            destination = root / "config" / "nvim"
            (destination / "lua").mkdir(parents=True)
            (destination / "init.lua").write_text("old init\n", encoding="utf-8")
            (destination / "lua" / "old.lua").write_text("old module\n", encoding="utf-8")

            imported = ImportedConfigInstaller().install(archive_path, destination)

            self.assertTrue(imported.success, imported.diagnostics)
            self.assertEqual(1, len(imported.backup_paths))
            backup = pathlib.Path(imported.backup_paths[0])
            self.assertEqual("old init\n", (backup / "init.lua").read_text(encoding="utf-8"))
            self.assertEqual("old module\n", (backup / "lua" / "old.lua").read_text(encoding="utf-8"))
            self.assertFalse((destination / "lua" / "old.lua").exists())

    def test_builder_rejects_missing_entrypoint_and_size_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            missing = root / "missing-entrypoint"
            missing.mkdir()
            (missing / "module.lua").write_text("return {}", encoding="utf-8")
            self.assertFalse(LocalConfigArchiveBuilder().build(missing).success)

            source = self.make_source(root)

            with mock.patch("nvim_nvda_core.config_transfer.MAX_CONFIG_BYTES", 1):
                oversized = LocalConfigArchiveBuilder().build(source)
            self.assertFalse(oversized.success)
            self.assertIn("exceeds", oversized.diagnostics)

            with mock.patch("nvim_nvda_core.config_transfer.MAX_CONFIG_ENTRIES", 2):
                too_many_entries = LocalConfigArchiveBuilder().build(source)
            self.assertFalse(too_many_entries.success)
            self.assertIn("more than 2 entries", too_many_entries.diagnostics)

    def test_builder_rejects_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            source = self.make_source(pathlib.Path(directory_name))
            try:
                (source / "linked.lua").symlink_to(source / "init.lua")
            except OSError as error:
                if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                    self.skipTest("Windows does not grant permission to create symbolic links")
                raise
            self.assertFalse(LocalConfigArchiveBuilder().build(source).success)

    def test_init_vim_and_empty_directories_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            source = root / "windows-config"
            (source / "after" / "plugin").mkdir(parents=True)
            (source / "init.vim").write_text("set number\n", encoding="utf-8")
            archive = LocalConfigArchiveBuilder().build(source)
            archive_path = root / "config.tar.gz"
            archive_path.write_bytes(archive.payload)
            destination = root / "config" / "nvim"

            imported = ImportedConfigInstaller().install(archive_path, destination)

            self.assertTrue(archive.success, archive.diagnostics)
            self.assertTrue(imported.success, imported.diagnostics)
            self.assertEqual("set number\n", (destination / "init.vim").read_text(encoding="utf-8"))
            self.assertTrue((destination / "after" / "plugin").is_dir())

    def test_installer_rejects_traversal_and_link_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "config" / "nvim"
            for name, configure in (
                ("traversal", lambda member: setattr(member, "name", "../outside")),
                ("link", lambda member: setattr(member, "type", tarfile.SYMTYPE)),
            ):
                archive_path = root / f"{name}.tar.gz"
                with tarfile.open(archive_path, "w:gz") as archive:
                    member = tarfile.TarInfo("init.lua")
                    member.size = 1
                    configure(member)
                    archive.addfile(member, io.BytesIO(b"x"))
                result = ImportedConfigInstaller().install(archive_path, destination)
                self.assertFalse(result.success)
                self.assertFalse(destination.exists())
            self.assertFalse((root / "config" / "outside").exists())

    def test_invalid_archive_does_not_touch_existing_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "config" / "nvim"
            destination.mkdir(parents=True)
            original = destination / "init.lua"
            original.write_text("keep me\n", encoding="utf-8")
            archive_path = root / "invalid.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                member = tarfile.TarInfo("init.lua")
                member.size = 1
                archive.addfile(member, io.BytesIO(b"x"))
                duplicate = tarfile.TarInfo("./init.lua")
                duplicate.size = 1
                archive.addfile(duplicate, io.BytesIO(b"y"))

            imported = ImportedConfigInstaller().install(archive_path, destination)

            self.assertFalse(imported.success)
            self.assertEqual("keep me\n", original.read_text(encoding="utf-8"))
            self.assertEqual([], list(destination.parent.glob(".nvim.new-*")))

    def test_installer_rejects_non_archive_and_unusual_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            invalid_archive = root / "config.tar.gz"
            invalid_archive.write_bytes(b"not a gzip archive")
            destination = root / "config" / "nvim"
            self.assertFalse(ImportedConfigInstaller().install(invalid_archive, destination).success)

            valid_source = self.make_source(root)
            valid_archive = LocalConfigArchiveBuilder().build(valid_source)
            valid_archive_path = root / "valid.tar.gz"
            valid_archive_path.write_bytes(valid_archive.payload)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("not a directory", encoding="utf-8")
            self.assertFalse(ImportedConfigInstaller().install(valid_archive_path, destination).success)
            self.assertEqual("not a directory", destination.read_text(encoding="utf-8"))

            destination.unlink()
            actual_directory = root / "actual-config"
            actual_directory.mkdir()
            try:
                destination.symlink_to(actual_directory, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory links unavailable: {error}")
            self.assertFalse(ImportedConfigInstaller().install(valid_archive_path, destination).success)
            self.assertTrue(destination.is_symlink())

    def test_failed_atomic_replacement_restores_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            source = self.make_source(root)
            archive = LocalConfigArchiveBuilder().build(source)
            archive_path = root / "config.tar.gz"
            archive_path.write_bytes(archive.payload)
            destination = root / "config" / "nvim"
            destination.mkdir(parents=True)
            (destination / "init.lua").write_text("keep me\n", encoding="utf-8")
            real_replace = os.replace

            def replace(source_path, target_path):
                if pathlib.Path(source_path).name.startswith(".nvim.new-"):
                    raise OSError("simulated replacement failure")
                return real_replace(source_path, target_path)

            with mock.patch("nvim_nvda_core.config_transfer.os.replace", side_effect=replace):
                imported = ImportedConfigInstaller().install(archive_path, destination)

            self.assertFalse(imported.success)
            self.assertEqual("keep me\n", (destination / "init.lua").read_text(encoding="utf-8"))

    def test_failed_rollback_retains_backup_and_reports_its_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            source = self.make_source(root)
            archive = LocalConfigArchiveBuilder().build(source)
            archive_path = root / "config.tar.gz"
            archive_path.write_bytes(archive.payload)
            destination = root / "config" / "nvim"
            destination.mkdir(parents=True)
            (destination / "init.lua").write_text("retained backup\n", encoding="utf-8")
            real_replace = os.replace

            def replace(source_path, target_path):
                source_name = pathlib.Path(source_path).name
                if source_name.startswith(".nvim.new-"):
                    raise OSError("simulated replacement failure")
                if source_name.startswith("nvim.neovim-access-link-backup-"):
                    raise OSError("simulated rollback failure")
                return real_replace(source_path, target_path)

            with mock.patch("nvim_nvda_core.config_transfer.os.replace", side_effect=replace):
                imported = ImportedConfigInstaller().install(archive_path, destination)

            self.assertFalse(imported.success)
            self.assertIn("rollback failed", imported.diagnostics)
            backups = list(destination.parent.glob("nvim.neovim-access-link-backup-*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(
                "retained backup\n",
                (backups[0] / "init.lua").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
