from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import unittest


MODULE_PATH = (
	pathlib.Path(__file__).parents[1]
	/ "addon"
	/ "globalPlugins"
	/ "NeovimAccessLink"
	/ "control_dispatcher.py"
)


def load_dispatcher():
	spec = importlib.util.spec_from_file_location("nvim_nvda_control_dispatcher_test", MODULE_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the control dispatcher")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module.ControlDispatcher


class ControlDispatcherTests(unittest.TestCase):
	def test_controls_run_on_bounded_worker_and_payload_is_copied(self) -> None:
		ControlDispatcher = load_dispatcher()

		completed = threading.Event()
		calls = []
		results = []

		class Client:
			def send_control(self, kind, payload):
				calls.append((threading.current_thread().name, kind, payload))
				completed.set()
				return True

		dispatcher = ControlDispatcher(
			on_result=lambda *result: results.append(result),
			max_pending=1,
		)
		payload = {"requestId": 1}
		self.assertTrue(dispatcher.submit(Client(), "exploreTextRequest", payload))
		payload["requestId"] = 99
		self.assertTrue(completed.wait(1.0))
		self.assertEqual(("nvim-nvda-control-dispatch", "exploreTextRequest", {"requestId": 1}), calls[0])
		self.assertEqual(("exploreTextRequest", 1, True, None), results[0])
		self.assertTrue(dispatcher.close())
		self.assertFalse(dispatcher.submit(Client(), "exploreTextRequest", payload))
		self.assertFalse(dispatcher.close())

	def test_transport_failure_is_contained(self) -> None:
		ControlDispatcher = load_dispatcher()

		completed = threading.Event()
		results = []

		class Client:
			def send_control(self, _kind, _payload):
				raise OSError("closed")

		dispatcher = ControlDispatcher(
			on_result=lambda *result: (results.append(result), completed.set()),
		)
		self.assertTrue(dispatcher.submit(Client(), "endExplorationRequest", {"requestId": 7}))
		self.assertTrue(completed.wait(1.0))
		self.assertEqual(("endExplorationRequest", 7, False, "OSError"), results[0])
		dispatcher.close()


if __name__ == "__main__":
	unittest.main()
