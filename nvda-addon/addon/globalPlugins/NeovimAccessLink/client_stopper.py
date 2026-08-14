"""Owned off-main-thread shutdown for managed transport clients."""

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
	"""Own every accepted detached client and stop it with fixed parallelism."""

	def __init__(self, *, on_error: Callable[[str, Exception], None], worker_count: int = 4) -> None:
		if not callable(on_error) or not isinstance(worker_count, int) or worker_count < 1:
			raise ValueError("an error callback and positive worker count are required")
		self._onError = on_error
		self._queue: queue.Queue[_StopRequest | None] = queue.Queue()
		self._closed = threading.Event()
		self._stateLock = threading.Lock()
		self._workers = tuple(
			threading.Thread(
				target=self._run,
				name="nvim-nvda-client-stop",
				daemon=True,
			)
			for _worker_index in range(worker_count)
		)
		for worker in self._workers:
			worker.start()

	def submit(self, instance_id: str, client: Any) -> bool:
		"""Transfer ownership of one detached client to the shutdown workers."""
		if not isinstance(instance_id, str) or not instance_id or client is None:
			return False
		with self._stateLock:
			if self._closed.is_set():
				return False
			self._queue.put_nowait(_StopRequest(instance_id, client))
		return True

	def close(self) -> bool:
		"""Finish already accepted stop requests, without joining the workers."""
		with self._stateLock:
			if self._closed.is_set():
				return False
			self._closed.set()
			for _worker in self._workers:
				self._queue.put_nowait(None)
		return True

	def _run(self) -> None:
		while True:
			request = self._queue.get()
			if request is None:
				return
			try:
				request.client.stop()
			except Exception as error:
				try:
					self._onError(request.instance_id, error)
				except Exception:
					pass
