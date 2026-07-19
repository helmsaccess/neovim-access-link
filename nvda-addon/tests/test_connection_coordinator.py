from __future__ import annotations

import unittest

from nvim_nvda_core import ConnectionCoordinator, ConnectionInstanceManager, TerminalIdentity


class ConnectionCoordinatorTests(unittest.TestCase):
    def test_coordinators_do_not_share_connection_or_terminal_state(self) -> None:
        first = ConnectionCoordinator()
        second = ConnectionCoordinator()
        terminal = TerminalIdentity(10, 100)

        first.remembered_terminal_bindings.add(terminal)
        first.authenticated_instances.add("connection-1")
        first.terminal_passthrough["connection-1"] = True

        self.assertIsInstance(first.instances, ConnectionInstanceManager)
        self.assertIsNot(first.instances, second.instances)
        self.assertEqual(set(), second.remembered_terminal_bindings)
        self.assertEqual(set(), second.authenticated_instances)
        self.assertEqual({}, second.terminal_passthrough)

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

    def test_runtime_switches_preserve_each_instance_and_drop_active_state(self) -> None:
        coordinator = ConnectionCoordinator()
        created = []

        def create_runtime():
            runtime = {"label": f"new-{len(created) + 1}"}
            created.append(runtime)
            return runtime

        first = coordinator.switch_runtime("connection-1", {"label": "initial"}, create_runtime)
        self.assertEqual({"label": "new-1"}, first)
        self.assertIsNone(coordinator.switch_runtime(
            "connection-1", {"label": "ignored"}, create_runtime,
        ))
        second = coordinator.switch_runtime(
            "connection-2", {"label": "first-active"}, create_runtime,
        )
        self.assertEqual({"label": "new-2"}, second)
        self.assertEqual(
            {"label": "first-active"}, coordinator.runtime_states["connection-1"],
        )
        restored = coordinator.switch_runtime(
            "connection-1", {"label": "second-active"}, create_runtime,
        )
        self.assertEqual({"label": "first-active"}, restored)
        self.assertEqual(
            {"label": "second-active"}, coordinator.runtime_states["connection-2"],
        )

        self.assertIsNone(coordinator.drop_runtime("connection-2", create_runtime))
        blank = coordinator.drop_runtime("connection-1", create_runtime)
        self.assertEqual({"label": "new-3"}, blank)
        self.assertIsNone(coordinator.active_instance_id)


if __name__ == "__main__":
    unittest.main()
