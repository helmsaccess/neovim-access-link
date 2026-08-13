from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import time
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

	def test_correlated_completion_is_delivered_without_blocking_submit(self) -> None:
		ControlDispatcher = load_dispatcher()
		started = threading.Event()
		release = threading.Event()
		completed = threading.Event()
		global_results = []
		request_results = []

		class Client:
			def send_control(self, _kind, _payload):
				started.set()
				release.wait(1.0)
				return True

		def on_result(*result):
			global_results.append(result)
			callback = result[-1]
			callback(result[2], result[3])

		dispatcher = ControlDispatcher(on_result=on_result)
		before = time.monotonic()
		self.assertTrue(
			dispatcher.submit(
				Client(),
				"clipboardSetRequest",
				{"requestId": 19},
				on_result=lambda *result: (request_results.append(result), completed.set()),
			)
		)
		self.assertLess(time.monotonic() - before, 0.1)
		self.assertTrue(started.wait(1.0))
		release.set()
		self.assertTrue(completed.wait(1.0))
		self.assertEqual((True, None), request_results[0])
		self.assertEqual(("clipboardSetRequest", 19, True, None), global_results[0][:4])
		dispatcher.close()

	def test_detached_client_controls_are_discarded_before_transport(self) -> None:
		ControlDispatcher = load_dispatcher()
		started = threading.Event()
		release = threading.Event()
		completed = threading.Event()
		results = []

		class BlockingClient:
			def send_control(self, _kind, _payload):
				started.set()
				release.wait(1.0)
				return True

		class DetachedClient:
			def __init__(self):
				self.calls = []

			def send_control(self, kind, payload):
				self.calls.append((kind, payload))
				return True

		def on_result(*result):
			results.append(result)
			if len(results) == 2:
				completed.set()

		dispatcher = ControlDispatcher(on_result=on_result)
		detached = DetachedClient()
		self.assertTrue(dispatcher.submit(BlockingClient(), "first", {}))
		self.assertTrue(started.wait(1.0))
		self.assertTrue(dispatcher.submit(detached, "requestFullState", {}))
		self.assertTrue(dispatcher.discard_client(detached))
		release.set()
		self.assertTrue(completed.wait(1.0))
		self.assertEqual([], detached.calls)
		self.assertEqual(("requestFullState", None, False, "ControlDiscarded"), results[-1])
		self.assertFalse(dispatcher.discard_client(detached))
		dispatcher.close()


if __name__ == "__main__":
	unittest.main()
