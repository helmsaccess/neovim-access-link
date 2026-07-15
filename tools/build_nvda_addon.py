#!/usr/bin/env python3
"""Build a deterministic NVDA add-on archive with pure-Python dependencies."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import pathlib
import re
import shutil
import sys
import tempfile
import zipfile

from configobj import ConfigObj

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import buildVars

PROTOCOL_MODULES = (
    "codec.py", "local_client.py", "messages.py", "nvim_rpc.py", "reconnect.py",
    "session.py", "stdio_client.py", "text.py",
)
CORE_MODULES = (
    "__init__.py", "braille.py", "connection_instances.py", "connection_profiles.py",
    "connection_targets.py", "diagnostics.py",
    "frontend_policy.py", "gate.py", "local_install.py", "local_sessions.py", "speech.py",
    "ssh_install.py", "ssh_sessions.py",
)
API_VERSION = re.compile(r"^(0|\d{4})\.\d(?:\.\d)?$")
ADDON_VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def write_manifest(path: pathlib.Path) -> None:
    """Generate the NVDA manifest from the central product metadata."""
    manifest = buildVars.manifest()
    path.write_text(
        "".join(
            f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
            for key, value in manifest.items()
        ),
        encoding="utf-8",
    )


def validate_manifest(path: pathlib.Path) -> ConfigObj:
    manifest = ConfigObj(str(path), encoding="utf-8", list_values=True)
    required = (
        "name", "summary", "description", "author", "version",
        "minimumNVDAVersion", "lastTestedNVDAVersion",
    )
    for field in required:
        value = manifest.get(field)
        if not isinstance(value, str) or not value:
            raise RuntimeError(f"manifest field {field} must be one non-empty string, got {value!r}")
    for field in ("minimumNVDAVersion", "lastTestedNVDAVersion"):
        if not API_VERSION.fullmatch(manifest[field]):
            raise RuntimeError(f"invalid NVDA API version in {field}: {manifest[field]!r}")
    if ADDON_VERSION.fullmatch(manifest["version"]) is None:
        raise RuntimeError(f"invalid Add-on Store version: {manifest['version']!r}")
    def api_tuple(value: str) -> tuple[int, int, int]:
        parts = [int(part) for part in value.split(".")]
        return tuple((parts + [0])[:3])
    if api_tuple(manifest["minimumNVDAVersion"]) > api_tuple(manifest["lastTestedNVDAVersion"]):
        raise RuntimeError("minimumNVDAVersion must not exceed lastTestedNVDAVersion")
    return manifest


def copy_python_files(source: pathlib.Path, destination: pathlib.Path, names: tuple[str, ...]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(source / name, destination / name)


def build() -> pathlib.Path:
    metadata = buildVars.manifest()
    artifact_version = buildVars.artifact_version()
    output = ROOT / "dist" / f"{metadata['name']}-{artifact_version}.nvda-addon"
    msgpack_distribution = importlib.metadata.distribution("msgpack")
    if msgpack_distribution.version != "1.1.1":
        raise RuntimeError(f"msgpack 1.1.1 required, found {msgpack_distribution.version}")
    msgpack_source = pathlib.Path(msgpack_distribution.locate_file("msgpack"))
    with tempfile.TemporaryDirectory() as temporary:
        stage = pathlib.Path(temporary)
        write_manifest(stage / "manifest.ini")
        shutil.copy2(ROOT / "LICENSE", stage / "LICENSE")
        staged_manifest = validate_manifest(stage / "manifest.ini")
        if dict(staged_manifest) != metadata:
            raise RuntimeError("generated manifest differs from central product metadata")
        shutil.copytree(ROOT / "nvda-addon" / "addon", stage, dirs_exist_ok=True)
        plugin = stage / "globalPlugins" / metadata["name"]
        (plugin / "build_info.py").write_text(
            f"ARTIFACT_VERSION = {artifact_version!r}\n",
            encoding="utf-8",
        )
        core = plugin / "core"
        copy_python_files(ROOT / "protocol" / "python" / "nvim_nvda_protocol", core, PROTOCOL_MODULES)
        copy_python_files(ROOT / "nvda-addon" / "core" / "nvim_nvda_core", core, CORE_MODULES)
        package_spec = importlib.util.spec_from_file_location(
            "nvim_nvda_build_user_package", ROOT / "tools" / "build_user_package.py"
        )
        if package_spec is None or package_spec.loader is None:
            raise RuntimeError("cannot load rootless package builder")
        package_builder = importlib.util.module_from_spec(package_spec)
        package_spec.loader.exec_module(package_builder)
        package_builder.linux_component_config()
        server_package = package_builder.build()
        resources = plugin / "resources"
        resources.mkdir(exist_ok=True)
        shutil.copy2(server_package, resources / "server-user.tar.gz")
        shutil.copy2(package_builder.COMPONENT_CONFIG, resources / "linux-components.json")
        shutil.copytree(
            ROOT / "neovim-plugin", resources / "neovim-plugin",
            ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
        )
        vendor = plugin / "vendor" / "msgpack"
        vendor.mkdir(parents=True)
        for source in msgpack_source.glob("*.py"):
            shutil.copy2(source, vendor / source.name)
        license_source = pathlib.Path(msgpack_distribution.locate_file("msgpack-1.1.1.dist-info/COPYING"))
        shutil.copy2(license_source, plugin / "vendor" / "MSGPACK-LICENSE.txt")
        (plugin / "vendor" / "THIRD_PARTY_NOTICES.txt").write_text(
            "msgpack-python 1.1.1, Apache License 2.0, https://msgpack.org/\n",
            encoding="utf-8",
        )
        forbidden = list(stage.rglob("*.so")) + list(stage.rglob("*.pyc"))
        if forbidden:
            raise RuntimeError(f"non-portable files in add-on: {forbidden}")
        output.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in sorted(path for path in stage.rglob("*") if path.is_file()):
                relative = source.relative_to(stage).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, source.read_bytes(), compresslevel=9)
        output.chmod(0o644)
    return output


if __name__ == "__main__":
    result = build()
    print(f"built {result} ({result.stat().st_size} bytes)")
