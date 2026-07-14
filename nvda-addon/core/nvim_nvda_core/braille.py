"""Plan structured Braille regions while leaving translation to NVDA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


def plan_braille(state: dict[str, Any]) -> BraillePlan:
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
    return BraillePlan(expanded, cursor, selection_start, selection_end, tuple(offsets))


def source_offset_for_expanded(plan: BraillePlan, expanded_offset: int) -> int:
    """Map a routed expanded-text offset back to a source code-point offset."""
    expanded_offset = max(0, min(expanded_offset, len(plan.text)))
    source = 0
    for index, offset in enumerate(plan.source_offsets):
        if offset > expanded_offset:
            break
        source = index
    return source
