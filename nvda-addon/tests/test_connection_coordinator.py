from __future__ import annotations

import unittest

from nvim_nvda_core import (
    ConnectionCoordinator,
    ConnectionInstanceManager,
    PendingControlRequest,
    PendingFocusContext,
    SpeechPlanner,
    TerminalIdentity,
    remote_ssh_target,
)


class ConnectionCoordinatorTests(unittest.TestCase):
    def test_coordinators_do_not_share_connection_or_terminal_state(self) -> None:
        first = ConnectionCoordinator()
        second = ConnectionCoordinator()
        terminal = TerminalIdentity(10, 100)

        first.remembered_terminal_bindings.add(terminal)
        first.authenticated_instances.add("connection-1")
        first.terminal_passthrough["connection-1"] = True
        first.pending_focus_contexts["connection-1"] = PendingFocusContext(
            1, terminal,
        )
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
        coordinator.remember_focus_context("connection-1", 1, terminal)
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

    def test_discard_instance_tracking_removes_only_owned_instance_state(self) -> None:
        coordinator = ConnectionCoordinator()
        terminal = TerminalIdentity(10, 100)
        other_terminal = TerminalIdentity(11, 101)

        def create_runtime():
            return {
                "planner": SpeechPlanner(), "currentState": {}, "lastMode": None,
                "typedWord": [], "typedPosition": None, "menuDocumentation": "",
                "connected": False, "lastConnectionState": None,
                "transportCapabilities": frozenset(),
            }

        coordinator.active_client = object()
        coordinator.switch_runtime("connection-1", create_runtime)
        coordinator.runtime_states["connection-2"] = create_runtime()
        coordinator.authenticated_instances.update({"connection-1", "connection-2"})
        coordinator.terminal_passthrough.update({"connection-1": True, "connection-2": False})
        coordinator.pending_full_states.update({
            "connection-1": {"type": "fullState"},
            "connection-2": {"type": "fullState"},
        })
        coordinator.remember_offer_instances.update({"connection-1", "connection-2"})
        coordinator.remember_focus_context("connection-1", 1, terminal)
        coordinator.remember_focus_context("connection-2", 2, other_terminal)
        coordinator.pending_clipboard_requests[1] = PendingControlRequest(
            "connection-1", terminal, "copyTextRequest",
        )
        coordinator.pending_clipboard_requests[2] = PendingControlRequest(
            "connection-2", other_terminal, "copyTextRequest",
        )
        coordinator.pending_terminal_control_requests[3] = PendingControlRequest(
            "connection-1", terminal, "leaveTerminalInputRequest",
        )

        self.assertTrue(coordinator.discard_instance_tracking(
            "connection-1", create_runtime,
        ))

        self.assertIsNone(coordinator.active_client)
        self.assertIsNone(coordinator.active_instance_id)
        self.assertEqual({"connection-2"}, coordinator.authenticated_instances)
        self.assertEqual({"connection-2": False}, coordinator.terminal_passthrough)
        self.assertEqual(
            {"connection-2": {"type": "fullState"}},
            coordinator.pending_full_states,
        )
        self.assertEqual({"connection-2"}, coordinator.remember_offer_instances)
        self.assertEqual(
            {"connection-2": PendingFocusContext(2, other_terminal)},
            coordinator.pending_focus_contexts,
        )
        self.assertEqual({2}, set(coordinator.pending_clipboard_requests))
        self.assertEqual({}, coordinator.pending_terminal_control_requests)
        self.assertIn("connection-2", coordinator.runtime_states)

        with self.assertRaisesRegex(ValueError, "instance ID is required"):
            coordinator.discard_instance_tracking("", create_runtime)

    def test_instance_selection_and_focus_confirmation_preserve_fail_open_order(self) -> None:
        manager = ConnectionInstanceManager()
        coordinator = ConnectionCoordinator(manager)
        terminal = TerminalIdentity(10, 100)
        class Client:
            def start(self):
                pass

        client = Client()
        instance = manager.add_target(
            remote_ssh_target("target", "Target"), "session", "One", client,
        )

        def create_runtime():
            return {
                "planner": SpeechPlanner(), "currentState": {}, "lastMode": None,
                "typedWord": [], "typedPosition": None, "menuDocumentation": "",
                "connected": False, "lastConnectionState": None,
                "transportCapabilities": frozenset(),
            }

        selected = coordinator.prepare_unconfirmed_instance(
            instance.identifier, terminal, create_runtime, trusted=True,
        )
        self.assertIs(client, selected)
        self.assertIs(client, coordinator.active_client)
        self.assertTrue(coordinator.connected)
        self.assertEqual(terminal, coordinator.gate.focused)
        self.assertFalse(coordinator.gate.suppression_active)

        coordinator.terminal_passthrough[instance.identifier] = True
        confirmed = coordinator.confirm_foreground_instance(
            instance.identifier, terminal, create_runtime,
        )
        self.assertIs(client, confirmed)
        self.assertEqual(terminal, coordinator.gate.bound_terminal)
        self.assertTrue(coordinator.gate.authenticated)
        self.assertTrue(coordinator.gate.nvim_active)
        self.assertTrue(coordinator.gate.terminal_passthrough)

        with self.assertRaisesRegex(ValueError, "terminal identity is required"):
            coordinator.select_instance(instance.identifier, None, create_runtime)

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

    def test_focus_contexts_are_correlated_and_discarded_by_instance(self) -> None:
        coordinator = ConnectionCoordinator()
        terminal = TerminalIdentity(10, 100)
        other_terminal = TerminalIdentity(11, 101)

        coordinator.remember_focus_context("connection-1", 1, terminal)
        self.assertTrue(coordinator.matches_focus_context(
            "connection-1", 1, terminal,
        ))
        self.assertFalse(coordinator.matches_focus_context(
            "connection-1", 2, terminal,
        ))
        self.assertFalse(coordinator.matches_focus_context(
            "connection-1", 1, other_terminal,
        ))
        self.assertFalse(coordinator.matches_focus_context(
            "connection-1", None, terminal,
        ))
        coordinator.remember_focus_context("connection-2", 2, other_terminal)
        coordinator.discard_focus_context("connection-1")
        self.assertEqual(
            {"connection-2": PendingFocusContext(2, other_terminal)},
            coordinator.pending_focus_contexts,
        )
        coordinator.discard_focus_context()
        self.assertEqual({}, coordinator.pending_focus_contexts)

        with self.assertRaisesRegex(ValueError, "instance ID is required"):
            coordinator.remember_focus_context("", 1, terminal)
        with self.assertRaisesRegex(ValueError, "valid pending focus context"):
            coordinator.remember_focus_context("connection-1", True, terminal)


if __name__ == "__main__":
    unittest.main()
