"""Prepare read-only guest media and drive the test using its serial output."""
import argparse
from contextlib import suppress
import hashlib
import json
import os
from pathlib import Path
import re
from shutil import copyfile
import subprocess
import time
import uuid
from zipfile import ZIP_DEFLATED, ZipFile

from lab_paths import SOURCES, WORKSPACE as ROOT
from qmp import PORT, Qmp
from receive_wasapi import LoopbackRecording


SERIAL = ROOT / ("guest-serial.log" if PORT == 31946 else f"guest-serial-{PORT}.log")
KEYS = {
    "dismiss-shell-overlay": [("esc",)],
    "toggle": [("insert", "alt", "n")],
    "claim-a": [("f12",)],
    "claim-b": [("f12",)],
    "edit-a": [("shift", "4"), ("a",), ("z",), ("esc",)],
    "return": [("alt", "tab")],
    "focus-switch": [("alt", "tab")],
    "close-editor": [("shift", "semicolon"), ("q",), ("a",), ("shift", "1"), ("ret",)],
    "guided-first-line": [("esc",), ("g",), ("g",), ("0",)],
    "guided-claim": [("esc",), ("f12",)],
    "guided-exit": [("esc",), ("f10",)],
    "guided-native-tab": [("ctrl", "shift", "t")],
    "guided-first-tab": [("ctrl", "alt", "1")],
    "guided-new-tab-edit": [(key,) for key in "auxnativea"] + [("left",), ("b",)],
    "guided-returned-edit": [(key,) for key in "auxreturna"] + [("left",), ("b",)],
    "c1-insert": [("f3",)],
    "c1-open": [("f5",)],
    "c1-next": [("ctrl", "n")],
    "c1-previous": [("ctrl", "p")],
    "c1-accept": [("ctrl", "y")],
    "d1-run": [("f6",)],
    "d3-task": [("f2",)],
    "d1-current": [("f7",)],
    "d1-next": [("f9",)],
    "d1-previous": [("f8",)],
    "d1-clean": [("f5",)],
    "d2-next": [("j",)],
    "d2-previous": [("k",)],
    "l3-next-parameter": [("l",)],
    "l3-previous-parameter": [("h",)],
    "l3-cycle": [("f4",)],
    "l3-position": [("esc",), ("3",), ("5",), ("shift", "g"), ("0",), ("w",), ("w",)],
    "lsp-query": [("f3",)],
    "lsp-stop": [("f8",)],
    "lsp-first-argument": [("3",), ("dot",), ("5",), ("comma",), ("spc",)],
    "lsp-second-argument": [("2",), ("comma",), ("spc",)],
    "lsp-third-argument": [("0",), ("dot",), ("1",)],
    "lsp-previous-word": [("ctrl", "left")],
    "lsp-left": [("left",)],
    "lsp-right": [("right",)],
    "lsp-report": [("f4",)],
    "lsp-accept": [("ret",)],
    "lsp-cancel": [("esc",)],
    "l5-name": [(("shift", "minus") if char == "_" else (char,)) for char in "calculate_gratuity"],
    "l4-search": [("slash",), *[(("shift", "minus") if char == "_" else (char,)) for char in "calculate_tip"]],
    "l4-next-match": [("n",)],
    "l4-prev-result": [("f5",)],
    "l4-substitute": [("f6",)],
    "l4-answer-y": [("y",)],
    "l4-answer-n": [("n",)],
    "l4-answer-a": [("a",)],
    "l4-answer-q": [("q",)],
    "lazy-operation": [("f4",)],
    "lazy-verify": [("f5",)],
    "lazy-close": [("q",)],
    "lazy-help": [("shift", "slash")],
}


def add_pinned_plugin(archive, path, name, pin, git_bin):
    revision = subprocess.check_output(
        (str(git_bin / "git.exe"), "-C", str(path), "rev-parse", "HEAD"), text=True,
    ).strip()
    status = subprocess.check_output(
        (str(git_bin / "git.exe"), "-C", str(path), "status", "--porcelain"), text=True,
    )
    if revision != pin or status or not (path / ".git").is_dir():
        raise ValueError(f"Need a clean standalone {name} checkout at {pin}")
    destination = Path("data/nvim-data/site/pack/core/opt") / name
    for file in sorted(path.rglob("*")):
        if file.is_file():
            archive.write(file, destination / file.relative_to(path))


def add_guest_git(archive, git_bin):
    for path in (git_bin / "git.exe", *git_bin.glob("*.dll")):
        archive.write(path, "git-bin/" + path.name)


def add_pack_lock(archive, pins, plugins):
    records = {
        name: {"src": pins["plugins"][key]["source"], "rev": pins["plugins"][key]["revision"]}
        for key, name in plugins.items()
    }
    archive.writestr("config/nvim/nvim-pack-lock.json", json.dumps({"plugins": records}))


