"""Match the native completion guest and PCM evidence across the two audio settings."""

import argparse
import hashlib
import json
from pathlib import Path


MARKERS = ("begin", "before-open", "before-selection", "before-accept", "end")
WITH_CUES = ("begin", "before-open", "open", "before-selection", "before-accept", "close", "end")
MUTATIONS = {"muted cue", "duplicated cue", "reordered cues", "missing render marker"}
SELECTION = [0, 1, 2, -1, 0, -1, 2]
QEMU_START_MARKER_LOSS = "Expected one render marker at each end, found [0, 1]"
QEMU_C1_MARKER_METHOD = "c1-calibration-segments-v1"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def lost_qemu_start_marker(proof, run_id, *, muted):
    qemu = proof["qemuCapture"]
    return (proof["ok"] is True and proof["captureEndpoint"] == "Windows WASAPI loopback"
            and proof["guestRun"] == run_id and proof["muted"] is muted and proof["profile"] == "native"
            and qemu["ok"] is False and qemu["error"] == QEMU_START_MARKER_LOSS
            and qemu.get("markerMethod") in (None, QEMU_C1_MARKER_METHOD))


def check_run(proof_path, *, muted, workspace=None):
    proof = read_json(proof_path)
    workspace = workspace or proof_path.parent
    require(proof["profile"] == "native" and proof["muted"] is muted, "Wrong completion case or audio setting")
    run_id = proof["guestRun"]
    guest = read_json(workspace / f"run-{run_id}.json")
    require(guest["run"] == run_id and guest["ok"] is True and guest["guestCleanupCompleted"] is True,
            f"Guest did not finish the verified run {run_id}")
    evidence = guest["completionEvidence"]
    require(evidence["case"] == "c1" and evidence["provider"] == "native"
            and [change["index"] for change in evidence["selection"]] == SELECTION
            and len(evidence["accepted"]["cells"]) == 80, "The guest completion trace is incomplete")
    require(proof["captureEndpoint"] == "Windows WASAPI loopback", "Missing Windows render endpoint capture")
    endpoint = guest["wasapiCapture"]
    require(proof["captureFile"] == endpoint["file"], "Wrong WASAPI artifact for this guest run")
    with (workspace / endpoint["file"]).open("rb") as stream:
        require(hashlib.file_digest(stream, "sha256").hexdigest() == endpoint["sha256"],
                "WASAPI artifact no longer matches the verified serial transfer")

    for name, capture in (("WASAPI", proof), ("QEMU", proof["qemuCapture"])):
        require(capture["ok"] is True
                and tuple(item["cue"] for item in capture["matches"]) == (MARKERS if muted else WITH_CUES),
                f"{name} did not record the required timeline")
        if muted:
            require(capture["normalOracleRejection"].startswith("Expected ('before-open', 'open',"),
                    f"{name} mute control did not fail normal playback verification")
        else:
            require(set(capture["rejectedControls"]) == MUTATIONS, f"{name} did not reject all waveform mutations")
    return guest


def compare(positive_path, muted_path, *, workspace=None):
    positive = check_run(positive_path, muted=False, workspace=workspace)
    muted = check_run(muted_path, muted=True, workspace=workspace)
    require(positive["run"] != muted["run"]
            and positive["wasapiCapture"]["sha256"] != muted["wasapiCapture"]["sha256"],
            "The mute control needs a separate guest run and recording")
    require(all(positive[key] == muted[key] for key in ("candidate", "terminal", "nvda", "steps", "completionEvidence")),
            "The mute control changed the candidate or the observable editor, speech or Braille result")
    return {"ok": True, "positive": positive["run"], "muted": muted["run"],
            "candidate": positive["candidate"], "steps": positive["steps"],
            "positiveAudio": positive_path.name, "mutedAudio": muted_path.name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("positive", type=Path)
    parser.add_argument("muted", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.positive, args.muted)
    except (KeyError, OSError, ValueError) as error:
        parser.exit(1, f"C1 evidence pair rejected: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
