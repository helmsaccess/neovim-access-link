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
CONTROL_RESULTS_PATH = MODULE_PATH.with_name("control_results.py")
RUNTIME_SCHEDULER_PATH = MODULE_PATH.with_name("runtime_scheduler.py")


def load_dispatcher():
	spec = importlib.util.spec_from_file_location("nvim_nvda_control_dispatcher_test", MODULE_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the control dispatcher")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module.ControlDispatcher


def load_class(path, module_name, class_name):
	spec = importlib.util.spec_from_file_location(module_name, path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"could not load {class_name}")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return getattr(module, class_name)


class ControlDispatcherTests(unittest.TestCase):
	def test_controls_run_on_bounded_worker_and_payload_is_copied(self) -> None:
		ControlDispatcher = load_dispatcher()

		completed = threading.Event()
		calls = []
		results = []

		class Client:
			def send_control(self, kind, payload):
				calls.append((threading.current_thread().name, kind, payload))
				return True

		dispatcher = ControlDispatcher(
			on_result=lambda *result: (results.append(result), completed.set()),
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

		dispatcher = ControlDispatcher(on_result=on_result, worker_count=1)
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

	def test_blocked_client_does_not_delay_an_independent_client(self) -> None:
		ControlDispatcher = load_dispatcher()
		blocked = threading.Event()
		release = threading.Event()
		independent_completed = threading.Event()

		class BlockingClient:
			def send_control(self, _kind, _payload):
				blocked.set()
				release.wait(1.0)
				return True

		class IndependentClient:
			def send_control(self, _kind, _payload):
				independent_completed.set()
				return True

		dispatcher = ControlDispatcher(on_result=lambda *_result: None, worker_count=2)
		self.assertTrue(dispatcher.submit(BlockingClient(), "blocked", {}))
		self.assertTrue(blocked.wait(1.0))
		self.assertTrue(dispatcher.submit(IndependentClient(), "independent", {}))
		self.assertTrue(independent_completed.wait(0.5))
		release.set()
		dispatcher.close()

	def test_controls_for_one_client_remain_strictly_ordered(self) -> None:
		ControlDispatcher = load_dispatcher()
		first_started = threading.Event()
		release_first = threading.Event()
		second_completed = threading.Event()
		calls = []

		class Client:
			def send_control(self, kind, _payload):
				calls.append(kind)
				if kind == "first":
					first_started.set()
					release_first.wait(1.0)
				else:
					second_completed.set()
				return True

		client = Client()
		dispatcher = ControlDispatcher(on_result=lambda *_result: None, worker_count=2)
		self.assertTrue(dispatcher.submit(client, "first", {}))
		self.assertTrue(first_started.wait(1.0))
		self.assertTrue(dispatcher.submit(client, "second", {}))
		self.assertFalse(second_completed.wait(0.05))
		release_first.set()
		self.assertTrue(second_completed.wait(1.0))
		self.assertEqual(["first", "second"], calls)
		dispatcher.close()

	def test_worker_completion_waits_for_explicit_nvda_queue_drain(self) -> None:
		ControlDispatcher = load_dispatcher()
		ControlResultDelivery = load_class(
			CONTROL_RESULTS_PATH,
			"nvim_nvda_control_results_test",
			"ControlResultDelivery",
		)
		RuntimeScheduler = load_class(
			RUNTIME_SCHEDULER_PATH,
			"nvim_nvda_runtime_scheduler_integration_test",
			"RuntimeScheduler",
		)
		queued = []
		diagnostics = []
		sent = threading.Event()
		completions = []
		main_thread_name = threading.current_thread().name

		class EditorSession:
			def fail_exploration_request(self, _request_id):
				raise AssertionError("successful controls must not fail exploration")

			def fail_braille_exploration_request(self, _request_id):
				raise AssertionError("successful controls must not fail Braille exploration")

		class Client:
			def send_control(self, _kind, _payload):
				sent.set()
				return True

		def queue_function(_event_queue, callback, *args, **_kwargs):
			queued.append((callback, args))

		scheduler = RuntimeScheduler(
			queue_function=queue_function,
			event_queue=object(),
			call_later=lambda *_args: None,
			record_diagnostic=lambda category, **fields: diagnostics.append((category, fields)),
		)
		delivery = ControlResultDelivery(
			scheduler=scheduler,
			editor_session=EditorSession(),
			diagnostics=type(
				"Diagnostics",
				(),
				{"record": lambda _self, category, **fields: diagnostics.append((category, fields))},
			)(),
		)
		dispatcher = ControlDispatcher(on_result=delivery)
		self.assertTrue(
			dispatcher.submit(
				Client(),
				"requestFullState",
				{},
				on_result=lambda accepted, error: completions.append(
					(threading.current_thread().name, accepted, error)
				),
			)
		)
		self.assertTrue(sent.wait(1.0))
		deadline = time.monotonic() + 1.0
		while not queued and time.monotonic() < deadline:
			time.sleep(0.005)
		self.assertEqual([], completions)
		self.assertEqual([], diagnostics)
		callback, args = queued.pop(0)
		callback(*args)
		self.assertEqual([(main_thread_name, True, None)], completions)
		self.assertEqual("controlDispatched", diagnostics[0][0])
		dispatcher.close()
		scheduler.close()


if __name__ == "__main__":
	unittest.main()
