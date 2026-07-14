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


if __name__ == "__main__":
    unittest.main()
