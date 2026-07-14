"""Conversions for Neovim UTF-8 byte columns.

Neovim cursor columns are zero-based byte offsets. Python string indices are
Unicode code points; neither value is a terminal display/virtual column.
"""

from __future__ import annotations

from dataclasses import dataclass


class InvalidByteColumn(ValueError):
    """Raised when a byte column splits a UTF-8 sequence or is out of range."""


@dataclass(frozen=True)
class CursorText:
    byte_column: int
    character_column: int
    character: str


def cursor_text(line: str, byte_column: int) -> CursorText:
    """Return the code-point column and character at a Neovim byte offset."""
    if byte_column < 0:
        raise InvalidByteColumn("byte column must not be negative")
    encoded = line.encode("utf-8")
    if byte_column > len(encoded):
        raise InvalidByteColumn("byte column is beyond end of line")
    try:
        prefix = encoded[:byte_column].decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise InvalidByteColumn("byte column splits a UTF-8 sequence") from error
    character_column = len(prefix)
    character = line[character_column] if character_column < len(line) else ""
    return CursorText(byte_column, character_column, character)


def utf16_column(line: str, character_column: int) -> int:
    """Convert a Python code-point column to an LSP/NVDA UTF-16 unit column."""
    if not 0 <= character_column <= len(line):
        raise ValueError("character column is out of range")
    return len(line[:character_column].encode("utf-16-le")) // 2
