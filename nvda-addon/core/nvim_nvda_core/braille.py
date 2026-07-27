"""Plan structured Braille regions while leaving translation to NVDA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

try:
    from .text import InvalidByteColumn, cursor_text
except ImportError:
    from nvim_nvda_protocol import InvalidByteColumn, cursor_text


@dataclass(frozen=True)
class BraillePlan:
    text: str
    cursor: int | None
    selection_start: int | None
    selection_end: int | None
    source_offsets: tuple[int, ...]
    routing_byte_columns: tuple[int | None, ...] | None = None


_FILE_MANAGER_KIND_NAMES = {
    "file": "file",
    "directory": "directory",
    "symbolicLink": "symbolic link",
    "socket": "socket",
    "fifo": "named pipe",
    "characterDevice": "character device",
    "blockDevice": "block device",
}


def _identity(message: str) -> str:
    return message


def _file_manager_location(manager: dict[str, Any]) -> str | None:
    value = manager.get("currentDirectory")
    if not isinstance(value, str) or not value:
        value = manager.get("root")
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("\\", "/").rstrip("/")
    location = normalized.rsplit("/", 1)[-1]
    return location or None


def _unique_name_start(line: str, name: str) -> int | None:
    start = line.find(name)
    if start < 0 or line.find(name, start + 1) >= 0:
        return None
    return start


def _file_manager_context_plan(
    manager: dict[str, Any],
    translate: Callable[[str], str],
) -> BraillePlan:
    name = manager.get("name")
    parts = [name] if isinstance(name, str) and name else [translate("file manager")]
    location = _file_manager_location(manager)
    if location:
        parts.append(location)
    text = ", ".join(parts)
    return BraillePlan(
        text, 0, None, None, tuple(range(len(text) + 1)),
        tuple(None for _ in text),
    )


def _file_manager_plan(
    state: dict[str, Any],
    translate: Callable[[str], str],
) -> BraillePlan | None:
    manager = state.get("fileManager")
    if not isinstance(manager, dict):
        return None
    entry = manager.get("entry")
    if not isinstance(entry, dict):
        return _file_manager_context_plan(manager, translate)

    name = entry.get("name")
    if not isinstance(name, str) or not name:
        return _file_manager_context_plan(manager, translate)
    parts = [name]
    entry_type = entry.get("type")
    if isinstance(entry_type, str) and entry_type:
        kind_name = _FILE_MANAGER_KIND_NAMES.get(entry_type)
        parts.append(translate(kind_name) if kind_name else entry_type)
    selection_state = entry.get("selectionState")
    clipboard_state = entry.get("clipboardState")
    if selection_state == "marked" or (
        selection_state not in {"marked", "unmarked"}
        and entry.get("marked") is True
        and clipboard_state not in {"copied", "cut", "none"}
    ):
        parts.append(translate("marked"))
    if clipboard_state == "copied":
        parts.append(translate("copied"))
    elif clipboard_state == "cut":
        parts.append(translate("cut"))
    if entry.get("expanded") is True:
        parts.append(translate("expanded"))
    elif entry.get("expanded") is False:
        parts.append(translate("collapsed"))
    text = ", ".join(parts)

    line = state.get("lineText")
    line = line if isinstance(line, str) else ""
    name_start = _unique_name_start(line, name)
    routing: list[int | None] = [None] * len(text)
    cursor = 0
    if name_start is not None:
        byte_start = len(line[:name_start].encode("utf-8"))
        byte_offsets = [byte_start]
        for character in name:
            byte_offsets.append(byte_offsets[-1] + len(character.encode("utf-8")))
        for index in range(len(name)):
            routing[index] = byte_offsets[index]
        cursor_data = state.get("cursor")
        byte_column = cursor_data.get("byteColumn") if isinstance(cursor_data, dict) else None
        if isinstance(byte_column, int) and byte_start <= byte_column <= byte_offsets[-1]:
            cursor = max(
                index for index, offset in enumerate(byte_offsets) if offset <= byte_column
            )
            cursor = min(cursor, max(0, len(name) - 1))
    return BraillePlan(
        text, cursor, None, None, tuple(range(len(text) + 1)), tuple(routing),
    )


def _expand_tabs(text: str, tabstop: int) -> tuple[str, list[int]]:
    output: list[str] = []
    offsets = [0]
    column = 0
    for character in text:
        if character == "\t":
            width = tabstop - (column % tabstop)
            output.append(" " * width)
            column += width
        else:
            output.append(character)
            column += 1
        offsets.append(column)
    return "".join(output), offsets


def plan_braille(
    state: dict[str, Any],
    *,
    translate: Callable[[str], str] | None = None,
) -> BraillePlan:
    translate = translate or _identity
    file_manager_plan = _file_manager_plan(state, translate)
    if file_manager_plan is not None:
        return file_manager_plan
    line = state.get("lineText", "")
    if not isinstance(line, str):
        line = ""
    tabstop = state.get("tabstop", 8)
    if not isinstance(tabstop, int) or not 1 <= tabstop <= 64:
        tabstop = 8
    expanded, offsets = _expand_tabs(line, tabstop)
    if state.get("reportSpellingBraille"):
        insertions: list[tuple[int, str]] = []
        for error in state.get("spellingErrors", []):
            if not isinstance(error, dict):
                continue
            try:
                start = cursor_text(line, error["startByteColumn"]).character_column
                end = cursor_text(line, error["endByteColumn"]).character_column
            except (KeyError, TypeError, InvalidByteColumn):
                continue
            kind = error.get("kind")
            insertions.extend([
                (offsets[min(start, len(line))], "⠛" if kind == "grammar" else "⠑"),
                (offsets[min(end, len(line))], "⡛" if kind == "grammar" else "⡑"),
            ])
        for position, marker in sorted(insertions, reverse=True):
            expanded = expanded[:position] + marker + expanded[position:]
            offsets = [offset + (1 if offset >= position else 0) for offset in offsets]
    cursor_data = state.get("cursor", {})
    character_column = cursor_data.get("characterColumn")
    if not isinstance(character_column, int):
        byte_column = cursor_data.get("byteColumn", 0)
        try:
            character_column = cursor_text(line, byte_column).character_column
        except (InvalidByteColumn, TypeError):
            character_column = 0
    character_column = max(0, min(character_column, len(line)))
    cursor = offsets[character_column]

    selection_start = selection_end = None
    selection = state.get("selection")
    current_line = selection.get("currentLine") if isinstance(selection, dict) else None
    if isinstance(current_line, dict):
        try:
            raw_start = cursor_text(line, current_line["startByteColumn"]).character_column
            raw_end = cursor_text(line, current_line["endByteColumn"]).character_column
            selection_start = offsets[min(raw_start, len(line))]
            selection_end = offsets[min(raw_end, len(line))]
            if selection_start == selection_end:
                selection_start = selection_end = None
            else:
                cursor = None
        except (KeyError, TypeError, InvalidByteColumn):
            selection_start = selection_end = None
    if state.get("brailleCursorVisible") is False:
        cursor = None
    insert_mode = (
        state.get("mode") == "insert"
        or str(state.get("modeRaw", "")).startswith("i")
    )
    if insert_mode or not expanded:
        # An Insert-mode cursor may sit after the final character. Liblouis can
        # only render dots 7+8 on an existing cell, so expose one virtual blank
        # whose source mapping resolves to the UTF-8 end of the unchanged line.
        # An empty Normal-mode line also needs one cursor-bearing cell. Without
        # it, NVDA cannot focus this region and leaves its preceding terminal
        # context (for example "Windows PowerShell") at the display start.
        expanded += " "
    return BraillePlan(expanded, cursor, selection_start, selection_end, tuple(offsets))


def plan_command_line_braille(state: dict[str, Any]) -> BraillePlan:
    """Plan the structured command line, keeping its prompt cells non-routable."""
    command_line = state.get("commandLine")
    command_line = command_line if isinstance(command_line, str) else ""
    command_type = state.get("commandLineType")
    command_type = command_type if isinstance(command_type, str) else ""
    byte_position = state.get("commandLinePosition")
    try:
        character_position = cursor_text(command_line, byte_position).character_column
    except (InvalidByteColumn, TypeError):
        character_position = 0

    byte_offsets = [0]
    for character in command_line:
        byte_offsets.append(byte_offsets[-1] + len(character.encode("utf-8")))
    routing = (
        tuple(None for _ in command_type)
        + tuple(byte_offsets[index] for index in range(len(command_line)))
        + (byte_offsets[-1],)
    )
    text = command_type + command_line + " "
    return BraillePlan(
        text,
        len(command_type) + character_position,
        None,
        None,
        tuple(range(len(text) + 1)),
        routing,
    )


def source_offset_for_expanded(plan: BraillePlan, expanded_offset: int) -> int:
    """Map a routed expanded-text offset back to a source code-point offset."""
    expanded_offset = max(0, min(expanded_offset, len(plan.text)))
    source = 0
    for index, offset in enumerate(plan.source_offsets):
        if offset > expanded_offset:
            break
        source = index
    return source