def add_lazy_tools(archive, checkout, tools, skip_operation):
    case, plugin, git_bin = tools
    human = checkout / "tests" / "human"
    pins = json.loads((human / "dependencies.json").read_text(encoding="utf-8"))
    archive.writestr("lazy-case.txt", case + "\n")
    if skip_operation:
        archive.writestr("lazy-skip-operation.txt", "Leave the initial Git state intact\n")
    for name in ("lazy-test.txt", "lazy-plugin-a.lua", "lazy-plugin-b.lua"):
        archive.write(human / "fixtures" / name, name)
    archive.write(human / "dependencies.json", "dependencies.json")
    for name in ("prepare-lazy-fixture.ps1", "audio-neovim-observer.lua"):
        archive.write(SOURCES / name, name)
    add_pinned_plugin(archive, plugin, "lazy.nvim", pins["plugins"]["lazyNvim"]["revision"], git_bin)
    add_pack_lock(archive, pins, {"lazyNvim": "lazy.nvim"})
    distribution = git_bin.parent.resolve()
    if git_bin.name != "cmd" or not all((distribution / name).is_dir() for name in ("etc", "ucrt64", "usr")):
        raise ValueError("Lazy cases require the cmd directory of the complete Git for Windows MinGit distribution")
    for file in sorted(distribution.rglob("*")):
        if file.is_file():
            archive.write(file, Path("git-mingit") / file.relative_to(distribution))


def add_diagnostic_tools(archive, checkout, pins, tools, muted):
    ruff, lint, git_bin = tools
    add_pinned_plugin(archive, lint, "nvim-lint", pins["plugins"]["nvimLint"]["revision"], git_bin)
    add_pack_lock(archive, pins, {"nvimLint": "nvim-lint"})
    if subprocess.check_output((str(ruff), "--version"), text=True).strip() != "ruff " + pins["tools"]["ruff"]:
        raise ValueError("D1 needs the pinned Ruff executable")
    fixture = checkout / "tests" / "human" / "fixtures" / "diagnostics.py"
    expected = subprocess.run((
        str(ruff), "check", "--isolated", "--no-cache", "--output-format=json", str(fixture),
    ), capture_output=True, encoding="utf-8")
    findings = json.loads(expected.stdout) if expected.returncode == 1 else []
    if not findings:
        raise ValueError(f"Ruff did not return fixture findings: {expected.stderr}")
    archive.writestr("audio-d1.txt", "D1\n")
    if muted:
        archive.writestr("audio-d1-muted.txt", "Disable both diagnostic cue settings\n")
    archive.writestr("expected-ruff.json", json.dumps([
        {key: item[key] for key in ("code", "location", "end_location")} for item in findings
    ]))
    archive.write(fixture, fixture.name)
    archive.write(ruff, "ruff.exe")
    add_guest_git(archive, git_bin)


def add_clang_tools(archive, checkout, tools, muted):
    clang, lint, git_bin, markers = tools
    human = checkout / "tests" / "human"
    pins = json.loads((human / "dependencies.json").read_text(encoding="utf-8"))
    version = subprocess.check_output((str(clang), "--version"), text=True, timeout=15)
    if f'version {pins["tools"]["clangTidy"]}' not in version:
        raise ValueError("D3 requires the pinned Clang-Tidy executable")
    fixture = human / "fixtures"
    result = subprocess.run(
        (str(clang), "--quiet", "--config-file=.clang-tidy", "diagnostics.c", "--", "-std=c11"),
        cwd=fixture, capture_output=True, encoding="utf-8", timeout=25,
    )
    parsed = re.findall(
        r"diagnostics\.c:(\d+):(\d+): error: (.+?) \[(clang-diagnostic-error)\]",
        result.stdout + result.stderr,
    )
    if result.returncode == 0 or len(parsed) != 2 or any(
        identifier not in item[2] for item, identifier in zip(parsed, ("missing_first", "missing_second"))
    ):
        raise ValueError(f"D3 independent Clang-Tidy findings were unexpected: {result.stdout}{result.stderr}")
    findings = [{"row": int(row), "byteColumn": int(column) - 1, "message": message, "code": code}
                for row, column, message, code in parsed]
    archive.writestr("expected-clang.json", json.dumps(findings))
    archive.write(clang, "clang-tidy.exe")
    add_external_linter_fixture(archive, human, pins, lint, git_bin, markers, muted,
                               "D3", "cDiagnostics", "diagnostics.c", ".clang-tidy")


