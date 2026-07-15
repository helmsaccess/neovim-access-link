from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from nvim_nvda_core import SshUserInstaller


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
                "server-user@example-host", package, 2222, r"C:\keys\server key",
            )
        self.assertTrue(result.success)
        self.assertEqual(2, len(calls))
        self.assertEqual(b"payload", calls[0][1])
        self.assertEqual([60, 60], [call[2] for call in calls])
        self.assertIn("BatchMode=yes", calls[0][0])
        self.assertIn("ClearAllForwardings=yes", calls[0][0])
        self.assertEqual(["-p", "2222"], calls[0][0][calls[0][0].index("-p"):calls[0][0].index("-p") + 2])
        self.assertEqual(
            ["-i", r"C:\keys\server key"],
            calls[0][0][calls[0][0].index("-i"):calls[0][0].index("-i") + 2],
        )
        self.assertEqual("server-user@example-host", calls[0][0][-2])
        self.assertIn("install.py", calls[1][0][-1])
        self.assertIn("os.environ[\"HOME\"]", calls[1][0][-1])
        self.assertIn("python3 -c '", calls[1][0][-1])
        self.assertIn('filter="data"', calls[1][0][-1])

    def test_rejects_target_that_could_be_an_option(self) -> None:
        result = SshUserInstaller().install("-oProxyCommand=bad", pathlib.Path("missing"))
        self.assertFalse(result.success)
        self.assertFalse(SshUserInstaller().install("host", pathlib.Path("missing"), 0).success)
        self.assertFalse(SshUserInstaller().install(
            "host", pathlib.Path("missing"), identity_file="-bad",
        ).success)

    def test_password_install_uses_ephemeral_askpass_environment_for_both_processes(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs.get("env")))
            return subprocess.CompletedProcess(command, 0, stdout=b"ok", stderr=b"")
        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory) / "package.tar.gz"
            package.write_bytes(b"payload")
            result = SshUserInstaller(runner).install(
                "user@host", package, password="secret value",
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

    def test_uninstall_removes_only_project_owned_remote_paths(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout=b"removed", stderr=b"")

        result = SshUserInstaller(runner).uninstall(
            "user@example-host", 2222, r"C:\keys\example",
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
        self.assertNotIn("init.lua", script)
        self.assertEqual(30, options["timeout"])

    def test_uninstall_uses_password_askpass_without_exposing_secret(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs.get("env")))
            return subprocess.CompletedProcess(command, 0, stdout=b"removed", stderr=b"")

        result = SshUserInstaller(runner).uninstall(
            "user@host", password="temporary secret", askpass_path=r"C:\addon\askpass.cmd",
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
