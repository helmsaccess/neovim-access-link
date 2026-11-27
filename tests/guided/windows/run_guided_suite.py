"""Run selected guided cases on one isolated Windows desktop and verify the evidence."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from guided_jobs import AUDIO, DESKTOP, NATIVE_CONTROLS, Job, cards, jobs
from verify_c1_pair import compare as compare_c1
from verify_lazy_pair import compare as compare_lazy


SOURCES = Path(__file__).resolve().parent
MOUNT = re.compile(r"Mounted test ([a-f0-9]{12}) in the isolated guest\.")
NATIVE_CONTROL_FLAGS = {"L2": "hintsDisabled", "L4": "aborted", "L6": "incomplete"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


@contextmanager
def exclusive_guest(workspace, port):
    import msvcrt

    with (workspace / f"guided-suite-{port}.lock").open("a+b") as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError(f"A suite already owns the Windows guest on port {port}") from error
        yield


def run_job(job: Job, env, observed):
    start = len(observed)
    command = (sys.executable, SOURCES / job.script, *job.arguments)
    with subprocess.Popen(command, env=env, cwd=SOURCES, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, encoding="utf-8", errors="replace") as process:
        for line in process.stdout:
            print(line, end="", flush=True)
            if match := MOUNT.fullmatch(line.rstrip()):
                observed.append(match[1])
        returncode = process.wait()
    if returncode:
        raise RuntimeError(f"{job.script} failed with exit status {returncode}. Guest runs: {observed[start:]}")
    require(len(observed) > start and len(observed) == len(set(observed)),
            f"{job.script} produced no distinct guest runs")


def guest_run(workspace, run_id, candidate_hash):
    report = read_json(workspace / f"run-{run_id}.json")
    require(report["run"] == run_id and report["guestCleanupCompleted"] is True
            and report["candidate"]["sha256"] == candidate_hash and report["steps"],
            f"Guest evidence {run_id} lacks cleanup, candidate provenance, or executed steps")
    return report


def observed_failure(workspace, run_ids):
    for run_id in run_ids:
        path = workspace / f"run-{run_id}.json"
        if path.is_file():
            report = read_json(path)
            observed = report.get("observedGuestResult", report)
            if observed.get("ok") is False and "steps" in observed:
                return True
    return False


def verify_case(case, run_ids, workspace, output, candidate_hash):
    paired = case in AUDIO or case in NATIVE_CONTROLS or case in {"L3", "S1"} or case.startswith("P")
    expected_runs = 2 if paired else 1
    require(len(run_ids) == len(set(run_ids)) == expected_runs, f"{case} did not produce {expected_runs} distinct runs")
    if case in {"L3", "S1"}:
        positive, control = run_ids
        prefix = case.lower()
        pair = read_json(workspace / f"{prefix}-pair-{positive}.json")
        require(pair["ok"] is True and pair["positive"] == positive and pair["control"] == control,
                f"{case} did not observe the expected controlled failure")
        require(guest_run(workspace, positive, candidate_hash)["ok"] is True
                and guest_run(workspace, control, candidate_hash)["ok"] is False,
                f"{case} did not prove both outcomes")
        return

    observed = [guest_run(workspace, run_id, candidate_hash) for run_id in run_ids]
    require(all(run["ok"] is True and run["steps"][0].startswith(case.lower() + "_") for run in observed),
            f"A guest did not pass the expected {case} scenario")
    if case.startswith("P"):
        positive, control = (workspace / f"run-{run_id}.json" for run_id in run_ids)
        compare_lazy(case, positive, control)
    elif case in NATIVE_CONTROL_FLAGS:
        flag = NATIVE_CONTROL_FLAGS[case]
        require(observed[0]["lspEvidence"][flag] is False and observed[1]["lspEvidence"][flag] is True,
                f"{case} did not observe its separate control condition")
    elif case in AUDIO:
        positive_path = output / f"{case}-positive.verification.json"
        muted_path = output / f"{case}-muted.verification.json"
        positive = read_json(positive_path)
        muted = read_json(muted_path)
        positive_id, muted_id = run_ids
        require(positive["ok"] is True and muted["ok"] is True and positive["guestRun"] == positive_id
                and muted["guestRun"] == muted_id and positive["muted"] is False and muted["muted"] is True
                and positive["rejectedControls"] and muted["normalOracleRejection"],
                f"{case} did not record and verify both the real output and its mute control")
        field = "completionEvidence" if case.startswith("C") else "diagnosticAudio"
        require(all(observed[0][key] == observed[1][key] for key in (field, "steps", "nvda", "terminal")),
                f"{case} changed its observable guest behavior with the sound setting")
        if case == "C1":
            compare_c1(positive_path, muted_path, workspace=workspace)
        elif case.startswith("C"):
            require(all(proof["captureEndpoint"] == "Windows WASAPI loopback"
                        and proof["captureFile"] == run["wasapiCapture"]["file"]
                        for proof, run in zip((positive, muted), observed, strict=True)),
                    f"{case} lacks matching Windows render endpoint evidence")


def run_suite(args, selected):
    if os.name != "nt":
        raise ValueError("The desktop and audio test groups need a Windows host")
    config = read_json(args.config)
    config_dir = args.config.resolve().parent
    workspace = (config_dir / config["workspace"]).resolve(strict=True)
    tools = {key: (config_dir / value).resolve() for key, value in config["tools"].items()}
    port = config["qmpPort"]
    reuse = config["reuseRun"]
    require(type(port) is int and 1 <= port <= 65535, "Invalid port for the isolated QEMU guest")
    require(isinstance(reuse, str) and re.fullmatch(r"[a-f0-9]{12}", reuse), "Invalid guest tool seed run ID")
    addon = args.addon.resolve(strict=True)
    with addon.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    options = {"NAL_TEST_WORK_DIR": str(workspace), "NAL_TEST_QMP_PORT": str(port), "PYTHONIOENCODING": "utf-8",
               "NAL_TEST_DISCARD_RUN_COPIES": "1"}
    env = {**os.environ, **options}
    guest = None
    if restart := config.get("restart"):
        from suite_guest import RestartableGuest

        guest = RestartableGuest(workspace, port, config_dir, restart, env, audio=bool(set(selected) & AUDIO))
    output = workspace / ("guided-suite-" + uuid.uuid4().hex[:12])
    planned = {case: jobs(case, addon=addon, checkout=args.checkout, tools=tools, output=output, reuse=reuse)
               for case in selected}
    started = datetime.now(timezone.utc).isoformat()
    summary = {"started": started, "candidate": {"name": addon.name, "sha256": digest},
               "cases": {case: {"status": "pending"} for case in selected}}
    with exclusive_guest(workspace, port):
        output.mkdir()
        report_path = output / "summary.json"
        print(f"Evidence directory: {output}", flush=True)
        for case, steps in planned.items():
            ids = []
            interruptions = []
            partial_audio = []
            try:
                for job in steps:
                    if guest is not None:
                        guest.ready(SOURCES)
                    start = len(ids)
                    try:
                        run_job(job, env, ids)
                    except RuntimeError:
                        if guest is None or not guest.stopped() or observed_failure(workspace, ids[start:]):
                            raise
                        interruptions.extend(ids[start:])
                        del ids[start:]
                        if case in AUDIO:
                            setting = "muted" if job.muted else "positive"
                            recording = output / f"{case}-{setting}.wav"
                            if recording.is_file():
                                partial = recording.with_stem(f"{recording.stem}-interrupted")
                                recording.rename(partial)
                                partial_audio.append(partial.name)
                        guest.ready(SOURCES)
                        run_job(job, env, ids)
                verify_case(case, ids, workspace, output, digest)
            except (KeyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                summary["cases"][case] = {"status": "failed", "runs": ids, "interruptedRuns": interruptions,
                                          "partialAudio": partial_audio, "error": str(error)}
                report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
                raise
            summary["cases"][case] = {"status": "passed", "runs": ids, "interruptedRuns": interruptions,
                                      "partialAudio": partial_audio}
            report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, help="Local JSON with workspace, qmpPort, reuseRun and tool paths")
    parser.add_argument("--addon", type=Path, help="Built .nvda-addon candidate")
    parser.add_argument("--group", choices=("desktop", "audio"))
    parser.add_argument("--case", action="append", dest="cases", help="Guided case ID, repeatable")
    parser.add_argument("--list", action="store_true", help="List the selected cards without running them")
    args = parser.parse_args()
    try:
        args.checkout = args.checkout.resolve(strict=True)
        eligible = {"desktop": DESKTOP, "audio": AUDIO}.get(args.group, DESKTOP | AUDIO)
        requested = set(args.cases or eligible)
        require(requested <= eligible, f"Case selection outside the group: {sorted(requested - eligible)}")
        selected = [case for case in cards(args.checkout) if case in requested]
        if args.list:
            for case in selected:
                print(case, "audio" if case in AUDIO else "desktop")
            return
        if args.config is None or args.addon is None:
            parser.error("--config and --addon are required for an actual suite run")
        print(f"Passed: {run_suite(args, selected)}")
    except (KeyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Guided suite failed: {error}\n")


if __name__ == "__main__":
    main()