def add_markdown_tools(archive, checkout, tools, muted):
    node, modules, lint, git_bin, markers = tools
    human = checkout / "tests" / "human"
    pins = json.loads((human / "dependencies.json").read_text(encoding="utf-8"))
    fixture = human / "fixtures"
    entry_point = modules / "markdownlint-cli2" / "markdownlint-cli2-bin.mjs"
    result = subprocess.run(
        (str(node), str(entry_point), "--config", ".markdownlint.json", "diagnostics.md"),
        cwd=fixture, capture_output=True, encoding="utf-8", timeout=25,
    )
    output = result.stdout + result.stderr
    parsed = re.findall(r"diagnostics\.md:(\d+)(?::(\d+))? (error MD025\b[^\r\n]+)", output)
    if (result.returncode != 1 or f'markdownlint-cli2 v{pins["tools"]["markdownlintCli2"]} ' not in output
            or len(parsed) != 1 or parsed[0][0] != "3"):
        raise ValueError(f"D4 independent markdownlint findings were unexpected: {output}")
    row, column, message = parsed[0]
    archive.writestr("expected-markdown.json", json.dumps([
        {"row": int(row), "byteColumn": int(column) - 1 if column else 0, "message": message}
    ]))
    archive.write(node, "node.exe")
    for file in sorted(modules.rglob("*")):
        if file.is_file():
            archive.write(file, Path("node_modules") / file.relative_to(modules))
    add_external_linter_fixture(archive, human, pins, lint, git_bin, markers, muted,
                               "D4", "markdownDiagnostics", "diagnostics.md", ".markdownlint.json")


def add_external_linter_fixture(archive, human, pins, lint, git_bin, markers, muted,
                                case, group, fixture, config):
    locale = json.loads((human / "locales" / "en.json").read_text(encoding="utf-8"))
    archive.writestr(f"audio-{case.lower()}.txt", case + "\n")
    if muted:
        archive.writestr("audio-d1-muted.txt", "Disable both diagnostic cue settings\n")
    archive.writestr("diagnostic-card.json", json.dumps({
        field: locale[f"plan.{group}.presentation.{field}"]
        for field in ("purpose", "action", "expected")
    }))
    for name in (fixture, config):
        archive.write(human / "fixtures" / name, name)
    archive.write(human / "dependencies.json", "dependencies.json")
    archive.write(SOURCES / "audio-neovim-observer.lua", "audio-neovim-observer.lua")
    for name in ("begin", "action", "end"):
        archive.write(markers / f"{name}.wav", f"{name}.wav")
    add_pinned_plugin(archive, lint, "nvim-lint", pins["plugins"]["nvimLint"]["revision"], git_bin)
    add_pack_lock(archive, pins, {"nvimLint": "nvim-lint"})
    add_guest_git(archive, git_bin)


COMPLETION_PLUGINS = {
    "cmp": {"nvimCmp": "nvim-cmp", "cmpNvimLsp": "cmp-nvim-lsp"},
    "blink": {"blinkCmp": "blink.cmp"},
}


