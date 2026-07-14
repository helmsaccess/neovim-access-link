"""NVDA-independent conversion of semantic state events to speech actions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Any
import unicodedata

try:
    from .text import InvalidByteColumn, cursor_text
except ImportError:  # Development layout before add-on packaging.
    from nvim_nvda_protocol import InvalidByteColumn, cursor_text


class Priority(IntEnum):
    NAVIGATION = 10
    STATUS = 20
    CRITICAL = 30


@dataclass(frozen=True)
class SpeechAction:
    text: str
    priority: Priority
    interrupt: bool = False
    sound: str | None = None
    typed: bool = False
    spelling: bool = False
    force_symbols: bool = False
    character_suffix: str | None = None
    indentation_tones: int | None = None
    indentation_level: int | None = None
    braille_message: str | None = None
    format_error: str | None = None
    typed_format_error: bool = False


_MODES = {
    "n": "normal mode",
    "i": "insert mode",
    "R": "replace mode",
    "v": "visual character mode",
    "V": "visual line mode",
    "\x16": "visual block mode",
    "c": "command-line mode",
    "no": "operator-pending mode",
    "t": "terminal mode",
}

_CANONICAL_MODES = {
    "normal": "normal mode",
    "insert": "insert mode",
    "replace": "replace mode",
    "visualCharacter": "visual character mode",
    "visualLine": "visual line mode",
    "visualBlock": "visual block mode",
    "commandLine": "command-line mode",
    "operatorPending": "operator-pending mode",
    "terminal": "terminal mode",
}


class SpeechPlanner:
    def __init__(self) -> None:
        self._previous: dict[str, Any] | None = None
        self._last_mode: str | None = None

    def reset(self) -> None:
        self._previous = None
        self._last_mode = None

    def plan(self, event: dict[str, Any]) -> list[SpeechAction]:
        kind = event["type"]
        state = event.get("payload", {})
        actions: list[SpeechAction] = []
        if kind == "errorReceived":
            text = state.get("message")
            if isinstance(text, str) and text:
                actions.append(SpeechAction(text, Priority.CRITICAL, interrupt=True))
        elif kind == "matchingPairNotFound":
            actions.append(SpeechAction(
                "no matching pair", Priority.STATUS, interrupt=True, sound="matchingError",
            ))
        elif kind == "connectionStateChanged":
            connection = state.get("connection", {}).get("neovim")
            if connection in {"connected", "disconnected"}:
                actions.append(SpeechAction(f"Neovim {connection}", Priority.CRITICAL, interrupt=True))
                if connection == "disconnected":
                    self.reset()
        elif kind == "modeChanged":
            canonical = state.get("mode")
            # CTRL-X completion and similar Neovim submodes change modeRaw
            # while remaining semantically in Insert mode. Do not expose their
            # control-byte names as spurious "mode 9" announcements.
            if canonical != self._last_mode:
                raw = state.get("modeRaw")
                description = _CANONICAL_MODES.get(canonical, _MODES.get(raw, f"mode {raw}"))
                actions.append(SpeechAction(description, Priority.CRITICAL, interrupt=True))
                if canonical in {"visualCharacter", "visualLine", "visualBlock"}:
                    selection_action = self._selection_action(state, None)
                    if selection_action is not None:
                        actions.append(replace(selection_action, interrupt=False))
            self._last_mode = canonical
        elif kind in {
            "cursorMoved", "characterMoved", "wordMoved", "lineChanged",
            "lineStart", "lineEnd", "fileStart", "fileEnd", "matchingPairMoved", "fullState",
            "diagnosticMoved",
        }:
            format_action = self._format_error_change(state, kind)
            if format_action is not None:
                actions.append(format_action)
            action = self._navigation(state, announce_full=kind == "fullState")
            if action is not None:
                if kind != "cursorMoved" and kind != "fullState":
                    action = self._semantic_navigation(kind, state, action)
                elif kind == "cursorMoved" and self._line_changed(state):
                    action = SpeechAction(
                        action.text, action.priority, action.interrupt, "lineCrossed",
                        action.typed, action.spelling, action.force_symbols, action.character_suffix,
                        action.indentation_tones,
                    )
                actions.append(action)
        elif kind == "textChanged":
            action = self._text_change(state)
            if action is not None:
                actions.append(action)
        elif kind in {"textDeleted", "textReplaced"}:
            before = state.get("beforeText")
            if isinstance(before, str) and before:
                verb = "deleted" if kind == "textDeleted" else "replaced"
                sound = "delete" if kind == "textDeleted" else "replace"
                deleted = before if state.get("linewise") else self._removed_segment(before, state.get("lineText"))
                actions.append(SpeechAction(f"{verb} {deleted}", Priority.NAVIGATION, sound=sound))
                if kind == "textDeleted" and state.get("linewise"):
                    line = state.get("lineText")
                    if isinstance(line, str):
                        actions.append(SpeechAction(
                            line if line else "blank",
                            Priority.NAVIGATION,
                            indentation_tones=self._indentation_quarter_tones(line),
                        ))
        elif kind == "commandLineChanged":
            action = self._command_line_change(state)
            if action is not None:
                actions.append(action)
        elif kind == "selectionChanged":
            action = self._selection_action(state, (self._previous or {}).get("selection"))
            if action is not None:
                actions.append(action)
        elif kind == "menuOpened":
            actions.append(SpeechAction(
                "", Priority.STATUS, sound="suggestionsOpen", braille_message="Suggestions",
            ))
        elif kind == "menuClosed":
            actions.append(SpeechAction("", Priority.STATUS, sound="suggestionsClose"))
        elif kind == "menuSelectionChanged":
            action = self._menu_selection(state)
            if action is not None:
                actions.append(action)
        elif kind == "promptOpened":
            prompt = state.get("prompt")
            if isinstance(prompt, str) and prompt:
                actions.append(SpeechAction(
                    prompt, Priority.STATUS, interrupt=True, braille_message=prompt,
                ))
        elif kind == "promptClosed":
            selected = state.get("selectedLabel")
            if isinstance(selected, str) and selected:
                text = f"selected {selected}"
                actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
            elif state.get("accepted") is False:
                actions.append(SpeechAction("canceled", Priority.STATUS, braille_message="canceled"))
        elif kind == "foldChanged":
            action = state.get("foldAction")
            labels = {
                "close": "fold closed", "open": "fold opened", "toggle": "fold toggled",
                "closeRecursive": "folds closed", "openRecursive": "folds opened",
                "closeAll": "all folds closed", "openAll": "all folds opened",
            }
            text = labels.get(action, "fold changed")
            start, end = state.get("startLine"), state.get("endLine")
            if isinstance(start, int) and isinstance(end, int) and end >= start:
                text = f"{text}, lines {start} to {end}"
            actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
        elif kind == "foldMoved":
            action = "next fold" if state.get("foldAction") == "next" else "previous fold"
            line = state.get("cursor", {}).get("line")
            text = f"{action}, line {line}" if isinstance(line, int) else action
            actions.append(SpeechAction(text, Priority.NAVIGATION, braille_message=text))
        elif kind == "markSet":
            text = f"mark {state.get('markName', '')} set, line {state.get('markLine', '')}"
            actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
        elif kind == "markMoved":
            text = f"mark {state.get('markName', '')}, {state.get('lineText', '')}"
            actions.append(SpeechAction(text, Priority.NAVIGATION, braille_message=text))
        elif kind == "registerChanged":
            name = state.get("registerName", '"')
            text = f"yanked to register {name}"
            actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
        elif kind == "registerSelected":
            name = state.get("registerName", '"')
            contents = state.get("registerText")
            preview = " ".join(contents.splitlines()) if isinstance(contents, str) else ""
            text = f"register {name}"
            if preview:
                text = f"{text}, {preview}"
            actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
        elif kind == "macroRecordingStarted":
            text = f"recording macro {state.get('registerName', '')}"
            actions.append(SpeechAction(text, Priority.STATUS, interrupt=True, braille_message=text))
        elif kind == "macroRecordingStopped":
            text = f"macro {state.get('registerName', '')} recorded"
            actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
        elif kind == "macroPlayed":
            text = f"macro {state.get('registerName', '')} played"
            actions.append(SpeechAction(text, Priority.STATUS, braille_message=text))
        elif kind == "signatureChanged":
            action = self._signature(state)
            if action is not None:
                actions.append(action)
        elif kind == "searchMatchChanged":
            action = self._search_match(state)
            if action is not None:
                actions.append(action)
        elif kind == "replacementPerformed":
            message = state.get("replacementMessage")
            text = message if isinstance(message, str) and message else "text replaced"
            actions.append(SpeechAction(text, Priority.STATUS, interrupt=True, sound="replace"))
        elif kind == "spellingErrorTyped":
            error = state.get("spellingError")
            if isinstance(error, dict):
                actions.append(SpeechAction(
                    "", Priority.STATUS, format_error=error.get("kind", "spelling"),
                    typed_format_error=True,
                ))
        elif kind == "messageReceived":
            message = state.get("message")
            if isinstance(message, str) and message:
                title = state.get("messageTitle")
                text = f"{title}: {message}" if isinstance(title, str) and title else message
                level = state.get("messageLevel")
                critical = isinstance(level, int) and level >= 4
                actions.append(SpeechAction(
                    text, Priority.CRITICAL if critical else Priority.STATUS,
                    interrupt=critical, braille_message=text,
                ))
        elif kind == "contextChanged":
            action = self._context_change(state)
            if action is not None:
                actions.append(action)
        elif kind == "fileManagerEntryChanged":
            action = self._file_manager_entry(state)
            if action is not None:
                actions.append(action)
        actions = [
            replace(
                action,
                indentation_level=self._indentation_level(state, action.indentation_tones),
            )
            if action.indentation_tones is not None and action.indentation_level is None
            else action
            for action in actions
        ]
        actions = self._suppress_unchanged_indentation(actions)
        if state and kind != "connectionStateChanged":
            self._previous = state
            if kind == "fullState":
                self._last_mode = state.get("mode")
        return actions

    @staticmethod
    def _menu_selection(state: dict[str, Any]) -> SpeechAction | None:
        item = state.get("item")
        if not isinstance(item, dict):
            return None
        label = item.get("label")
        if not isinstance(label, str) or not label:
            return None
        parts = [label]
        index = state.get("itemIndex")
        count = state.get("itemCount")
        if isinstance(index, int) and isinstance(count, int) and count > 1 and 1 <= index <= count:
            parts.append(f"{index} von {count}")
        kind = item.get("kind")
        if isinstance(kind, str) and kind:
            parts.append(kind)
        parameters = item.get("parameters")
        if isinstance(parameters, str) and parameters:
            parts.append(f"Parameter {parameters}")
        text = ", ".join(parts)
        return SpeechAction(
            text, Priority.NAVIGATION, interrupt=True,
            braille_message=text,
        )

    @staticmethod
    def _signature(state: dict[str, Any]) -> SpeechAction | None:
        signature = state.get("signature")
        if not isinstance(signature, str) or not signature:
            return None
        parts = [signature]
        parameter = state.get("parameter")
        active = state.get("activeParameter")
        if isinstance(parameter, str) and parameter:
            parts.append(f"Parameter {parameter}")
        elif isinstance(active, int) and active > 0:
            parts.append(f"Parameter {active}")
        index = state.get("signatureIndex")
        count = state.get("signatureCount")
        if isinstance(index, int) and isinstance(count, int) and count > 1:
            parts.append(f"{index} von {count}")
        text = ", ".join(parts)
        return SpeechAction(text, Priority.NAVIGATION, interrupt=True, braille_message=text)

    @staticmethod
    def _search_match(state: dict[str, Any]) -> SpeechAction | None:
        line = state.get("lineText")
        if not isinstance(line, str):
            return None
        index = state.get("matchIndex")
        count = state.get("matchCount")
        line_number = state.get("matchLine")
        parts = [line if line else "blank"]
        if isinstance(index, int) and isinstance(count, int) and count > 0:
            parts.append(f"match {index} of {count}")
        if isinstance(line_number, int) and line_number > 0:
            parts.append(f"line {line_number}")
        text = ", ".join(parts)
        return SpeechAction(text, Priority.NAVIGATION, interrupt=True, braille_message=text)

    @staticmethod
    def _invisible_selection_text(text: str) -> str:
        names = {
            " ": "space", "\t": "tab", "\n": "line break", "\r": "carriage return",
            "\u00a0": "nonbreaking space", "\u200b": "zero width space",
            "\u2028": "line separator", "\u2029": "paragraph separator",
        }

        def invisible(character: str) -> bool:
            return character.isspace() or unicodedata.category(character) in {"Cf", "Cc", "Zl", "Zp"}

        def describe(fragment: str) -> str:
            descriptions: list[str] = []
            index = 0
            while index < len(fragment):
                character = fragment[index]
                finish = index + 1
                while finish < len(fragment) and fragment[finish] == character:
                    finish += 1
                count = finish - index
                name = names.get(character)
                if name is None:
                    name = unicodedata.name(character, "invisible character").lower()
                if count > 1:
                    plural = name if name.endswith("s") else f"{name}s"
                    descriptions.append(f"{count} {plural}")
                else:
                    descriptions.append(name)
                index = finish
            return " ".join(descriptions)

        if not text:
            return "blank"
        if all(invisible(character) for character in text):
            return describe(text)
        start = 0
        while start < len(text) and invisible(text[start]):
            start += 1
        finish = len(text)
        while finish > start and invisible(text[finish - 1]):
            finish -= 1
        parts = []
        if start:
            parts.append(describe(text[:start]))
        core = text[start:finish]
        if core:
            rendered: list[str] = []
            index = 0
            while index < len(core):
                if not invisible(core[index]):
                    rendered.append(core[index])
                    index += 1
                    continue
                run_end = index + 1
                while run_end < len(core) and invisible(core[run_end]):
                    run_end += 1
                fragment = core[index:run_end]
                rendered.append(fragment if fragment == " " else f" {describe(fragment)} ")
                index = run_end
            parts.append("".join(rendered).strip())
        if finish < len(text):
            parts.append(describe(text[finish:]))
        return " ".join(parts)

    @staticmethod
    def _selection_action(
        state: dict[str, Any], previous: dict[str, Any] | None,
    ) -> SpeechAction | None:
        selection = state.get("selection")
        if not isinstance(selection, dict):
            return None
        kind = selection.get("kind")
        text = selection.get("text")
        if not isinstance(text, str):
            return None

        if kind == "block":
            selected_lines = selection.get("selectedLines")
            if isinstance(selected_lines, list):
                rendered = "\n".join(
                    SpeechPlanner._invisible_selection_text(item.get("text", ""))
                    for item in selected_lines if isinstance(item, dict)
                )
            else:
                rendered = SpeechPlanner._invisible_selection_text(text)
            spoken = f"{rendered or 'blank'} block selected"
            return SpeechAction(
                spoken, Priority.NAVIGATION, interrupt=True,
                force_symbols=True, braille_message=spoken,
            )

        if kind == "line":
            current_lines = selection.get("selectedLines")
            previous_lines = previous.get("selectedLines") if isinstance(previous, dict) else None
            if not isinstance(current_lines, list):
                return None
            old = {
                item.get("line"): item.get("text", "")
                for item in previous_lines or [] if isinstance(item, dict)
            }
            current = {
                item.get("line"): item.get("text", "")
                for item in current_lines if isinstance(item, dict)
            }
            added = [current[number] for number in sorted(current) if number not in old]
            removed = [old[number] for number in sorted(old) if number not in current]
            if added:
                spoken = "\n".join(
                    f"{SpeechPlanner._invisible_selection_text(line)} selected" for line in added
                )
            elif removed:
                spoken = "\n".join(
                    f"{SpeechPlanner._invisible_selection_text(line)} unselected" for line in removed
                )
            else:
                return None
            return SpeechAction(
                spoken, Priority.NAVIGATION, interrupt=True,
                force_symbols=True, braille_message=spoken,
            )

        previous_text = previous.get("text") if isinstance(previous, dict) else ""
        if not isinstance(previous_text, str):
            previous_text = ""
        if text == previous_text:
            return None
        selected = True
        if text.startswith(previous_text):
            changed = text[len(previous_text):]
        elif text.endswith(previous_text):
            changed = text[:len(text) - len(previous_text)]
        elif previous_text.startswith(text):
            changed = previous_text[len(text):]
            selected = False
        elif previous_text.endswith(text):
            changed = previous_text[:len(previous_text) - len(text)]
            selected = False
        else:
            changed = text
        spoken = (
            f"{SpeechPlanner._invisible_selection_text(changed)} "
            f"{'selected' if selected else 'unselected'}"
        )
        return SpeechAction(
            spoken, Priority.NAVIGATION, interrupt=True,
            force_symbols=True, braille_message=spoken,
        )

    def _format_error_change(self, state: dict[str, Any], event_kind: str) -> SpeechAction | None:
        if event_kind not in {"characterMoved", "wordMoved", "lineChanged", "fullState"}:
            return None
        current = state.get("spellingError")
        previous = (self._previous or {}).get("spellingError")
        if event_kind in {"lineChanged", "fullState"} and not isinstance(current, dict):
            errors = state.get("spellingErrors")
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                current = errors[0]
        current_kind = current.get("kind") if isinstance(current, dict) else None
        previous_kind = previous.get("kind") if isinstance(previous, dict) else None
        current_range = (
            (state.get("cursor") or {}).get("line"), current.get("startByteColumn"),
            current.get("endByteColumn"), current_kind
        ) if isinstance(current, dict) else None
        previous_range = (
            ((self._previous or {}).get("cursor") or {}).get("line"), previous.get("startByteColumn"),
            previous.get("endByteColumn"), previous_kind
        ) if isinstance(previous, dict) else None
        if current_range == previous_range:
            return None
        if current_kind:
            return SpeechAction("", Priority.NAVIGATION, format_error=current_kind)
        if previous_kind:
            return SpeechAction("", Priority.NAVIGATION, format_error=f"out:{previous_kind}")
        return None

    def _context_change(self, state: dict[str, Any]) -> SpeechAction | None:
        manager = state.get("fileManager")
        if isinstance(manager, dict):
            entry_action = self._file_manager_entry(state)
            if entry_action is not None:
                return entry_action
            name = manager.get("name")
            root = manager.get("root")
            parts = [str(name)] if isinstance(name, str) and name else ["file manager"]
            if isinstance(root, str) and root:
                parts.append(root)
            text = ", ".join(parts)
            return SpeechAction(text, Priority.STATUS, interrupt=True, braille_message=text)
        previous = self._previous or {}
        window_type = state.get("windowType")
        line = state.get("lineText")
        if window_type in {"quickfix", "locationList"}:
            label = "location list" if window_type == "locationList" else "quickfix"
            text = f"{label}, {line if isinstance(line, str) and line else 'empty'}"
            return SpeechAction(text, Priority.STATUS, interrupt=True, braille_message=text)

        parts = []
        if state.get("tabpageId") != previous.get("tabpageId"):
            parts.append(f"tab {state.get('tabIndex', 1)} of {state.get('tabCount', 1)}")
        elif state.get("windowId") != previous.get("windowId"):
            parts.append(f"window {state.get('windowIndex', 1)} of {state.get('windowCount', 1)}")
        elif state.get("bufferId") == previous.get("bufferId"):
            return None
        buftype = state.get("buftype")
        filetype = state.get("filetype")
        if buftype == "help" or filetype == "help":
            parts.append("help")
        elif buftype == "terminal":
            parts.append("terminal")
        name = state.get("bufferName")
        if isinstance(name, str) and name:
            parts.append(name.replace("\\", "/").rsplit("/", 1)[-1])
        else:
            parts.append("unnamed buffer")
        if state.get("modified"):
            parts.append("modified")
        if state.get("readonly"):
            parts.append("read only")
        text = ", ".join(parts)
        return SpeechAction(text, Priority.STATUS, interrupt=True, braille_message=text)

    @staticmethod
    def _file_manager_entry(state: dict[str, Any]) -> SpeechAction | None:
        manager = state.get("fileManager")
        entry = manager.get("entry") if isinstance(manager, dict) else None
        if not isinstance(entry, dict):
            return None
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            return None
        kind_names = {
            "file": "file", "directory": "directory", "symbolicLink": "symbolic link",
            "socket": "socket", "fifo": "named pipe", "characterDevice": "character device",
            "blockDevice": "block device",
        }
        parts = [name]
        entry_type = entry.get("type")
        if isinstance(entry_type, str) and entry_type:
            parts.append(kind_names.get(entry_type, entry_type))
        if entry.get("marked") is True:
            parts.append("marked")
        if entry.get("expanded") is True:
            parts.append("expanded")
        elif entry.get("expanded") is False:
            parts.append("collapsed")
        text = ", ".join(parts)
        return SpeechAction(
            text, Priority.NAVIGATION, interrupt=True,
            force_symbols=True, braille_message=text,
        )

    def _navigation(self, state: dict[str, Any], announce_full: bool) -> SpeechAction | None:
        line = state.get("lineText")
        cursor = state.get("cursor")
        if not isinstance(line, str) or not isinstance(cursor, dict):
            return None
        previous_cursor = (self._previous or {}).get("cursor", {})
        line_changed = previous_cursor.get("line") != cursor.get("line")
        if announce_full or line_changed:
            return SpeechAction(
                line if line else "blank", Priority.NAVIGATION, interrupt=True,
                indentation_tones=self._indentation_quarter_tones(line),
            )
        byte_column = cursor.get("byteColumn")
        if not isinstance(byte_column, int):
            return None
        try:
            character = cursor_text(line, byte_column).character
        except InvalidByteColumn:
            return SpeechAction("invalid cursor position", Priority.CRITICAL, interrupt=True)
        if character:
            return SpeechAction(character, Priority.NAVIGATION, interrupt=True, spelling=True)
        return None

    def _semantic_navigation(
        self, kind: str, state: dict[str, Any], fallback: SpeechAction
    ) -> SpeechAction:
        line = state.get("lineText", "")
        cursor = state.get("cursor", {})
        character = state.get("character", "")
        if not character and isinstance(line, str) and isinstance(cursor, dict):
            byte_column = cursor.get("byteColumn")
            if isinstance(byte_column, int):
                try:
                    character = cursor_text(line, byte_column).character
                except InvalidByteColumn:
                    character = ""
        spoken_character = character if character else ""
        if kind == "characterMoved":
            if spoken_character:
                sound = "lineCrossed" if self._line_changed(state) else None
                indentation = self._indentation_quarter_tones(line) if sound else None
                return SpeechAction(
                    spoken_character, Priority.NAVIGATION, interrupt=True,
                    sound=sound, spelling=True, indentation_tones=indentation,
                )
            return SpeechAction("", Priority.NAVIGATION, sound="lineEnd")
        if kind == "wordMoved":
            word = state.get("word")
            text = word if isinstance(word, str) and word else spoken_character
            suffix = spoken_character if spoken_character and spoken_character != text else None
            sound = "lineCrossed" if self._line_changed(state) else None
            indentation = self._indentation_quarter_tones(line) if sound else None
            return SpeechAction(
                text, Priority.NAVIGATION, interrupt=True, sound=sound,
                force_symbols=True, character_suffix=suffix,
                indentation_tones=indentation,
            )
        if kind == "lineStart":
            byte_column = cursor.get("byteColumn") if isinstance(cursor, dict) else None
            sound = "lineStart" if byte_column == 0 else None
            return SpeechAction("", Priority.NAVIGATION, interrupt=False, sound=sound)
        if kind == "lineEnd":
            return SpeechAction("", Priority.NAVIGATION, interrupt=False, sound="lineEnd")
        if kind in {"fileStart", "fileEnd"}:
            boundary = "beginning of file" if kind == "fileStart" else "end of file"
            sound = "fileStart" if kind == "fileStart" else "fileEnd"
            return SpeechAction(
                f"{boundary}, {line if line else 'blank'}",
                Priority.NAVIGATION, True, sound,
                character_suffix=spoken_character or None,
            )
        if kind == "lineChanged":
            text = line if line else "blank"
            previous_cursor = (self._previous or {}).get("cursor", {})
            previous_column = previous_cursor.get("byteColumn") if isinstance(previous_cursor, dict) else None
            current_column = cursor.get("byteColumn") if isinstance(cursor, dict) else None
            sound = None
            if current_column == 0 and previous_column not in {None, 0}:
                sound = "lineStart"
            elif isinstance(line, str) and current_column == len(line.encode("utf-8")) and previous_column != current_column:
                sound = "lineEnd"
            return SpeechAction(
                text, Priority.NAVIGATION, interrupt=True, sound=sound,
                character_suffix=spoken_character or None,
                indentation_tones=self._indentation_quarter_tones(line),
            )
        if kind == "matchingPairMoved":
            line_number = cursor.get("line") if isinstance(cursor, dict) else None
            parts = [f"matching {spoken_character}" if spoken_character else "matching pair"]
            if isinstance(line_number, int):
                parts.append(f"line {line_number}")
            crossed = self._line_changed(state)
            return SpeechAction(
                ", ".join(parts), Priority.NAVIGATION, interrupt=True,
                sound="lineCrossed" if crossed else None,
                force_symbols=True,
                indentation_tones=self._indentation_quarter_tones(line) if crossed else None,
            )
        if kind == "diagnosticMoved":
            diagnostic = state.get("diagnostic")
            if not isinstance(diagnostic, dict):
                return SpeechAction("no diagnostic", Priority.STATUS, interrupt=True)
            parts = []
            source = diagnostic.get("source")
            severity = diagnostic.get("severity")
            if isinstance(source, str) and source:
                parts.append(source)
            if isinstance(severity, str) and severity:
                parts.append(severity)
            code = diagnostic.get("code")
            if isinstance(code, (str, int)) and str(code):
                parts.append(str(code))
            message = diagnostic.get("message")
            if isinstance(message, str) and message:
                parts.append(message)
            index, count = diagnostic.get("index"), diagnostic.get("count")
            if isinstance(index, int) and isinstance(count, int) and count > 1:
                parts.append(f"{index} of {count}")
            line_number = diagnostic.get("line")
            if isinstance(line_number, int):
                parts.append(f"line {line_number}")
            text = ", ".join(parts) if parts else "diagnostic"
            return SpeechAction(
                text, Priority.NAVIGATION, interrupt=True,
                sound="lineCrossed" if self._line_changed(state) else None,
                braille_message=text,
            )
        return fallback

    def _line_changed(self, state: dict[str, Any]) -> bool:
        cursor = state.get("cursor", {})
        previous_cursor = (self._previous or {}).get("cursor", {})
        return (
            isinstance(cursor, dict)
            and isinstance(previous_cursor, dict)
            and cursor.get("line") != previous_cursor.get("line")
        )

    def _text_change(self, state: dict[str, Any]) -> SpeechAction | None:
        line = state.get("lineText")
        previous_line = (self._previous or {}).get("lineText")
        if not isinstance(line, str) or not isinstance(previous_line, str):
            return None
        previous_cursor = (self._previous or {}).get("cursor", {})
        cursor = state.get("cursor", {})
        if isinstance(previous_cursor, dict) and isinstance(cursor, dict) and previous_cursor.get("line") != cursor.get("line"):
            quarter_tones = self._indentation_quarter_tones(line)
            return SpeechAction(
                "", Priority.NAVIGATION, interrupt=False,
                sound="lineStart" if quarter_tones == 0 else None,
                indentation_tones=quarter_tones,
                indentation_level=self._indentation_level(state, quarter_tones),
            )
        if line == previous_line:
            return None
        prefix = 0
        limit = min(len(line), len(previous_line))
        while prefix < limit and line[prefix] == previous_line[prefix]:
            prefix += 1
        suffix = 0
        while (
            suffix < len(line) - prefix
            and suffix < len(previous_line) - prefix
            and line[len(line) - suffix - 1] == previous_line[len(previous_line) - suffix - 1]
        ):
            suffix += 1
        inserted_end = len(line) - suffix if suffix else len(line)
        inserted = line[prefix:inserted_end]
        previous_end = len(previous_line) - suffix if suffix else len(previous_line)
        deleted = previous_line[prefix:previous_end]
        if inserted:
            sound = "replace" if deleted else None
            return SpeechAction(inserted, Priority.NAVIGATION, interrupt=False, sound=sound, typed=True)
        if deleted:
            return SpeechAction(f"deleted {deleted}", Priority.NAVIGATION, interrupt=False, sound="delete")
        return None

    def _command_line_change(self, state: dict[str, Any]) -> SpeechAction | None:
        command_line = state.get("commandLine")
        previous_line = (self._previous or {}).get("commandLine", "")
        if not isinstance(command_line, str) or not isinstance(previous_line, str) or command_line == previous_line:
            return None
        prefix = 0
        limit = min(len(command_line), len(previous_line))
        while prefix < limit and command_line[prefix] == previous_line[prefix]:
            prefix += 1
        suffix = 0
        while (
            suffix < len(command_line) - prefix
            and suffix < len(previous_line) - prefix
            and command_line[-suffix - 1] == previous_line[-suffix - 1]
        ):
            suffix += 1
        end = len(command_line) - suffix if suffix else len(command_line)
        inserted = command_line[prefix:end]
        if inserted:
            return SpeechAction(inserted, Priority.NAVIGATION, interrupt=False, typed=True)
        previous_end = len(previous_line) - suffix if suffix else len(previous_line)
        deleted = previous_line[prefix:previous_end]
        if deleted:
            return SpeechAction(f"deleted {deleted}", Priority.NAVIGATION, interrupt=False, sound="delete")
        return None

    @staticmethod
    def _removed_segment(before: str, after: Any) -> str:
        if not isinstance(after, str):
            return before
        prefix = 0
        limit = min(len(before), len(after))
        while prefix < limit and before[prefix] == after[prefix]:
            prefix += 1
        suffix = 0
        while (
            suffix < len(before) - prefix
            and suffix < len(after) - prefix
            and before[-suffix - 1] == after[-suffix - 1]
        ):
            suffix += 1
        end = len(before) - suffix if suffix else len(before)
        return before[prefix:end] or before

    @staticmethod
    def _indentation_quarter_tones(line: str) -> int:
        """Match NVDA: one quarter-tone per space and four per tab."""
        total = 0
        for character in line:
            if character == " ":
                total += 1
            elif character == "\t":
                total += 4
            else:
                break
        return total

    @staticmethod
    def _indentation_level(state: dict[str, Any], quarter_tones: int) -> int:
        columns = state.get("indentation", quarter_tones)
        if not isinstance(columns, int) or columns < 0:
            columns = quarter_tones
        width = state.get("shiftwidth", state.get("tabstop", 4))
        if not isinstance(width, int) or width <= 0:
            width = 4
        if columns == 0:
            return 0
        return max(1, (columns + width - 1) // width)

    def _suppress_unchanged_indentation(self, actions: list[SpeechAction]) -> list[SpeechAction]:
        previous_line = (self._previous or {}).get("lineText", "")
        previous = self._indentation_quarter_tones(previous_line) if isinstance(previous_line, str) else 0
        result: list[SpeechAction] = []
        for action in actions:
            if action.indentation_tones is not None and action.indentation_tones == previous:
                action = replace(action, indentation_tones=None, indentation_level=None)
            result.append(action)
        return result
