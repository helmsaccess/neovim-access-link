"""Drive the existing S1 observer and its omitted-F10 control on a hosted desktop."""

import argparse
from contextlib import suppress
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from audit_result import verify_s1_focus, verify_serial_log
from hosted_focus_smoke import (
    NVDA_SHA256,
    NVDA_URL,
    TERMINAL_SHA256,
    TERMINAL_URL,
    Input,
    InputData,
    KeyboardInput,
    MouseInput,
    WindowsDesktop,
    verified_download,
    wait_for,
)


NVIM_URL = "https://github.com/neovim/neovim/releases/download/v0.12.6/nvim-win64.zip"
NVIM_SHA256 = "4e12b7103b601ffc8f25954b4da100f339faa73dccb69a5b135e897fa3d893ed"
VIRTUAL_KEYS = {
    "ctrl": 0xA2, "shift": 0xA0, "alt": 0xA4, "insert": 0x2D,
    "f10": 0x79, "f12": 0x7B, "esc": 0x1B, "left": 0x25,
    **{key: ord(key.upper()) for key in "abcdefghijklmnopqrstuvwxyz01"},
}
S1_ACTIONS = {
    "guided-first-line", "toggle", "guided-claim", "guided-native-tab",
    "guided-new-tab-edit", "guided-first-tab", "guided-exit", "guided-returned-edit",
}


class S1Keyboard(WindowsDesktop):
    def __init__(self, terminal):
        super().__init__()
        self.terminal = terminal
        self.owned = None
        self.user.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
        self.user.MapVirtualKeyW.restype = wintypes.UINT
        self.user.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        self.user.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_int, wintypes.UINT)
        self.user.WindowFromPoint.argtypes = (wintypes.POINT,)
        self.user.WindowFromPoint.restype = wintypes.HWND
        self.user.IsChild.argtypes = (wintypes.HWND, wintypes.HWND)
        self.user.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)

    def target(self):
        if self.owned is None:
            self.owned = self.window("NAL Editor A", self.terminal)
        if self.owned is None:
            return None
        hwnd, _pid = self.owned
        if self.confirm_owner(hwnd, self.terminal) != self.owned:
            raise RuntimeError("The original test terminal lost its identity")
        return hwnd

    def recover_focus(self):
        hwnd = self.target()
        if not hwnd or self.foreground(hwnd):
            return
        # The existing observer uses a pointer fallback on its isolated VM.
        # Only click a point whose hit-test belongs to this runner's test window.
        rect = wintypes.RECT()
        if not self.user.GetWindowRect(hwnd, ctypes.byref(rect)):
            return
        topmost, not_topmost, flags = wintypes.HWND(-1), wintypes.HWND(-2), 0x0013
        if not self.user.SetWindowPos(hwnd, topmost, 0, 0, 0, 0, flags):
            return
        try:
            point = wintypes.POINT(min(rect.left + 240, rect.right - 20), min(rect.top + 140, rect.bottom - 20))
            pointed = self.user.WindowFromPoint(point)
            if not pointed or (pointed != hwnd and not self.user.IsChild(hwnd, pointed)):
                return
            if not self.user.SetCursorPos(point.x, point.y) or self.user.WindowFromPoint(point) != pointed:
                return
            events = (Input * 2)(*(Input(0, InputData(mouse=MouseInput(0, 0, 0, flag, 0, 0)))
                                   for flag in (0x0002, 0x0004)))
            sent = self.user.SendInput(len(events), events, ctypes.sizeof(Input))
            if sent != len(events):
                if sent:
                    self.user.SendInput(1, ctypes.byref(events[1]), ctypes.sizeof(Input))
                raise RuntimeError("SendInput did not deliver the complete focus click")
        finally:
            self.user.SetWindowPos(hwnd, not_topmost, 0, 0, 0, 0, flags)

    def key(self, *codes):
        hwnd = wait_for(self.target, "The test runner could not find its original Windows Terminal window",
                        seconds=10)
        wait_for(lambda: self.foreground(hwnd), "The owned Windows Terminal could not receive foreground input",
                 seconds=5)
        downs, ups = [], []
        for code in codes:
            scan = self.user.MapVirtualKeyW(VIRTUAL_KEYS[code], 4)
            if not scan:
                raise RuntimeError(f"Unexpected Win32 scan code for {code}: 0x{scan:x}")
            # MapVirtualKeyW may return the numpad variant without the E0 prefix.
            flags = 0x0008 | int(code in {"insert", "left"} or scan >> 8 == 0xE0)
            downs.append(Input(1, InputData(keyboard=KeyboardInput(0, scan & 0xFF, flags, 0, 0))))
            ups.append(Input(1, InputData(keyboard=KeyboardInput(0, scan & 0xFF, flags | 0x0002, 0, 0))))
        events = (Input * (2 * len(codes)))(*downs, *reversed(ups))
        if self.target() != hwnd or self.user.GetForegroundWindow() != hwnd:
            raise RuntimeError("Refusing keyboard input because the test terminal no longer owns foreground")
        sent = self.user.SendInput(len(events), events, ctypes.sizeof(Input))
        if sent != len(events):
            for event in reversed(ups[:min(sent, len(events) - sent)]):
                self.user.SendInput(1, ctypes.byref(event), ctypes.sizeof(Input))
            raise RuntimeError("SendInput did not deliver the complete keyboard chord")


