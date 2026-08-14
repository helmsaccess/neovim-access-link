from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
import unittest


MODULE_PATH = (
	pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink" / "managed_clients.py"
)


def load_factory():
	spec = importlib.util.spec_from_file_location("nvim_nvda_managed_clients_test", MODULE_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the managed client factory")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module.ManagedClientFactory


class _Client:
	pass


class ManagedClientFactoryTests(unittest.TestCase):
	def setUp(self) -> None:
		self.callbacks = {}
		self.events = []
		self.states = []
		self.diagnostics = []

	def _factory(self, local_constructor, remote_constructor):
		return load_factory()(
			local_client_constructor=local_constructor,
			ssh_client_constructor=remote_constructor,
			on_event=lambda instance_id, event: self.events.append((instance_id, event)),
			on_state=lambda instance_id, state: self.states.append((instance_id, state)),
			record_network_diagnostic=lambda category, fields: self.diagnostics.append((category, fields)),
		)

	def test_local_callbacks_are_correlated_after_instance_assignment(self) -> None:
		def local_constructor(host, port, on_event, on_state, **kwargs):
			self.callbacks.update(
				host=host,
				port=port,
				on_event=on_event,
				on_state=on_state,
				on_diagnostic=kwargs["on_diagnostic"],
				session_nonce=kwargs["session_nonce"],
			)
			return _Client()

		factory = self._factory(local_constructor, lambda *_args, **_kwargs: _Client())
		session = types.SimpleNamespace(host="127.0.0.1", port=45678, session_nonce="a" * 32)
		client = factory.create_local(session)
		self.callbacks["on_event"]({"type": "preAssignment"})
		client.nvim_nvda_instance_id = "connection-7"
		self.callbacks["on_event"]({"type": "fullState"})
		self.callbacks["on_state"]("connected")
		self.callbacks["on_diagnostic"]("transport", {"attempt": 1})

		self.assertEqual(
			("127.0.0.1", 45678, "a" * 32),
			(
				self.callbacks["host"],
				self.callbacks["port"],
				self.callbacks["session_nonce"],
			),
		)
		self.assertEqual(
			[(None, {"type": "preAssignment"}), ("connection-7", {"type": "fullState"})],
			self.events,
		)
		self.assertEqual([("connection-7", "connected")], self.states)
		self.assertEqual(
			[("transport", {"attempt": 1, "instanceId": "connection-7"})],
			self.diagnostics,
		)

	def test_remote_constructor_receives_profile_and_authentication_ports(self) -> None:
		def remote_constructor(target, on_event, on_state, **kwargs):
			self.callbacks.update(
				target=target,
				on_event=on_event,
				on_state=on_state,
				**kwargs,
			)
			return _Client()

		factory = self._factory(lambda *_args, **_kwargs: _Client(), remote_constructor)
		profile = types.SimpleNamespace(
			ssh_target="user@example.test",
			port=2222,
			identity_file="key-file",
		)
		client = factory.create_remote(
			profile,
			"session-9",
			password="secret",
			askpass_path="askpass.cmd",
		)
		client.nvim_nvda_instance_id = "connection-9"
		self.callbacks["on_state"]("connected")

		self.assertEqual("user@example.test", self.callbacks["target"])
		self.assertEqual(2222, self.callbacks["ssh_port"])
		self.assertEqual("key-file", self.callbacks["identity_file"])
		self.assertEqual("session-9", self.callbacks["session_id"])
		self.assertEqual("secret", self.callbacks["password"])
		self.assertEqual("askpass.cmd", self.callbacks["askpass_path"])
		self.assertEqual([("connection-9", "connected")], self.states)


if __name__ == "__main__":
	unittest.main()
