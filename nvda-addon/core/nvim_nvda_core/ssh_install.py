"""Rootless remote installation through the user's existing OpenSSH setup."""

from __future__ import annotations

import pathlib
import os
import subprocess
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class InstallResult:
    success: bool
    message: str
    diagnostics: str = ""


class SshUserInstaller:
    def __init__(self, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self._runner = runner

    def install(self, ssh_target: str, package_path: pathlib.Path,
                ssh_port: int = 22, identity_file: str = "",
                password: str = "", askpass_path: str = "") -> InstallResult:
        if not ssh_target or ssh_target.startswith("-") or any(character.isspace() for character in ssh_target):
            return InstallResult(False, "invalid SSH target")
        if not isinstance(ssh_port, int) or isinstance(ssh_port, bool) or not 1 <= ssh_port <= 65535:
            return InstallResult(False, "invalid SSH port")
        if identity_file and (
            not isinstance(identity_file, str) or identity_file.startswith("-")
            or "\r" in identity_file or "\n" in identity_file or "\0" in identity_file
        ):
            return InstallResult(False, "invalid SSH identity file")
        if password and (not isinstance(password, str) or "\0" in password or not askpass_path):
            return InstallResult(False, "invalid SSH password authentication")
        try:
            payload = package_path.read_bytes()
        except OSError as error:
            return InstallResult(False, "bundled server package is unavailable", str(error))
        base = [
            "ssh.exe", "-T", "-o", f"BatchMode={'no' if password else 'yes'}", "-o", "ConnectTimeout=10",
            "-o", "ClearAllForwardings=yes",
            "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
        ]
        if password:
            base.extend((
                "-o", "PreferredAuthentications=keyboard-interactive,password",
                "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1",
            ))
        if ssh_port != 22:
            base.extend(("-p", str(ssh_port)))
        if identity_file:
            base.extend(("-i", identity_file))
        base.append(ssh_target)
        environment = None
        if password:
            environment = os.environ.copy()
            environment.update({
                "SSH_ASKPASS": askpass_path, "SSH_ASKPASS_REQUIRE": "force",
                "DISPLAY": environment.get("DISPLAY", "nvim-nvda"),
                "NVIM_NVDA_SSH_PASSWORD": password,
            })
        upload_command = (
            'umask 077; mkdir -p "$HOME/.cache/nvim-nvda-install" && '
            'cat > "$HOME/.cache/nvim-nvda-install/package.tar.gz"'
        )
        try:
            upload = self._runner(
                [*base, upload_command], input=payload, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=environment, timeout=60,
            )
        except subprocess.TimeoutExpired as error:
            return InstallResult(False, "SSH package upload timed out", str(error))
        if upload.returncode != 0:
            return InstallResult(False, "SSH package upload failed", self._diagnostics(upload))
        install_command = (
            'set -e; d="$HOME/.cache/nvim-nvda-install"; '
            'rm -rf "$d/unpacked"; mkdir -p "$d/unpacked"; '
            "python3 -c 'import os,tarfile; d=os.path.join(os.environ[\"HOME\"],\".cache\",\"nvim-nvda-install\"); "
            "tarfile.open(os.path.join(d,\"package.tar.gz\")).extractall(os.path.join(d,\"unpacked\"),filter=\"data\")'; "
            'python3 "$d"/unpacked/server-components-*/install.py; '
            '"$HOME/.local/bin/nvim-nvda-bridge" --help >/dev/null; '
            'rm -rf "$d/unpacked" "$d/package.tar.gz"'
        )
        try:
            installed = self._runner(
                [*base, install_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=environment,
                timeout=60,
            )
        except subprocess.TimeoutExpired as error:
            return InstallResult(False, "remote user installation timed out", str(error))
        if installed.returncode != 0:
            return InstallResult(False, "remote user installation failed", self._diagnostics(installed))
        return InstallResult(True, "Neovim server components installed", self._diagnostics(installed))

    @staticmethod
    def _diagnostics(result: subprocess.CompletedProcess) -> str:
        stdout = bytes(result.stdout or b"").decode("utf-8", "replace")
        stderr = bytes(result.stderr or b"").decode("utf-8", "replace")
        return (stdout + "\n" + stderr).strip()[-4000:]
