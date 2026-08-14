"""Bounded background delivery for controls that may perform transport I/O."""

from __future__ import annotations

import queue
import threading
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class _Control:
	client: Any
	client_id: int
	kind: str
	payload: Mapping[str, Any]
	cancelled: threading.Event
	on_result: Callable[[bool, str | None], None] | None = None


@dataclass
class _ClientLane:
	client: Any
	controls: deque[_Control] = field(default_factory=deque)
	running: bool = False
	scheduled: bool = False


class ControlDispatcher:
	"""Deliver controls in per-client order without coupling independent clients."""

	def __init__(
		self,
		*,
		on_result: Callable[..., None],
		max_pending: int = 64,
		worker_count: int = 4,
	) -> None:
		if (
			not callable(on_result)
			or not isinstance(max_pending, int)
			or max_pending < 1
			or not isinstance(worker_count, int)
			or worker_count < 1
		):
			raise ValueError("a result callback, positive queue bound, and worker count are required")
		self._onResult = on_result
		self._maxPending = max_pending
		self._readyClients: queue.Queue[int | None] = queue.Queue()
		self._closed = threading.Event()
		self._stateLock = threading.Lock()
		self._lanes: dict[int, _ClientLane] = {}
		self._pendingCount = 0
		self._workers = tuple(
			threading.Thread(
				target=self._run,
				name="nvim-nvda-control-dispatch",
				daemon=True,
			)
			for _worker_index in range(worker_count)
		)
		for worker in self._workers:
			worker.start()

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
		try:
			client_id = id(client)
			control = _Control(
				client,
				client_id,
				kind,
				dict(payload),
				threading.Event(),
				on_result,
			)
		except (TypeError, ValueError):
			return False
		with self._stateLock:
			if self._closed.is_set() or self._pendingCount >= self._maxPending:
				return False
			lane = self._lanes.get(client_id)
			if lane is None:
				lane = _ClientLane(client)
				self._lanes[client_id] = lane
			elif lane.client is not client:
				return False
			lane.controls.append(control)
			self._pendingCount += 1
			if not lane.running and not lane.scheduled:
				lane.scheduled = True
				self._readyClients.put_nowait(client_id)
		return True

	def discard_client(self, client: Any) -> bool:
		"""Invalidate controls for one detached client without waiting for its transport."""
		if client is None:
			return False
		with self._stateLock:
			lane = self._lanes.get(id(client))
			if lane is None or lane.client is not client:
				return False
			for control in lane.controls:
				control.cancelled.set()
			return bool(lane.controls) or lane.running

	def close(self) -> bool:
		"""Stop accepting work without waiting on possibly blocked transport I/O."""
		with self._stateLock:
			if self._closed.is_set():
				return False
			self._closed.set()
			for client_id, lane in tuple(self._lanes.items()):
				for control in lane.controls:
					control.cancelled.set()
				self._pendingCount -= len(lane.controls)
				lane.controls.clear()
				lane.scheduled = False
				if not lane.running:
					self._lanes.pop(client_id, None)
			while True:
				try:
					self._readyClients.get_nowait()
				except queue.Empty:
					break
			for _worker in self._workers:
				self._readyClients.put_nowait(None)
		return True

	def _run(self) -> None:
		while True:
			client_id = self._readyClients.get()
			if client_id is None:
				return
			with self._stateLock:
				lane = self._lanes.get(client_id)
				if lane is None:
					continue
				lane.scheduled = False
				if self._closed.is_set() or not lane.controls:
					if not lane.running:
						self._lanes.pop(client_id, None)
					continue
				control = lane.controls.popleft()
				lane.running = True
			accepted = False
			error_type = "ControlDiscarded" if control.cancelled.is_set() else None
			if error_type is None:
				try:
					accepted = bool(control.client.send_control(control.kind, dict(control.payload)))
				except Exception as error:
					error_type = type(error).__name__
			self._deliver_result(control, accepted, error_type)
			with self._stateLock:
				self._pendingCount -= 1
				lane = self._lanes.get(client_id)
				if lane is None or lane.client is not control.client:
					continue
				lane.running = False
				if self._closed.is_set() or not lane.controls:
					self._lanes.pop(client_id, None)
				elif not lane.scheduled:
					lane.scheduled = True
					self._readyClients.put_nowait(client_id)

	def _deliver_result(self, control: _Control, accepted: bool, error_type: str | None) -> None:
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
