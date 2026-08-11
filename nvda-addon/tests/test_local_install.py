from __future__ import annotations

import pathlib
import tempfile
import unittest

from nvim_nvda_core import LocalPluginInstaller, default_local_plugin_directory


class LocalPluginInstallerTests(unittest.TestCase):
    def make_plugin(self, root: pathlib.Path, marker: str) -> pathlib.Path:
        source = root / f"source-{marker}"
        (source / "plugin").mkdir(parents=True)
        (source / "lua" / "nvim_nvda").mkdir(parents=True)
        (source / "plugin" / "nvim_nvda.lua").write_text(marker, encoding="utf-8")
        (source / "lua" / "nvim_nvda" / "init.lua").write_text(marker, encoding="utf-8")
        return source

    def test_default_destination_uses_standard_windows_neovim_data_path(self) -> None:
        destination = default_local_plugin_directory({"LOCALAPPDATA": r"C:\Users\ExampleUser\AppData\Local"})
        self.assertEqual("nvim-nvda", destination.name)
        self.assertEqual(("site", "pack", "nvim-nvda", "start", "nvim-nvda"), destination.parts[-5:])

    def test_install_and_update_replace_only_plugin_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "data" / "site" / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
            installer = LocalPluginInstaller()
            first = installer.install(self.make_plugin(root, "one"), destination)
            self.assertTrue(first.success)
            unrelated = root / "data" / "init.lua"
            unrelated.write_text("user config", encoding="utf-8")
            second = installer.install(self.make_plugin(root, "two"), destination)
            self.assertTrue(second.success)
            self.assertEqual("two", (destination / "plugin" / "nvim_nvda.lua").read_text(encoding="utf-8"))
            self.assertEqual("user config", unrelated.read_text(encoding="utf-8"))
            self.assertEqual([], list(destination.parent.glob(".nvim-nvda.*")))

    def test_missing_or_malformed_source_fails_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "target"
            destination.mkdir()
            marker = destination / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            result = LocalPluginInstaller().install(root / "missing", destination)
            self.assertFalse(result.success)
            self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_uninstall_removes_only_owned_plugin_and_empty_package_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "data" / "site" / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
            unrelated = root / "data" / "site" / "pack" / "other-plugin" / "keep.txt"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("keep", encoding="utf-8")
            installer = LocalPluginInstaller()
            self.assertTrue(installer.install(self.make_plugin(root, "installed"), destination).success)

            result = installer.uninstall(destination)

            self.assertTrue(result.success)
            self.assertFalse(destination.exists())
            self.assertFalse((root / "data" / "site" / "pack" / "nvim-nvda").exists())
            self.assertEqual("keep", unrelated.read_text(encoding="utf-8"))

    def test_uninstall_is_idempotent_and_preserves_nonempty_owned_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
            marker = destination.parent.parent / "keep.txt"
            marker.parent.mkdir(parents=True)
            marker.write_text("user file", encoding="utf-8")

            result = LocalPluginInstaller().uninstall(destination)

            self.assertTrue(result.success)
            self.assertEqual("user file", marker.read_text(encoding="utf-8"))

    def test_uninstall_preserves_configuration_and_backups(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            destination = root / "data" / "site" / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
            configuration = root / "config" / "nvim"
            configuration.mkdir(parents=True)
            init = configuration / "init.lua"
            init.write_text("load access link explicitly\n", encoding="utf-8")
            backup = root / "config" / "nvim.neovim-access-link-backup-example"
            backup.mkdir()
            (backup / "init.lua").write_text("previous config\n", encoding="utf-8")
            installer = LocalPluginInstaller()
            self.assertTrue(installer.install(self.make_plugin(root, "installed"), destination).success)

            result = installer.uninstall(destination)

            self.assertTrue(result.success)
            self.assertEqual("load access link explicitly\n", init.read_text(encoding="utf-8"))
            self.assertEqual("previous config\n", (backup / "init.lua").read_text(encoding="utf-8"))

    def test_install_and_uninstall_reject_non_directory_or_link_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = pathlib.Path(directory_name)
            installer = LocalPluginInstaller()
            file_target = root / "plugin-file"
            file_target.write_text("keep", encoding="utf-8")

            self.assertFalse(installer.install(self.make_plugin(root, "source"), file_target).success)
            self.assertFalse(installer.uninstall(file_target).success)
            self.assertEqual("keep", file_target.read_text(encoding="utf-8"))

            actual_directory = root / "actual-plugin"
            actual_directory.mkdir()
            link_target = root / "plugin-link"
            try:
                link_target.symlink_to(actual_directory, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory links unavailable: {error}")
            self.assertFalse(installer.install(self.make_plugin(root, "linked-source"), link_target).success)
            self.assertFalse(installer.uninstall(link_target).success)
            self.assertTrue(link_target.is_symlink())


if __name__ == "__main__":
    unittest.main()