def image(package, nvda_archive, nvim_archive, reuse_run, redistributable, uiaccess, guided_root=None,
          c1_tools=None, c1_muted=False, d1_tools=None, d1_muted=False, d2=False,
          l3=False, l3_no_pan=False, s1_no_f10=False, completion_tools=None,
          clang_tools=None, markdown_tools=None, external_diagnostics_muted=False,
          native_lsp=None, lsp_hints_disabled=False, lsp_missing_reference=False, l4_abort=False,
          lazy_tools=None, lazy_skip_operation=False, wasapi_tools=None, *, stage_directory=False):
    run_id = uuid.uuid4().hex[:12]
    with package.open("rb") as candidate:
        provenance = {"name": package.name, "sha256": hashlib.file_digest(candidate, "sha256").hexdigest()}
    candidate_manifest = ROOT / f"candidate-{run_id}.json"
    candidate_manifest.write_text(json.dumps(provenance), encoding="ascii")
    names = {
        "RUNID.TXT": ("run-id.txt", None),
        "GUEST.PS1": ("guest-test.ps1", SOURCES / "guest-test.ps1"),
        "BOOT.PS1": ("bootstrap.ps1", SOURCES / "NalBoot.ps1"),
        "AUDIT.PY": ("nalAudit.py", SOURCES / "nalAudit.py"),
        "NVDA.ZIP": ("nvda.zip", nvda_archive),
        "NVIM.ZIP": ("nvim.zip", nvim_archive),
        "TERMINAL.ZIP": ("terminal.zip", ROOT / "terminal-x64.zip"),
        "ADDON.ZIP": ("candidate.nvda-addon", package),
        "PROV.JSON": ("candidate.json", candidate_manifest),
    }
    if reuse_run:
        for name in ("NVDA.ZIP", "NVIM.ZIP", "TERMINAL.ZIP"):
            del names[name]
        reuse_file = ROOT / f"reuse-{run_id}.txt"
        reuse_file.write_text(reuse_run + "\n", encoding="ascii")
        names["REUSE.TXT"] = ("reuse-run.txt", reuse_file)
        if os.environ.get("NAL_TEST_DISCARD_RUN_COPIES") == "1":
            names["DISCARD.TXT"] = ("discard-run-copies.txt", reuse_file)
    if redistributable:
        names["VCREDIST.EXE"] = ("vc-redist.x64.exe", redistributable)
    if wasapi_tools is not None:
        loopback = ROOT / f"wasapi-tools-{run_id}.zip"
        with ZipFile(loopback, "w", compression=ZIP_DEFLATED) as archive:
            for name in ("wasapi-loopback-probe.exe", "NAudio.Core.dll", "NAudio.Wasapi.dll"):
                archive.write(wasapi_tools / name, name)
        names["WASAPI.ZIP"] = ("wasapi-tools.zip", loopback)
    if uiaccess:
        marker = ROOT / f"uiaccess-{run_id}.txt"
        marker.write_text("yes\n", encoding="ascii")
        names["UIACCESS.TXT"] = ("uiaccess.txt", marker)
    if guided_root:
        guided = ROOT / f"guided-{run_id}.zip"
        with ZipFile(guided, "w", compression=ZIP_DEFLATED) as archive:
            for name in ("init.lua", "linter_readiness.lua", "lazy_fixture.lua", "completion_parentheses.lua"):
                archive.write(guided_root / "tests" / "human" / "framework" / name, name)
            archive.write(guided_root / "tests" / "human" / "fixtures" / "lsp_features.py", "lsp_features.py")
            if native_lsp in {"L4", "L5", "L6"}:
                consumer = guided_root / "tests" / "human" / "fixtures" / "lsp_rename_consumer.py"
                if lsp_missing_reference:
                    archive.writestr(consumer.name, consumer.read_bytes().replace(b"calculate_tip", b"unrelated_tip"))
                    archive.writestr("lsp-missing-reference.txt", "Secondary buffer lacks the search term\n")
                else:
                    archive.write(consumer, consumer.name)
            if s1_no_f10:
                archive.writestr("s1-no-f10.txt", "Suppress the F10 editor exit\n")
            if clang_tools:
                add_clang_tools(archive, guided_root, clang_tools, external_diagnostics_muted)
            if markdown_tools:
                add_markdown_tools(archive, guided_root, markdown_tools, external_diagnostics_muted)
            if lazy_tools:
                add_lazy_tools(archive, guided_root, lazy_tools, lazy_skip_operation)
            if c1_tools or native_lsp:
                archive.write(SOURCES / "audio-neovim-observer.lua", "audio-neovim-observer.lua")
            if native_lsp:
                archive.writestr("native-lsp-profile.txt", native_lsp + "\n")
            if lsp_hints_disabled:
                archive.writestr("lsp-hints-disabled.txt", "Disable automatic parameter hints\n")
            if l4_abort:
                archive.writestr("l4-abort.txt", "Quit at the first replacement prompt in each file\n")
            if c1_tools and native_lsp not in {"L4", "L6"}:
                node, pyright, markers = c1_tools
                pins_path = guided_root / "tests" / "human" / "dependencies.json"
                pins = json.loads(pins_path.read_text(encoding="utf-8"))
                metadata = json.loads((pyright / "package.json").read_text(encoding="utf-8"))
                if metadata["name"] != "pyright" or metadata["version"] != pins["tools"]["pyright"]:
                    raise ValueError("C1 needs the pinned Pyright package")
                if not d1_tools and not l3 and not native_lsp:
                    archive.writestr("audio-c1.txt", "C1\n")
                if c1_muted:
                    archive.writestr("audio-c1-muted.txt", "Disable NVDA suggestion cues\n")
                if completion_tools:
                    profile, plugin_root, git_bin = completion_tools
                    archive.writestr("completion-profile.txt", profile + "\n")
                    for key, name in COMPLETION_PLUGINS[profile].items():
                        add_pinned_plugin(archive, plugin_root / key, name,
                                          pins["plugins"][key]["revision"], git_bin)
                    add_pack_lock(archive, pins, COMPLETION_PLUGINS[profile])
                    add_guest_git(archive, git_bin)
                archive.write(node, "node.exe")
                archive.write(pins_path, "dependencies.json")
                archive.write(guided_root / "tests" / "human" / "fixtures" / "pyrightconfig.json",
                              "pyrightconfig.json")
                marker_names = ("begin", "action", "end") if d1_tools else (
                    "begin", "before-open", "before-selection", "before-accept", "end",
                )
                if not l3 and not native_lsp:
                    for name in marker_names:
                        archive.write(markers / f"{name}.wav", f"{name}.wav")
                for path in sorted(pyright.rglob("*")):
                    if path.is_file():
                        archive.write(path, Path("pyright") / path.relative_to(pyright))
                if d1_tools:
                    add_diagnostic_tools(archive, guided_root, pins, d1_tools, d1_muted)
                if d2:
                    archive.writestr("held-d2.txt", "D2\n")
                if l3:
                    archive.writestr("held-l3.txt", "L3\n")
                if l3_no_pan:
                    archive.writestr("l3-no-pan.txt", "Suppress first forward Braille gesture\n")
        names["GUIDED.ZIP"] = ("guided.zip", guided)
    run_id_file = ROOT / f"run-{run_id}.txt"
    run_id_file.write_text(run_id + "\n", encoding="ascii")
    if stage_directory:
        staged = ROOT / f"payload-{run_id}"
        staged.mkdir()
        for name, path in names.values():
            copyfile((path or run_id_file).resolve(strict=True), staged / name)
        return run_id, staged

    import pycdlib

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3, vol_ident="NALPAYLOAD")
    for short, (name, path) in names.items():
        iso.add_file(str((path or run_id_file).resolve(strict=True)),
                     iso_path=f"/{short};1", joliet_path=f"/{name}")
    media = ROOT / f"test-{run_id}.iso"
    iso.write(str(media))
    iso.close()
    return run_id, media


