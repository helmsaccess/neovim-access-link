from __future__ import annotations

import socket
import threading
import unittest
from unittest import mock

import msgpack

from nvim_nvda_protocol.nvim_rpc import NvimRpcEndpoint, NvimRpcSource, _MAX_PENDING_NOTIFICATIONS


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
            mock.patch.object(source, "_request", side_effect=[[7, {}], "b" * 32]) as request,
        ):
            source._run()
        self.assertEqual(["connecting", "disconnected"], states)
        socket_type.assert_called_once()
        self.assertEqual(2, request.call_count)
        connection.close.assert_called_once_with()

    def test_controls_are_rejected_until_the_rpc_channel_is_ready(self) -> None:
        source = self.make_source()
        connection = mock.Mock()
        source._socket = connection
        self.assertFalse(source.notify("nvim_exec_lua", "return true", []))
        connection.sendall.assert_not_called()

    def test_setup_request_has_a_deadline_even_while_data_arrives(self) -> None:
        source = self.make_source()
        with (
            mock.patch("nvim_nvda_protocol.nvim_rpc.time.monotonic", side_effect=[0.0, 0.5, 3.0]),
            mock.patch.object(source, "_send"),
            mock.patch.object(source, "_feed") as feed,
            self.assertRaises(TimeoutError),
        ):
            source._request("nvim_get_api_info")
        feed.assert_called_once_with()

    def test_idle_reads_do_not_end_a_ready_connection(self) -> None:
        source = self.make_source()
        with (
            mock.patch.object(source, "_feed", side_effect=[TimeoutError, EOFError]) as feed,
            self.assertRaises(EOFError),
        ):
            source._notifications_loop()
        self.assertEqual(2, feed.call_count)

    def test_setup_buffers_only_a_bounded_number_of_notifications(self) -> None:
        source = self.make_source()
        notification = [2, "nvim_nvda_event", []]
        with (
            mock.patch.object(source, "_send"),
            mock.patch.object(source, "_messages", return_value=iter(
                [notification] * (_MAX_PENDING_NOTIFICATIONS + 1),
            )),
            self.assertRaisesRegex(RuntimeError, "too many notifications"),
        ):
            source._request("nvim_get_api_info")
        self.assertEqual(_MAX_PENDING_NOTIFICATIONS, len(source._pending_notifications))

    def test_invalid_rpc_message_disconnects_without_delivering_an_event(self) -> None:
        source = self.make_source()
        states = []

        def state_changed(state):
            states.append(state)
            if state == "disconnected":
                source._stop.set()

        source.on_connection_state = state_changed
        source.on_event = mock.Mock()
        connection = mock.Mock()
        connection.recv.return_value = msgpack.packb(None)
        with (
            mock.patch("nvim_nvda_protocol.nvim_rpc.socket.socket", return_value=connection),
            mock.patch.object(source, "_request", side_effect=[[7, {}], "a" * 32, None]),
        ):
            source._run()
        self.assertEqual(["connecting", "connected", "disconnected"], states)
        source.on_event.assert_not_called()
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
        source._ready = True
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
