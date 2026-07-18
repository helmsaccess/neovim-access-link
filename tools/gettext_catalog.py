#!/usr/bin/env python3
"""Extract, validate and compile the add-on's gettext catalogs.

The project deliberately uses only the Python standard library here.  This
keeps normal add-on builds reproducible even when GNU gettext is unavailable.
The PO files remain standard gettext input and can still be edited with common
translation tools.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import json
from pathlib import Path
import struct
from string import Formatter
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import buildVars


PRODUCT_NAME = buildVars.addon_info["summary"]
LOCALE_ROOT = ROOT / "nvda-addon" / "locale"
POT_PATH = LOCALE_ROOT / "NeovimAccessLink.pot"
SOURCE_PATHS = (
    ROOT / "nvda-addon" / "addon" / "globalPlugins" / "NeovimAccessLink" / "__init__.py",
    ROOT / "nvda-addon" / "addon" / "appModules" / "windowsterminal.py",
    ROOT / "nvda-addon" / "core" / "nvim_nvda_core" / "speech.py",
)


@dataclass
class Message:
    msgid: str
    msgstr: str = ""
    references: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _translation_argument(call: ast.Call) -> ast.AST | None:
    function = call.func
    name = function.id if isinstance(function, ast.Name) else (
        function.attr if isinstance(function, ast.Attribute) else ""
    )
    if name in {"ngettext", "pgettext", "npgettext"}:
        raise ValueError(f"unsupported gettext call {name!r} at source line {call.lineno}")
    if name in {"_", "gettext", "translatable", "_translate"} and call.args:
        return call.args[0]
    return None


def extract_messages(paths: Iterable[Path] = SOURCE_PATHS) -> dict[str, Message]:
    messages: dict[str, Message] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            argument = _translation_argument(node)
            msgid = _literal_string(argument) if argument is not None else None
            if msgid is None or not msgid:
                continue
            message = messages.setdefault(msgid, Message(msgid))
            message.references.add(f"{relative}:{node.lineno}")
            if _format_fields(msgid):
                message.flags.add("python-brace-format")
    return messages


def _format_fields(value: str) -> tuple[str, ...]:
    fields: list[str] = []
    try:
        parsed = Formatter().parse(value)
        for _literal, field_name, _format_spec, _conversion in parsed:
            if field_name is not None:
                fields.append(field_name)
    except ValueError as error:
        raise ValueError(f"invalid Python format string {value!r}: {error}") from error
    return tuple(sorted(fields))


def validate_translation(msgid: str, msgstr: str) -> None:
    if msgstr and _format_fields(msgid) != _format_fields(msgstr):
        raise ValueError(
            f"translation placeholders differ for {msgid!r}: "
            f"{_format_fields(msgid)!r} != {_format_fields(msgstr)!r}"
        )


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _header(*, language: str = "") -> str:
    lines = [
        f"Project-Id-Version: {PRODUCT_NAME}",
        "Report-Msgid-Bugs-To: https://github.com/helmsaccess/neovim-access-link/issues",
        "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE",
        "Last-Translator: FULL NAME <EMAIL@ADDRESS>",
        "Language-Team: LANGUAGE <LL@li.org>",
        f"Language: {language}",
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=UTF-8",
        "Content-Transfer-Encoding: 8bit",
        "Plural-Forms: nplurals=2; plural=(n != 1);",
    ]
    return "\n".join(lines) + "\n"


def render_catalog(
    messages: dict[str, Message], *, language: str = "", include_translations: bool,
    header: str | None = None,
) -> str:
    rendered_header = header if header is not None else _header(
        language=language if include_translations else "",
    )
    result = [
        f"# {PRODUCT_NAME} translations.",
        f"# This file is distributed under the same license as the {PRODUCT_NAME} package.",
        "#",
        "msgid \"\"",
        f"msgstr {_quoted(rendered_header)}",
        "",
    ]
    for msgid in sorted(messages, key=lambda value: (value.casefold(), value)):
        message = messages[msgid]
        if message.references:
            result.append("#: " + " ".join(sorted(message.references)))
        if message.flags:
            result.append("#, " + ", ".join(sorted(message.flags)))
        result.append(f"msgid {_quoted(msgid)}")
        result.append(f"msgstr {_quoted(message.msgstr if include_translations else '')}")
        result.append("")
    return "\n".join(result)


def parse_po(path: Path) -> tuple[dict[str, str], str]:
    entries: dict[str, str] = {}
    current: dict[str, str] = {}
    active: str | None = None

    def finish() -> None:
        nonlocal current, active
        if "msgid" in current and "msgstr" in current:
            msgid = current["msgid"]
            if msgid in entries:
                raise ValueError(f"duplicate msgid {msgid!r} in {path}")
            entries[msgid] = current["msgstr"]
        current = {}
        active = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            finish()
            continue
        if line.startswith("#"):
            continue
        field_name = next(
            (name for name in ("msgid", "msgstr") if line.startswith(name + " ")),
            None,
        )
        if field_name is not None:
            active = field_name
            literal = line[len(field_name):].strip()
            try:
                value = ast.literal_eval(literal)
            except (SyntaxError, ValueError) as error:
                raise ValueError(f"invalid PO string at {path}:{line_number}") from error
            if not isinstance(value, str):
                raise ValueError(f"PO value is not a string at {path}:{line_number}")
            current[field_name] = value
            continue
        if line.startswith('"') and active is not None:
            try:
                value = ast.literal_eval(line)
            except (SyntaxError, ValueError) as error:
                raise ValueError(f"invalid PO continuation at {path}:{line_number}") from error
            if not isinstance(value, str):
                raise ValueError(f"PO continuation is not a string at {path}:{line_number}")
            current[active] = current.get(active, "") + value
            continue
        raise ValueError(f"unsupported PO syntax at {path}:{line_number}: {raw_line!r}")
    finish()
    header = entries.pop("", "")
    return entries, header


def update_catalog(path: Path, *, language: str) -> None:
    extracted = extract_messages()
    existing, header = parse_po(path) if path.exists() else ({}, "")
    for msgid, message in extracted.items():
        message.msgstr = existing.get(msgid, "")
        validate_translation(msgid, message.msgstr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_catalog(
            extracted,
            language=language,
            include_translations=True,
            header=header or None,
        ),
        encoding="utf-8",
        newline="\n",
    )


def update_template() -> None:
    POT_PATH.parent.mkdir(parents=True, exist_ok=True)
    POT_PATH.write_text(
        render_catalog(extract_messages(), include_translations=False),
        encoding="utf-8",
        newline="\n",
    )


def validate_template() -> None:
    expected = render_catalog(extract_messages(), include_translations=False)
    if not POT_PATH.is_file():
        raise ValueError(f"gettext template is missing: {POT_PATH}")
    if POT_PATH.read_text(encoding="utf-8") != expected:
        raise ValueError(
            f"gettext template is not synchronized with source; run update: {POT_PATH}"
        )


def validate_catalog(path: Path, *, require_complete: bool = False) -> dict[str, str]:
    translations, header = parse_po(path)
    if "charset=UTF-8" not in header:
        raise ValueError(f"catalog header must declare UTF-8: {path}")
    source = extract_messages()
    missing = sorted(set(source) - set(translations))
    obsolete = sorted(set(translations) - set(source))
    untranslated = sorted(msgid for msgid in source if not translations.get(msgid))
    if missing:
        raise ValueError(f"catalog is missing {len(missing)} messages: {missing[:5]!r}")
    if obsolete:
        raise ValueError(f"catalog has {len(obsolete)} obsolete messages: {obsolete[:5]!r}")
    if require_complete and untranslated:
        raise ValueError(f"catalog has {len(untranslated)} untranslated messages: {untranslated[:5]!r}")
    for msgid, msgstr in translations.items():
        validate_translation(msgid, msgstr)
    return {"": header, **translations}


def compile_mo(path: Path, destination: Path, *, require_complete: bool = False) -> None:
    catalog = validate_catalog(path, require_complete=require_complete)
    # GNU msgfmt omits untranslated entries.  Keeping an empty msgstr in the
    # MO would make gettext return an empty string instead of the English
    # msgid, breaking the required fallback behavior.
    items = sorted(
        (msgid, msgstr)
        for msgid, msgstr in catalog.items()
        if msgid == "" or msgstr
    )
    ids = b""
    strings = b""
    id_offsets: list[tuple[int, int]] = []
    string_offsets: list[tuple[int, int]] = []
    for msgid, msgstr in items:
        encoded_id = msgid.encode("utf-8")
        encoded_string = msgstr.encode("utf-8")
        id_offsets.append((len(encoded_id), len(ids)))
        string_offsets.append((len(encoded_string), len(strings)))
        ids += encoded_id + b"\0"
        strings += encoded_string + b"\0"
    count = len(items)
    header_size = 7 * 4
    id_table_offset = header_size
    string_table_offset = id_table_offset + count * 8
    ids_offset = string_table_offset + count * 8
    strings_offset = ids_offset + len(ids)
    output = [
        struct.pack(
            "<7I", 0x950412DE, 0, count, id_table_offset,
            string_table_offset, 0, 0,
        )
    ]
    output.extend(struct.pack("<2I", length, ids_offset + offset) for length, offset in id_offsets)
    output.extend(
        struct.pack("<2I", length, strings_offset + offset)
        for length, offset in string_offsets
    )
    output.extend((ids, strings))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"".join(output))


def compile_catalogs(destination: Path, *, require_complete: bool = False) -> list[Path]:
    """Compile every source PO into an NVDA-compatible locale tree."""
    outputs: list[Path] = []
    for catalog_path in _catalog_paths():
        language = catalog_path.parts[-3]
        output = destination / language / "LC_MESSAGES" / "nvda.mo"
        compile_mo(catalog_path, output, require_complete=require_complete)
        outputs.append(output)
    if not outputs:
        raise ValueError("no gettext catalogs found")
    return outputs


def _catalog_paths() -> list[Path]:
    return sorted(LOCALE_ROOT.glob("*/LC_MESSAGES/nvda.po"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("update", "check", "compile"))
    parser.add_argument("--destination", type=Path, help="output locale root for compiled catalogs")
    arguments = parser.parse_args()
    if arguments.command == "update":
        update_template()
        for catalog_path in _catalog_paths():
            update_catalog(catalog_path, language=catalog_path.parts[-3])
        return
    catalogs = _catalog_paths()
    if not catalogs:
        raise SystemExit("no gettext catalogs found")
    validate_template()
    for catalog_path in catalogs:
        validate_catalog(catalog_path)
    if arguments.command == "compile":
        if arguments.destination is None:
            parser.error("compile requires --destination")
        compile_catalogs(arguments.destination)


if __name__ == "__main__":
    main()
