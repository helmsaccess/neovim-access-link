#!/usr/bin/env python3
"""Install the extracted Neovim NVDA user package without root privileges."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil


def install(source: pathlib.Path, prefix: pathlib.Path) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the bundled Neovim accessibility components")
    parser.add_argument("--prefix", type=pathlib.Path, default=pathlib.Path("~/.local"))
    args = parser.parse_args()
    install(pathlib.Path(__file__).resolve().parent, args.prefix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
