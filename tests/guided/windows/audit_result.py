"""Recheck every completed guided case and the original PCM from a local suite run."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path


def verify_serial_log(workspace, run_id, candidate):
    lines = (workspace / f"run-{run_id}.log").read_text(encoding="utf-8").splitlines()
    report = json.loads((workspace / f"run-{run_id}.json").read_text(encoding="utf-8-sig"))
    provenance = f"NAL_SETUP candidate {candidate['name']} SHA256 {candidate['sha256']}"
    passed = [line.removeprefix("NAL_PASS ") for line in lines if line.startswith("NAL_PASS ")]
    if (lines.count(f"NAL_START {run_id}") != 1 or lines.count(f"NAL_END {run_id}") != 1
            or lines.count(provenance) != 1 or passed != report["steps"]):
        raise ValueError(f"Guest report {run_id} does not match its original serial log")
    results = [line.removeprefix("NAL_RESULT ") for line in lines if line.startswith("NAL_RESULT ")]
    if len(results) != 1 or not json.loads(results[0]).items() <= report.items():
        raise ValueError(f"Guest report {run_id} differs from the result emitted by the guest")
    return lines


def verify_l1_status(observed, log):
    relevant = {"NAL_KEY lsp-query", "NAL_KEY lsp-stop", "NAL_PASS l1_pyright_actually_detached",
                "NAL_PASS l1_enabled_native_status_spoken", "NAL_PASS l1_disabled_native_status_spoken"}
    order = [line for line in log if line in relevant]
    if (order != ["NAL_KEY lsp-query", "NAL_PASS l1_enabled_native_status_spoken", "NAL_KEY lsp-stop",
                  "NAL_PASS l1_pyright_actually_detached", "NAL_KEY lsp-query",
                  "NAL_PASS l1_disabled_native_status_spoken"]
            or observed["status"] != [{"clients": ["pyright"], "speech": ["LSP clients: pyright"]},
                                      {"clients": [], "speech": ["No LSP client attached"]}]):
        raise ValueError("L1 did not verify both native client states and their spoken status")


def verify_l2_hints(positive, control):
    with_hints, without_hints = positive["actions"], control["actions"]
    keys = ["lsp-query", "lsp-first-argument", "lsp-second-argument", "lsp-third-argument",
            "lsp-previous-word", "lsp-left", "lsp-right"]
    expected = [["parameter 1 of 3: price: float"], ["parameter 2 of 3: quantity: int = 1"],
                ["parameter 3 of 3: discount: float = 0"], [],
                ["parameter 2 of 3: quantity: int = 1", "parameter 1 of 3: price: float"], [], []]
    if (any([action["key"] for action in runs] != keys for runs in (with_hints, without_hints))
            or [action["hints"] for action in with_hints] != expected
            or any(action["hints"] for action in without_hints)
            or any([action["byteColumn"] for action in run[-2:]] != [35, 36]
                   for run in (with_hints, without_hints))):
        raise ValueError("L2 did not demonstrate silenced hints and unchanged native cursor movement")


def verify_l4_edits(fixtures, positive, control):
    names = ("lsp_features.py", "lsp_rename_consumer.py")
    originals = {name: (fixtures / name).read_text(encoding="utf-8").splitlines() for name in names}
    pattern = "calculate_tip"
    targets = [{"filename": name, "row": row, "column": line.index(pattern) + 1, "text": line}
               for name, lines in originals.items() for row, line in enumerate(lines, 1) if pattern in line]
    if len(targets) != 4:
        raise ValueError("L4 fixture must contain four native Quickfix matches")
    changed = {name: lines.copy() for name, lines in originals.items()}
    for item in (targets[0], *targets[2:]):
        changed[item["filename"]][item["row"] - 1] = item["text"].replace(pattern, "calculate_tip_checked")

    summary = "text replaced; 2 buffers changed; 2 changed buffers remain unsaved"
    for report, expected_lines, answers, summary_messages in (
        (positive, changed, ((0, "y"), (1, "n"), (2, "a")), [summary]),
        (control, originals, ((0, "q"), (2, "q")), []),
    ):
        spoken_prompts = []
        for offset, answer in answers:
            item = targets[offset]
            location = f"{item['text'].strip()}, line {item['row']}, column {item['column']}"
            spoken_prompts.append({"answer": answer, "speech": f"{location}, Replace this match? Y yes, N no, "
                                   "A all, Q quit, L last"})
        if (report["quickfix"]["items"] != targets or report["prompts"] != spoken_prompts
                or [item["index"] for item in report["quickfixSelections"]] != [1, 2, 3, 4, 4, 3, 2, 1, 1]
                or report["summary"] != summary_messages or set(report["buffers"]) != set(names)
                or any(report["buffers"][name]["lines"] != expected_lines[name]
                       or report["buffers"][name]["modified"] is not bool(summary_messages) for name in names)):
            raise ValueError("L4 Quickfix navigation, spoken prompts, or resulting buffers disagree with the fixture")


def verify_buffer_operation(fixtures, case, observed, *, incomplete=False):
    primary, secondary = names = ("lsp_features.py", "lsp_rename_consumer.py")
    renamed = case == "L5"
    replacement = "calculate_gratuity" if renamed else "calculate_tip_buffered"
    changed_names = (primary,) if incomplete else names
    original = {name: (fixtures / name).read_text(encoding="utf-8").splitlines() for name in names}
    expected = {name: [line.replace("calculate_tip", replacement if name in changed_names else "unrelated_tip")
                       for line in lines] for name, lines in original.items()}
    buffers = observed["buffers"]

    if renamed:
        references = [(row, line) for row, line in enumerate(expected[secondary], 1) if replacement in line]
        if len(references) != 2:
            raise ValueError("L5 fixture must contain two secondary references")
        expected_reports = [f"Renamed reference {i} of 2, line {row}: {line}"
                            for i, (row, line) in enumerate(references, 1)]
        prompts = observed["prompts"]
        if ([(prompt["phase"], prompt["commandText"]) for prompt in prompts] != [("cancel", ""), ("accept", "")]
                or any(not any("New Name:" in sound for sound in prompt["speech"]) for prompt in prompts)
                or observed["cancelPreservedBuffers"] is not True):
            raise ValueError("L5 did not open both empty native rename prompts and preserve the canceled buffers")
    elif incomplete:
        expected_reports = ["The prepared buffer replacement is not fully visible."]
    else:
        expected_reports = [f"Changed buffer {i} of 2, {name}: 2 occurrences of {replacement}"
                            for i, name in enumerate(names, 1)]

    reports = observed["reports"]
    if (observed["operation"] != ("rename" if renamed else "bufdo")
            or observed["incomplete"] is not incomplete or observed["changedBuffers"] != list(changed_names)
            or set(buffers) != set(names)
            or any(buffers[name]["lines"] != expected[name]
                   or buffers[name]["modified"] is not (name in changed_names) for name in names)
            or [entry["speech"] for entry in reports] != expected_reports
            or any(entry["position"] != reports[0]["position"] for entry in reports[1:])
            or (renamed and reports[0]["position"]["activeBuffer"] != buffers[primary]["id"])):
        raise ValueError(f"{case} did not verify the expected native buffer changes and stationary reports")


def verify_d2_frames(observed):
    initial = observed["initial"]
    restored = observed["restored"]
    held = observed["held"]
    native_move = observed["nativeMove"]
    frames = [initial, *held, restored, native_move]
    if (len(held) != 3 or any(len(frame["cells"]) != 80 for frame in frames)
            or [frame["key"] for frame in held] != ["d2-begin", "d2-next", "d2-previous"]
            or ["os.path" in frame["text"] for frame in held] != [True, False, True]
            or "os.sep" not in held[1]["text"] or held[0]["cells"] != held[2]["cells"]
            or held[0]["cells"] == held[1]["cells"] or initial != restored
            or any(frame["cursor"] != initial["cursor"] for frame in held)
            or native_move["text"].strip() or native_move["cursor"]["row"] != initial["cursor"]["row"] + 1
            or native_move["cursor"]["cursorMoves"] <= initial["cursor"]["cursorMoves"]):
        raise ValueError("D2 did not preserve and restore the observed Braille and cursor state")


def verify_d2_keys(lines):
    keys_and_passes = [line for line in lines if line.startswith(("NAL_KEY d2-", "NAL_PASS d2_"))]
    if keys_and_passes[-11:] != [
        "NAL_KEY d2-begin", "NAL_PASS d2_held_path_renders_complete_dot_pattern",
        "NAL_KEY d2-next", "NAL_PASS d2_next_sep_renders_complete_dot_pattern",
        "NAL_KEY d2-previous", "NAL_PASS d2_previous_path_renders_complete_dot_pattern",
        "NAL_KEY d2-release", "NAL_PASS d2_key_up_restores_identical_braille_cells",
        "NAL_KEY d2-next", "NAL_PASS d2_same_key_without_modifier_moves_editor",
        "NAL_PASS d2_editor_exited_cleanly",
    ]:
        raise ValueError("D2 did not observe the held keys, modifier release, and native key in order")


def verify_l3_pages(positive, control):
    native = positive["signatureEvidence"]
    omitted = control["signatureEvidence"]
    actions = native["observed"]
    names = ["name", "first_price", "first_quantity", "first_discount", "second_signature",
             "second_price", "second_quantity", "back_to_first", "first_price_reset", "back_to_second",
             "second_price_via_previous", "repeat", "open", "close"]
    if [item["action"] for item in actions] != names or native["nativePyright"] != omitted["nativePyright"]:
        raise ValueError("L3 does not contain the same Pyright reference and the full exploration sequence")
    first_cursor = actions[0]["cursor"]
    if (any(item["cursor"] != first_cursor for item in actions[:-2])
            or [item["cursor"][1] for item in actions[-2:]] != [23, 35]
            or any(len(frame) != 40 for item in actions for frame in item["cells"])):
        raise ValueError("L3 did not preserve the editor cursor or use the expected digital Braille width")
    for item in (actions[0], actions[4]):
        frames = item["cells"]
        forward = frames[: (len(frames) + 1) // 2]
        if (len(forward) < 3 or len({tuple(frame) for frame in forward}) != len(forward)
                or frames != forward + forward[-2::-1]):
            raise ValueError(f"L3 did not record distinct Braille pages and their return order for {item['action']}")
    initial, = omitted["observed"]
    editor = control["editorState"]
    if (control["pending"] != "l3_name_pan_right_2" or initial["action"] != "name"
            or initial["cells"] != actions[0]["cells"][:1] or initial["cursor"][:2] != first_cursor[:2]
            or control["recentBrailleCells"][-1:] != initial["cells"]
            or [editor[key] for key in ("row", "byteColumn", "cursorMoves")] != initial["cursor"]):
        raise ValueError("The L3 control did not stay on the original Braille page without moving the cursor")


def verify_s1_focus(positive, control, positive_log, control_log):
    restore = "s1_guided_f10_restores_original_powershell"
    passed = positive["steps"]
    if (passed[-3:] != [restore, "s1_restored_tab_edits_native_input_at_caret",
                        "s1_restored_tab_updates_native_digital_braille"]
            or control["steps"] != [*passed[:-3], "s1_control_keeps_bound_editor"]
            or control["pending"] != restore
            or positive["focusEvidence"]["omittedF10"] is not False
            or control["focusEvidence"]["omittedF10"] is not True
            or control["focusEvidence"]["editorStillBound"] is not True
            or positive_log.count("NAL_KEY guided-exit") != 1
            or positive_log.index("NAL_KEY guided-exit") >= positive_log.index(f"NAL_PASS {restore}")
            or "NAL_KEY guided-exit" in control_log or f"NAL_WAIT {restore}" not in control_log):
        raise ValueError("S1 did not distinguish real F10 restoration from the editor remaining bound")


def verify_d1_actions(actions, log):
    expected = [
        ("F401", 1, 15, "warning"), ("F401", 1, 21, "warning"),
        ("reportAssignmentType", 3, 14, "error"), ("reportOperatorIssue", 4, 14, "error"),
        ("reportUnknownArgumentType", 4, 14, "error"), ("reportUndefinedVariable", 5, 6, "error"),
        ("reportUnknownArgumentType", 5, 6, "error"), ("F821", 5, 6, "error"),
        ("F401", 1, 15, "warning"), ("F821", 5, 6, "error"), (None, 2, 0, "none"),
    ]
    keys = ["d1-current", *(["d1-next"] * 8), "d1-previous", "d1-clean"]
    markers = ["NAL_AUDIO marker begin"]
    for number, key in enumerate(keys, 1):
        markers.extend(("NAL_AUDIO marker action", f"NAL_KEY {key}",
                        f"NAL_PASS d1_action_{number}_cursor_and_complete_speech"))
    markers.append("NAL_AUDIO marker end")
    relevant = set(markers)
    actual = [(item["code"], item["row"], item["byteColumn"], item["cue"]) for item in actions]
    if (actual != expected or [item["key"] for item in actions] != keys
            or [line for line in log if line in relevant] != markers):
        raise ValueError("D1 did not demonstrate the full diagnostic traversal and one marked recording per action")


def verify_capture_result(recording, original, recomputed):
    if not recomputed or not recomputed.items() <= original.items():
        raise ValueError(f"Reprocessed PCM differs from the original verification for {recording.name}")
    with recording.open("rb") as stream:
        return {"file": recording.name, "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def verify_wasapi_transfer(workspace, run_id, capture, log):
    filename = f"wasapi-{run_id}.wav"
    if capture["file"] != filename:
        raise ValueError(f"WASAPI filename does not identify {run_id}")
    endpoint = workspace / filename
    header = f"NAL_WASAPI {endpoint.stat().st_size} {capture['sha256']}"
    if (log.count(header) != 1 or log.count("NAL_WASAPI_END") != 1
            or log.index(header) >= log.index("NAL_WASAPI_END")):
        raise ValueError(f"WASAPI artifact does not match the capture transferred by {run_id}")
    return endpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("addon", type=Path)
    parser.add_argument("references", type=Path)
    parser.add_argument("--additional-summary", action="append", type=Path, default=[],
                        help="Include a separate case selection from the same workspace and candidate")
    parser.add_argument("--complete", action="store_true", help="Require every guided case to have passed")
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    summary = args.summary.resolve(strict=True)
    workspace = summary.parent.parent
    os.environ["NAL_TEST_WORK_DIR"] = str(workspace)

    from guided_jobs import AUDIO, cards
    from run_c1_audio import verify_recording as verify_completion_pcm
    from run_external_diagnostic_audio import verify_recording as verify_diagnostic_pcm
    from run_guided_suite import read_json, require, verify_case

    with args.addon.open("rb") as package:
        actual = hashlib.file_digest(package, "sha256").hexdigest()
    candidate = {"name": args.addon.name, "sha256": actual}
    expected = cards(checkout)
    states = {}
    for source in (summary, *args.additional_summary):
        source = source.resolve(strict=True)
        require(source.parent.parent == workspace, "The suite summaries must use the same VM workspace")
        recorded = read_json(source)
        require(recorded["candidate"] == candidate, "The suite summary does not match the supplied package")
        require(set(recorded["cases"]) <= set(expected), "The suite summary contains an unknown guided case")
        for case, observation in recorded["cases"].items():
            previous = states.get(case, ({"status": "missing"}, None))[0]["status"]
            current = observation["status"]
            require(previous != "passed" or current != "passed", f"More than one passing summary for {case}")
            if current == "passed" or previous in {"missing", "pending"}:
                states[case] = observation, source.parent

    def audit(case):
        observed, output = states.get(case, ({}, None))
        if observed.get("status") != "passed":
            return {"status": observed.get("status", "missing")}
        ids = observed["runs"]
        verify_case(case, ids, workspace, output, actual)
        logs = [verify_serial_log(workspace, run_id, candidate) for run_id in ids]
        if case in {"L1", "L2", "L4", "L5", "L6"}:
            fixtures = checkout / "tests/human/fixtures"
            reports = [read_json(workspace / f"run-{run_id}.json")["lspEvidence"] for run_id in ids]
            if case == "L1":
                verify_l1_status(reports[0], logs[0])
            elif case == "L2":
                verify_l2_hints(*reports)
            elif case == "L4":
                verify_l4_edits(fixtures, *reports)
            else:
                verify_buffer_operation(fixtures, case, reports[0])
                if case == "L6":
                    verify_buffer_operation(fixtures, case, reports[1], incomplete=True)
        elif case == "L3":
            reports = [read_json(workspace / f"run-{run_id}.json") for run_id in ids]
            verify_l3_pages(*reports)
        elif case == "S1":
            reports = [read_json(workspace / f"run-{run_id}.json") for run_id in ids]
            verify_s1_focus(*reports, *logs)
        elif case == "D2":
            guest = read_json(workspace / f"run-{ids[0]}.json")
            verify_d2_keys(logs[0])
            verify_d2_frames(guest["heldDiagnosticEvidence"])
        captures = []
        rejected_qemu = []
        if case in AUDIO:
            for run_id, mode, log in zip(ids, ("positive", "muted"), logs, strict=True):
                recording = output / f"{case}-{mode}.wav"
                proof = read_json(recording.with_suffix(".verification.json"))
                muted = mode == "muted"
                if case == "D1":
                    guest = read_json(workspace / f"run-{run_id}.json")
                    verify_d1_actions(guest["diagnosticAudio"], log)
                    measured = verify_diagnostic_pcm(recording, args.references, run_id, case, muted=muted)
                    captures.append(verify_capture_result(recording, proof, measured))
                else:
                    def assess(path):
                        if case.startswith("C"):
                            return verify_completion_pcm(path, args.references, muted=muted)
                        return verify_diagnostic_pcm(path, args.references, run_id, case, muted=muted)

                    qemu = proof["qemuCapture"]
                    try:
                        measured = assess(recording)
                    except RuntimeError as error:
                        require(case != "C1" and qemu["ok"] is False and qemu["error"] == str(error),
                                f"QEMU capture outcome changed for {recording.name}: {error}")
                        rejected_qemu.append({"file": recording.name, "error": str(error)})
                    else:
                        require(qemu["ok"] is True, f"QEMU capture outcome changed for {recording.name}")
                        captures.append(verify_capture_result(recording, qemu, measured))

                    guest = read_json(workspace / f"run-{run_id}.json")
                    transfer = guest["wasapiCapture"]
                    endpoint = verify_wasapi_transfer(workspace, run_id, transfer, log)
                    assessed = assess(endpoint)
                    captures.append(verify_capture_result(endpoint, proof, assessed))
                    require(captures[-1]["sha256"] == transfer["sha256"], "The WASAPI PCM changed after transfer")
        result = {"status": "verified", "runs": ids, "pcmRechecked": captures}
        if rejected_qemu:
            result["rejectedQemu"] = rejected_qemu
        return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = dict(zip(expected, pool.map(audit, expected), strict=True))
    executed = [run for outcome in outcomes.values() for run in outcome.get("runs", ())]
    require(len(executed) == len(set(executed)), "The same guest run was credited more than once")
    complete = all(outcome["status"] == "verified" for outcome in outcomes.values())
    print(json.dumps({"complete": complete, "candidate": candidate, "cases": outcomes}, indent=2))
    return 1 if args.complete and not complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
