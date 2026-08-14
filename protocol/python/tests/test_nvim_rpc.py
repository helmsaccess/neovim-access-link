from __future__ import annotations

import socket
import threading
import unittest
from unittest import mock

from nvim_nvda_protocol.nvim_rpc import NvimRpcEndpoint, NvimRpcSource


class NvimRpcSourceIdentityTests(unittest.TestCase):
    def make_source(self, nonce: str | None = "a" * 32) -> NvimRpcSource:
        return NvimRpcSource(
            NvimRpcEndpoint.windows_loopback_tcp("127.0.0.1", 45678),
            lambda _event, _payload: None,
            lambda _state: None,
            nonce,
        )

    def test_identity_is_verified_by_request_on_the_permanent_source(self) -> None:
        source = self.make_source()
        with mock.patch.object(source, "_request", return_value="a" * 32) as request:
            source._verify_session_identity()
        request.assert_called_once_with(
            "nvim_exec_lua",
            "return require('nvim_nvda.session').identity()",
            [],
        )

    def test_mismatched_identity_aborts_before_plugin_setup(self) -> None:
        source = self.make_source()
        with (
            mock.patch.object(source, "_request", return_value="b" * 32),
            self.assertRaisesRegex(RuntimeError, "identity mismatch"),
        ):
            source._verify_session_identity()

    def test_mismatched_identity_disconnects_without_reconnect_loop(self) -> None:
        states = []
        source = NvimRpcSource(
            NvimRpcEndpoint.windows_loopback_tcp("127.0.0.1", 45678),
            lambda _event, _payload: None,
            states.append,
            "a" * 32,
        )
        connection = mock.Mock()
        with (
            mock.patch("nvim_nvda_protocol.nvim_rpc.socket.socket", return_value=connection) as socket_type,
            mock.patch.object(source, "_request", side_effect=[(7, {}), "b" * 32]) as request,
        ):
            source._run()
        self.assertEqual(["connecting", "disconnected"], states)
        socket_type.assert_called_once()
        self.assertEqual(2, request.call_count)
        connection.close.assert_called_once_with()

    def test_unregistered_explicit_endpoint_skips_registry_identity(self) -> None:
        source = self.make_source(None)
        with mock.patch.object(source, "_request") as request:
            source._verify_session_identity()
        request.assert_not_called()

    def test_invalid_expected_nonce_is_rejected(self) -> None:
        for nonce in ("", "a" * 31, "A" * 32, "g" * 32):
            with self.subTest(nonce=nonce), self.assertRaisesRegex(ValueError, "nonce"):
                self.make_source(nonce)

    def test_raw_socket_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "typed Neovim RPC endpoint"):
            NvimRpcSource(
                "/run/user/1000/nvim.sock",
                lambda _event, _payload: None,
                lambda _state: None,
            )

    def test_stop_interrupts_a_blocked_notification_send(self) -> None:
        source = self.make_source(None)
        send_started = threading.Event()
        send_released = threading.Event()
        stopped = threading.Event()
        notify_result: list[bool] = []

        class BlockingSocket:
            def sendall(self, _data: bytes) -> None:
                send_started.set()
                send_released.wait(1.0)
                raise OSError("closed")

            def shutdown(self, how: int) -> None:
                self.shutdown_how = how
                send_released.set()

            def close(self) -> None:
                stopped.set()

        connection = BlockingSocket()
        source._socket = connection
        notify_thread = threading.Thread(
            target=lambda: notify_result.append(source.notify("nvim_nvda_control", {})),
        )
        notify_thread.start()
        self.assertTrue(send_started.wait(1.0))
        stop_returned = threading.Event()
        stop_thread = threading.Thread(target=lambda: (source.stop(), stop_returned.set()))
        stop_thread.start()
        self.assertTrue(stop_returned.wait(1.0))
        stop_thread.join()
        notify_thread.join(timeout=1.0)
        self.assertFalse(notify_thread.is_alive())
        self.assertEqual([False], notify_result)
        self.assertEqual(socket.SHUT_RDWR, connection.shutdown_how)
        self.assertTrue(stopped.is_set())


if __name__ == "__main__":
    unittest.main()
