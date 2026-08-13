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
	client_id: int
	kind: str
	payload: Mapping[str, Any]
	cancelled: threading.Event
	on_result: Callable[[bool, str | None], None] | None = None


class ControlDispatcher:
	"""Deliver fixed controls off NVDA's main thread without an unbounded queue."""

	def __init__(
		self,
		*,
		on_result: Callable[..., None],
		max_pending: int = 64,
	) -> None:
		if not callable(on_result) or not isinstance(max_pending, int) or max_pending < 1:
			raise ValueError("a result callback and positive queue bound are required")
		self._onResult = on_result
		self._queue: queue.Queue[_Control | None] = queue.Queue(maxsize=max_pending)
		self._closed = threading.Event()
		self._stateLock = threading.Lock()
		self._pendingByClient: dict[int, set[threading.Event]] = {}
		self._worker = threading.Thread(
			target=self._run,
			name="nvim-nvda-control-dispatch",
			daemon=True,
		)
		self._worker.start()

	def submit(
		self,
		client: Any,
		kind: str,
		payload: Mapping[str, Any],
		*,
		on_result: Callable[[bool, str | None], None] | None = None,
	) -> bool:
		"""Queue one immutable control immediately, returning False when unavailable."""
		if (
			client is None
			or not isinstance(kind, str)
			or not kind
			or (on_result is not None and not callable(on_result))
		):
			return False
		with self._stateLock:
			if self._closed.is_set():
				return False
			try:
				client_id = id(client)
				cancelled = threading.Event()
				control = _Control(client, client_id, kind, dict(payload), cancelled, on_result)
				self._queue.put_nowait(control)
				self._pendingByClient.setdefault(client_id, set()).add(cancelled)
			except (TypeError, ValueError, queue.Full):
				return False
		return True

	def discard_client(self, client: Any) -> bool:
		"""Invalidate controls for one detached client without waiting for its transport."""
		if client is None:
			return False
		with self._stateLock:
			pending = tuple(self._pendingByClient.get(id(client), ()))
			for cancelled in pending:
				cancelled.set()
		return bool(pending)

	def close(self) -> bool:
		"""Stop accepting work without waiting on possibly blocked transport I/O."""
		with self._stateLock:
			if self._closed.is_set():
				return False
			self._closed.set()
			while True:
				try:
					control = self._queue.get_nowait()
					if control is not None:
						control.cancelled.set()
				except queue.Empty:
					break
			self._pendingByClient.clear()
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
			error_type = "ControlDiscarded" if control.cancelled.is_set() else None
			if error_type is None:
				try:
					accepted = bool(control.client.send_control(control.kind, dict(control.payload)))
				except Exception as error:
					error_type = type(error).__name__
			with self._stateLock:
				pending = self._pendingByClient.get(control.client_id)
				if pending is not None:
					pending.discard(control.cancelled)
					if not pending:
						self._pendingByClient.pop(control.client_id, None)
			try:
				request_id = control.payload.get("requestId")
				request_id = request_id if isinstance(request_id, int) else None
				if control.on_result is None:
					self._onResult(control.kind, request_id, accepted, error_type)
				else:
					self._onResult(
						control.kind,
						request_id,
						accepted,
						error_type,
						control.on_result,
					)
			except Exception:
				pass
