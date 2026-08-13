"""Main-thread completion handling for outbound transport controls."""

from __future__ import annotations


class ControlResultDelivery:
	"""Correlate dispatcher results with one live runtime generation."""

	def __init__(self, *, scheduler, editor_session, diagnostics) -> None:
		self._scheduler = scheduler
		self._editorSession = editor_session
		self._diagnostics = diagnostics

	def __call__(self, kind, request_id, accepted, error_type, completion=None) -> None:
		self._scheduler.queue(
			self._deliver,
			kind,
			request_id,
			accepted,
			error_type,
			completion,
		)

	def rejected(self, kind, payload, completion=None) -> None:
		"""Deliver immediate bounded-queue rejection through the same contract."""
		request_id = payload.get("requestId")
		self._deliver(
			kind,
			request_id if isinstance(request_id, int) else None,
			False,
			"QueueUnavailable",
			completion,
		)

	def _deliver(self, kind, request_id, accepted, error_type, completion) -> None:
		self._diagnostics.record(
			"controlDispatched",
			type=kind,
			requestId=request_id,
			accepted=accepted,
			errorType=error_type,
		)
		if not accepted and kind == "exploreTextRequest" and isinstance(request_id, int):
			self._editorSession.fail_exploration_request(request_id)
		if not accepted and kind == "brailleExploreLineRequest" and isinstance(request_id, int):
			self._editorSession.fail_braille_exploration_request(request_id)
		if completion is not None:
			completion(accepted, error_type)