def drive_keys(keyboard, action, held):
    if action == "lazy-hold":
        keyboard.key_transition("insert", down=True)
        held.add("insert")
    elif action in {"d2-begin", "l3-begin"}:
        keys = ("insert", "shift", "spc") if action == "d2-begin" else ("insert", "spc")
        for code in keys:
            held.add(code)
            keyboard.key_transition(code, down=True)
            time.sleep(0.1)
        for code in reversed(keys[1:]):
            keyboard.key_transition(code, down=False)
            held.remove(code)
    elif action == "d2-release":
        keyboard.key_transition("insert", down=False)
        held.discard("insert")
    else:
        for codes in KEYS[action]:
            keyboard.key(*codes)
            time.sleep(0.16)


class QemuTransport:
    serial = SERIAL

    @staticmethod
    def check_health(run_id):
        try:
            with Qmp() as guest:
                status = guest.execute("query-status")["status"]
        except (OSError, EOFError) as error:
            raise RuntimeError(f"QEMU stopped responding during guest run {run_id}") from error
        if status != "running":
            raise RuntimeError(f"QEMU reported {status} during guest run {run_id}")

    @staticmethod
    def drive(action, held):
        with Qmp() as keyboard:
            drive_keys(keyboard, action, held)

    @staticmethod
    def release(held):
        if not held:
            return
        with Qmp() as keyboard:
            for code in sorted(held):
                keyboard.key_transition(code, down=False)
                held.remove(code)


def monitor(run_id, offset, candidate=None, *, wasapi=False, transport=None):
    if transport is None:
        transport = QemuTransport()
    held = set()
    try:
        return monitor_output(run_id, offset, held, candidate, wasapi=wasapi, transport=transport)
    except BaseException:
        with suppress(OSError, EOFError):
            transport.release(held)
        raise


