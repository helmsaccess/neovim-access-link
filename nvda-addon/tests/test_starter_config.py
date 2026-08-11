from __future__ import annotations

import os
import pathlib
import tempfile
import unittest
from unittest import mock

from nvim_nvda_core import StarterConfigInstaller, default_local_config_directory


class StarterConfigInstallerTests(unittest.TestCase):
    def make_source(self, root: pathlib.Path, content: str = "new configuration") -> pathlib.Path:
        source = root / "starter-init.lua"
        source.write_text(content, encoding="utf-8")
        return source

    def test_default_directory_uses_standard_windows_neovim_config_path(self) -> None:
        destination = default_local_config_directory(
            {
                "LOCALAPPDATA": r"C:\Users\ExampleUser\AppData\Local",
            }
        )
        self.assertEqual(("nvim",), destination.parts[-1:])

    def test_install_creates_new_configuration_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "config" / "nvim"

            result = StarterConfigInstaller().install(self.make_source(root), destination)

            self.assertTrue(result.success)
            self.assertEqual("new configuration", (destination / "init.lua").read_text(encoding="utf-8"))
            self.assertEqual(str(destination / "init.lua"), result.configuration_path)
            self.assertEqual((), result.backup_paths)

    def test_existing_lua_and_vim_configurations_are_backed_up_before_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "config" / "nvim"
            destination.mkdir(parents=True)
            (destination / "init.lua").write_text("old lua", encoding="utf-8")
            (destination / "init.vim").write_text("old vim", encoding="utf-8")

            result = StarterConfigInstaller().install(self.make_source(root), destination)

            self.assertTrue(result.success)
            self.assertEqual("new configuration", (destination / "init.lua").read_text(encoding="utf-8"))
            self.assertFalse((destination / "init.vim").exists())
            self.assertEqual(2, len(result.backup_paths))
            backups = {
                pathlib.Path(path).name.split(".neovim-access-link-backup-")[0]: path
                for path in result.backup_paths
            }
            self.assertEqual("old lua", pathlib.Path(backups["init.lua"]).read_text(encoding="utf-8"))
            self.assertEqual("old vim", pathlib.Path(backups["init.vim"]).read_text(encoding="utf-8"))

    def test_failed_replacement_restores_original_and_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "config" / "nvim"
            destination.mkdir(parents=True)
            original = destination / "init.lua"
            original.write_text("keep me", encoding="utf-8")
            real_replace = os.replace

            def replace(source, target):
                if pathlib.Path(source).name.startswith(".init.lua.new-"):
                    raise OSError("simulated replacement failure")
                return real_replace(source, target)

            with mock.patch("nvim_nvda_core.starter_config.os.replace", side_effect=replace):
                result = StarterConfigInstaller().install(self.make_source(root), destination)

            self.assertFalse(result.success)
            self.assertEqual("keep me", original.read_text(encoding="utf-8"))
            backups = list(destination.glob("init.lua.neovim-access-link-backup-*"))
            self.assertEqual(1, len(backups))
            self.assertEqual("keep me", backups[0].read_text(encoding="utf-8"))

    def test_invalid_source_or_target_preserves_existing_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "config" / "nvim"
            destination.mkdir(parents=True)
            original = destination / "init.lua"
            original.write_text("keep me", encoding="utf-8")

            missing = StarterConfigInstaller().install(root / "missing.lua", destination)
            self.assertFalse(missing.success)
            self.assertEqual("keep me", original.read_text(encoding="utf-8"))

            invalid_target = root / "not-a-directory"
            invalid_target.write_text("keep target", encoding="utf-8")
            invalid = StarterConfigInstaller().install(self.make_source(root), invalid_target)
            self.assertFalse(invalid.success)
            self.assertEqual("keep target", invalid_target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
