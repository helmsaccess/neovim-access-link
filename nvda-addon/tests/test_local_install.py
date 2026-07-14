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


if __name__ == "__main__":
    unittest.main()
