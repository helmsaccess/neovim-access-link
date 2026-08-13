from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import time
import unittest


MODULE_PATH = (
	pathlib.Path(__file__).parents[1] / "addon" / "globalPlugins" / "NeovimAccessLink" / "client_stopper.py"
)


def load_stopper():
	spec = importlib.util.spec_from_file_location("nvim_nvda_client_stopper_test", MODULE_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the client stopper")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module.ClientStopper


class ClientStopperTests(unittest.TestCase):
	def test_submit_and_close_never_wait_for_blocked_client_stop(self) -> None:
		ClientStopper = load_stopper()
		started = threading.Event()
		release = threading.Event()
		finished = threading.Event()

		class Client:
			def stop(self):
				started.set()
				release.wait(1.0)
				finished.set()

		stopper = ClientStopper(on_error=lambda *_args: None)
		before = time.monotonic()
		self.assertTrue(stopper.submit("instance-1", Client()))
		self.assertLess(time.monotonic() - before, 0.1)
		self.assertTrue(started.wait(1.0))
		before = time.monotonic()
		self.assertTrue(stopper.close())
		self.assertLess(time.monotonic() - before, 0.1)
		self.assertFalse(stopper.submit("instance-2", Client()))
		release.set()
		self.assertTrue(finished.wait(1.0))
		self.assertFalse(stopper.close())

	def test_queue_is_bounded_and_stop_errors_are_contained(self) -> None:
		ClientStopper = load_stopper()
		started = threading.Event()
		release = threading.Event()
		errors = []

		class BlockingClient:
			def stop(self):
				started.set()
				release.wait(1.0)

		class FailingClient:
			def stop(self):
				raise OSError("closed")

		stopper = ClientStopper(
			on_error=lambda instance_id, error: errors.append((instance_id, type(error).__name__)),
			max_pending=1,
		)
		self.assertTrue(stopper.submit("blocking", BlockingClient()))
		self.assertTrue(started.wait(1.0))
		self.assertTrue(stopper.submit("failing", FailingClient()))
		self.assertFalse(stopper.submit("overflow", FailingClient()))
		release.set()
		deadline = time.monotonic() + 1.0
		while not errors and time.monotonic() < deadline:
			time.sleep(0.005)
		self.assertEqual([("failing", "OSError")], errors)
		stopper.close()


if __name__ == "__main__":
	unittest.main()
