"""Capture D3 Clang-Tidy or D4 markdownlint in a real NVDA Windows session."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from lab_paths import SOURCES
from run_c1_audio import capture
from run_focus_test import ROOT, image, run_media, wait_for_desktop


D1_QEMU_MARKER_METHOD = "d1-calibration-segments-v1"


def verify_recording(recording, references, run_id, case, *, muted, qemu_markers=False):
    command = (
        sys.executable, str(SOURCES / "verify_audio_capture.py"), str(recording), str(references),
        "--diagnostic-trace", str(ROOT / f"run-{run_id}.json"),
    )
    if qemu_markers:
        command += ("--qemu-calibration-markers",)
    checked = subprocess.run(
        (*command, "--diagnostics-muted" if muted else "--negative-controls"),
        capture_output=True, encoding="utf-8",
    )
    if checked.returncode:
        raise RuntimeError(checked.stderr.strip())
    report = json.loads(checked.stdout)
    if muted:
        rejected = subprocess.run(command, capture_output=True, encoding="utf-8")
        cue = "error" if case == "D3" else "warning"
        if rejected.returncode != 1 or not rejected.stderr.startswith(f"Expected ('action', '{cue}',"):
            raise RuntimeError(f"The normal oracle did not reject the muted {case} capture: {rejected.stderr}")
        report["normalOracleRejection"] = rejected.stderr.strip()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("D3", "D4"))
    for name in ("addon", "checkout", "linter", "lint", "git_bin", "references", "recording"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--node", type=Path, help="Node runtime for D4. Pass node_modules as the linter path.")
    parser.add_argument("--wasapi-tools", type=Path, help="Also record at the Windows render endpoint and require its PCM check.")
    parser.add_argument("--reuse-run", required=True)
    parser.add_argument("--muted", action="store_true")
    args = parser.parse_args()
    if (args.node is not None) != (args.case == "D4"):
        parser.error("--node is required for D4")
    wait_for_desktop(0)
    references = args.references.resolve(strict=True)
    tools = tuple(path.resolve(strict=True) for path in (args.linter, args.lint, args.git_bin, references))
    staged = ({"clang_tools": tools} if args.case == "D3"
              else {"markdown_tools": (args.node.resolve(strict=True), *tools)})
    run_id, media = image(
        args.addon.resolve(strict=True), None, None, args.reuse_run, None, False,
        args.checkout.resolve(strict=True), external_diagnostics_muted=args.muted,
        wasapi_tools=args.wasapi_tools.resolve(strict=True) if args.wasapi_tools else None, **staged,
    )
    recording = args.recording.resolve()
    with capture(recording):
        passed = run_media(run_id, media, wasapi=args.wasapi_tools is not None)
    if not passed:
        return 1

    def check(path):
        try:
            return {"ok": True, **verify_recording(path, references, run_id, args.case, muted=args.muted)}
        except RuntimeError as error:
            return {"ok": False, "error": str(error)}

    if args.wasapi_tools:
        endpoint = ROOT / f"wasapi-{run_id}.wav"
        report = {
            **check(endpoint), "captureEndpoint": "Windows WASAPI loopback",
            "captureFile": endpoint.name, "qemuCapture": check(recording),
        }
    else:
        report = {**check(recording), "captureEndpoint": "QEMU audio output", "captureFile": recording.name}
    report["guestRun"] = run_id
    report["case"] = args.case
    report["muted"] = args.muted
    content = json.dumps(report, indent=2)
    recording.with_suffix(".verification.json").write_text(content + "\n", encoding="utf-8")
    print(content)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
