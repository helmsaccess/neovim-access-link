#!/usr/bin/env python3
"""Build the relocatable, rootless server-component package."""

from __future__ import annotations

import importlib.metadata
import json
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile
import zipapp


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import buildVars

COMPONENT_CONFIG = ROOT / "neovim-plugin" / "config" / "linux-components.json"


def linux_component_config() -> dict:
    value = json.loads(COMPONENT_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Linux component configuration must be an object")
    claim = value.get("sessionClaim", {})
    if not isinstance(claim, dict):
        raise RuntimeError("session claim configuration must be an object")
    neovim_key = claim.get("neovimKey", "")
    gesture = claim.get("nvdaGesture", "")
    match = re.fullmatch(r"<F([1-9]|1\d|2[0-4])>", neovim_key)
    if value.get("format") != 1 or match is None or gesture != f"kb:f{match.group(1)}":
        raise RuntimeError("invalid or inconsistent Linux component configuration")
    return value

def project_version() -> str:
    return buildVars.version()


def copy_python_package(source: pathlib.Path, destination: pathlib.Path) -> None:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def build() -> pathlib.Path:
    version = project_version()
    linux_component_config()
    output = ROOT / "dist" / f"{buildVars.product_slug()}-{version}-user.tar.gz"
    with tempfile.TemporaryDirectory() as temporary_name:
        temporary = pathlib.Path(temporary_name)
        package = temporary / f"server-components-{version}"
        application = temporary / "zipapp"
        application.mkdir()
        copy_python_package(
            ROOT / "bridge" / "python" / "nvim_nvda_bridge",
            application / "nvim_nvda_bridge",
        )
        copy_python_package(
            ROOT / "protocol" / "python" / "nvim_nvda_protocol",
            application / "nvim_nvda_protocol",
        )
        msgpack = importlib.metadata.distribution("msgpack")
        if msgpack.version != "1.1.1":
            raise RuntimeError(f"msgpack 1.1.1 required, found {msgpack.version}")
        copy_python_package(pathlib.Path(msgpack.locate_file("msgpack")), application / "msgpack")
        (application / "__main__.py").write_text(
            "from nvim_nvda_bridge.__main__ import main\nraise SystemExit(main())\n",
            encoding="utf-8",
        )
        bridge = package / "bin" / "nvim-nvda-bridge"
        bridge.parent.mkdir(parents=True)
        zipapp.create_archive(application, bridge, interpreter="/usr/bin/env python3", compressed=True)
        bridge.chmod(0o755)
        plugin = package / "share" / "nvim" / "site" / "pack" / "nvim-nvda" / "start" / "nvim-nvda"
        shutil.copytree(ROOT / "neovim-plugin", plugin, ignore=shutil.ignore_patterns("tests"))
        config = package / "config"
        config.mkdir()
        shutil.copy2(COMPONENT_CONFIG, config / COMPONENT_CONFIG.name)
        shutil.copy2(ROOT / "packaging" / "install_user.py", package / "install.py")
        shutil.copy2(ROOT / "LICENSE", package / "LICENSE")
        (package / "install.py").chmod(0o755)
        output.parent.mkdir(exist_ok=True)
        with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(package, arcname=package.name)
    return output


if __name__ == "__main__":
    print(build())