class HostedTransport:
    def __init__(self, serial, process, terminal, drive_keys):
        self.serial = serial
        self.process = process
        self.keyboard = S1Keyboard(terminal)
        self.drive_keys = drive_keys

    def check_health(self, run_id):
        if self.process.poll() is not None:
            raise RuntimeError(f"Hosted S1 {run_id} ended without a completed ledger ({self.process.returncode})")

    def drive(self, action, held):
        if action in {"focus-switch", "dismiss-shell-overlay"}:
            self.keyboard.recover_focus()
        elif action in S1_ACTIONS:
            self.drive_keys(self.keyboard, action, held)
        else:
            raise ValueError(f"Unexpected input request from the S1 observer: {action}")

    @staticmethod
    def release(held):
        if held:
            raise RuntimeError(f"S1 requested unsupported held input: {held}")


def prepare_tools(work):
    installer = work / "nvda-installer.exe"
    terminal = work / "terminal-x64.zip"
    nvim = work / "nvim.zip"
    portable = work / "nvda-portable"
    verified_download(NVDA_URL, NVDA_SHA256, installer)
    verified_download(TERMINAL_URL, TERMINAL_SHA256, terminal)
    verified_download(NVIM_URL, NVIM_SHA256, nvim)
    subprocess.run([str(installer), "--create-portable-silent", "--portable-path", str(portable),
                    "--config-path", str(work / "bootstrap-profile"), "--no-sr-flag", "--minimal",
                    "--ease-of-access"], cwd=work, check=True, timeout=150)
    if not (portable / "nvda_noUIAccess.exe").is_file():
        raise RuntimeError("The verified NVDA installer did not create the portable runtime")
    nvda = work / "nvda.zip"
    with ZipFile(nvda, "w", compression=ZIP_DEFLATED) as archive:
        for item in sorted(portable.rglob("*")):
            if item.is_file():
                archive.write(item, item.relative_to(portable))
    with ZipFile(terminal) as archive:
        terminal_image, = (Path(name) for name in archive.namelist() if Path(name).name == "WindowsTerminal.exe")
    return nvda, nvim, terminal_image


def run_card(work, run_id, source, terminal_image, *, monitor, drive_keys):
    serial = work / f"serial-{run_id}.log"
    serial.touch(exist_ok=False)
    candidate = json.loads((source / "candidate.json").read_text(encoding="ascii"))
    terminal = (work / run_id / "terminal" / terminal_image).resolve()
    shell = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    launcher = Path(__file__).with_name("hosted-s1-launch.ps1")
    stdout = work / f"launcher-{run_id}.log"
    # Let Windows PowerShell construct its own module path when Actions uses pwsh.
    environment = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    with stdout.open("w", encoding="utf-8") as output, subprocess.Popen(
        [str(shell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(launcher), "-Source", str(source), "-WorkDir", str(work), "-Transcript", str(serial)],
        env=environment, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    ) as process:
        try:
            transport = HostedTransport(serial, process, terminal, drive_keys)
            passed = monitor(run_id, 0, candidate, transport=transport)
            if process.wait(timeout=15):
                raise RuntimeError("Hosted S1 launcher returned an error after the terminal ledger")
        finally:
            if process.poll() is None:
                (work / f"cancel-{run_id}").touch()
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=20)
                if process.poll() is None:
                    process.kill()
    report = json.loads((work / f"run-{run_id}.json").read_text(encoding="utf-8"))
    return passed, report, verify_serial_log(work, run_id, candidate)


def exercise(work, addon):
    os.environ["NAL_TEST_WORK_DIR"] = str(work)
    from run_focus_test import drive_keys, image, monitor, record_s1_pair

    nvda, nvim, terminal_image = prepare_tools(work)
    checkout = Path(__file__).resolve().parents[3]
    inputs = addon, nvda, nvim, None, None, False, checkout
    positive, source = image(*inputs, stage_directory=True)
    passed, positive_report, positive_log = run_card(
        work, positive, source, terminal_image, monitor=monitor, drive_keys=drive_keys,
    )
    if not passed:
        raise RuntimeError(f"Hosted S1 positive failed at {positive_report.get('pending')}")
    control, source = image(*inputs, s1_no_f10=True, stage_directory=True)
    passed, control_report, control_log = run_card(
        work, control, source, terminal_image, monitor=monitor, drive_keys=drive_keys,
    )
    pair = record_s1_pair(positive, control, passed)
    if not pair["ok"]:
        raise RuntimeError("Hosted S1 did not reject the omitted F10 at the expected step")
    verify_s1_focus(positive_report, control_report, positive_log, control_log)
    pair["inputBackend"] = "Win32 SendInput on the interactive Windows desktop"
    (work / f"s1-pair-{positive}.json").write_text(json.dumps(pair, indent=2), encoding="utf-8")
    return pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addon", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        parser.error("Run S1 only on a disposable GitHub-hosted Windows runner")
    temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    output = args.output.resolve()
    if not output.is_relative_to(temp) or output == temp:
        parser.error("Place S1 evidence in a new directory under RUNNER_TEMP")
    if any(character.isspace() for character in str(temp)):
        parser.error("The Windows guest launcher requires a runner temporary path without spaces")
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="nal-s1-", dir=temp, ignore_cleanup_errors=True) as directory:
        work = Path(directory)
        try:
            result = exercise(work, args.addon.resolve(strict=True))
        finally:
            for pattern in ("run-*.log", "run-*.json", "s1-pair-*.json", "launcher-*.log", "serial-*.log"):
                for item in work.glob(pattern):
                    shutil.copyfile(item, output / item.name)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
