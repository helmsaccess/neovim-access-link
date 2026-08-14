from __future__ import annotations

import threading
import time

import pexpect


def drain_tui_output(
	process,
	*,
	byte_limit: int = 8 * 1024 * 1024,
	time_limit: float = 1.0,
) -> None:
	deadline = time.monotonic() + time_limit
	drained = 0
	try:
		while True:
			if drained >= byte_limit:
				raise AssertionError(f"TUI output drain exceeded byte limit ({byte_limit} bytes)")
			remaining = deadline - time.monotonic()
			if remaining <= 0:
				raise AssertionError(f"TUI output drain exceeded time limit ({time_limit:.3f} seconds)")
			chunk = process.read_nonblocking(
				min(65536, byte_limit - drained),
				timeout=min(0.01, remaining),
			)
			if not chunk:
				return
			drained += len(chunk)
	except (pexpect.TIMEOUT, pexpect.EOF):
		return


class RecordingTransport:
	"""Record semantic bridge output without reintroducing the removed TCP protocol."""

	def __init__(self) -> None:
		self.events: list[dict] = []
		self.condition = threading.Condition()

	def start(self) -> None:
		pass

	def stop(self) -> None:
		pass

	def publish(self, event_type: str, payload: dict) -> bool:
		with self.condition:
			self.events.append({"type": event_type, "payload": payload})
			self.condition.notify_all()
		return True
