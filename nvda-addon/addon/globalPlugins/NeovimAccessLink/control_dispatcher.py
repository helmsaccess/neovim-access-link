"""Bounded background delivery for controls that may perform transport I/O."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Control:
	client: Any
	kind: str
	payload: Mapping[str, Any]


class ControlDispatcher:
	"""Deliver fixed controls off NVDA's main thread without an unbounded queue."""

	def __init__(
		self,
		*,
		on_result: Callable[[str, int | None, bool, str | None], None],
		max_pending: int = 64,
	) -> None:
		if not callable(on_result) or not isinstance(max_pending, int) or max_pending < 1:
			raise ValueError("a result callback and positive queue bound are required")
		self._onResult = on_result
		self._queue: queue.Queue[_Control | None] = queue.Queue(maxsize=max_pending)
		self._closed = threading.Event()
		self._worker = threading.Thread(
			target=self._run,
			name="nvim-nvda-control-dispatch",
			daemon=True,
		)
		self._worker.start()

	def submit(self, client: Any, kind: str, payload: Mapping[str, Any]) -> bool:
		"""Queue one immutable control immediately, returning False when unavailable."""
		if self._closed.is_set() or client is None or not isinstance(kind, str) or not kind:
			return False
		try:
			self._queue.put_nowait(_Control(client, kind, dict(payload)))
		except (TypeError, ValueError, queue.Full):
			return False
		return True

	def close(self) -> bool:
		"""Stop accepting work without waiting on possibly blocked transport I/O."""
		if self._closed.is_set():
			return False
		self._closed.set()
		while True:
			try:
				self._queue.get_nowait()
			except queue.Empty:
				break
		try:
			self._queue.put_nowait(None)
		except queue.Full:
			pass
		return True

	def _run(self) -> None:
		while not self._closed.is_set():
			control = self._queue.get()
			if control is None or self._closed.is_set():
				return
			accepted = False
			error_type = None
			try:
				accepted = bool(control.client.send_control(control.kind, dict(control.payload)))
			except Exception as error:
				error_type = type(error).__name__
			try:
				request_id = control.payload.get("requestId")
				request_id = request_id if isinstance(request_id, int) else None
				self._onResult(control.kind, request_id, accepted, error_type)
			except Exception:
				pass
