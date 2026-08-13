"""Bounded off-main-thread shutdown for managed transport clients."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _StopRequest:
	instance_id: str
	client: Any


class ClientStopper:
	"""Stop detached clients sequentially without waiting on NVDA's main thread."""

	def __init__(self, *, on_error: Callable[[str, Exception], None], max_pending: int = 128) -> None:
		if not callable(on_error) or not isinstance(max_pending, int) or max_pending < 1:
			raise ValueError("an error callback and positive queue bound are required")
		self._onError = on_error
		self._queue: queue.Queue[_StopRequest | None] = queue.Queue(maxsize=max_pending)
		self._closed = threading.Event()
		self._stateLock = threading.Lock()
		self._worker = threading.Thread(
			target=self._run,
			name="nvim-nvda-client-stop",
			daemon=True,
		)
		self._worker.start()

	def submit(self, instance_id: str, client: Any) -> bool:
		"""Queue a client already detached from canonical runtime state."""
		if not isinstance(instance_id, str) or not instance_id or client is None:
			return False
		with self._stateLock:
			if self._closed.is_set():
				return False
			try:
				self._queue.put_nowait(_StopRequest(instance_id, client))
			except queue.Full:
				return False
		return True

	def close(self) -> bool:
		"""Finish already queued stop requests, without joining the worker."""
		with self._stateLock:
			if self._closed.is_set():
				return False
			self._closed.set()
			try:
				self._queue.put_nowait(None)
			except queue.Full:
				# The worker exits after observing closed once the bounded queue drains.
				pass
		return True

	def _run(self) -> None:
		while True:
			try:
				request = self._queue.get(timeout=0.1)
			except queue.Empty:
				if self._closed.is_set():
					return
				continue
			if request is None:
				return
			try:
				request.client.stop()
			except Exception as error:
				try:
					self._onError(request.instance_id, error)
				except Exception:
					pass
