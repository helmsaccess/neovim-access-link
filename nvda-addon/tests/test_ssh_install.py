from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from nvim_nvda_core import (
    CONFIGURATION_COPY_LOCAL,
    CONFIGURATION_STARTER,
    SshUserInstaller,
)


class SshUserInstallerTests(unittest.TestCase):
    def test_uploads_and_installs_with_batch_mode(self) -> None:
        calls: list[tuple[list[str], bytes | None, int | None]] = []

        def runner(command, **kwargs):
            calls.append((command, kwargs.get("input"), kwargs.get("timeout")))
            return subprocess.CompletedProcess(command, 0, stdout=b"ok", stderr=b"")

        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            result = SshUserInstaller(runner).install(
                "server-user@example-host",
                package,
                2222,
                r"C:\keys\server key",
            )
        self.assertTrue(result.success)
        self.assertEqual(2, len(calls))
        self.assertEqual(b"payload", calls[0][1])
        self.assertEqual([60, 60], [call[2] for call in calls])
        self.assertIn("BatchMode=yes", calls[0][0])
        self.assertIn("ClearAllForwardings=yes", calls[0][0])
        self.assertEqual(["-p", "2222"], calls[0][0][calls[0][0].index("-p") : calls[0][0].index("-p") + 2])
        self.assertEqual(
            ["-i", r"C:\keys\server key"],
            calls[0][0][calls[0][0].index("-i") : calls[0][0].index("-i") + 2],
        )
        self.assertEqual("server-user@example-host", calls[0][0][-2])
        self.assertIn("install.py", calls[1][0][-1])
        self.assertIn("trap 'rm -rf", calls[1][0][-1])
        self.assertIn('os.environ["HOME"]', calls[1][0][-1])
        self.assertIn("python3 -c '", calls[1][0][-1])
        self.assertIn('filter="data"', calls[1][0][-1])

    def test_rejects_target_that_could_be_an_option(self) -> None:
        result = SshUserInstaller().install("-oProxyCommand=bad", pathlib.Path("missing"))
        self.assertFalse(result.success)
        self.assertFalse(SshUserInstaller().install("host", pathlib.Path("missing"), 0).success)
        self.assertFalse(
            SshUserInstaller()
            .install(
                "host",
                pathlib.Path("missing"),
                identity_file="-bad",
            )
            .success
        )

    def test_password_install_uses_ephemeral_askpass_environment_for_both_processes(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs.get("env")))
            return subprocess.CompletedProcess(command, 0, stdout=b"ok", stderr=b"")

        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            result = SshUserInstaller(runner).install(
                "user@host",
                package,
                password="secret value",
                askpass_path=r"C:\addon\ssh-askpass.cmd",
            )
        self.assertTrue(result.success)
        self.assertEqual(2, len(calls))
        for command, environment in calls:
            self.assertNotIn("secret value", " ".join(command))
            self.assertEqual("secret value", environment["NVIM_NVDA_SSH_PASSWORD"])
            self.assertEqual("force", environment["SSH_ASKPASS_REQUIRE"])

    def test_timeout_is_reported_as_a_normal_failed_result(self) -> None:
        def runner(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout", 0))

        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            result = SshUserInstaller(runner).install("user@host", package)
        self.assertFalse(result.success)
        self.assertEqual("SSH package upload timed out", result.message)

    def test_optional_starter_configuration_is_requested_and_reported(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            stdout = b"ok"
            if len(calls) == 2:
                stdout = (
                    b"installed starter configuration: /home/editor/.config/nvim/init.lua\n"
                    b"backed up Neovim configuration: "
                    b"/home/editor/.config/nvim/init.vim.neovim-access-link-backup-example\n"
                )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            result = SshUserInstaller(runner).install(
                "editor@example-host",
                package,
                configuration_mode=CONFIGURATION_STARTER,
            )

        self.assertTrue(result.success)
        self.assertIn("--install-starter-config", calls[1][-1])
        self.assertEqual("/home/editor/.config/nvim/init.lua", result.configuration_path)
        self.assertEqual(
            ("/home/editor/.config/nvim/init.vim.neovim-access-link-backup-example",),
            result.configuration_backups,
        )

    def test_missing_remote_starter_configuration_result_fails_closed(self) -> None:
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, stdout=b"components only", stderr=b"")

        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            result = SshUserInstaller(runner).install(
                "editor@example-host",
                package,
                configuration_mode=CONFIGURATION_STARTER,
            )

        self.assertFalse(result.success)
        self.assertEqual("remote Neovim configuration result was missing", result.message)

    def test_complete_local_configuration_is_uploaded_separately_and_reported(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs.get("input")))
            stdout = b"ok"
            if len(calls) == 3:
                stdout = (
                    b"imported Windows Neovim configuration: /home/editor/.config/nvim\n"
                    b"backed up Neovim configuration: "
                    b"/home/editor/.config/nvim.neovim-access-link-backup-example\n"
                )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"component payload")
            result = SshUserInstaller(runner).install(
                "editor@example-host",
                package,
                configuration_mode=CONFIGURATION_COPY_LOCAL,
                imported_config=b"configuration payload",
            )

        self.assertTrue(result.success)
        self.assertEqual(3, len(calls))
        self.assertEqual(b"component payload", calls[0][1])
        self.assertEqual(b"configuration payload", calls[1][1])
        self.assertIn("windows-config.tar.gz", calls[1][0][-1])
        self.assertIn("windows-config.tar.gz.new", calls[1][0][-1])
        self.assertIn("trap 'rm -f", calls[1][0][-1])
        self.assertIn('--import-config-archive "$d/windows-config.tar.gz"', calls[2][0][-1])
        self.assertEqual("/home/editor/.config/nvim", result.configuration_path)
        self.assertEqual(CONFIGURATION_COPY_LOCAL, result.configuration_kind)
        self.assertEqual(
            ("/home/editor/.config/nvim.neovim-access-link-backup-example",),
            result.configuration_backups,
        )

    def test_configuration_archive_is_required_only_for_copy_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            missing = SshUserInstaller().install(
                "editor@example-host",
                package,
                configuration_mode=CONFIGURATION_COPY_LOCAL,
            )
            unexpected = SshUserInstaller().install(
                "editor@example-host",
                package,
                imported_config=b"unexpected",
            )

        self.assertFalse(missing.success)
        self.assertFalse(unexpected.success)

    def test_uninstall_removes_only_project_owned_remote_paths(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout=b"removed", stderr=b"")

        result = SshUserInstaller(runner).uninstall(
            "user@example-host",
            2222,
            r"C:\keys\example",
        )

        self.assertTrue(result.success)
        self.assertEqual(1, len(calls))
        command, options = calls[0]
        self.assertEqual("user@example-host", command[-2])
        script = command[-1]
        self.assertIn('"$p/bin/nvim-nvda-bridge"', script)
        self.assertIn('"$p/share/nvim/site/pack/nvim-nvda"', script)
        self.assertIn('"$p/share/nvim-nvda"', script)
        self.assertIn('"$HOME/.cache/nvim-nvda-install"', script)
        self.assertNotIn(".ssh", script)
        self.assertNotIn(".config", script)
        self.assertNotIn("XDG_CONFIG_HOME", script)
        self.assertNotIn("init.lua", script)
        self.assertNotIn("backup", script)
        self.assertEqual(30, options["timeout"])

    def test_uninstall_uses_password_askpass_without_exposing_secret(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs.get("env")))
            return subprocess.CompletedProcess(command, 0, stdout=b"removed", stderr=b"")

        result = SshUserInstaller(runner).uninstall(
            "user@host",
            password="temporary secret",
            askpass_path=r"C:\addon\askpass.cmd",
        )

        self.assertTrue(result.success)
        command, environment = calls[0]
        self.assertNotIn("temporary secret", " ".join(command))
        self.assertEqual("temporary secret", environment["NVIM_NVDA_SSH_PASSWORD"])
        self.assertIn("BatchMode=no", command)

    def test_uninstall_timeout_and_invalid_target_fail_normally(self) -> None:
        def runner(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout", 0))

        result = SshUserInstaller(runner).uninstall("user@host")
        self.assertFalse(result.success)
        self.assertEqual("remote user removal timed out", result.message)
        self.assertFalse(SshUserInstaller().uninstall("-invalid").success)


if __name__ == "__main__":
    unittest.main()
