"""Run a guided completion case in an audio-enabled Windows guest."""

import argparse
from contextlib import contextmanager, suppress
import json
from pathlib import Path
import subprocess
import sys

from qmp import Qmp
from lab_paths import SOURCES
from run_focus_test import ROOT, image, run_media, wait_for_desktop
from verify_c1_pair import QEMU_C1_MARKER_METHOD


def monitor(qmp: Qmp, command: str) -> str:
    return qmp.execute("human-monitor-command", **{"command-line": command})


def stop_capture():
    with Qmp() as qmp:
        monitor(qmp, "stopcapture 0")


@contextmanager
def capture(path: Path):
    if path.exists() or not path.parent.is_dir() or any(char.isspace() for char in path.as_posix()):
        raise ValueError("Use a new capture filename and an existing directory without whitespace")
    with Qmp() as qmp:
        if not any(device["id"] == "capture" for device in qmp.execute("query-audiodevs")):
            raise RuntimeError("The selected guest has no dedicated audio capture device")
        if "Capturing audio" in monitor(qmp, "info capture"):
            raise RuntimeError("The selected guest already has a running audio capture")
        monitor(qmp, f"wavcapture {path.as_posix()} capture 48000 16 2")
        if path.as_posix() not in monitor(qmp, "info capture"):
            raise RuntimeError("QEMU did not start the requested capture")
    try:
        yield
    except BaseException:
        with suppress(OSError, EOFError):
            stop_capture()
        raise
    else:
        stop_capture()


def verify_recording(recording, references, *, muted, qemu_c1=False):
    verifier = (
        sys.executable, str(SOURCES / "verify_audio_capture.py"), str(recording),
        str(references), "--c1-timeline",
    )
    if qemu_c1:
        verifier += ("--qemu-c1-markers",)
    checked = subprocess.run(
        (*verifier, "--c1-muted" if muted else "--negative-controls"),
        capture_output=True, encoding="utf-8",
    )
    if checked.returncode:
        raise RuntimeError(checked.stderr.strip())
    report = json.loads(checked.stdout)
    if muted:
        rejected = subprocess.run(verifier, capture_output=True, encoding="utf-8")
        if rejected.returncode != 1 or not rejected.stderr.startswith("Expected ('before-open', 'open',"):
            raise RuntimeError(f"The normal cue oracle did not reject the muted capture: {rejected.stderr}")
        report["normalOracleRejection"] = rejected.stderr.strip()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addon", type=Path)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("node", type=Path)
    parser.add_argument("pyright", type=Path)
    parser.add_argument("references", type=Path)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--reuse-run")
    parser.add_argument("--completion-profile", choices=("cmp", "blink"))
    parser.add_argument("--completion-plugins", type=Path)
    parser.add_argument("--completion-git-bin", type=Path)
    parser.add_argument("--muted", action="store_true")
    parser.add_argument("--wasapi-tools", type=Path, help="Require PCM recorded at the Windows render endpoint.")
    arguments = parser.parse_args()
    completion = (arguments.completion_profile, arguments.completion_plugins, arguments.completion_git_bin)
    if any(completion) and not all(completion):
        parser.error("Plugin completion requires the profile, pinned plugin checkouts and Git")

    staged_completion = None
    if all(completion):
        profile, plugins, git_bin = completion
        staged_completion = profile, plugins.resolve(strict=True), git_bin.resolve(strict=True)
    references = arguments.references.resolve(strict=True)
    wasapi = arguments.wasapi_tools is not None
    wait_for_desktop(0)
    run_id, media = image(
        arguments.addon.resolve(strict=True), ROOT / "nvda-2026.3.1.zip",
        ROOT.parent / "neovim" / "0.12.6" / "nvim-win64.zip",
        arguments.reuse_run, None, False, arguments.checkout.resolve(strict=True),
        c1_tools=(arguments.node.resolve(strict=True), arguments.pyright.resolve(strict=True), references),
        c1_muted=arguments.muted, completion_tools=staged_completion,
        wasapi_tools=arguments.wasapi_tools.resolve(strict=True) if wasapi else None,
    )
    recording = arguments.recording.resolve()
    with capture(recording):
        passed = run_media(run_id, media, wasapi=wasapi)
    if not passed:
        return 1

    def check(path, *, qemu_c1=False):
        try:
            result = {"ok": True, **verify_recording(path, references, muted=arguments.muted, qemu_c1=qemu_c1)}
        except RuntimeError as error:
            result = {"ok": False, "error": str(error)}
        if qemu_c1:
            result["markerMethod"] = QEMU_C1_MARKER_METHOD
        return result

    if wasapi:
        endpoint = ROOT / f"wasapi-{run_id}.wav"
        report = {
            **check(endpoint), "captureEndpoint": "Windows WASAPI loopback",
            "captureFile": endpoint.name, "qemuCapture": check(recording, qemu_c1=arguments.completion_profile is None),
        }
    else:
        report = {**check(recording), "captureEndpoint": "QEMU audio output", "captureFile": recording.name}
    report["guestRun"] = run_id
    report["profile"] = arguments.completion_profile or "native"
    report["muted"] = arguments.muted
    result = json.dumps(report, indent=2)
    recording.with_suffix(".verification.json").write_text(result + "\n", encoding="utf-8")
    print(result)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
