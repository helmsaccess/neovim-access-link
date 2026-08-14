"""Generation-safe delivery onto NVDA's main thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class RuntimeScheduler:
	"""Own queued callbacks and delayed calls for one add-on runtime."""

	def __init__(
		self,
		*,
		queue_function: Callable[..., Any],
		event_queue: Any,
		call_later: Callable[..., Any],
		record_diagnostic: Callable[..., None],
	) -> None:
		if not all(callable(value) for value in (queue_function, call_later, record_diagnostic)):
			raise ValueError("scheduler callbacks are required")
		self._queueFunction = queue_function
		self._eventQueue = event_queue
		self._callLater = call_later
		self._recordDiagnostic = record_diagnostic
		self._pending: set[Any] = set()
		self._generation = 1
		self._closed = False

	@property
	def closed(self) -> bool:
		return self._closed

	def queue(self, callback: Callable[..., Any], *args: Any, immediate: bool = False) -> bool:
		"""Queue a callback for this generation without running it after close."""
		if self._closed or not callable(callback):
			return False
		generation = self._generation
		try:
			self._queueFunction(
				self._eventQueue,
				self._invoke,
				generation,
				callback,
				args,
				_immediate=immediate,
			)
		except Exception as error:
			self._recordDiagnostic(
				"runtimeQueueError",
				action=getattr(callback, "__name__", "unknown"),
				errorType=type(error).__name__,
				error=str(error),
			)
			return False
		return True

	def later(self, delay_ms: int, callback: Callable[..., Any], *args: Any) -> Any:
		"""Schedule and retain one delayed callback until it fires or close cancels it."""
		if self._closed or not callable(callback):
			return None
		generation = self._generation
		holder = {"pending": None, "fired": False}

		def invoke() -> None:
			holder["fired"] = True
			pending = holder["pending"]
			if pending is not None:
				self._pending.discard(pending)
			if self._closed or generation != self._generation:
				return
			self._recordDiagnostic(
				"delayedActionStarted",
				action=getattr(callback, "__name__", "unknown"),
			)
			self._invoke_callback(callback, args)

		try:
			pending = self._callLater(delay_ms, invoke)
		except Exception as error:
			self._recordDiagnostic(
				"delayedActionScheduleError",
				action=getattr(callback, "__name__", "unknown"),
				delayMs=delay_ms,
				errorType=type(error).__name__,
				error=str(error),
			)
			return None
		holder["pending"] = pending
		if pending is not None and not holder["fired"]:
			self._pending.add(pending)
		self._recordDiagnostic(
			"delayedActionScheduled",
			action=getattr(callback, "__name__", "unknown"),
			delayMs=delay_ms,
		)
		return pending

	def close(self) -> bool:
		"""Invalidate queued work and cancel every retained delayed callback."""
		if self._closed:
			return False
		self._closed = True
		self._generation += 1
		for pending in tuple(self._pending):
			try:
				pending.Stop()
			except Exception as error:
				self._recordDiagnostic(
					"runtimeCloseStepError",
					step="mainThreadCall",
					errorType=type(error).__name__,
					error=str(error),
				)
		self._pending.clear()
		return True

	def _invoke(
		self,
		generation: int,
		callback: Callable[..., Any],
		args: tuple[Any, ...],
	) -> None:
		if self._closed or generation != self._generation:
			return
		self._invoke_callback(callback, args)

	def _invoke_callback(
		self,
		callback: Callable[..., Any],
		args: tuple[Any, ...],
	) -> None:
		try:
			callback(*args)
		except Exception as error:
			self._recordDiagnostic(
				"runtimeCallbackError",
				action=getattr(callback, "__name__", "unknown"),
				errorType=type(error).__name__,
				error=str(error),
			)
