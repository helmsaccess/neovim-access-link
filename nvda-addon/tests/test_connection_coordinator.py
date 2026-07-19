from __future__ import annotations

import unittest

from nvim_nvda_core import (
    ConnectionCoordinator,
    ConnectionInstanceManager,
    PendingControlRequest,
    SpeechPlanner,
    TerminalIdentity,
)


class ConnectionCoordinatorTests(unittest.TestCase):
    def test_coordinators_do_not_share_connection_or_terminal_state(self) -> None:
        first = ConnectionCoordinator()
        second = ConnectionCoordinator()
        terminal = TerminalIdentity(10, 100)

        first.remembered_terminal_bindings.add(terminal)
        first.authenticated_instances.add("connection-1")
        first.terminal_passthrough["connection-1"] = True
        first.pending_focus_contexts["connection-1"] = object()
        first.transport_capabilities = frozenset({"focusContext"})

        self.assertIsInstance(first.instances, ConnectionInstanceManager)
        self.assertIsNot(first.instances, second.instances)
        self.assertIsNot(first.gate, second.gate)
        self.assertIsNot(first.planner, second.planner)
        self.assertEqual(set(), second.remembered_terminal_bindings)
        self.assertEqual(set(), second.authenticated_instances)
        self.assertEqual({}, second.terminal_passthrough)
        self.assertEqual({}, second.pending_focus_contexts)
        self.assertEqual(frozenset(), second.transport_capabilities)

    def test_clear_runtime_tracking_preserves_last_observed_state_and_manager(self) -> None:
        manager = ConnectionInstanceManager()
        coordinator = ConnectionCoordinator(manager)
        terminal = TerminalIdentity(10, 100)
        coordinator.active_client = object()
        coordinator.last_connection_state = "disconnected"
        coordinator.connected = True
        coordinator.remembered_terminal_bindings.add(terminal)
        coordinator.remember_offer_instances.add("connection-1")
        coordinator.authenticated_instances.add("connection-1")
        coordinator.terminal_passthrough["connection-1"] = True
        coordinator.active_instance_id = "connection-1"
        coordinator.runtime_states["connection-1"] = {"connected": True}
        coordinator.pending_full_states["connection-1"] = {"type": "fullState"}
        coordinator.pending_focus_contexts["connection-1"] = (1, terminal)
        coordinator.pending_clipboard_requests[1] = PendingControlRequest(
            "connection-1", terminal, "copyTextRequest",
        )
        coordinator.pending_terminal_control_requests[2] = PendingControlRequest(
            "connection-1", terminal, "leaveTerminalInputRequest",
        )
        coordinator.transport_capabilities = frozenset({"focusContext", "clipboardTransfer"})

        coordinator.clear_runtime_tracking()

        self.assertIs(manager, coordinator.instances)
        self.assertIsNone(coordinator.active_client)
        self.assertEqual("disconnected", coordinator.last_connection_state)
        self.assertFalse(coordinator.connected)
        self.assertEqual(set(), coordinator.remembered_terminal_bindings)
        self.assertEqual(set(), coordinator.remember_offer_instances)
        self.assertEqual(set(), coordinator.authenticated_instances)
        self.assertEqual({}, coordinator.terminal_passthrough)
        self.assertIsNone(coordinator.active_instance_id)
        self.assertEqual({}, coordinator.runtime_states)
        self.assertEqual({}, coordinator.pending_full_states)
        self.assertEqual({}, coordinator.pending_focus_contexts)
        self.assertEqual({}, coordinator.pending_clipboard_requests)
        self.assertEqual({}, coordinator.pending_terminal_control_requests)
        self.assertEqual(frozenset(), coordinator.transport_capabilities)

    def test_runtime_switches_preserve_each_instance_and_drop_active_state(self) -> None:
        coordinator = ConnectionCoordinator()
        created = []

        def create_runtime():
            runtime = {
                "planner": SpeechPlanner(),
                "currentState": {"label": f"new-{len(created) + 1}"},
                "lastMode": None,
                "typedWord": [],
                "typedPosition": None,
                "menuDocumentation": "",
                "connected": False,
                "lastConnectionState": None,
                "transportCapabilities": frozenset(),
            }
            created.append(runtime)
            return runtime

        self.assertTrue(coordinator.switch_runtime("connection-1", create_runtime))
        self.assertEqual({"label": "new-1"}, coordinator.current_state)
        self.assertFalse(coordinator.switch_runtime("connection-1", create_runtime))
        coordinator.current_state = {"label": "first-active"}
        self.assertTrue(coordinator.switch_runtime("connection-2", create_runtime))
        self.assertEqual({"label": "new-2"}, coordinator.current_state)
        self.assertEqual(
            {"label": "first-active"},
            coordinator.runtime_states["connection-1"]["currentState"],
        )
        coordinator.current_state = {"label": "second-active"}
        self.assertTrue(coordinator.switch_runtime("connection-1", create_runtime))
        self.assertEqual({"label": "first-active"}, coordinator.current_state)
        self.assertEqual(
            {"label": "second-active"},
            coordinator.runtime_states["connection-2"]["currentState"],
        )

        self.assertFalse(coordinator.drop_runtime("connection-2", create_runtime))
        self.assertTrue(coordinator.drop_runtime("connection-1", create_runtime))
        self.assertEqual({"label": "new-3"}, coordinator.current_state)
        self.assertIsNone(coordinator.active_instance_id)

    def test_request_ids_are_bounded_and_independent_by_channel(self) -> None:
        coordinator = ConnectionCoordinator()

        self.assertEqual(1, coordinator.next_request_id("focusContext"))
        self.assertEqual(1, coordinator.next_request_id("clipboard"))
        self.assertEqual(2, coordinator.next_request_id("focusContext"))
        coordinator._request_ids["terminalControl"] = coordinator._REQUEST_ID_LIMIT - 1
        self.assertEqual(0, coordinator.next_request_id("terminalControl"))
        with self.assertRaisesRegex(ValueError, "unknown request channel"):
            coordinator.next_request_id("other")

    def test_pending_requests_are_bounded_correlated_and_discarded_by_instance(self) -> None:
        coordinator = ConnectionCoordinator()
        terminal = TerminalIdentity(10, 100)
        first = PendingControlRequest("connection-1", terminal, "copyTextRequest")
        second = PendingControlRequest("connection-2", terminal, "pasteTextRequest")
        third = PendingControlRequest("connection-1", terminal, "setRegisterRequest")

        self.assertEqual((), coordinator.remember_pending_request(
            "clipboard", 1, first, 2,
        ))
        self.assertEqual((), coordinator.remember_pending_request(
            "clipboard", 2, second, 2,
        ))
        self.assertEqual((1,), coordinator.remember_pending_request(
            "clipboard", 3, third, 2,
        ))
        self.assertIsNone(coordinator.take_pending_request("clipboard", 1))
        self.assertEqual(second, coordinator.take_pending_request("clipboard", 2))
        coordinator.remember_pending_request("clipboard", 4, second, 2)
        coordinator.discard_pending_requests("clipboard", "connection-1")
        self.assertEqual({4: second}, coordinator.pending_clipboard_requests)
        coordinator.discard_pending_requests("clipboard")
        self.assertEqual({}, coordinator.pending_clipboard_requests)

        with self.assertRaisesRegex(ValueError, "unknown pending request channel"):
            coordinator.take_pending_request("focusContext", 1)
        with self.assertRaisesRegex(ValueError, "invalid pending request"):
            coordinator.remember_pending_request("clipboard", True, first, 2)


if __name__ == "__main__":
    unittest.main()
