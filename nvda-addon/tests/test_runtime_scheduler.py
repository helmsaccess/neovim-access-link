from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = (
	pathlib.Path(__file__).parents[1]
	/ "addon"
	/ "globalPlugins"
	/ "NeovimAccessLink"
	/ "runtime_scheduler.py"
)


def load_scheduler():
	spec = importlib.util.spec_from_file_location("nvim_nvda_runtime_scheduler_test", MODULE_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError("could not load the runtime scheduler")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module.RuntimeScheduler


class _PendingCall:
	def __init__(self, callback) -> None:
		self.callback = callback
		self.stopped = False

	def Stop(self) -> None:
		self.stopped = True


class RuntimeSchedulerTests(unittest.TestCase):
	def test_queued_callback_is_invalidated_by_close(self) -> None:
		RuntimeScheduler = load_scheduler()
		queued = []
		diagnostics = []

		def queue_function(event_queue, callback, *args, **kwargs):
			queued.append((event_queue, callback, args, kwargs))

		scheduler = RuntimeScheduler(
			queue_function=queue_function,
			event_queue=object(),
			call_later=lambda *_args: None,
			record_diagnostic=lambda category, **fields: diagnostics.append((category, fields)),
		)
		calls = []
		self.assertTrue(scheduler.queue(calls.append, "queued", immediate=True))
		self.assertTrue(scheduler.close())
		_ignored_queue, callback, args, kwargs = queued[0]
		self.assertTrue(kwargs["_immediate"])
		callback(*args)
		self.assertEqual([], calls)
		self.assertFalse(scheduler.queue(calls.append, "late"))
		self.assertFalse(scheduler.close())

	def test_delayed_callbacks_are_owned_until_fire_or_close(self) -> None:
		RuntimeScheduler = load_scheduler()
		pending = []
		diagnostics = []

		def call_later(_delay, callback):
			pending.append(_PendingCall(callback))
			return pending[-1]

		scheduler = RuntimeScheduler(
			queue_function=lambda *_args, **_kwargs: None,
			event_queue=object(),
			call_later=call_later,
			record_diagnostic=lambda category, **fields: diagnostics.append((category, fields)),
		)
		calls = []
		first = scheduler.later(25, calls.append, "first")
		first.callback()
		second = scheduler.later(50, calls.append, "second")
		self.assertEqual(["first"], calls)
		self.assertTrue(scheduler.close())
		self.assertFalse(first.stopped)
		self.assertTrue(second.stopped)
		second.callback()
		self.assertEqual(["first"], calls)
		self.assertEqual(
			["delayedActionScheduled", "delayedActionStarted", "delayedActionScheduled"],
			[category for category, _fields in diagnostics],
		)

	def test_nvda_queue_and_timer_failures_are_contained(self) -> None:
		RuntimeScheduler = load_scheduler()
		diagnostics = []
		scheduler = RuntimeScheduler(
			queue_function=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("queue")),
			event_queue=object(),
			call_later=lambda *_args: (_ for _ in ()).throw(RuntimeError("timer")),
			record_diagnostic=lambda category, **fields: diagnostics.append((category, fields)),
		)
		self.assertFalse(scheduler.queue(lambda: None))
		self.assertIsNone(scheduler.later(10, lambda: None))
		self.assertEqual(
			["runtimeQueueError", "delayedActionScheduleError"], [item[0] for item in diagnostics]
		)
		scheduler.close()

	def test_callback_failures_and_synchronous_timer_delivery_are_contained(self) -> None:
		RuntimeScheduler = load_scheduler()
		queued = []
		diagnostics = []

		def queue_function(_event_queue, callback, *args, **_kwargs):
			queued.append((callback, args))

		def call_later(_delay, callback):
			pending = _PendingCall(callback)
			callback()
			return pending

		def fail():
			raise RuntimeError("callback")

		scheduler = RuntimeScheduler(
			queue_function=queue_function,
			event_queue=object(),
			call_later=call_later,
			record_diagnostic=lambda category, **fields: diagnostics.append((category, fields)),
		)
		self.assertTrue(scheduler.queue(fail))
		queued[0][0](*queued[0][1])
		pending = scheduler.later(0, fail)
		self.assertTrue(scheduler.close())
		self.assertFalse(pending.stopped)
		self.assertEqual(
			[
				"runtimeCallbackError",
				"delayedActionStarted",
				"runtimeCallbackError",
				"delayedActionScheduled",
			],
			[category for category, _fields in diagnostics],
		)


if __name__ == "__main__":
	unittest.main()
