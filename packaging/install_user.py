#!/usr/bin/env python3
"""Install the extracted Neovim NVDA user package without root privileges."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil


def _neovim_config_directory() -> pathlib.Path:
    configured = os.environ.get("XDG_CONFIG_HOME", "")
    if "\0" in configured:
        raise ValueError("XDG_CONFIG_HOME contains a null byte")
    root = pathlib.Path(configured).expanduser() if configured else pathlib.Path("~/.config").expanduser()
    if not root.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be an absolute path")
    return root / "nvim"


def install(
    source: pathlib.Path,
    prefix: pathlib.Path,
    install_starter_config: bool = False,
    import_config_archive: pathlib.Path | None = None,
) -> None:
    if install_starter_config and import_config_archive is not None:
        raise ValueError("only one Neovim configuration mode may be selected")
    prefix = prefix.expanduser().resolve()
    bridge_source = source / "bin" / "nvim-nvda-bridge"
    bridge_target = prefix / "bin" / "nvim-nvda-bridge"
    plugin_source = source / "share" / "nvim" / "site" / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
    plugin_target = prefix / "share" / "nvim" / "site" / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
    config_source = source / "config" / "linux-components.json"
    config_target = prefix / "share" / "nvim-nvda" / "linux-components.json"
    bridge_target.parent.mkdir(parents=True, exist_ok=True)
    plugin_target.parent.mkdir(parents=True, exist_ok=True)
    temporary = bridge_target.with_suffix(".new")
    shutil.copy2(bridge_source, temporary)
    temporary.chmod(0o755)
    os.replace(temporary, bridge_target)
    if plugin_target.exists():
        shutil.rmtree(plugin_target)
    shutil.copytree(plugin_source, plugin_target)
    config_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_source, config_target)
    print(f"installed bridge: {bridge_target}")
    print(f"installed Neovim plugin: {plugin_target}")
    print(f"installed component configuration: {config_target}")
    if install_starter_config:
        from starter_config import StarterConfigInstaller

        starter_result = StarterConfigInstaller().install(
            source / "config" / "starter-init.lua",
            _neovim_config_directory(),
        )
        if not starter_result.success:
            raise RuntimeError(f"{starter_result.message}: {starter_result.diagnostics}")
        print(f"installed starter configuration: {starter_result.configuration_path}")
        for backup in starter_result.backup_paths:
            print(f"backed up Neovim configuration: {backup}")
    elif import_config_archive is not None:
        from config_transfer import ImportedConfigInstaller

        imported_result = ImportedConfigInstaller().install(
            import_config_archive,
            _neovim_config_directory(),
        )
        if not imported_result.success:
            raise RuntimeError(f"{imported_result.message}: {imported_result.diagnostics}")
        print(f"imported Windows Neovim configuration: {imported_result.configuration_path}")
        for backup in imported_result.backup_paths:
            print(f"backed up Neovim configuration: {backup}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the bundled Neovim accessibility components")
    parser.add_argument("--prefix", type=pathlib.Path, default=pathlib.Path("~/.local"))
    configuration = parser.add_mutually_exclusive_group()
    configuration.add_argument("--install-starter-config", action="store_true")
    configuration.add_argument("--import-config-archive", type=pathlib.Path)
    args = parser.parse_args()
    install(
        pathlib.Path(__file__).resolve().parent,
        args.prefix,
        args.install_starter_config,
        args.import_config_archive,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
