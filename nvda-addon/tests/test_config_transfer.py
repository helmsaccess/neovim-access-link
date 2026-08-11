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

    def test_builder_rejects_missing_entrypoint_links_and_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            missing = root / "missing-entrypoint"
            missing.mkdir()
            (missing / "module.lua").write_text("return {}", encoding="utf-8")
            self.assertFalse(LocalConfigArchiveBuilder().build(missing).success)

            linked = self.make_source(root)
            (linked / "linked.lua").symlink_to(linked / "init.lua")
            self.assertFalse(LocalConfigArchiveBuilder().build(linked).success)
            (linked / "linked.lua").unlink()

            with mock.patch("nvim_nvda_core.config_transfer.MAX_CONFIG_BYTES", 1):
                oversized = LocalConfigArchiveBuilder().build(linked)
            self.assertFalse(oversized.success)
            self.assertIn("exceeds", oversized.diagnostics)

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


if __name__ == "__main__":
    unittest.main()
