"""Exercise the packaged NVDA AppModule on a disposable hosted Windows desktop."""

import argparse
from contextlib import ExitStack
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from zipfile import ZipFile


NVDA_RELEASE = "2026.3.1"
NVDA_URL = f"https://download.nvaccess.org/releases/{NVDA_RELEASE}/nvda_{NVDA_RELEASE}.exe"
NVDA_SHA256 = "6f80a5b0ca720a7d0d314b5be212f37388bbe81a1107ac3298c1821a1cd3f052"
TERMINAL_RELEASE = "1.25.3131.0"
TERMINAL_URL = (f"https://github.com/microsoft/terminal/releases/download/v{TERMINAL_RELEASE}/"
                f"Microsoft.WindowsTerminal_{TERMINAL_RELEASE}_x64.zip")
TERMINAL_SHA256 = "273d6f1502eca1b5bd95c43f5d4d7ec72cc503df340102f8659717e5bead3437"


def verified_download(url, expected, target):
    with urlopen(url, timeout=60) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination)
    if sha256(target) != expected:
        raise ValueError(f"SHA-256 mismatch for {target.name}")


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def wait_for(check, description, *, seconds=50):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if result := check():
            return result
        time.sleep(0.15)
    raise TimeoutError(description)


def stop(process):
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=15)


class KeyboardInput(ctypes.Structure):
    _fields_ = [("virtualKey", wintypes.WORD), ("scan", wintypes.WORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class InputData(ctypes.Union):
    _fields_ = [("mouse", MouseInput), ("keyboard", KeyboardInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("data", InputData)]


class WindowsDesktop:
    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.window_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = (self.window_callback, wintypes.LPARAM)
        self.user.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        self.user.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        self.user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user.SetForegroundWindow.argtypes = (wintypes.HWND,)
        self.user.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self.user.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int)
        self.user.SendInput.restype = wintypes.UINT
        self.kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                          ctypes.POINTER(wintypes.DWORD))
        self.kernel.CloseHandle.argtypes = (wintypes.HANDLE,)

    def window(self, title, terminal):
        found = None

        @self.window_callback
        def find(hwnd, _parameter):
            nonlocal found
            text = ctypes.create_unicode_buffer(300)
            self.user.GetWindowTextW(hwnd, text, len(text))
            if title not in text.value:
                return True
            self.user.GetClassNameW(hwnd, text, len(text))
            if text.value != "CASCADIA_HOSTING_WINDOW_CLASS":
                return True
            found = self.confirm_owner(hwnd, terminal)
            return found is None

        self.user.EnumWindows(find, 0)
        return found

    def confirm_owner(self, hwnd, terminal):
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = self.kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            image = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(image))
            if self.kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
                if Path(image.value).resolve() == terminal:
                    return hwnd, pid.value
        finally:
            self.kernel.CloseHandle(handle)
        return None

    def foreground(self, hwnd):
        if hwnd != self.user.GetForegroundWindow():
            self.user.SetForegroundWindow(hwnd)
        return hwnd == self.user.GetForegroundWindow()

    def type_line(self, hwnd, text):
        if self.user.GetForegroundWindow() != hwnd:
            raise RuntimeError("Refusing input because the test window is no longer foreground")
        keys = (*map(ord, text.upper()), 0x0D)
        events = (Input * (2 * len(keys)))(
            *(Input(1, InputData(keyboard=KeyboardInput(key, 0, flag, 0, 0)))
              for key in keys for flag in (0, 2)))
        if self.user.SendInput(len(events), events, ctypes.sizeof(Input)) != len(events):
            raise RuntimeError("SendInput did not deliver the complete test stimulus")

    def close(self, hwnd, terminal):
        if self.confirm_owner(hwnd, terminal):
            self.user.PostMessageW(hwnd, 0x0010, 0, 0)


def terminal_child(work):
    (work / "terminal-ready").touch()
    print("Windows Terminal smoke test ready", flush=True)
    entered = sys.stdin.readline().rstrip("\r\n")
    pending = work / "key-received.tmp"
    pending.write_text(entered, encoding="utf-8")
    pending.replace(work / "key-received.txt")
    time.sleep(70)


