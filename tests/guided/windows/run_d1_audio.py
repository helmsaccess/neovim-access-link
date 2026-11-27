"""Run D1 in the audio guest and pair its native trace with captured PCM."""

import argparse
import json
from pathlib import Path

from run_c1_audio import capture
from run_external_diagnostic_audio import D1_QEMU_MARKER_METHOD, verify_recording
from run_focus_test import image, run_media, wait_for_desktop


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("addon", "checkout", "node", "pyright", "ruff",
                 "lint", "git_bin", "references", "recording"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--reuse-run", required=True)
    parser.add_argument("--muted", action="store_true")
    args = parser.parse_args()
    wait_for_desktop(0)
    checkout = args.checkout.resolve(strict=True)
    references = args.references.resolve(strict=True)
    run_id, media = image(
        args.addon.resolve(strict=True), None, None, args.reuse_run, None, False,
        checkout, (args.node.resolve(strict=True), args.pyright.resolve(strict=True), references),
        d1_tools=tuple(path.resolve(strict=True) for path in (args.ruff, args.lint, args.git_bin)),
        d1_muted=args.muted,
    )
    recording = args.recording.resolve()
    with capture(recording):
        ok = run_media(run_id, media)
    if not ok:
        return 1
    try:
        report = {"ok": True, **verify_recording(recording, references, run_id, "D1", muted=args.muted, qemu_markers=True)}
    except RuntimeError as error:
        report = {"ok": False, "error": str(error)}
    report.update(guestRun=run_id, case="D1", muted=args.muted, captureEndpoint="QEMU audio output",
                  captureFile=recording.name, markerMethod=D1_QEMU_MARKER_METHOD)
    content = json.dumps(report, indent=2)
    recording.with_suffix(".verification.json").write_text(content + "\n", encoding="utf-8")
    print(content)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
