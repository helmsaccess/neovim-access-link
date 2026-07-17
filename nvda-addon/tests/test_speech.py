from __future__ import annotations

import unittest

from nvim_nvda_core import (
    DiagnosticBuffer, Priority, SessionGate, SpeechPlanner, TerminalIdentity,
    plan_braille, source_offset_for_expanded,
)


def event(kind: str, line: str = "a界🙂", row: int = 1, byte_column: int = 0, **extra) -> dict:
    payload = {"lineText": line, "cursor": {"line": row, "byteColumn": byte_column}, **extra}
    return {"type": kind, "payload": payload}


class SpeechPlannerTests(unittest.TestCase):
    def test_full_state_and_line_movement_speak_line(self) -> None:
        planner = SpeechPlanner()
        self.assertEqual("first", planner.plan(event("fullState", line="first"))[0].text)
        self.assertEqual("second", planner.plan(event("cursorMoved", line="second", row=2))[0].text)

    def test_same_line_movement_uses_utf8_byte_column(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState"))
        self.assertEqual("界", planner.plan(event("cursorMoved", byte_column=1))[0].text)
        self.assertEqual("🙂", planner.plan(event("cursorMoved", byte_column=4))[0].text)
        self.assertEqual([], planner.plan(event("cursorMoved", byte_column=8)))

    def test_mode_and_error_priorities(self) -> None:
        planner = SpeechPlanner()
        mode = planner.plan(event("modeChanged", mode="insert", modeRaw="i"))[0]
        self.assertEqual(("insert mode", Priority.CRITICAL), (mode.text, mode.priority))
        error = planner.plan({"type": "errorReceived", "payload": {"message": "E42"}})[0]
        self.assertEqual(Priority.CRITICAL, error.priority)

    def test_insert_completion_submode_is_not_announced_as_unknown_mode(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", mode="insert", modeRaw="i"))
        self.assertEqual([], planner.plan(event("modeChanged", mode="insert", modeRaw="ix")))

    def test_command_line_mode_survives_preceding_command_line_event(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", mode="normal", modeRaw="n"))
        planner.plan(event("commandLineChanged", mode="commandLine", modeRaw="c", commandLine=""))
        action = planner.plan(event("modeChanged", mode="commandLine", modeRaw="c"))[0]
        self.assertEqual("command-line mode", action.text)

    def test_terminal_normal_is_distinct_from_file_normal_mode(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan(event(
            "modeChanged", mode="terminalNormal", modeRaw="nt", buftype="terminal",
        ))[0]
        self.assertEqual("terminal-normal mode", action.text)

    def test_search_match_speaks_text_position_and_line(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan(event(
            "searchMatchChanged", line="alpha beta", row=4,
            matchIndex=2, matchCount=5, matchLine=4,
        ))[0]
        self.assertEqual("alpha beta, match 2 of 5, line 4", action.text)
        self.assertEqual(action.text, action.braille_message)

    def test_search_single_match_and_incomplete_count_remain_useful(self) -> None:
        planner = SpeechPlanner()
        single = planner.plan(event(
            "searchMatchChanged", line="only result", matchIndex=1, matchCount=1, matchLine=1,
        ))[0]
        self.assertEqual("only result, match 1 of 1, line 1", single.text)
        unknown = planner.plan(event(
            "searchMatchChanged", line="large result", row=9,
            matchIndex=0, matchCount=0, matchLine=9, matchIncomplete=2,
        ))[0]
        self.assertEqual("large result, line 9", unknown.text)

    def test_replacement_uses_status_and_sound(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan(event(
            "replacementPerformed", replacementMessage="2 substitutions on 2 lines",
        ))[0]
        self.assertEqual(("2 substitutions on 2 lines", "replace"), (action.text, action.sound))

    def test_visual_line_speaks_only_newly_selected_line(self) -> None:
        planner = SpeechPlanner()
        first = {
            "kind": "line", "text": "Petra war gestern einkaufen.",
            "selectedLines": [{"line": 1, "text": "Petra war gestern einkaufen."}],
        }
        entered = planner.plan(event(
            "modeChanged", mode="visualLine", modeRaw="V", selection=first,
        ))
        self.assertEqual("Petra war gestern einkaufen. selected", entered[1].text)
        extended = {
            "kind": "line", "text": "Petra war gestern einkaufen.\nZweite Zeile",
            "selectedLines": [
                {"line": 1, "text": "Petra war gestern einkaufen."},
                {"line": 2, "text": "Zweite Zeile"},
            ],
        }
        action = planner.plan(event("selectionChanged", row=2, selection=extended))[0]
        self.assertEqual("Zweite Zeile selected", action.text)

    def test_visual_line_handles_empty_single_line_and_multiple_additions(self) -> None:
        planner = SpeechPlanner()
        empty = {"kind": "line", "text": "", "selectedLines": [{"line": 1, "text": ""}]}
        action = planner.plan(event("selectionChanged", line="", selection=empty))[0]
        self.assertEqual("blank selected", action.text)
        expanded = {
            "kind": "line", "text": "\ntwo\nthree",
            "selectedLines": [
                {"line": 1, "text": ""}, {"line": 2, "text": "two"},
                {"line": 3, "text": "three"},
            ],
        }
        action = planner.plan(event("selectionChanged", row=3, selection=expanded))[0]
        self.assertEqual("two selected\nthree selected", action.text)

    def test_visual_line_shrink_reports_unselected_line(self) -> None:
        planner = SpeechPlanner()
        two = {
            "kind": "line", "text": "one\ntwo",
            "selectedLines": [{"line": 1, "text": "one"}, {"line": 2, "text": "two"}],
        }
        planner.plan(event("selectionChanged", row=2, selection=two))
        one = {"kind": "line", "text": "one", "selectedLines": [{"line": 1, "text": "one"}]}
        action = planner.plan(event("selectionChanged", selection=one))[0]
        self.assertEqual("two unselected", action.text)

    def test_visual_block_always_speaks_complete_block(self) -> None:
        planner = SpeechPlanner()
        block = {
            "kind": "block", "text": "Pet\nwar",
            "selectedLines": [{"line": 1, "text": "Pet"}, {"line": 2, "text": "war"}],
        }
        action = planner.plan(event("selectionChanged", row=2, selection=block))[0]
        self.assertEqual("Pet\nwar block selected", action.text)
        self.assertTrue(action.interrupt)

    def test_visual_block_handles_empty_and_ragged_rows(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan(event(
            "selectionChanged", selection={
                "kind": "block", "text": "界\n\nxy",
                "selectedLines": [
                    {"line": 1, "text": "界"}, {"line": 2, "text": ""},
                    {"line": 3, "text": "xy"},
                ],
            },
        ))[0]
        self.assertEqual("界\nblank\nxy block selected", action.text)

    def test_visual_character_speaks_only_added_text(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("selectionChanged", selection={"kind": "character", "text": "P"}))
        action = planner.plan(event(
            "selectionChanged", selection={"kind": "character", "text": "Petra"}, byte_column=4,
        ))[0]
        self.assertEqual("etra selected", action.text)

    def test_visual_selection_adds_no_punctuation_but_preserves_document_comma(self) -> None:
        plain = SpeechPlanner()
        plain.plan(event("selectionChanged", selection={"kind": "character", "text": "a"}))
        self.assertEqual(
            "b selected",
            plain.plan(event("selectionChanged", selection={"kind": "character", "text": "ab"}))[0].text,
        )
        punctuated = SpeechPlanner()
        punctuated.plan(event("selectionChanged", selection={"kind": "character", "text": "a"}))
        self.assertEqual(
            ", selected",
            punctuated.plan(event("selectionChanged", selection={"kind": "character", "text": "a,"}))[0].text,
        )

    def test_visual_selection_names_invisible_characters_and_forces_all_symbols(self) -> None:
        cases = {
            " ": "space selected",
            "  ": "2 spaces selected",
            "\t": "tab selected",
            "\u00a0": "nonbreaking space selected",
            "\u200b": "zero width space selected",
            "?": "? selected",
            "!": "! selected",
            ";": "; selected",
            ":": ": selected",
            "#": "# selected",
            "@": "@ selected",
            "€": "€ selected",
            "🙂": "🙂 selected",
            " x ": "space x space selected",
            "a b": "a b selected",
            "a  b": "a 2 spaces b selected",
            "a\tb": "a tab b selected",
            "a\nb": "a line break b selected",
        }
        for source, expected in cases.items():
            with self.subTest(source=repr(source)):
                action = SpeechPlanner().plan(event(
                    "selectionChanged", selection={"kind": "character", "text": source},
                ))[0]
                self.assertEqual(expected, action.text)
                self.assertTrue(action.force_symbols)
        planner = SpeechPlanner()
        planner.plan(event("selectionChanged", selection={"kind": "character", "text": "a?"}))
        removed = planner.plan(event(
            "selectionChanged", selection={"kind": "character", "text": "a"},
        ))[0]
        self.assertEqual("? unselected", removed.text)
        self.assertTrue(removed.force_symbols)

    def test_visual_character_reverse_growth_shrink_and_unchanged(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("selectionChanged", selection={"kind": "character", "text": "tra"}))
        grown = planner.plan(event(
            "selectionChanged", selection={"kind": "character", "text": "Petra"},
        ))[0]
        self.assertEqual("Pe selected", grown.text)
        shrunk = planner.plan(event(
            "selectionChanged", selection={"kind": "character", "text": "etra"},
        ))[0]
        self.assertEqual("P unselected", shrunk.text)
        self.assertEqual([], planner.plan(event(
            "selectionChanged", selection={"kind": "character", "text": "etra"},
        )))

    def test_matching_pair_speaks_symbol_line_and_crossing_sound(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="if (x) {", row=1, byte_column=3))
        same = planner.plan(event(
            "matchingPairMoved", line="if (x) {", row=1, byte_column=5, character=")",
        ))[0]
        self.assertEqual("matching ), line 1", same.text)
        self.assertTrue(same.force_symbols)
        crossed = planner.plan(event(
            "matchingPairMoved", line="}", row=4, byte_column=0, character="}",
        ))[0]
        self.assertEqual(("matching }, line 4", "lineCrossed"), (crossed.text, crossed.sound))

    def test_missing_matching_pair_has_status_and_error_sound(self) -> None:
        action = SpeechPlanner().plan(event("matchingPairNotFound", line="plain text"))[0]
        self.assertEqual(("no matching pair", "matchingError"), (action.text, action.sound))

    def test_spelling_format_enter_leave_and_typing_are_semantic(self) -> None:
        planner = SpeechPlanner()
        entered = planner.plan(event(
            "wordMoved", line="mispelled", word="mispelled", character="m",
            spellingError={"kind": "spelling", "startByteColumn": 0, "endByteColumn": 9},
        ))
        self.assertEqual("spelling", entered[0].format_error)
        left = planner.plan(event(
            "wordMoved", line="correct", word="correct", character="c",
        ))
        self.assertEqual("out:spelling", left[0].format_error)
        typed = planner.plan({
            "type": "spellingErrorTyped",
            "payload": {"spellingError": {"kind": "spelling"}},
        })[0]
        self.assertTrue(typed.typed_format_error)

    def test_line_reading_reports_spelling_error_anywhere_on_line(self) -> None:
        actions = SpeechPlanner().plan(event(
            "lineChanged", line="correct then mispelled", row=2,
            spellingErrors=[{
                "kind": "spelling", "startByteColumn": 13, "endByteColumn": 22,
            }],
        ))
        self.assertEqual("spelling", actions[0].format_error)
        self.assertEqual("correct then mispelled", actions[1].text)

    def test_diagnostic_navigation_speaks_source_severity_code_and_position(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="first", row=1))
        action = planner.plan(event(
            "diagnosticMoved", line="echo $value", row=4,
            diagnostic={
                "source": "shellcheck", "severity": "warning", "code": "SC2086",
                "message": "Double quote to prevent globbing", "index": 2, "count": 3,
                "line": 4,
            },
        ))[0]
        self.assertEqual(
            "shellcheck, warning, SC2086, Double quote to prevent globbing, 2 of 3, line 4",
            action.text,
        )
        self.assertEqual(action.text, action.braille_message)
        self.assertEqual("lineCrossed", action.sound)

    def test_context_changes_announce_tabs_windows_buffers_and_special_lists(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event(
            "fullState", bufferId=1, windowId=10, tabpageId=20,
            bufferName="/tmp/one.lua", tabIndex=1, tabCount=2,
        ))
        tab = planner.plan(event(
            "contextChanged", bufferId=2, windowId=11, tabpageId=21,
            bufferName="/tmp/two.lua", tabIndex=2, tabCount=2,
        ), focus_announcement="none")[0]
        self.assertEqual("tab 2 of 2, two.lua", tab.text)
        window = planner.plan(event(
            "contextChanged", bufferId=3, windowId=12, tabpageId=21,
            bufferName="/tmp/three.lua", windowIndex=2, windowCount=3, modified=True,
        ))[0]
        self.assertEqual("window 2 of 3, file three.lua, modified", window.text)
        quickfix = planner.plan(event(
            "contextChanged", windowType="quickfix", line="script.sh|4| warning SC2086",
        ))[0]
        self.assertEqual("quickfix, script.sh|4| warning SC2086", quickfix.text)

    def test_context_choice_coalesces_window_mode_file_flags_and_connection(self) -> None:
        planner = SpeechPlanner()
        text_window = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "windowIndex": 1, "windowCount": 2,
            "bufferName": "/work/T", "buftype": "", "modified": True,
            "lineText": "Text", "cursor": {"line": 1, "byteColumn": 0},
            "_connectionLabel": "Example",
        }
        terminal_window = {
            "bufferId": 2, "windowId": 11, "tabpageId": 20,
            "windowIndex": 2, "windowCount": 2,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "prompt", "cursor": {"line": 1, "byteColumn": 0},
            "_connectionLabel": "Example",
        }
        planner.plan({"type": "fullState", "payload": {
            **text_window, "mode": "normal", "modeRaw": "n",
        }})

        terminal_mode = planner.plan({"type": "modeChanged", "payload": {
            **terminal_window, "mode": "terminalNormal", "modeRaw": "nt",
        }}, focus_announcement="context")
        terminal_context = planner.plan({"type": "contextChanged", "payload": {
            **terminal_window, "mode": "terminalNormal", "modeRaw": "nt",
        }}, focus_announcement="context")
        text_mode = planner.plan({"type": "modeChanged", "payload": {
            **text_window, "mode": "normal", "modeRaw": "n",
        }}, focus_announcement="context")
        text_context = planner.plan({"type": "contextChanged", "payload": {
            **text_window, "mode": "normal", "modeRaw": "n",
        }}, focus_announcement="context")

        self.assertEqual([], terminal_mode)
        self.assertEqual(
            ["window 2 of 2, terminal-normal mode, on Example"],
            [action.text for action in terminal_context],
        )
        self.assertEqual([], text_mode)
        self.assertEqual(
            ["window 1 of 2, file T, modified, normal mode, on Example"],
            [action.text for action in text_context],
        )

    def test_in_place_buffer_switch_uses_configured_focus_presentation(self) -> None:
        initial = event(
            "fullState", line="first line", bufferId=1, windowId=10, tabpageId=20,
            bufferName="/work/one.lua", mode="normal",
        )
        switched = event(
            "contextChanged", line="second line", bufferId=2, windowId=10, tabpageId=20,
            bufferName="/work/two.lua", mode="insert", _connectionLabel="Example",
        )

        def enter_target_mode(planner: SpeechPlanner) -> None:
            planner.plan(event(
                "modeChanged", line="second line", bufferId=2, windowId=10, tabpageId=20,
                bufferName="/work/two.lua", mode="insert", modeRaw="i",
            ))

        silent_planner = SpeechPlanner()
        silent_planner.plan(initial)
        enter_target_mode(silent_planner)
        self.assertEqual(
            [], silent_planner.plan(switched, focus_announcement="none"),
        )

        line_planner = SpeechPlanner()
        line_planner.plan(initial)
        enter_target_mode(line_planner)
        line = line_planner.plan(switched, focus_announcement="line")[0]
        self.assertEqual(("second line", "second line"), (line.text, line.braille_message))

        context_planner = SpeechPlanner()
        context_planner.plan(initial)
        enter_target_mode(context_planner)
        context = context_planner.plan(switched, focus_announcement="context")[0]
        self.assertEqual(
            "file two.lua, insert mode, on Example", context.text,
        )

    def test_buffer_switch_line_is_not_overwritten_by_automatic_cursor_event(self) -> None:
        for starting_column in (0, 4):
            with self.subTest(startingColumn=starting_column):
                planner = SpeechPlanner()
                planner.plan(event(
                    "fullState", line="alpha", bufferId=1, windowId=10, tabpageId=20,
                    bufferName="/work/one.txt", mode="normal", byte_column=starting_column,
                ))
                target = {
                    "bufferId": 2, "windowId": 10, "tabpageId": 20,
                    "bufferName": "/work/two.txt", "mode": "normal",
                }
                self.assertEqual([], planner.plan(event(
                    "textChanged", line="target shell heading", byte_column=0, **target,
                )))
                line = planner.plan(event(
                    "contextChanged", line="target shell heading", byte_column=0, **target,
                ), focus_announcement="line")
                duplicate = planner.plan(event(
                    "contextChanged", line="target shell heading", byte_column=0, **target,
                ), focus_announcement="line")
                cursor = planner.plan(event(
                    "cursorMoved", line="target shell heading", byte_column=0, **target,
                ), focus_announcement="line")

                self.assertEqual(["target shell heading"], [action.text for action in line])
                self.assertEqual([], duplicate)
                self.assertEqual([], cursor)

    def test_buffer_command_coalesces_return_modes_into_focus_presentation(self) -> None:
        source = {
            "bufferId": 2, "windowId": 10, "tabpageId": 20,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "shell prompt", "cursor": {"line": 1, "byteColumn": 0},
        }
        target = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "bufferName": "/work/target.txt", "buftype": "",
            "lineText": "target line", "cursor": {"line": 1, "byteColumn": 0},
        }

        for focus_announcement, expected in (
            ("none", []),
            ("line", ["target line"]),
            ("context", ["file target.txt, normal mode, on Example"]),
        ):
            with self.subTest(focusAnnouncement=focus_announcement):
                planner = SpeechPlanner()
                planner.plan({"type": "fullState", "payload": {
                    **source, "mode": "terminalNormal", "modeRaw": "nt",
                }})
                planner.plan({"type": "commandLineChanged", "payload": {
                    **source, "mode": "commandLine", "modeRaw": "c",
                    "commandLine": "", "commandLineType": ":",
                }})
                command_mode = planner.plan({"type": "modeChanged", "payload": {
                    **source, "mode": "commandLine", "modeRaw": "c",
                }})
                planner.plan({"type": "commandLineChanged", "payload": {
                    **source, "mode": "commandLine", "modeRaw": "c",
                    "commandLine": "bp", "commandLineType": ":",
                }})
                terminal_return = planner.plan({"type": "modeChanged", "payload": {
                    **source, "mode": "terminalNormal", "modeRaw": "nt",
                }})
                target_return = planner.plan({"type": "modeChanged", "payload": {
                    **target, "mode": "normal", "modeRaw": "n",
                }})
                text_change = planner.plan({"type": "textChanged", "payload": {
                    **target, "mode": "normal", "modeRaw": "n",
                }})
                context = planner.plan({"type": "contextChanged", "payload": {
                    **target, "mode": "normal", "modeRaw": "n",
                    "_connectionLabel": "Example",
                }}, focus_announcement=focus_announcement)
                duplicate = planner.plan({"type": "contextChanged", "payload": {
                    **target, "mode": "normal", "modeRaw": "n",
                    "_connectionLabel": "Example",
                }}, focus_announcement=focus_announcement)
                cursor = planner.plan({"type": "cursorMoved", "payload": {
                    **target, "mode": "normal", "modeRaw": "n",
                }}, focus_announcement=focus_announcement)

                self.assertEqual(["command-line mode"], [a.text for a in command_mode])
                self.assertEqual([], terminal_return)
                self.assertEqual([], target_return)
                self.assertEqual([], text_change)
                self.assertEqual(expected, [a.text for a in context])
                self.assertEqual([], duplicate)
                self.assertEqual([], cursor)

    def test_search_named_like_buffer_command_does_not_coalesce_mode(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", mode="normal", modeRaw="n"))
        planner.plan(event(
            "commandLineChanged", mode="commandLine", modeRaw="c",
            commandLine="bn", commandLineType="/",
        ))
        planner.plan(event("modeChanged", mode="commandLine", modeRaw="c"))
        returned = planner.plan(event("modeChanged", mode="normal", modeRaw="n"))
        self.assertEqual(["normal mode"], [action.text for action in returned])

    def test_unswitched_terminal_buffer_command_speaks_message_not_return_mode(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event(
            "fullState", mode="terminalNormal", modeRaw="nt", buftype="terminal",
        ))
        planner.plan(event(
            "commandLineChanged", mode="commandLine", modeRaw="c", buftype="terminal",
            commandLine="bp", commandLineType=":",
        ))
        planner.plan(event(
            "modeChanged", mode="commandLine", modeRaw="c", buftype="terminal",
        ))
        message = planner.plan({"type": "messageReceived", "payload": {
            "reason": "terminalBufferNavigation",
            "message": "no other listed buffer; the buffer command did not switch",
        }})
        returned = planner.plan(event(
            "modeChanged", mode="terminalNormal", modeRaw="nt", buftype="terminal",
        ))
        later = planner.plan(event("modeChanged", mode="terminal", modeRaw="t", buftype="terminal"))
        self.assertEqual(
            ["no other listed buffer; the buffer command did not switch"],
            [action.text for action in message],
        )
        self.assertEqual([], returned)
        self.assertEqual(["a界🙂"], [action.text for action in later])

    def test_terminal_command_entry_uses_focus_choice_and_direct_input_reads_line(self) -> None:
        source = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "bufferName": "/work/source.txt", "buftype": "",
            "lineText": "source", "cursor": {"line": 1, "byteColumn": 0},
        }
        target_blank = {
            "bufferId": 2, "windowId": 10, "tabpageId": 20,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }
        target_ready = {
            **target_blank, "lineText": "shell prompt", "changedtick": 4,
            "cursor": {"line": 1, "byteColumn": 12},
        }
        target_final = {
            **target_blank, "lineText": "ready prompt", "changedtick": 5,
            "cursor": {"line": 2, "byteColumn": 12},
        }

        for focus_announcement, expected_context, expected_line in (
            ("none", [], []),
            ("line", [], ["shell prompt"]),
            ("context", ["terminal-normal mode, on Example"], []),
        ):
            with self.subTest(focusAnnouncement=focus_announcement):
                planner = SpeechPlanner()
                planner.plan({"type": "fullState", "payload": {
                    **source, "mode": "normal", "modeRaw": "n",
                }})
                planner.plan({"type": "commandLineChanged", "payload": {
                    **source, "mode": "commandLine", "modeRaw": "c",
                    "commandLine": "terminal", "commandLineType": ":",
                }})
                planner.plan({"type": "modeChanged", "payload": {
                    **source, "mode": "commandLine", "modeRaw": "c",
                }})
                normal_return = planner.plan({"type": "modeChanged", "payload": {
                    **source, "mode": "normal", "modeRaw": "n",
                }})
                terminal_return = planner.plan({"type": "modeChanged", "payload": {
                    **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
                }})
                blank_text = planner.plan({"type": "textChanged", "payload": {
                    **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
                }}, focus_announcement=focus_announcement)
                context = planner.plan({"type": "contextChanged", "payload": {
                    **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
                    "_connectionLabel": "Example",
                }}, focus_announcement=focus_announcement)
                blank_cursor = planner.plan({"type": "cursorMoved", "payload": {
                    **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
                }}, focus_announcement=focus_announcement)
                first_line = planner.plan({"type": "textChanged", "payload": {
                    **target_ready, "mode": "terminalNormal", "modeRaw": "nt",
                }}, focus_announcement=focus_announcement)
                automatic_cursor = planner.plan({"type": "cursorMoved", "payload": {
                    **target_ready, "mode": "terminalNormal", "modeRaw": "nt",
                }}, focus_announcement=focus_announcement)
                later_initialization = planner.plan({"type": "textChanged", "payload": {
                    **target_final, "mode": "terminalNormal", "modeRaw": "nt",
                }}, focus_announcement=focus_announcement)
                later_cursor = planner.plan({"type": "cursorMoved", "payload": {
                    **target_final, "mode": "terminalNormal", "modeRaw": "nt",
                }}, focus_announcement=focus_announcement)
                direct = planner.plan({"type": "modeChanged", "payload": {
                    **target_final, "mode": "terminal", "modeRaw": "t",
                }}, focus_announcement=focus_announcement)

                self.assertEqual([], normal_return)
                self.assertEqual([], terminal_return)
                self.assertEqual([], blank_text)
                self.assertEqual(expected_context, [action.text for action in context])
                self.assertEqual([], blank_cursor)
                self.assertEqual(expected_line, [action.text for action in first_line])
                self.assertEqual([], automatic_cursor)
                self.assertEqual([], later_initialization)
                self.assertEqual([], later_cursor)
                self.assertEqual(["ready prompt"], [action.text for action in direct])

    def test_terminal_context_before_target_mode_still_suppresses_initial_output(self) -> None:
        planner = SpeechPlanner()
        source = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "bufferName": "/work/source.txt", "buftype": "",
            "lineText": "source", "cursor": {"line": 1, "byteColumn": 0},
        }
        terminal = {
            "bufferId": 2, "windowId": 10, "tabpageId": 20,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }
        planner.plan({"type": "fullState", "payload": {
            **source, "mode": "normal", "modeRaw": "n",
        }})
        planner.plan({"type": "commandLineChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
            "commandLine": "terminal", "commandLineType": ":",
        }})
        planner.plan({"type": "modeChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
        }})
        self.assertEqual([], planner.plan({"type": "modeChanged", "payload": {
            **source, "mode": "normal", "modeRaw": "n",
        }}))

        context = planner.plan({"type": "contextChanged", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
            "_connectionLabel": "Example",
        }}, focus_announcement="context")
        late_mode = planner.plan({"type": "modeChanged", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
        }}, focus_announcement="context")
        initialization = planner.plan({"type": "textChanged", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
            "lineText": "Terminal heading", "changedtick": 4,
            "cursor": {"line": 1, "byteColumn": 8},
        }}, focus_announcement="context")
        cursor = planner.plan({"type": "cursorMoved", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
            "lineText": "Terminal heading", "changedtick": 4,
            "cursor": {"line": 1, "byteColumn": 8},
        }}, focus_announcement="context")

        self.assertEqual(
            ["terminal-normal mode, on Example"],
            [action.text for action in context],
        )
        self.assertEqual([], late_mode)
        self.assertEqual([], initialization)
        self.assertEqual([], cursor)

    def test_non_terminal_ex_command_still_announces_return_mode(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", mode="normal", modeRaw="n"))
        planner.plan(event(
            "commandLineChanged", mode="commandLine", modeRaw="c",
            commandLine="echo 1", commandLineType=":",
        ))
        planner.plan(event("modeChanged", mode="commandLine", modeRaw="c"))
        returned = planner.plan(event("modeChanged", mode="normal", modeRaw="n"))
        self.assertEqual(["normal mode"], [action.text for action in returned])

    def test_file_manager_entries_announce_semantic_type_and_tree_state(self) -> None:
        planner = SpeechPlanner()
        directory = planner.plan({"type": "fileManagerEntryChanged", "payload": {
            "fileManager": {"name": "netrw", "root": "/tmp", "entry": {
                "name": "src", "type": "directory", "selectionState": "marked",
            }},
        }})[0]
        link = planner.plan({"type": "fileManagerEntryChanged", "payload": {
            "fileManager": {"name": "adapter", "entry": {
                "name": "current", "type": "symbolicLink", "expanded": False,
            }},
        }})[0]
        copied = SpeechPlanner().plan({"type": "fileManagerEntryChanged", "payload": {
            "fileManager": {"name": "neo-tree", "entry": {
                "name": "notes.txt", "type": "file", "marked": True,
                "clipboardState": "copied",
            }},
        }})[0]
        self.assertEqual("src, directory, marked", directory.text)
        self.assertTrue(directory.force_symbols)
        self.assertEqual(directory.text, directory.braille_message)
        self.assertEqual("current, symbolic link, collapsed", link.text)
        self.assertEqual("notes.txt, file, copied", copied.text)

    def test_file_manager_same_entry_state_changes_are_explicit(self) -> None:
        planner = SpeechPlanner()
        def manager(**entry: object) -> dict:
            return {"type": "fileManagerEntryChanged", "payload": {
                "fileManager": {"name": "tree", "entry": {
                    "name": "src", "path": "/work/src", "type": "directory", **entry,
                }},
            }}

        initial = planner.plan(manager(selectionState="unmarked", expanded=False))[0]
        marked = planner.plan(manager(selectionState="marked", expanded=False))[0]
        unmarked = planner.plan(manager(selectionState="unmarked", expanded=False))[0]
        copied = planner.plan(manager(clipboardState="copied", expanded=False))[0]
        cut = planner.plan(manager(clipboardState="cut", expanded=False))[0]
        cleared = planner.plan(manager(clipboardState="none", expanded=False))[0]
        expanded = planner.plan(manager(clipboardState="none", expanded=True))[0]

        self.assertEqual("src, directory, collapsed", initial.text)
        self.assertEqual("src, marked", marked.text)
        self.assertEqual("src, unmarked", unmarked.text)
        self.assertEqual("src, copied", copied.text)
        self.assertEqual("src, cut", cut.text)
        self.assertEqual("src, clipboard cleared", cleared.text)
        self.assertEqual("src, expanded", expanded.text)

    def test_file_manager_action_results_are_compact_and_typed(self) -> None:
        planner = SpeechPlanner()
        def result(**action: object) -> dict:
            return {"type": "fileManagerActionResult", "payload": {
                "fileManagerAction": {
                    "manager": "tree", "action": "copy", "result": "success",
                    **action,
                },
            }}

        copied = planner.plan(result(name="notes.txt"))[0]
        batch = planner.plan(result(action="multiple", count=4))[0]
        cancelled = planner.plan(result(action="rename", result="cancelled", name="old.txt"))[0]
        failed = planner.plan(result(action="delete", result="failed", name="locked.txt"))[0]

        self.assertEqual("notes.txt, copied", copied.text)
        self.assertEqual("4 file-manager actions completed", batch.text)
        self.assertEqual("rename of old.txt cancelled", cancelled.text)
        self.assertEqual(Priority.STATUS, cancelled.priority)
        self.assertEqual("delete of locked.txt failed", failed.text)
        self.assertEqual(Priority.CRITICAL, failed.priority)
        self.assertTrue(failed.interrupt)
        self.assertEqual(failed.text, failed.braille_message)

    def test_focus_context_announces_file_mode_and_special_buffers_compactly(self) -> None:
        planner = SpeechPlanner()
        file_action = planner.plan(event(
            "focusContext", bufferName="C:\\work\\example.lua", mode="insert",
            modified=True, _connectionLabel="Example",
        ))[0]
        terminal_action = planner.plan(event(
            "focusContext", bufferName="term://sensitive-shell", buftype="terminal",
            mode="terminal",
        ))[0]
        manager_action = planner.plan(event(
            "focusContext", mode="normal", fileManager={
                "name": "netrw", "root": "/work", "entry": {
                    "name": "src", "type": "directory", "expanded": True,
                },
            },
        ))[0]
        empty_manager_action = planner.plan(event(
            "focusContext", mode="normal", fileManager={
                "name": "netrw", "root": "/private/root",
                "currentDirectory": "/private/root/current",
            },
        ))[0]
        self.assertEqual("file example.lua, modified, insert mode, on Example", file_action.text)
        self.assertEqual("terminal mode", terminal_action.text)
        self.assertNotIn("sensitive", terminal_action.text)
        self.assertEqual("netrw, src, directory, expanded, normal mode", manager_action.text)
        self.assertEqual(manager_action.text, manager_action.braille_message)
        self.assertEqual("netrw, current, normal mode", empty_manager_action.text)
        self.assertNotIn("private", empty_manager_action.text)

    def test_focus_context_presentation_can_be_silent_or_announce_current_line(self) -> None:
        state = event(
            "focusContext", bufferName="C:\\work\\example.lua", mode="insert",
            lineText="\tprint('Grüße 👋')", _connectionLabel="Example",
        )
        silent = SpeechPlanner().plan(state, focus_announcement="none")
        line = SpeechPlanner().plan(state, focus_announcement="line")[0]
        blank = SpeechPlanner().plan(
            event("focusContext", mode="normal", lineText=""),
            focus_announcement="line",
        )[0]

        self.assertEqual([], silent)
        self.assertEqual("\tprint('Grüße 👋')", line.text)
        self.assertEqual(line.text, line.braille_message)
        self.assertIsNotNone(line.indentation_tones)
        self.assertEqual(("blank", "blank"), (blank.text, blank.braille_message))

    def test_notify_message_priority_title_and_braille(self) -> None:
        planner = SpeechPlanner()
        normal = planner.plan({
            "type": "messageReceived",
            "payload": {"message": "Formatting complete", "messageTitle": "LSP", "messageLevel": 2},
        })[0]
        self.assertEqual(("LSP: Formatting complete", Priority.STATUS), (normal.text, normal.priority))
        self.assertEqual(normal.text, normal.braille_message)
        error = planner.plan({
            "type": "messageReceived", "payload": {"message": "Build failed", "messageLevel": 4},
        })[0]
        self.assertEqual(Priority.CRITICAL, error.priority)
        self.assertTrue(error.interrupt)

    def test_disconnect_resets_navigation_context(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="old"))
        action = planner.plan({"type": "connectionStateChanged", "payload": {"connection": {"neovim": "disconnected"}}})[0]
        self.assertEqual("Neovim disconnected", action.text)
        self.assertEqual("new", planner.plan(event("cursorMoved", line="new"))[0].text)

    def test_invalid_byte_boundary_is_critical(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="界"))
        action = planner.plan(event("cursorMoved", line="界", byte_column=1))[0]
        self.assertEqual(Priority.CRITICAL, action.priority)

    def test_inserted_text_is_spoken_from_text_change(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="ab", byte_column=2))
        action = planner.plan(event("textChanged", line="ab界", byte_column=5))[0]
        self.assertEqual(("界", False, True), (action.text, action.interrupt, action.typed))

    def test_inserted_text_in_middle_is_spoken(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="ac"))
        self.assertEqual("b", planner.plan(event("textChanged", line="abc"))[0].text)

    def test_terminal_punctuation_is_forwarded_to_nvda_typing_echo(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line=""))
        action = planner.plan(event("textChanged", line="d!?", byte_column=3))[0]
        self.assertEqual(("d!?", True), (action.text, action.typed))

    def test_character_and_word_navigation_force_symbol_detail(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="!? word"))
        character = planner.plan(event("characterMoved", line="!? word", character="?", byte_column=1))[0]
        word = planner.plan(event("wordMoved", line="!? word", word="word", character="w", byte_column=3))[0]
        self.assertTrue(character.spelling)
        self.assertTrue(word.force_symbols)

    def test_non_line_navigation_signals_crossed_line(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="last", row=1, byte_column=3))
        word = planner.plan(event("wordMoved", line="next", row=2, byte_column=0, word="next", character="n"))[0]
        self.assertEqual("lineCrossed", word.sound)
        self.assertIsNone(word.indentation_tones)
        planner.plan(event("lineChanged", line="third", row=3, byte_column=0, character="t"))
        character = planner.plan(event("characterMoved", line="fourth", row=4, byte_column=0, character="f"))[0]
        self.assertEqual("lineCrossed", character.sound)

    def test_normal_mode_cross_line_navigation_reports_indentation_tone(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="plain", row=1, mode="normal"))
        character = planner.plan(event(
            "characterMoved", line="\t  indented", row=2, byte_column=2,
            character=" ", mode="normal",
        ))[0]
        self.assertEqual(("lineCrossed", 6), (character.sound, character.indentation_tones))

    def test_deleted_text_has_delete_sound(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="abc"))
        action = planner.plan(event("textChanged", line="ac"))[0]
        self.assertEqual(("deleted b", "delete"), (action.text, action.sound))

    def test_word_and_line_navigation_include_character(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="old"))
        word = planner.plan(event("wordMoved", line="hallo welt", word="hallo", character="h"))[0]
        self.assertEqual(("hallo", "h"), (word.text, word.character_suffix))
        line = planner.plan(event("lineChanged", line="hallo", row=2, character="h", indentation=0))[0]
        self.assertEqual(("hallo", "h"), (line.text, line.character_suffix))

    def test_word_navigation_treats_punctuation_as_its_own_target(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="hallo", word="hallo", character="h"))
        punctuation = planner.plan(event(
            "wordMoved", line="hallo, wie", byte_column=5, word=",", character=",",
        ))[0]
        self.assertEqual((",", None, True), (
            punctuation.text, punctuation.character_suffix, punctuation.force_symbols,
        ))

    def test_line_cursor_character_is_spelled_separately_from_abbreviation_context(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="old"))
        action = planner.plan(event(
            "lineChanged", line="moin", row=2, character="m", indentation=0,
        ))[0]
        self.assertEqual(("moin", "m"), (action.text, action.character_suffix))

    def test_vertical_navigation_ticks_only_when_horizontal_position_changes(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="abc", row=1, byte_column=0))
        unchanged = planner.plan(event("lineChanged", line="def", row=2, byte_column=0, character="d"))[0]
        self.assertIsNone(unchanged.sound)
        planner.plan(event("characterMoved", line="def", row=2, byte_column=1, character="e"))
        changed = planner.plan(event("lineChanged", line="x", row=3, byte_column=0, character="x"))[0]
        self.assertEqual("lineStart", changed.sound)

    def test_linewise_delete_and_word_change_have_distinct_sounds(self) -> None:
        planner = SpeechPlanner()
        deleted = planner.plan({"type": "textDeleted", "payload": {
            "beforeText": "delete this line", "lineText": "next", "linewise": True,
        }})[0]
        changed = planner.plan({"type": "textReplaced", "payload": {
            "beforeText": "hello world", "lineText": " world", "linewise": False,
        }})[0]
        self.assertEqual(("deleted delete this line", "delete"), (deleted.text, deleted.sound))
        self.assertEqual(("replaced hello", "replace"), (changed.text, changed.sound))

    def test_linewise_delete_speaks_new_cursor_line_and_its_indentation(self) -> None:
        planner = SpeechPlanner()
        actions = planner.plan({"type": "textDeleted", "payload": {
            "beforeText": "old line", "lineText": "\t  next line", "linewise": True,
        }})
        self.assertEqual(["deleted old line", "\t  next line"], [action.text for action in actions])
        self.assertEqual(6, actions[1].indentation_tones)

    def test_line_navigation_exposes_nvda_compatible_indentation_pitch(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="plain", row=1))
        action = planner.plan(event("lineChanged", line="    indented", row=2))[0]
        self.assertEqual(4, action.indentation_tones)

    def test_indentation_is_reported_only_when_it_changes(self) -> None:
        planner = SpeechPlanner()
        first = planner.plan(event(
            "fullState", line="    one", row=1, indentation=4, shiftwidth=4,
        ))[0]
        same = planner.plan(event(
            "lineChanged", line="    two", row=2, indentation=4, shiftwidth=4,
        ))[0]
        none = planner.plan(event(
            "lineChanged", line="plain", row=3, indentation=0, shiftwidth=4,
        ))[0]
        still_none = planner.plan(event(
            "lineChanged", line="also plain", row=4, indentation=0, shiftwidth=4,
        ))[0]
        self.assertEqual((4, 1), (first.indentation_tones, first.indentation_level))
        self.assertIsNone(same.indentation_tones)
        self.assertEqual((0, 0), (none.indentation_tones, none.indentation_level))
        self.assertIsNone(still_none.indentation_tones)

    def test_indentation_level_uses_neovim_shiftwidth(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan(event(
            "fullState", line="        nested", indentation=8, shiftwidth=4,
        ))[0]
        self.assertEqual(2, action.indentation_level)

    def test_boundaries_have_distinct_sounds(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="first"))
        start = planner.plan(event("fileStart", line="first", character="f"))[0]
        end = planner.plan(event("fileEnd", line="last", row=9, character="l"))[0]
        self.assertEqual("fileStart", start.sound)
        self.assertEqual("fileEnd", end.sound)

    def test_line_boundaries_are_sound_only(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="abc"))
        start = planner.plan(event("lineStart", line="abc", byte_column=0))[0]
        end = planner.plan(event("lineEnd", line="abc", byte_column=2))[0]
        self.assertEqual(("", "lineStart"), (start.text, start.sound))
        self.assertEqual(("", "lineEnd"), (end.text, end.sound))

    def test_command_line_insert_uses_typed_echo(self) -> None:
        planner = SpeechPlanner()
        planner.plan({"type": "commandLineChanged", "payload": {"commandLine": ""}})
        action = planner.plan({"type": "commandLineChanged", "payload": {"commandLine": "set"}})[0]
        self.assertEqual(("set", True), (action.text, action.typed))

    def test_completion_menu_announces_position_kind_and_parameters(self) -> None:
        planner = SpeechPlanner()
        opened = planner.plan({"type": "menuOpened", "payload": {"itemCount": 5}})[0]
        selected = planner.plan({"type": "menuSelectionChanged", "payload": {
            "itemIndex": 1,
            "itemCount": 5,
            "item": {"label": "printf", "kind": "function", "parameters": "format, ..."},
        }})[0]
        closed = planner.plan({"type": "menuClosed", "payload": {}})[0]
        self.assertEqual("suggestionsOpen", opened.sound)
        self.assertEqual("printf, 1 von 5, function, Parameter format, ...", selected.text)
        self.assertEqual(selected.text, selected.braille_message)
        self.assertEqual("suggestionsClose", closed.sound)

    def test_single_completion_omits_redundant_position(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan({"type": "menuSelectionChanged", "payload": {
            "itemIndex": 1, "itemCount": 1,
            "item": {"label": "print", "kind": "function", "parameters": "value"},
        }})[0]
        self.assertNotIn("1 von 1", action.text)

    def test_structured_prompts_are_announced_without_echoing_input(self) -> None:
        planner = SpeechPlanner()
        opened = planner.plan({"type": "promptOpened", "payload": {
            "promptKind": "input", "prompt": "Branch name", "defaultValuePresent": True,
        }})[0]
        accepted = planner.plan({"type": "promptClosed", "payload": {
            "promptKind": "input", "accepted": True,
        }})
        canceled = planner.plan({"type": "promptClosed", "payload": {
            "promptKind": "input", "accepted": False,
        }})[0]
        selected = planner.plan({"type": "promptClosed", "payload": {
            "promptKind": "select", "accepted": True, "selectedLabel": "main",
        }})[0]
        self.assertEqual("Branch name", opened.text)
        self.assertEqual([], accepted)
        self.assertEqual("canceled", canceled.text)
        self.assertEqual("selected main", selected.text)

    def test_folds_marks_registers_and_macros_are_structured(self) -> None:
        planner = SpeechPlanner()
        fold = planner.plan({"type": "foldChanged", "payload": {
            "foldAction": "close", "startLine": 2, "endLine": 5,
        }})[0]
        mark = planner.plan({"type": "markMoved", "payload": {
            "markName": "a", "lineText": "target line",
        }})[0]
        yank = planner.plan({"type": "registerChanged", "payload": {
            "registerName": "b", "registerText": "secret text",
        }})[0]
        selected = planner.plan({"type": "registerSelected", "payload": {
            "registerName": "b", "registerText": "first\nsecond",
        }})[0]
        recording = planner.plan({"type": "macroRecordingStarted", "payload": {
            "registerName": "q",
        }})[0]
        self.assertEqual("fold closed, lines 2 to 5", fold.text)
        self.assertEqual("mark a, target line", mark.text)
        self.assertEqual("yanked to register b", yank.text)
        self.assertNotIn("secret", yank.text)
        self.assertEqual("register b, first second", selected.text)
        self.assertEqual("recording macro q", recording.text)

    def test_lsp_signature_announces_active_parameter(self) -> None:
        planner = SpeechPlanner()
        action = planner.plan({"type": "signatureChanged", "payload": {
            "signature": "printf(format, ...)", "parameter": "format",
            "activeParameter": 1, "signatureIndex": 1, "signatureCount": 2,
        }})[0]
        self.assertEqual("printf(format, ...), Parameter format, 1 von 2", action.text)
        self.assertEqual(action.text, action.braille_message)

    def test_new_unindented_line_ticks_without_boundary_speech(self) -> None:
        planner = SpeechPlanner()
        planner.plan(event("fullState", line="old", row=1))
        action = planner.plan(event("textChanged", line="", row=2, indentation=0))[0]
        self.assertEqual(("", "lineStart"), (action.text, action.sound))


class SessionGateTests(unittest.TestCase):
    def test_every_condition_is_required(self) -> None:
        gate = SessionGate()
        terminal = TerminalIdentity(10, 20, "windowsTerminal", (42, 20, 4, 6))
        gate.manual_enabled = True
        gate.authenticated = True
        gate.nvim_active = True
        gate.bound_terminal = terminal
        gate.focused = terminal
        self.assertTrue(gate.should_suppress(terminal))
        self.assertFalse(gate.should_suppress(
            TerminalIdentity(10, 21, "windowsTerminal", (42, 21, 4, 6))
        ))

    def test_unsupported_frontend_can_never_suppress(self) -> None:
        gate = SessionGate()
        terminal = TerminalIdentity(10, 20, "putty")
        gate.manual_enabled = gate.authenticated = gate.nvim_active = True
        gate.bound_terminal = gate.focused = terminal
        self.assertFalse(gate.suppression_active)
        self.assertFalse(gate.should_suppress(terminal))

    def test_disconnect_and_disable_fail_open(self) -> None:
        gate = SessionGate()
        terminal = TerminalIdentity(10, 20, "windowsTerminal", (42, 20, 4, 6))
        gate.manual_enabled = gate.authenticated = gate.nvim_active = True
        gate.bound_terminal = gate.focused = terminal
        gate.disconnect()
        self.assertFalse(gate.suppression_active)
        self.assertIsNone(gate.bound_terminal)

    def test_terminal_passthrough_disables_only_terminal_suppression(self) -> None:
        gate = SessionGate()
        terminal = TerminalIdentity(10, 20, "windowsTerminal", (42, 20, 4, 6))
        gate.manual_enabled = gate.authenticated = gate.nvim_active = True
        gate.focused = gate.bound_terminal = terminal
        self.assertTrue(gate.suppression_active)
        gate.terminal_passthrough = True
        self.assertFalse(gate.suppression_active)
        self.assertFalse(gate.should_suppress(terminal))
        gate.terminal_passthrough = False
        self.assertTrue(gate.suppression_active)
        gate.disconnect()
        self.assertFalse(gate.terminal_passthrough)
        gate.manual_enabled = True
        gate.disable()
        self.assertFalse(gate.manual_enabled)


class BraillePlannerTests(unittest.TestCase):
    def test_spelling_and_grammar_use_nvda_reference_markers(self) -> None:
        plan = plan_braille({
            "lineText": "bad grammar", "cursor": {"byteColumn": 1},
            "reportSpellingBraille": True,
            "spellingErrors": [
                {"kind": "spelling", "startByteColumn": 0, "endByteColumn": 3},
                {"kind": "grammar", "startByteColumn": 4, "endByteColumn": 11},
            ],
        })
        self.assertEqual("⠑bad⡑ ⠛grammar⡛", plan.text)
        self.assertEqual(2, plan.cursor)
    def test_indentation_and_tabs_are_preserved_visually(self) -> None:
        plan = plan_braille({
            "lineText": "\t  value",
            "tabstop": 4,
            "cursor": {"characterColumn": 3},
        })
        self.assertEqual("      value", plan.text)
        self.assertEqual(6, plan.cursor)

    def test_current_line_selection_uses_character_offsets(self) -> None:
        plan = plan_braille({
            "lineText": "\t界🙂z",
            "tabstop": 4,
            "cursor": {"byteColumn": 8},
            "selection": {"currentLine": {"startByteColumn": 1, "endByteColumn": 8}},
        })
        self.assertEqual("    界🙂z", plan.text)
        self.assertEqual((4, 6), (plan.selection_start, plan.selection_end))
        self.assertIsNone(plan.cursor)

    def test_no_selection_keeps_cursor(self) -> None:
        plan = plan_braille({"lineText": "a🙂", "cursor": {"byteColumn": 1}})
        self.assertEqual(1, plan.cursor)
        self.assertIsNone(plan.selection_start)

    def test_routing_inside_expanded_tab_maps_to_tab_source(self) -> None:
        plan = plan_braille({"lineText": "\tX", "tabstop": 4, "cursor": {"byteColumn": 0}})
        self.assertEqual(0, source_offset_for_expanded(plan, 3))
        self.assertEqual(1, source_offset_for_expanded(plan, 4))

    def test_file_manager_braille_is_semantic_and_persistent(self) -> None:
        plan = plan_braille({
            "lineText": "   café/ [decorated]",
            "cursor": {"byteColumn": 8},
            "fileManager": {"name": "tree", "entry": {
                "name": "café", "type": "directory",
                "selectionState": "marked", "expanded": False,
            }},
        })
        self.assertEqual("café, directory, marked, collapsed", plan.text)
        self.assertEqual(2, plan.cursor)
        self.assertEqual((6, 7, 8, 9), plan.routing_byte_columns[:4])
        self.assertIsNone(plan.routing_byte_columns[len("café")])

    def test_file_manager_braille_routes_only_an_unambiguous_name(self) -> None:
        duplicate = plan_braille({
            "lineText": "item -> item", "cursor": {"byteColumn": 0},
            "fileManager": {"name": "oil", "entry": {"name": "item", "type": "file"}},
        })
        self.assertTrue(all(value is None for value in duplicate.routing_byte_columns))
        context = plan_braille({
            "lineText": '" header', "cursor": {"byteColumn": 0},
            "fileManager": {"name": "netrw", "currentDirectory": "/private/work"},
        })
        self.assertEqual("netrw, work", context.text)
        self.assertTrue(all(value is None for value in context.routing_byte_columns))
        invalid_entry = plan_braille({
            "lineText": "decorated manager header", "cursor": {"byteColumn": 4},
            "fileManager": {"name": "oil", "entry": {"type": "directory"}},
        })
        self.assertEqual("oil", invalid_entry.text)
        self.assertTrue(all(value is None for value in invalid_entry.routing_byte_columns))


class DiagnosticTests(unittest.TestCase):
    def test_sensitive_content_is_redacted_and_buffer_is_bounded(self) -> None:
        diagnostics = DiagnosticBuffer(max_entries=2)
        diagnostics.record(
            "one", password="secret", lineText="private source",
            registerText="private macro", beforeText="deleted source",
        )
        diagnostics.record("two", sequence=2)
        diagnostics.record("three", sequence=3)
        report = diagnostics.report({"version": "test"})
        self.assertNotIn("secret", report)
        self.assertNotIn("private source", report)
        self.assertNotIn("private macro", report)
        self.assertNotIn("deleted source", report)
        self.assertNotIn('"category": "one"', report)
        self.assertIn('"category": "three"', report)

    def test_process_stderr_is_visible_but_editor_text_remains_redacted(self) -> None:
        diagnostics = DiagnosticBuffer()
        diagnostics.record(
            "sshStderr",
            stderrLine="nvim-nvda-bridge: no registered session found",
            text="private editor contents",
        )
        report = diagnostics.report()
        self.assertIn("no registered session found", report)
        self.assertNotIn("private editor contents", report)


if __name__ == "__main__":
    unittest.main()
