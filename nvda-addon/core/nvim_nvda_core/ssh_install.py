"""Rootless remote installation through the user's existing OpenSSH setup."""

from __future__ import annotations

import pathlib
import os
import subprocess
from dataclasses import dataclass
from typing import Callable

from .config_transfer import (
    CONFIGURATION_COPY_LOCAL,
    CONFIGURATION_MODES,
    CONFIGURATION_STARTER,
    CONFIGURATION_UNCHANGED,
    MAX_CONFIG_ARCHIVE_BYTES,
)


@dataclass(frozen=True)
class InstallResult:
    success: bool
    message: str
    diagnostics: str = ""
    configuration_path: str = ""
    configuration_backups: tuple[str, ...] = ()
    configuration_kind: str = ""


class SshUserInstaller:
    def __init__(self, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self._runner = runner

    def install(
        self,
        ssh_target: str,
        package_path: pathlib.Path,
        ssh_port: int = 22,
        identity_file: str = "",
        password: str = "",
        askpass_path: str = "",
        configuration_mode: str = CONFIGURATION_UNCHANGED,
        imported_config: bytes = b"",
    ) -> InstallResult:
        validation = self._validate(ssh_target, ssh_port, identity_file, password, askpass_path)
        if validation is not None:
            return validation
        if configuration_mode not in CONFIGURATION_MODES:
            return InstallResult(False, "invalid Neovim configuration mode")
        if configuration_mode == CONFIGURATION_COPY_LOCAL and not imported_config:
            return InstallResult(False, "local Neovim configuration archive is unavailable")
        if len(imported_config) > MAX_CONFIG_ARCHIVE_BYTES:
            return InstallResult(False, "local Neovim configuration archive is too large")
        if configuration_mode != CONFIGURATION_COPY_LOCAL and imported_config:
            return InstallResult(False, "unexpected local Neovim configuration archive")
        try:
            payload = package_path.read_bytes()
        except OSError as error:
            return InstallResult(False, "bundled server package is unavailable", str(error))
        base, environment = self._ssh_command(
            ssh_target,
            ssh_port,
            identity_file,
            password,
            askpass_path,
        )
        upload_command = (
            'umask 077; mkdir -p "$HOME/.cache/nvim-nvda-install" && '
            'cat > "$HOME/.cache/nvim-nvda-install/package.tar.gz"'
        )
        try:
            upload = self._runner(
                [*base, upload_command],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=environment,
                timeout=60,
            )
        except subprocess.TimeoutExpired as error:
            return InstallResult(False, "SSH package upload timed out", str(error))
        if upload.returncode != 0:
            return InstallResult(False, "SSH package upload failed", self._diagnostics(upload))
        if configuration_mode == CONFIGURATION_COPY_LOCAL:
            config_upload_command = (
                'umask 077; d="$HOME/.cache/nvim-nvda-install"; '
                'mkdir -p "$d" && f="$d/windows-config.tar.gz.new" && '
                'trap \'rm -f "$f"\' 0 && cat > "$f" && '
                'mv "$f" "$d/windows-config.tar.gz"'
            )
            try:
                config_upload = self._runner(
                    [*base, config_upload_command],
                    input=imported_config,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    env=environment,
                    timeout=60,
                )
            except subprocess.TimeoutExpired as error:
                return InstallResult(False, "SSH configuration upload timed out", str(error))
            if config_upload.returncode != 0:
                return InstallResult(
                    False,
                    "SSH configuration upload failed",
                    self._diagnostics(config_upload),
                )
        if configuration_mode == CONFIGURATION_STARTER:
            install_option = " --install-starter-config"
        elif configuration_mode == CONFIGURATION_COPY_LOCAL:
            install_option = ' --import-config-archive "$d/windows-config.tar.gz"'
        else:
            install_option = ""
        install_command = (
            'set -e; d="$HOME/.cache/nvim-nvda-install"; '
            'trap \'rm -rf "$d/unpacked" "$d/package.tar.gz" "$d/windows-config.tar.gz"\' 0; '
            'rm -rf "$d/unpacked"; mkdir -p "$d/unpacked"; '
            'python3 -c \'import os,tarfile; d=os.path.join(os.environ["HOME"],".cache","nvim-nvda-install"); '
            'tarfile.open(os.path.join(d,"package.tar.gz")).extractall(os.path.join(d,"unpacked"),filter="data")\'; '
            f'python3 "$d"/unpacked/server-components-*/install.py{install_option}; '
            '"$HOME/.local/bin/nvim-nvda-bridge" --help >/dev/null'
        )
        try:
            installed = self._runner(
                [*base, install_command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=environment,
                timeout=60,
            )
        except subprocess.TimeoutExpired as error:
            return InstallResult(False, "remote user installation timed out", str(error))
        if installed.returncode != 0:
            return InstallResult(False, "remote user installation failed", self._diagnostics(installed))
        configuration_path, configuration_backups = self._configuration_details(installed)
        if configuration_mode != CONFIGURATION_UNCHANGED and not configuration_path:
            return InstallResult(
                False,
                "remote Neovim configuration result was missing",
                self._diagnostics(installed),
            )
        if configuration_mode == CONFIGURATION_STARTER:
            message = "Neovim server components and starter configuration installed"
        elif configuration_mode == CONFIGURATION_COPY_LOCAL:
            message = "Neovim server components and local Windows configuration installed"
        else:
            message = "Neovim server components installed"
        return InstallResult(
            True,
            message,
            self._diagnostics(installed),
            configuration_path,
            configuration_backups,
            configuration_mode if configuration_path else "",
        )

    def uninstall(
        self,
        ssh_target: str,
        ssh_port: int = 22,
        identity_file: str = "",
        password: str = "",
        askpass_path: str = "",
    ) -> InstallResult:
        validation = self._validate(ssh_target, ssh_port, identity_file, password, askpass_path)
        if validation is not None:
            return validation
        base, environment = self._ssh_command(
            ssh_target,
            ssh_port,
            identity_file,
            password,
            askpass_path,
        )
        command = (
            'set -e; p="$HOME/.local"; '
            'rm -f "$p/bin/nvim-nvda-bridge"; '
            'rm -rf "$p/share/nvim/site/pack/nvim-nvda"; '
            'rm -rf "$p/share/nvim-nvda"; '
            'rm -rf "$HOME/.cache/nvim-nvda-install"; '
            "printf '%s\\n' 'removed Neovim accessibility components'"
        )
        try:
            removed = self._runner(
                [*base, command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=environment,
                timeout=30,
            )
        except subprocess.TimeoutExpired as error:
            return InstallResult(False, "remote user removal timed out", str(error))
        if removed.returncode != 0:
            return InstallResult(False, "remote user removal failed", self._diagnostics(removed))
        return InstallResult(True, "Neovim server components removed", self._diagnostics(removed))

    @staticmethod
    def _validate(
        ssh_target: str, ssh_port: int, identity_file: str, password: str, askpass_path: str
    ) -> InstallResult | None:
        if (
            not ssh_target
            or ssh_target.startswith("-")
            or any(character.isspace() for character in ssh_target)
        ):
            return InstallResult(False, "invalid SSH target")
        if not isinstance(ssh_port, int) or isinstance(ssh_port, bool) or not 1 <= ssh_port <= 65535:
            return InstallResult(False, "invalid SSH port")
        if identity_file and (
            not isinstance(identity_file, str)
            or identity_file.startswith("-")
            or "\r" in identity_file
            or "\n" in identity_file
            or "\0" in identity_file
        ):
            return InstallResult(False, "invalid SSH identity file")
        if password and (not isinstance(password, str) or "\0" in password or not askpass_path):
            return InstallResult(False, "invalid SSH password authentication")
        return None

    @staticmethod
    def _ssh_command(
        ssh_target: str, ssh_port: int, identity_file: str, password: str, askpass_path: str
    ) -> tuple[list[str], dict[str, str] | None]:
        base = [
            "ssh.exe",
            "-T",
            "-o",
            f"BatchMode={'no' if password else 'yes'}",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ClearAllForwardings=yes",
            "-o",
            "ServerAliveInterval=5",
            "-o",
            "ServerAliveCountMax=2",
        ]
        if password:
            base.extend(
                (
                    "-o",
                    "PreferredAuthentications=keyboard-interactive,password",
                    "-o",
                    "PubkeyAuthentication=no",
                    "-o",
                    "NumberOfPasswordPrompts=1",
                )
            )
        if ssh_port != 22:
            base.extend(("-p", str(ssh_port)))
        if identity_file:
            base.extend(("-i", identity_file))
        base.append(ssh_target)
        environment = None
        if password:
            environment = os.environ.copy()
            environment.update(
                {
                    "SSH_ASKPASS": askpass_path,
                    "SSH_ASKPASS_REQUIRE": "force",
                    "DISPLAY": environment.get("DISPLAY", "nvim-nvda"),
                    "NVIM_NVDA_SSH_PASSWORD": password,
                }
            )
        return base, environment

    @staticmethod
    def _diagnostics(result: subprocess.CompletedProcess) -> str:
        stdout = bytes(result.stdout or b"").decode("utf-8", "replace")
        stderr = bytes(result.stderr or b"").decode("utf-8", "replace")
        return (stdout + "\n" + stderr).strip()[-4000:]

    @staticmethod
    def _configuration_details(result: subprocess.CompletedProcess) -> tuple[str, tuple[str, ...]]:
        stdout = bytes(result.stdout or b"").decode("utf-8", "replace")
        configuration_path = ""
        backups = []
        for line in stdout.splitlines():
            if line.startswith("installed starter configuration: "):
                configuration_path = line.removeprefix("installed starter configuration: ")
            elif line.startswith("imported Windows Neovim configuration: "):
                configuration_path = line.removeprefix("imported Windows Neovim configuration: ")
            elif line.startswith("backed up Neovim configuration: "):
                backups.append(line.removeprefix("backed up Neovim configuration: "))
        return configuration_path, tuple(backups)