def monitor_output(run_id, offset, held, candidate=None, *, wasapi=False, transport):
    end = time.monotonic() + 28 * 60
    capture = ROOT / f"run-{run_id}.log"
    report_path = ROOT / f"run-{run_id}.json"
    collecting = False
    provenance_seen = False
    loopback = None
    loopback_path = ROOT / f"wasapi-{run_id}.wav"
    loopback_saved = False
    result = None
    next_status_probe = time.monotonic() + 15
    with transport.serial.open("rb", buffering=0) as stream, capture.open("w", encoding="utf-8") as log:
        stream.seek(offset)
        pending = b""
        while time.monotonic() < end:
            incoming = stream.read()
            if not incoming:
                if time.monotonic() >= next_status_probe:
                    next_status_probe = time.monotonic() + 15
                    transport.check_health(run_id)
                time.sleep(0.5)
                continue
            pending += incoming
            *lines, pending = pending.split(b"\n")
            for line in lines:
                line = line.decode("ascii", errors="replace").rstrip()
                if line == f"NAL_SKIP already started {run_id}":
                    raise RuntimeError(f"The guest already started run {run_id}")
                if line == f"NAL_START {run_id}":
                    collecting = True
                if not collecting:
                    continue
                if line.startswith("NAL_WASAPI"):
                    try:
                        if not wasapi or result is None or loopback_saved:
                            raise ValueError("Unexpected WASAPI transfer")
                        if line.startswith("NAL_WASAPI ") and loopback is None:
                            loopback = LoopbackRecording(line.removeprefix("NAL_WASAPI "))
                        elif line.startswith("NAL_WASAPI_DATA ") and loopback is not None:
                            loopback.append(line.removeprefix("NAL_WASAPI_DATA "))
                        elif line == "NAL_WASAPI_END" and loopback is not None:
                            loopback.save(loopback_path)
                            loopback_saved = True
                            result["wasapiCapture"] = {"file": loopback_path.name, "sha256": loopback.digest}
                        else:
                            raise ValueError("WASAPI transfer arrived out of order")
                    except (ValueError, EOFError, OSError) as error:
                        raise RuntimeError(f"WASAPI transfer failed for {run_id}: {error}") from error
                    if line.startswith("NAL_WASAPI_DATA "):
                        continue
                print(line, flush=True)
                print(line, file=log, flush=True)
                if line.startswith("NAL_SETUP candidate ") and candidate is not None:
                    expected = f"NAL_SETUP candidate {candidate['name']} SHA256 {candidate['sha256']}"
                    if line != expected or provenance_seen:
                        raise RuntimeError(f"Unexpected candidate provenance for {run_id}")
                    provenance_seen = True
                if line.startswith("NAL_KEY "):
                    action = line.removeprefix("NAL_KEY ")
                    transport.drive(action, held)
                if line.startswith("NAL_RESULT "):
                    if result is not None:
                        raise RuntimeError(f"The guest reported multiple results for {run_id}")
                    result = json.loads(line.removeprefix("NAL_RESULT "))
                    result.update(run=run_id, guestCleanupCompleted=False)
                    if provenance_seen:
                        result["candidate"] = candidate
                    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                    transport.release(held)
                    if candidate is not None and not provenance_seen:
                        raise RuntimeError(f"Guest run {run_id} did not verify the candidate hash")
                if line.startswith("NAL_CLEAN ") and result is not None:
                    result["copyCleanup"] = line.removeprefix("NAL_CLEAN ")
                if line == f"NAL_END {run_id}":
                    if result is None:
                        raise RuntimeError(f"Guest run {run_id} ended without a result")
                    if wasapi and not loopback_saved:
                        raise RuntimeError(f"Guest run {run_id} ended without the WASAPI recording")
                    result["guestCleanupCompleted"] = True
                    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                    return bool(result["ok"])
                if line.startswith("NAL_ERROR "):
                    raise RuntimeError(line.removeprefix("NAL_ERROR "))
    missing = "guest result" if result is None else "guest cleanup acknowledgement"
    raise TimeoutError(f"No {missing} for {run_id}")


def wait_for_desktop(seconds):
    from guest_signin import GuestSignIn

    serial = SERIAL
    deadline = time.monotonic() + seconds
    next_signin_probe = time.monotonic() + 60
    profile = ROOT / "guest-signin-profile.json"
    signin = None
    while True:
        if serial.is_file() and "NAL_BOOT audit desktop ready" in serial.read_text(encoding="ascii", errors="replace"):
            return
        now = time.monotonic()
        if now >= deadline:
            raise TimeoutError("The Windows guest has not reported an interactive audit desktop")
        if now >= next_signin_probe:
            next_signin_probe = now + 12
            if signin is None and profile.is_file():
                signin = GuestSignIn(profile)
            if signin is not None:
                with suppress(EOFError, OSError):
                    signin.observe()
        time.sleep(0.5)


def run_media(run_id, media, *, wasapi=False):
    candidate = json.loads((ROOT / f"candidate-{run_id}.json").read_text(encoding="ascii"))
    with Qmp() as qmp:
        offset = SERIAL.stat().st_size
        qmp.execute("blockdev-change-medium", device="payload", filename=media.as_posix(),
                    format="raw", **{"read-only-mode": "read-only"})
    print(f"Mounted test {run_id} in the isolated guest.", flush=True)
    try:
        return monitor(run_id, offset, candidate, wasapi=wasapi)
    except (EOFError, OSError, RuntimeError) as error:
        report = {
            "ok": False, "run": run_id, "failureType": "infrastructure",
            "guestCleanupCompleted": False, "error": str(error),
        }
        path = ROOT / f"run-{run_id}.json"
        if path.is_file():
            report["observedGuestResult"] = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise


