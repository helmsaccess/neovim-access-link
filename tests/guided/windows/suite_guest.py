"""Start only the configured disposable Windows guest when its process has stopped."""

from contextlib import suppress
from pathlib import Path
import subprocess
import sys
import time

from qmp import Qmp


def local_media(workspace, name, extension):
    if Path(name).name != name or Path(name).suffix.lower() != extension:
        raise ValueError(f"Expected a {extension} filename in the isolated guest workspace")
    path = (workspace / name).resolve(strict=True)
    if not path.is_file() or path.parent != workspace:
        raise ValueError("The restart media must be regular files in the isolated guest workspace")
    return path


class RestartableGuest:
    def __init__(self, workspace, port, config_dir, config, env, *, audio):
        self.workspace = workspace
        self.port = port
        self.env = env
        self.disk = local_media(workspace, config["disk"], ".qcow2")
        self.boot = local_media(workspace, config["bootMedia"], ".iso")
        self.launcher = (config_dir / config["launcher"]).resolve(strict=True)
        if self.launcher.parent != workspace or self.launcher.suffix.lower() != ".ps1" or not self.launcher.is_file():
            raise ValueError("The PowerShell launcher must be in the isolated guest workspace")
        suffix = "" if port == 31946 else f"-{port}"
        self.pid_file = workspace / f"qemu{suffix}.pid"
        self.audio = audio

    def monitor_matches(self):
        try:
            with Qmp(self.port) as monitor:
                blocks = {entry["device"]: entry for entry in monitor.execute("query-block") if entry.get("device")}
                disk = blocks.get("ide0-hd0", {}).get("inserted", {})
                boot = blocks.get("ide1-cd1", {}).get("inserted", {})
                payload = blocks.get("payload", {}).get("inserted", {})
                if (not disk.get("file") or Path(disk["file"]).resolve() != self.disk
                        or not boot.get("file") or Path(boot["file"]).resolve() != self.boot or boot.get("ro") is not True
                        or "payload" not in blocks or (payload and payload.get("ro") is not True)):
                    raise ValueError("The QEMU port is bound to a guest with different media or no test payload drive")
                return True
        except (EOFError, OSError):
            return False

    def process_exists(self):
        if not self.pid_file.is_file():
            return False
        process_id = int(self.pid_file.read_text(encoding="utf-8-sig").strip())
        if process_id <= 0:
            raise ValueError("Invalid QEMU process ID")
        lookup = (f"$p = Get-Process -Id {process_id} -ErrorAction SilentlyContinue; "
                  "if ($p -and $p.ProcessName -eq 'qemu-system-x86_64') { exit 0 }; exit 3")
        result = subprocess.run(("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", lookup),
                                env=self.env, timeout=20)
        if result.returncode not in (0, 3):
            raise RuntimeError("The isolated guest process lookup failed")
        return result.returncode == 0

    def stopped(self):
        return not self.monitor_matches() and not self.process_exists()

    def shutdown(self):
        if self.stopped():
            return
        for command, timeout in (("system_powerdown", 90), ("quit", 20)):
            if self.monitor_matches():
                with suppress(EOFError, OSError), Qmp(self.port) as monitor:
                    monitor.execute(command)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.stopped():
                    return
                time.sleep(2)
        raise TimeoutError("The isolated guest did not stop after the suite")

    def ready(self, sources):
        if self.stopped():
            command = ("powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                       "-File", self.launcher, "-DiskName", self.disk.name, "-BootMedia", self.boot.name,
                       "-QmpPort", str(self.port))
            if self.audio:
                command += ("-AudioCapture",)
            subprocess.run(command, cwd=self.workspace, env=self.env, check=True, timeout=60)
        deadline = time.monotonic() + 45
        while not self.monitor_matches():
            if time.monotonic() >= deadline:
                raise TimeoutError("The expected QEMU guest did not acknowledge its test media")
            time.sleep(1)
        subprocess.run((sys.executable, "-c", "from run_focus_test import wait_for_desktop; wait_for_desktop(720)"),
                       cwd=sources, env=self.env, check=True, timeout=740)
