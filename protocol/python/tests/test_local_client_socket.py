"""Exercise the production local client against a disposable Neovim process."""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import tempfile
import time
import unittest

import msgpack

from nvim_nvda_protocol.local_client import LocalTcpClient


ROOT = Path(__file__).resolve().parents[3]


def request(endpoint: tuple[str, int], method: str, arguments: list):
    """Send a fixture operation over a separate Neovim API channel."""
    with socket.create_connection(endpoint, timeout=2) as connection:
        connection.sendall(msgpack.packb([0, 1, method, arguments], use_bin_type=True))
        decoder = msgpack.Unpacker(raw=False, max_buffer_size=65_536)
        while data := connection.recv(4096):
            decoder.feed(data)
            for message in decoder:
                if message[:2] == [1, 1]:
                    if message[2] is not None:
                        raise AssertionError(message[2])
                    return message[3]
    raise EOFError(f"Neovim closed without answering {method}")


class LocalClientSocketTests(unittest.TestCase):
    def test_authenticated_neovim_state_and_cursor_routing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="local-rpc-") as directory:
            scratch = Path(directory)
            env = {
                **os.environ,
                "LOCALAPPDATA": str(scratch),
                "NVIM_NVDA_TEST_WINDOWS": "1",
                "NAL_SOCKET_TEST_RUNTIME": (ROOT / "neovim-plugin").as_posix(),
            }
            init = scratch / "init.lua"
            init.write_text(
                "vim.opt.loadplugins = false\n"
                "vim.opt.rtp:prepend(vim.env.NAL_SOCKET_TEST_RUNTIME)\n"
                "vim.cmd('runtime plugin/nvim_nvda.lua')\n",
                encoding="utf-8",
            )
            log_path = scratch / "nvim.log"
            with log_path.open("wb") as log, subprocess.Popen(
                ("nvim", "--headless", "-u", str(init), "-n", "-i", "NONE"),
                env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            ) as editor:
                try:
                    registry = scratch / "nvim-nvda" / "sessions"
                    deadline = time.monotonic() + 6
                    while not (entries := list(registry.glob(f"{editor.pid}-*.json"))):
                        if editor.poll() is not None or time.monotonic() >= deadline:
                            self.fail(f"Neovim did not register: {log_path.read_text(errors='replace')}")
                        time.sleep(0.05)
                    self.assertEqual(len(entries), 1)
                    session = json.loads(entries[0].read_text(encoding="utf-8"))
                    self.verify_client(session)
                finally:
                    editor.terminate()
                    try:
                        editor.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        editor.kill()

    def verify_client(self, session: dict) -> None:
        endpoint = (session["host"], session["port"])
        marker = "audit local cursor"
        request(endpoint, "nvim_buf_set_lines", [0, 0, -1, True, [marker]])
        request(endpoint, "nvim_win_set_cursor", [0, [1, 5]])
        states = queue.Queue()
        events = queue.Queue()
        client = LocalTcpClient(*endpoint, events.put, states.put, session_nonce=session["sessionNonce"])
        client.start()
        try:
            self.assertEqual("connecting", states.get(timeout=5))
            self.assertEqual("connected", states.get(timeout=5))
            event = events.get(timeout=5)
            self.assertEqual("fullState", event["type"])
            state = event["payload"]
            self.assertEqual(marker, state["lineText"])
            self.assertEqual("windows-loopback-tcp", state["_transport"]["kind"])
            self.assertEqual(5, state["cursor"]["byteColumn"])

            self.assertTrue(client.send_control("routeCursor", {
                **{key: state[key] for key in ("bufferId", "windowId", "changedtick", "modeRaw")},
                "target": "editor", "line": 1, "byteColumn": 0,
            }))
            deadline = time.monotonic() + 5
            while (cursor := request(endpoint, "nvim_win_get_cursor", [0])) != [1, 0]:
                if time.monotonic() >= deadline:
                    self.fail(f"Neovim did not route the cursor: {cursor!r}")
                time.sleep(0.05)
        finally:
            client.stop()


if __name__ == "__main__":
    unittest.main()