def record_s1_pair(run_id, control_id, control_passed):
    result = json.loads((ROOT / f"run-{control_id}.json").read_text(encoding="utf-8"))
    expected_step = "s1_guided_f10_restores_original_powershell"
    evidence = result.get("focusEvidence", {})
    native_probe = result.get("nativeProbe") or {}
    rejected_at_restore = (
        not control_passed and result.get("guestCleanupCompleted")
        and result.get("pending") == expected_step
        and result.get("steps", [])[-2:] == ["s1_return_restores_bound_tab", "s1_control_keeps_bound_editor"]
        and evidence.get("omittedF10") is True and evidence.get("editorStillBound") is True
        and native_probe.get("terminalFocused") is True and native_probe.get("titleMatches") is True
        and native_probe.get("nativeEvents") is False
    )
    pair = {"ok": bool(rejected_at_restore), "positive": run_id, "control": control_id,
            "expectedControlFailure": expected_step, "observedControlFailure": result.get("pending")}
    (ROOT / f"s1-pair-{run_id}.json").write_text(json.dumps(pair, indent=2), encoding="utf-8")
    return pair


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--nvda", default=ROOT / "nvda-2026.3.1.zip", type=Path)
    parser.add_argument("--nvim", type=Path,
                        default=ROOT.parent / "neovim" / "0.12.6" / "nvim-win64.zip")
    parser.add_argument("--reuse-run", help="Reuse tool archives unpacked by this prior guest run")
    parser.add_argument("--redistributable", type=Path, help="Install this signed Microsoft VC++ runtime in the guest")
    parser.add_argument("--uiaccess", action="store_true", help="Use signed NVDA under guest Program Files")
    parser.add_argument("--guided-root", type=Path, help="Run the focused S1 card using this checkout")
    parser.add_argument("--c1-node", type=Path)
    parser.add_argument("--c1-pyright", type=Path)
    parser.add_argument("--c1-markers", type=Path)
    parser.add_argument("--c1-muted", action="store_true")
    parser.add_argument("--completion-profile", choices=COMPLETION_PLUGINS)
    parser.add_argument("--completion-plugins", type=Path)
    parser.add_argument("--completion-git-bin", type=Path)
    parser.add_argument("--d1-ruff", type=Path)
    parser.add_argument("--d1-lint", type=Path)
    parser.add_argument("--d1-git-bin", type=Path)
    parser.add_argument("--d1-muted", action="store_true")
    parser.add_argument("--d2-held", action="store_true")
    parser.add_argument("--l3-held", action="store_true")
    parser.add_argument("--native-lsp", choices=("L1", "L2", "L4", "L5", "L6"))
    parser.add_argument("--lazy-case", choices=("P1", "P2", "P3", "P4"))
    parser.add_argument("--lazy-checkout", type=Path)
    parser.add_argument("--lazy-git-bin", type=Path)
    parser.add_argument("--lazy-skip-operation", action="store_true")
    parser.add_argument("--lsp-hints-disabled", action="store_true",
                        help="L2 control with NVDA automatic parameter hints disabled")
    parser.add_argument("--lsp-missing-reference", action="store_true",
                        help="L6 control without a replacement match in the second buffer")
    parser.add_argument("--l4-abort", action="store_true", help="L4 control that quits in every file")
    parser.add_argument("--l3-no-pan", action="store_true",
                        help="Negative control: omit the first forward Braille gesture")
    parser.add_argument("--l3-with-control", action="store_true",
                        help="Run L3 and require the omitted gesture to fail at the page check")
    parser.add_argument("--s1-no-f10", action="store_true",
                        help="Negative control: omit F10 in the guided focus fixture")
    parser.add_argument("--s1-with-control", action="store_true",
                        help="Run S1 and require the omitted F10 to fail at PowerShell restoration")
    parser.add_argument("--boot-timeout", type=int, default=0,
                        help="Seconds to wait for the interactive guest desktop before starting the test")
    values = parser.parse_args()
    if values.boot_timeout < 0:
        parser.error("--boot-timeout must be nonnegative")
    c1_tools = (values.c1_node, values.c1_pyright, values.c1_markers)
    lazy_tools = (values.lazy_case, values.lazy_checkout, values.lazy_git_bin)
    if (any(lazy_tools) or values.lazy_skip_operation) and (
        not all(lazy_tools) or not values.guided_root or any(c1_tools)
        or values.l3_held or values.native_lsp or values.s1_no_f10
    ):
        parser.error("Lazy cases require a guided checkout, the pinned lazy.nvim checkout and Git")
    native_scenario = values.l3_held or values.native_lsp
    needs_pyright = values.l3_held or values.native_lsp in {"L1", "L2", "L5"}
    if values.lsp_hints_disabled and values.native_lsp != "L2":
        parser.error("--lsp-hints-disabled requires --native-lsp L2")
    if values.lsp_missing_reference and values.native_lsp != "L6":
        parser.error("--lsp-missing-reference requires --native-lsp L6")
    if values.l4_abort and values.native_lsp != "L4":
        parser.error("--l4-abort requires --native-lsp L4")
    if values.native_lsp and values.l3_held:
        parser.error("Select one guided scenario per guest run")
    if (values.s1_no_f10 or values.s1_with_control) and (
        not values.guided_root or any(c1_tools) or native_scenario or any(lazy_tools)
        or (values.s1_no_f10 and values.s1_with_control)
    ):
        parser.error("Select one S1 control mode with the guided focus fixture")
    if values.l3_no_pan and not values.l3_held:
        parser.error("--l3-no-pan requires --l3-held")
    if values.l3_with_control and (not values.l3_held or values.l3_no_pan):
        parser.error("--l3-with-control requires the positive L3 scenario")
    if native_scenario and (not values.guided_root or values.c1_muted or
                            any((values.d1_ruff, values.d1_lint, values.d1_git_bin, values.d1_muted, values.d2_held))):
        parser.error("Native scenarios require a guided checkout and cannot run a diagnostic or completion scenario")
    if needs_pyright and not all(c1_tools[:2]):
        parser.error("L1, L2, L3 and L5 require Node and pinned Pyright")
    if not native_scenario and any(c1_tools) and (not all(c1_tools) or not values.guided_root):
        parser.error("C1 requires a guided checkout, Node, pinned Pyright, and render markers")
    if values.c1_muted and not all(c1_tools):
        parser.error("The muted control requires a complete C1 setup")
    d1_tools = (values.d1_ruff, values.d1_lint, values.d1_git_bin)
    if any(d1_tools) and (not all(d1_tools) or not all(c1_tools) or values.c1_muted):
        parser.error("D1 requires Ruff, nvim-lint, Git, Node, Pyright and markers")
    if values.d1_muted and not all(d1_tools):
        parser.error("The muted control requires a complete D1 setup")
    if values.d2_held and (not all(d1_tools) or values.d1_muted):
        parser.error("D2 needs the complete diagnostic fixture without muted settings")
    completion_tools = (values.completion_profile, values.completion_plugins, values.completion_git_bin)
    if any(completion_tools) and (not all(completion_tools) or not all(c1_tools)
                                    or any(d1_tools) or native_scenario):
        parser.error("Plugin completion needs a guided completion run, pinned plugin checkouts and Git")
    wait_for_desktop(values.boot_timeout)
    run_id, media = image(values.package, values.nvda, values.nvim, values.reuse_run,
                          values.redistributable, values.uiaccess, values.guided_root,
                          c1_tools if all(c1_tools) or needs_pyright else None, values.c1_muted,
                          d1_tools if all(d1_tools) else None, values.d1_muted,
                          values.d2_held, values.l3_held, values.l3_no_pan, values.s1_no_f10,
                          completion_tools if all(completion_tools) else None,
                          native_lsp=values.native_lsp, lsp_hints_disabled=values.lsp_hints_disabled,
                          lsp_missing_reference=values.lsp_missing_reference, l4_abort=values.l4_abort,
                          lazy_tools=lazy_tools if all(lazy_tools) else None,
                          lazy_skip_operation=values.lazy_skip_operation)
    if not run_media(run_id, media):
        return 1
    control_tools = values.reuse_run if os.environ.get("NAL_TEST_DISCARD_RUN_COPIES") == "1" and values.reuse_run else run_id
    if values.s1_with_control:
        control_id, control_media = image(
            values.package, values.nvda, values.nvim, control_tools, None, values.uiaccess,
            values.guided_root, s1_no_f10=True,
        )
        control_passed = run_media(control_id, control_media)
        return 0 if record_s1_pair(run_id, control_id, control_passed)["ok"] else 1
    if not values.l3_with_control:
        return 0

    control_id, control_media = image(
        values.package, values.nvda, values.nvim, control_tools, None, values.uiaccess,
        values.guided_root, c1_tools, l3=True, l3_no_pan=True,
    )
    control_passed = run_media(control_id, control_media)
    result_path = ROOT / f"run-{control_id}.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    expected_step = "l3_name_pan_right_2"
    observed = result.get("signatureEvidence", {}).get("observed", [])
    editor = result.get("editorState", {})
    rejected_at_page = (
        not control_passed
        and result.get("pending") == expected_step
        and "l3_name_speech_cells_and_fixed_cursor" in result.get("steps", [])
        and bool(observed) and observed[0]["action"] == "name"
        and len(observed[0]["cells"]) == 1
        and result.get("recentBrailleCells", [])[-1:] == observed[0]["cells"]
        and [editor.get(field) for field in ("row", "byteColumn", "cursorMoves")] == observed[0]["cursor"]
    )
    pair = {"ok": rejected_at_page, "positive": run_id, "control": control_id,
            "expectedControlFailure": expected_step, "observedControlFailure": result.get("pending")}
    (ROOT / f"l3-pair-{run_id}.json").write_text(json.dumps(pair, indent=2), encoding="utf-8")
    return 0 if rejected_at_page else 1


if __name__ == "__main__":
    raise SystemExit(main())