def exercise(work, addon):
    installer = work / "nvda.exe"
    terminal_archive = work / "terminal.zip"
    verified_download(NVDA_URL, NVDA_SHA256, installer)
    verified_download(TERMINAL_URL, TERMINAL_SHA256, terminal_archive)
    with ZipFile(terminal_archive) as archive:
        archive.extractall(work / "terminal")
    terminal, = (work / "terminal").rglob("WindowsTerminal.exe")
    (terminal.parent / ".portable").touch()

    portable = work / "nvda-portable"
    subprocess.run([str(installer), "--create-portable-silent", "--portable-path", str(portable),
                    "--config-path", str(work / "bootstrap-profile"), "--no-sr-flag", "--minimal",
                    "--ease-of-access"], cwd=work, check=True, timeout=150)
    nvda = portable / "nvda_noUIAccess.exe"
    if not nvda.is_file():
        raise RuntimeError("Official NVDA installer did not create the portable runtime")

    profile = work / "profile"
    add_on = profile / "addons" / "NeovimAccessLink"
    with ZipFile(addon) as archive:
        archive.extractall(add_on)
    shutil.copy2(Path(__file__).with_name("hosted_focus_observer.py"), add_on / "globalPlugins")
    (profile / "nvda.ini").write_text("[general]\n    showWelcomeDialogAtStartup = False\n"
                                    "[speech]\n    synth = silence\n[braille]\n    display = noBraille\n"
                                    "[update]\n    autoCheck = False\n", encoding="ascii")
    title = f"NAL Hosted Focus {secrets.token_hex(6)}"
    env = {**os.environ, "NAL_HOSTED_FOCUS_WORK": str(work), "NAL_HOSTED_FOCUS_TITLE": title}
    desktop = WindowsDesktop()
    with ExitStack() as cleanup:
        process = subprocess.Popen([str(terminal), "--window", "new", "new-tab", "--title", title,
                                    "--suppressApplicationTitle", "--inheritEnvironment", sys.executable,
                                    str(Path(__file__).resolve()), "--terminal-child", str(work)],
                                   cwd=terminal.parent, env=env)
        cleanup.callback(stop, process)
        hwnd, pid = wait_for(lambda: desktop.window(title, terminal), "Owned Windows Terminal window not found")
        cleanup.callback(desktop.close, hwnd, terminal)
        wait_for((work / "terminal-ready").is_file, "Console child did not start inside Windows Terminal")
        log = work / "nvda.log"
        reader = subprocess.Popen([str(nvda), "--minimal", "--no-sr-flag", "--debug-logging",
                                   "--config-path", str(profile), "--log-file", str(log)], env=env)
        cleanup.callback(stop, reader)
        first = work / "nvda-focus.json"
        try:
            wait_for(lambda: desktop.foreground(hwnd) and first.is_file(),
                     "NVDA did not observe focus on the candidate's Windows Terminal control")
            before = json.loads(first.read_text(encoding="utf-8"))
            if before["terminalPid"] != pid or before["nvda"] != NVDA_RELEASE:
                raise RuntimeError("NVDA focus observation came from a different Terminal or NVDA version")
            token = "".join(secrets.choice(string.ascii_lowercase) for _ in range(12))
            desktop.type_line(hwnd, token)
            result = work / "nvda-result.json"
            wait_for(result.is_file, "NVDA did not confirm the focused terminal after keyboard input")
            after = json.loads(result.read_text(encoding="utf-8"))
            if before != after or (work / "key-received.txt").read_text(encoding="utf-8") != token:
                raise RuntimeError("Terminal input or NVDA focus changed unexpectedly during the stimulus")
        except Exception:
            if log.is_file():
                print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-35:]), file=sys.stderr)
            raise
        return {**after, "terminal": TERMINAL_RELEASE, "typedLineReceived": True, "candidateSha256": sha256(addon)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--addon", type=Path)
    mode.add_argument("--terminal-child", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        parser.error("Run the focus smoke only on a disposable GitHub-hosted Windows runner")
    if args.terminal_child:
        terminal_child(args.terminal_child)
        return
    with tempfile.TemporaryDirectory(prefix="nal-hosted-focus-", dir=os.environ["RUNNER_TEMP"],
                                     ignore_cleanup_errors=True) as directory:
        result = exercise(Path(directory), args.addon.resolve(strict=True))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
