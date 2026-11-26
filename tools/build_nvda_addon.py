#!/usr/bin/env python3
"""Build a deterministic NVDA add-on archive with pure-Python dependencies."""

from __future__ import annotations

import argparse
import gettext
import importlib.metadata
import importlib.util
import json
import pathlib
import re
import shutil
import sys
import tempfile
import urllib.parse
import zipfile

from configobj import ConfigObj

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import buildVars  # noqa: E402
from tools.documentation_layout import (  # noqa: E402
    install_generated_documentation,
    validate_installed_documents,
)
from tools.gettext_catalog import compile_catalogs  # noqa: E402

PROTOCOL_MODULES = (
    "braille_exploration.py", "braille_navigation.py", "braille_routing_actions.py",
    "clipboard.py", "codec.py",
    "cursor_routing.py", "developer_context.py", "exploration.py",
    "local_client.py", "messages.py", "plugin_manager.py",
    "numbered_choice.py", "nvim_rpc.py", "reconnect.py", "session.py", "stdio_client.py",
    "signature_help.py", "terminal_control.py", "text.py", "tutor.py",
)
CORE_MODULES = (
    "__init__.py", "braille.py", "braille_exploration_state.py",
    "braille_routing_repeats.py", "connection_coordinator.py",
    "connection_instances.py",
    "connection_profiles.py", "config_transfer.py",
    "connection_targets.py", "diagnostics.py", "exploration_state.py", "held_context_state.py",
    "numbered_choice_state.py",
    "frontend_policy.py", "gate.py", "local_install.py", "local_sessions.py", "speech.py",
    "starter_config.py",
    "service_registrar.py", "ssh_install.py", "ssh_sessions.py",
)
API_VERSION = re.compile(r"^(?:0|[1-9]\d{3})\.\d+(?:\.\d+)?$")
ADDON_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
ADDON_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
AUTHOR_WITH_EMAIL = re.compile(r"^.+\s<[^<>\s@]+@[^<>\s@]+>$")
NVDA_TEMPLATE_MANIFEST_FIELDS = frozenset({
    "name", "summary", "description", "author", "url", "version", "changelog",
    "docFileName", "minimumNVDAVersion", "lastTestedNVDAVersion", "updateChannel",
})
LOCALIZED_MANIFEST_FIELDS = frozenset({"summary", "description", "changelog"})
MULTILINE_MANIFEST_FIELDS = frozenset({"description", "changelog"})


def find_msgpack_license(distribution: importlib.metadata.Distribution) -> pathlib.Path:
    distribution_directory = f"msgpack-{distribution.version}.dist-info"
    candidates = (
        pathlib.Path(distribution.locate_file(pathlib.Path(distribution_directory) / "COPYING")),
        pathlib.Path(
            distribution.locate_file(
                pathlib.Path(distribution_directory) / "licenses" / "COPYING"
            )
        ),
    )
    existing = tuple(path for path in candidates if path.is_file())
    if len(existing) != 1:
        raise RuntimeError(
            "expected exactly one msgpack COPYING file in a supported distribution layout, "
            f"found {existing!r}"
        )
    return existing[0]


def _manifest_value(key: str, value: str) -> str:
    if "\n" not in value:
        return json.dumps(value, ensure_ascii=False)
    if '"""' in value:
        raise RuntimeError(f"manifest field {key} contains an unsupported triple quote")
    return f'"""{value}"""'


def write_manifest(
    path: pathlib.Path,
    manifest: dict[str, str],
    *,
    template: pathlib.Path | None = None,
) -> None:
    """Render serialized NVDA fields into a base or localized manifest."""
    values = {key: _manifest_value(key, value) for key, value in manifest.items()}
    if template is None:
        text = "".join(f"{key} = {value}\n" for key, value in values.items())
    else:
        text = template.read_text(encoding="utf-8").format_map(
            {f"addon_{key}": value for key, value in values.items()}
        )
    path.write_text(text, encoding="utf-8", newline="\n")


