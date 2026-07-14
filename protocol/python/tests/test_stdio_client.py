from __future__ import annotations

import io
import unittest

from nvim_nvda_protocol import MessageFactory, SshStdioClient, encode_frame
from nvim_nvda_protocol.stdio_client import STDIO_MARKER


class FakeProcess:
    def __init__(self, output: bytes) -> None:
        self.stdout = io.BytesIO(output)
        self.stdin = io.BytesIO()
        self.stderr = io.BytesIO()

    def poll(self):
        return None


class ReadOneOnly(io.BytesIO):
    def read(self, size=-1):
        if size > 1:
            raise AssertionError("buffered read would block waiting for the requested size")
        return super().read(size)

    def read1(self, size=-1):
        return super().read(size)


class SshStdioClientTests(unittest.TestCase):
    def test_discards_shell_noise_and_accepts_full_state(self) -> None:
        events: list[dict] = []
        states: list[str] = []
        full_state = MessageFactory().create("fullState", {"lineText": "hello"})
        process = FakeProcess(b"shell noise\r\n" + STDIO_MARKER + encode_frame(full_state))
        process.stdout = ReadOneOnly(process.stdout.getvalue())
        client = SshStdioClient("example-host", events.append, states.append)
        with self.assertRaisesRegex(ConnectionResetError, "closed"):
            client._receive(process)
        self.assertEqual(["connected"], states)
        self.assertEqual("hello", events[0]["payload"]["lineText"])

    def test_stdio_v1_marker_is_not_accepted(self) -> None:
        client = SshStdioClient("example-host", lambda _event: None, lambda _state: None)
        process = FakeProcess(b"NVIM-NVDA-STDIO/1\n")
        with self.assertRaisesRegex(ConnectionResetError, "marker"):
            client._receive(process)

    def test_control_is_written_to_process_stdin(self) -> None:
        process = FakeProcess(b"")
        client = SshStdioClient("example-host", lambda _event: None, lambda _state: None)
        client._process = process
        self.assertTrue(client.send_control("requestFullState", {}))
        self.assertGreater(len(process.stdin.getvalue()), 4)

    def test_explicit_profile_port_user_and_identity_reach_openssh_command(self) -> None:
        client = SshStdioClient(
            "linux-user@host.example", lambda _event: None, lambda _state: None,
            ssh_port=2222, identity_file=r"C:\keys\editor key", session_id="4711",
        )
        command = client._build_command()
        self.assertEqual("ssh.exe", command[0])
        self.assertEqual(["-p", "2222"], command[command.index("-p"):command.index("-p") + 2])
        self.assertEqual(
            ["-i", r"C:\keys\editor key"],
            command[command.index("-i"):command.index("-i") + 2],
        )
        self.assertEqual(
            ["linux-user@host.example", "$HOME/.local/bin/nvim-nvda-bridge --session 4711"],
            command[-2:],
        )

    def test_profile_options_are_validated_before_start(self) -> None:
        for kwargs in (
            {"ssh_port": 0}, {"ssh_port": True}, {"identity_file": "-bad"},
            {"identity_file": "x\ny"}, {"session_id": "name;bad"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SshStdioClient("host", lambda _event: None, lambda _state: None, **kwargs)

    def test_password_uses_askpass_environment_and_never_command_line(self) -> None:
        password = "s p&ecial!%secret"
        client = SshStdioClient(
            "user@host", lambda _event: None, lambda _state: None,
            password=password, askpass_path=r"C:\addon\ssh-askpass.cmd",
        )
        command = client._build_command()
        environment = client._build_environment()
        self.assertNotIn(password, " ".join(command))
        self.assertIn("BatchMode=no", command)
        self.assertIn("NumberOfPasswordPrompts=1", command)
        self.assertEqual(password, environment["NVIM_NVDA_SSH_PASSWORD"])
        self.assertEqual("force", environment["SSH_ASKPASS_REQUIRE"])
        self.assertEqual(r"C:\addon\ssh-askpass.cmd", environment["SSH_ASKPASS"])
        with self.assertRaisesRegex(ValueError, "askpass"):
            SshStdioClient("host", lambda _event: None, lambda _state: None, password="secret")

    def test_ipv4_and_ipv6_literals_remain_distinct_ssh_targets(self) -> None:
        ipv4 = SshStdioClient("user@127.0.0.1", lambda _event: None, lambda _state: None)
        ipv6 = SshStdioClient("user@::1", lambda _event: None, lambda _state: None)
        self.assertEqual("user@127.0.0.1", ipv4._build_command()[-2])
        self.assertEqual("user@::1", ipv6._build_command()[-2])
        self.assertNotEqual(ipv4._build_command()[-2], ipv6._build_command()[-2])


if __name__ == "__main__":
    unittest.main()
