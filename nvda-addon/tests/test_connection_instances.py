from __future__ import annotations

import unittest

from nvim_nvda_core import (
    LOCAL_WINDOWS_TCP, ConnectionInstanceManager, TerminalIdentity,
    local_windows_target,
)


class FakeClient:
    def __init__(self, fail_start=False):
        self.starts = 0
        self.stops = 0
        self.fail_start = fail_start

    def start(self):
        self.starts += 1
        if self.fail_start:
            raise RuntimeError("start failed")

    def stop(self):
        self.stops += 1


class ConnectionInstanceManagerTests(unittest.TestCase):
    def test_same_profile_and_session_can_have_parallel_distinct_instances(self) -> None:
        manager = ConnectionInstanceManager()
        first_client = FakeClient()
        second_client = FakeClient()
        first = manager.add("example-host-eh", "4711", "Example host one", first_client)
        second = manager.add("example-host-eh", "4711", "Example host two", second_client)
        self.assertNotEqual(first.identifier, second.identifier)
        self.assertEqual([first, second], manager.list())
        self.assertEqual((1, 1), (first_client.starts, second_client.starts))

    def test_explicit_terminal_bindings_do_not_guess_or_cross(self) -> None:
        manager = ConnectionInstanceManager()
        first = manager.add("example-host-eh", "111", "Example host eh", FakeClient())
        second = manager.add("example-host-root", "222", "Example host root", FakeClient())
        terminal_one = TerminalIdentity(10, 100)
        terminal_two = TerminalIdentity(20, 200)
        self.assertIsNone(manager.selected_for(terminal_one))
        manager.bind(terminal_one, second.identifier)
        manager.bind(terminal_two, first.identifier)
        self.assertEqual(second, manager.selected_for(terminal_one))
        self.assertEqual(first, manager.selected_for(terminal_two))
        with self.assertRaisesRegex(ValueError, "unknown"):
            manager.bind(terminal_one, "missing")

    def test_runtime_ids_distinguish_tabs_sharing_process_and_window(self) -> None:
        manager = ConnectionInstanceManager()
        first = manager.add("one", "1", "First", FakeClient())
        second = manager.add_target(
            local_windows_target(), "2", "Local second", FakeClient(),
        )
        tab_one = TerminalIdentity(10, 100, "windowsTerminal", (42, 100, 4, 6))
        tab_two = TerminalIdentity(10, 100, "windowsTerminal", (42, 100, 4, 53))
        manager.bind(tab_one, first.identifier)
        manager.bind(tab_two, second.identifier)
        self.assertEqual(first, manager.selected_for(tab_one))
        self.assertEqual(second, manager.selected_for(tab_two))
        self.assertEqual(LOCAL_WINDOWS_TCP, second.transport_kind)
        self.assertEqual("local-windows", second.target_id)
        self.assertEqual("", second.profile_id)
        self.assertEqual(first, manager.unbind(tab_one))
        self.assertIsNone(manager.selected_for(tab_one))

    def test_remove_and_stop_all_close_clients_and_clear_bindings(self) -> None:
        manager = ConnectionInstanceManager()
        first_client = FakeClient()
        second_client = FakeClient()
        first = manager.add("one", "1", "One", first_client)
        second = manager.add("two", "2", "Two", second_client)
        terminal = TerminalIdentity(10, 100)
        manager.bind(terminal, first.identifier)
        manager.remove(first.identifier)
        self.assertIsNone(manager.selected_for(terminal))
        self.assertEqual(1, first_client.stops)
        manager.stop_all()
        self.assertEqual(1, second_client.stops)
        self.assertEqual([], manager.list())
        with self.assertRaisesRegex(ValueError, "unknown"):
            manager.client_for(second.identifier)

    def test_failed_start_is_not_retained(self) -> None:
        manager = ConnectionInstanceManager()
        with self.assertRaisesRegex(RuntimeError, "start failed"):
            manager.add("one", "1", "One", FakeClient(fail_start=True))
        self.assertEqual([], manager.list())

    def test_non_ssh_transport_cannot_bypass_typed_target(self) -> None:
        manager = ConnectionInstanceManager()
        with self.assertRaisesRegex(ValueError, "add_target"):
            manager.add("fake-profile", "1", "Local", FakeClient(), "localWindowsTcp")


if __name__ == "__main__":
    unittest.main()