def validate_manifest(path: pathlib.Path) -> ConfigObj:
    manifest = ConfigObj(str(path), encoding="utf-8", list_values=True)
    fields = set(manifest)
    if fields != NVDA_TEMPLATE_MANIFEST_FIELDS:
        missing = sorted(NVDA_TEMPLATE_MANIFEST_FIELDS - fields)
        unexpected = sorted(fields - NVDA_TEMPLATE_MANIFEST_FIELDS)
        raise RuntimeError(
            f"manifest fields differ from the NVDA AddonTemplate; "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )
    for field in NVDA_TEMPLATE_MANIFEST_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"manifest field {field} must be one non-empty string, got {value!r}")
        if value != value.strip():
            raise RuntimeError(f"manifest field {field} has leading or trailing whitespace")
        if "\x00" in value or "\r" in value:
            raise RuntimeError(f"manifest field {field} contains unsupported control characters")
        if field not in MULTILINE_MANIFEST_FIELDS and "\n" in value:
            raise RuntimeError(f"manifest field {field} must be a single line")
    if ADDON_NAME.fullmatch(manifest["name"]) is None:
        raise RuntimeError(f"manifest name must be one CamelCase-compatible identifier: {manifest['name']!r}")
    if AUTHOR_WITH_EMAIL.fullmatch(manifest["author"]) is None:
        raise RuntimeError("manifest author must include a name and contact email in angle brackets")
    for field in ("minimumNVDAVersion", "lastTestedNVDAVersion"):
        if not API_VERSION.fullmatch(manifest[field]):
            raise RuntimeError(f"invalid NVDA API version in {field}: {manifest[field]!r}")
    if ADDON_VERSION.fullmatch(manifest["version"]) is None:
        raise RuntimeError(f"Add-on Store version must use MAJOR.MINOR.PATCH: {manifest['version']!r}")
    url = urllib.parse.urlsplit(manifest["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise RuntimeError("manifest url must be one absolute HTTPS URL without credentials")
    if pathlib.PurePath(manifest["docFileName"]).name != manifest["docFileName"]:
        raise RuntimeError("manifest docFileName must be one portable file name")
    if pathlib.PurePath(manifest["docFileName"]).suffix.casefold() != ".html":
        raise RuntimeError("manifest docFileName must name an HTML document")
    default_document = path.parent / "doc" / "en" / manifest["docFileName"]
    if not default_document.is_file():
        raise RuntimeError(f"manifest docFileName does not resolve to English help: {default_document}")
    if manifest["updateChannel"] not in {"stable", "beta", "dev"}:
        raise RuntimeError(f"invalid manifest updateChannel: {manifest['updateChannel']!r}")
    def api_tuple(value: str) -> tuple[int, int, int]:
        parts = [int(part) for part in value.split(".")]
        return tuple((parts + [0])[:3])
    if api_tuple(manifest["minimumNVDAVersion"]) > api_tuple(manifest["lastTestedNVDAVersion"]):
        raise RuntimeError("minimumNVDAVersion must not exceed lastTestedNVDAVersion")
    return manifest


def validate_localized_manifest(path: pathlib.Path, language: str) -> ConfigObj:
    manifest = ConfigObj(str(path), encoding="utf-8", list_values=True)
    fields = set(manifest)
    if fields != LOCALIZED_MANIFEST_FIELDS:
        missing = sorted(LOCALIZED_MANIFEST_FIELDS - fields)
        unexpected = sorted(fields - LOCALIZED_MANIFEST_FIELDS)
        raise RuntimeError(
            f"localized {language} manifest fields are invalid; "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )
    for field in LOCALIZED_MANIFEST_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise RuntimeError(
                f"localized {language} manifest field {field} must be one trimmed non-empty string"
            )
        if "\x00" in value or "\r" in value:
            raise RuntimeError(
                f"localized {language} manifest field {field} contains unsupported control characters"
            )
    return manifest


def copy_python_files(source: pathlib.Path, destination: pathlib.Path, names: tuple[str, ...]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(source / name, destination / name)


def build(
    output_directory: pathlib.Path,
    documentation_directory: pathlib.Path | None = None,
) -> pathlib.Path:
    metadata = buildVars.manifest()
    artifact_version = buildVars.artifact_version()
    output_root = pathlib.Path(output_directory)
    output = output_root / f"{metadata['name']}-{artifact_version}.nvda-addon"
    output.parent.mkdir(parents=True, exist_ok=True)
    msgpack_distribution = importlib.metadata.distribution("msgpack")
    if msgpack_distribution.version != "1.1.2":
        raise RuntimeError(f"msgpack 1.1.2 required, found {msgpack_distribution.version}")
    msgpack_source = pathlib.Path(msgpack_distribution.locate_file("msgpack"))
    with tempfile.TemporaryDirectory(
        dir=output.parent,
        prefix=f".{output.name}.",
    ) as temporary:
        temporary_root = pathlib.Path(temporary)
        stage = temporary_root / "stage"
        stage.mkdir()
        write_manifest(stage / "manifest.ini", metadata, template=ROOT / "manifest.ini.tpl")
        shutil.copy2(ROOT / "LICENSE", stage / "LICENSE")
        shutil.copytree(
            ROOT / "nvda-addon" / "addon", stage, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("*.po", "*.pot"),
        )
        if documentation_directory is not None:
            shutil.rmtree(stage / "doc")
            install_generated_documentation(
                pathlib.Path(documentation_directory),
                stage / "doc",
            )
        validate_installed_documents(stage / "doc")
        staged_manifest = validate_manifest(stage / "manifest.ini")
        if dict(staged_manifest) != metadata:
            raise RuntimeError("generated manifest differs from central product metadata")
        for catalog in compile_catalogs(stage / "locale"):
            locale = catalog.parent.parent
            language = locale.name
            destination = locale / "manifest.ini"
            with catalog.open("rb") as stream:
                translations = gettext.GNUTranslations(stream)
            localized = {key: translations.gettext(metadata[key]) for key in ("summary", "description")}
            changelog = ROOT / "docs" / language / "development" / "changelog.md"
            localized["changelog"] = (
                buildVars.manifest_changelog(language) if changelog.is_file() else metadata["changelog"]
            )
            write_manifest(destination, localized, template=ROOT / "manifest-translated.ini.tpl")
            staged_localized = validate_localized_manifest(destination, language)
            if dict(staged_localized) != localized:
                raise RuntimeError(f"localized manifest differs from {language} metadata")
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
        server_output = temporary_root / "server-package"
        server_package = package_builder.build(output_directory=server_output)
        resources = plugin / "resources"
        resources.mkdir(exist_ok=True)
        shutil.copy2(server_package, resources / "server-user.tar.gz")
        shutil.copy2(package_builder.COMPONENT_CONFIG, resources / "linux-components.json")
        shutil.copytree(
            ROOT / "neovim-plugin", resources / "neovim-plugin",
            ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
        )
        shutil.copy2(
            ROOT / "examples" / "neovim-starter" / "init.lua",
            resources / "starter-init.lua",
        )
        vendor = plugin / "vendor" / "msgpack"
        vendor.mkdir(parents=True)
        for source in msgpack_source.glob("*.py"):
            shutil.copy2(source, vendor / source.name)
        license_source = find_msgpack_license(msgpack_distribution)
        shutil.copy2(license_source, plugin / "vendor" / "MSGPACK-LICENSE.txt")
        (plugin / "vendor" / "THIRD_PARTY_NOTICES.txt").write_text(
            "msgpack-python 1.1.2, Apache License 2.0, https://msgpack.org/\n",
            encoding="utf-8",
        )
        forbidden = list(stage.rglob("*.so")) + list(stage.rglob("*.pyc"))
        if forbidden:
            raise RuntimeError(f"non-portable files in add-on: {forbidden}")
        staged_output = temporary_root / output.name
        with zipfile.ZipFile(
            staged_output,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for source in sorted(path for path in stage.rglob("*") if path.is_file()):
                relative = source.relative_to(stage).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, source.read_bytes(), compresslevel=9)
        staged_output.replace(output)
        output.chmod(0o644)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=pathlib.Path, required=True)
    parser.add_argument("--documentation-directory", type=pathlib.Path, required=True)
    arguments = parser.parse_args()
    result = build(arguments.output_directory, arguments.documentation_directory)
    print(f"built {result} ({result.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
