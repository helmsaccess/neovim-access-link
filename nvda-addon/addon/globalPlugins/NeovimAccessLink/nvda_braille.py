"""NVDA Braille regions and overlays for structured Neovim state."""

from __future__ import annotations

from dataclasses import replace

import braille as nvdaBraille
import config
import core

from .core.braille import BraillePlan, plan_braille, source_offset_for_expanded
from .service_registry import getTerminalIntegrationService


def capture_structured_viewport(handler: object) -> int | None:
	"""Read the public NVDA Braille-window offset for our active structured region."""
	try:
		if handler.getTether() != "focus":
			return None
	except Exception:
		return None
	main_buffer = getattr(handler, "mainBuffer", None)
	if main_buffer is None or getattr(handler, "buffer", None) is not main_buffer:
		return None
	regions = getattr(main_buffer, "regions", ())
	if not regions or not isinstance(regions[-1], StructuredLineRegion):
		return None
	start_position = getattr(main_buffer, "windowStartPos", None)
	return (
		start_position
		if isinstance(start_position, int) and not isinstance(start_position, bool) and start_position >= 0
		else None
	)


def restore_structured_viewport(handler: object, start_position: int) -> bool:
	"""Restore a saved public NVDA Braille-window offset after a focus rebuild."""
	if not isinstance(start_position, int) or isinstance(start_position, bool) or start_position < 0:
		return False
	try:
		if handler.getTether() != "focus":
			return False
	except Exception:
		return False
	main_buffer = getattr(handler, "mainBuffer", None)
	if main_buffer is None or getattr(handler, "buffer", None) is not main_buffer:
		return False
	regions = getattr(main_buffer, "regions", ())
	if not regions or not isinstance(regions[-1], StructuredLineRegion):
		return False
	cells = getattr(main_buffer, "brailleCells", None)
	if not isinstance(cells, (list, tuple)):
		return False
	if not cells:
		restored_position = 0
	else:
		restored_position = min(start_position, len(cells) - 1)
	try:
		main_buffer.windowStartPos = restored_position
		handler.update()
	except Exception:
		return False
	return True


def numbered_choice_message_text(
	text: str,
	*,
	start_cell: int,
	display_size: int,
) -> str:
	"""Position a transient choice using the active NVDA Braille translation."""
	if (
		not text
		or not isinstance(start_cell, int)
		or isinstance(start_cell, bool)
		or not isinstance(display_size, int)
		or isinstance(display_size, bool)
		or start_cell <= 1
		or start_cell > display_size
	):
		return text
	try:
		region = nvdaBraille.Region()
		region.rawText = text
		region.update()
		content_cell_count = len(region.brailleCells)
	except Exception:
		return text
	if content_cell_count <= 0:
		return text
	last_complete_start = max(1, display_size - content_cell_count + 1)
	actual_start = min(start_cell, last_complete_start)
	return (" " * (actual_start - 1)) + text


def present_numbered_choice_message(text: str, *, start_cell: int) -> object | None:
	"""Show a choice through NVDA's immediate transient Braille-message path."""
	handler = nvdaBraille.handler
	previous_message_buffer = getattr(handler, "messageBuffer", None)
	previous_regions = getattr(previous_message_buffer, "regions", ())
	previous_token = (
		previous_regions[-1]
		if previous_message_buffer is not None
		and getattr(handler, "buffer", None) is previous_message_buffer
		and previous_regions
		else None
	)
	try:
		message_text = numbered_choice_message_text(
			text,
			start_cell=start_cell,
			display_size=handler.displaySize,
		)
		handler.message(message_text)
	except Exception:
		return None
	message_buffer = getattr(handler, "messageBuffer", None)
	if message_buffer is None:
		# Test doubles and older compatible handlers do not expose buffer identity.
		return True
	if getattr(handler, "buffer", None) is not message_buffer:
		return None
	regions = getattr(message_buffer, "regions", ())
	if not regions or regions[-1] is previous_token:
		# `message` has no result value. Prove ownership by requiring the active
		# buffer to contain a newly created region before touching its timer.
		return None
	message_token = regions[-1]
	# The selected spelling item is an active control value, not a notification
	# that may disappear while the user is still reading it. NVDA has no public
	# per-message lifetime override, so stop only the timer created by the call
	# above. A later foreign message creates and owns its own timer normally.
	message_timer = getattr(handler, "_messageCallLater", None)
	if message_timer is not None:
		try:
			message_timer.Stop()
		except Exception:
			pass
	return message_token


class DeveloperContextMessageRegion(nvdaBraille.Region):
	"""Keep one held developer message pageable inside its owned NVDA buffer."""

	def __init__(self, text: str, handler: object):
		super().__init__()
		self.rawText = text
		self._handler = handler
		self._pageIndex = 0
		translated = nvdaBraille.Region()
		translated.rawText = text
		translated.update()
		self._allBrailleCells = tuple(translated.brailleCells)
		self._allBrailleToRawPos = tuple(translated.brailleToRawPos)
		page_size = getattr(handler, "displaySize", 0)
		self._pageSize = (
			page_size
			if isinstance(page_size, int) and not isinstance(page_size, bool) and page_size > 0
			else max(1, len(self._allBrailleCells))
		)
		self._pageCount = max(1, (len(self._allBrailleCells) + self._pageSize - 1) // self._pageSize)
		self.update()

	def update(self):
		start = self._pageIndex * self._pageSize
		end = min(start + self._pageSize, len(self._allBrailleCells))
		self.brailleCells = list(self._allBrailleCells[start:end])
		self.brailleToRawPos = list(self._allBrailleToRawPos[start:end])
		self.rawToBraillePos = []
		self.brailleCursorPos = None
		self.brailleSelectionStart = None
		self.brailleSelectionEnd = None

	def nextLine(self):
		self._movePage(1)

	def previousLine(self, start=False):
		self._movePage(-1)

	def _movePage(self, delta: int) -> None:
		message_buffer = getattr(self._handler, "messageBuffer", None)
		regions = getattr(message_buffer, "regions", ())
		if (
			message_buffer is None
			or getattr(self._handler, "buffer", None) is not message_buffer
			or not regions
			or regions[-1] is not self
		):
			return
		previous_page = self._pageIndex
		self._pageIndex = min(max(0, self._pageIndex + delta), self._pageCount - 1)
		try:
			update_buffer = getattr(message_buffer, "update", None)
			if callable(update_buffer):
				update_buffer()
			message_buffer.windowStartPos = 0
			self._handler.update()
		except Exception:
			self._pageIndex = previous_page
			self.update()
			return
		# NVDA starts its normal transient-message timer again after a Braille
		# scroll command returns. Stop only the timer belonging to this still
		# visible owned region, after that command has finished.
		try:
			core.callLater(0, self._stopOwnedMessageTimer)
		except Exception:
			pass

	def _stopOwnedMessageTimer(self) -> None:
		message_buffer = getattr(self._handler, "messageBuffer", None)
		regions = getattr(message_buffer, "regions", ())
		if (
			message_buffer is None
			or getattr(self._handler, "buffer", None) is not message_buffer
			or not regions
			or regions[-1] is not self
		):
			return
		message_timer = getattr(self._handler, "_messageCallLater", None)
		if message_timer is not None:
			try:
				message_timer.Stop()
			except Exception:
				pass


def present_developer_context_message(text: str, *, start_cell: int) -> object | None:
	"""Show a held developer value with bounded in-message Braille paging."""
	message_token = present_numbered_choice_message(text, start_cell=start_cell)
	if message_token is None:
		return None
	handler = nvdaBraille.handler
	message_buffer = getattr(handler, "messageBuffer", None)
	regions = getattr(message_buffer, "regions", ())
	if (
		message_buffer is None
		or getattr(handler, "buffer", None) is not message_buffer
		or not regions
		or regions[-1] is not message_token
	):
		return message_token
	region = None
	try:
		message_text = numbered_choice_message_text(
			text,
			start_cell=start_cell,
			display_size=handler.displaySize,
		)
		region = DeveloperContextMessageRegion(message_text, handler)
		regions[-1] = region
		update_buffer = getattr(message_buffer, "update", None)
		if callable(update_buffer):
			update_buffer()
		message_buffer.windowStartPos = 0
		handler.update()
	except Exception:
		if region is not None and regions and regions[-1] is region:
			try:
				regions[-1] = message_token
				update_buffer = getattr(message_buffer, "update", None)
				if callable(update_buffer):
					update_buffer()
				message_buffer.windowStartPos = 0
				handler.update()
			except Exception:
				pass
		return message_token
	region._stopOwnedMessageTimer()
	return region


def dismiss_numbered_choice_message(message_token: object) -> bool:
	"""Dismiss the visible NVDA Braille message after contextual choice navigation."""
	handler = nvdaBraille.handler
	message_buffer = getattr(handler, "messageBuffer", None)
	if message_buffer is None or getattr(handler, "buffer", None) is not message_buffer:
		return False
	regions = getattr(message_buffer, "regions", ())
	if message_token is not message_buffer and (not regions or regions[-1] is not message_token):
		return False
	dismiss = getattr(handler, "_dismissMessage", None)
	if not callable(dismiss):
		return False
	try:
		dismiss()
	except Exception:
		return False
	return True


def position_numbered_choice(
	plan: BraillePlan,
	*,
	start_cell: int,
	display_size: int,
	content_cell_count: int,
) -> BraillePlan:
	"""Position a transient choice as far right as it completely fits."""
	if (
		not isinstance(start_cell, int)
		or isinstance(start_cell, bool)
		or not isinstance(display_size, int)
		or isinstance(display_size, bool)
		or not isinstance(content_cell_count, int)
		or isinstance(content_cell_count, bool)
		or start_cell <= 1
		or start_cell > display_size
		or content_cell_count <= 0
	):
		return plan
	last_complete_start = max(1, display_size - content_cell_count + 1)
	actual_start = min(start_cell, last_complete_start)
	if actual_start <= 1:
		return plan
	offset = actual_start - 1
	text = (" " * offset) + plan.text
	routing = (
		(tuple(None for _ in range(offset)) + plan.routing_byte_columns)
		if plan.routing_byte_columns is not None
		else None
	)
	return replace(
		plan,
		text=text,
		cursor=plan.cursor + offset if plan.cursor is not None else None,
		selection_start=plan.selection_start + offset if plan.selection_start is not None else None,
		selection_end=plan.selection_end + offset if plan.selection_end is not None else None,
		source_offsets=tuple(range(len(text) + 1)),
		routing_byte_columns=routing,
	)


class StructuredLineRegion(nvdaBraille.TextInfoRegion):
	"""Let NVDA translate and decorate one structured Neovim line."""

	def __init__(self, obj):
		super().__init__(obj)
		self.obj = obj
		self.focusToHardLeft = True
		# The structured editor line replaces Windows Terminal's focus-context
		# labels; keeping them as preceding visible regions can leave text
		# appended after labels such as "Windows PowerShell".
		self.hidePreviousRegions = True

	def update(self):
		service = getTerminalIntegrationService()
		formatting = config.conf.get("documentFormatting", {})
		report_spelling = bool(int(formatting.get("reportSpellingErrors2", 0)) & 4)
		try:
			session_plan = (
				service.braille_plan(self.obj, report_spelling=report_spelling)
				if service is not None
				else None
			)
		except Exception:
			session_plan = None
		plan = session_plan.plan if session_plan is not None else plan_braille({})
		self._apply_plan(plan, session_plan)
		# TextInfoRegion supplies NVDA's public caret-following contract, while
		# the semantic text itself comes from Neovim rather than an NVDA TextInfo.
		nvdaBraille.Region.update(self)
		if session_plan is not None and session_plan.numbered_choice and service is not None:
			try:
				positioned_plan = position_numbered_choice(
					plan,
					start_cell=service.numbered_choice_braille_start(),
					display_size=nvdaBraille.handler.displaySize,
					content_cell_count=len(self.brailleCells),
				)
			except Exception:
				# Missing or changing display metadata must leave ordinary cell-1 output intact.
				positioned_plan = plan
			if positioned_plan is not plan:
				plan = positioned_plan
				self._apply_plan(plan, session_plan)
				nvdaBraille.Region.update(self)
		if session_plan is not None and session_plan.preserve_viewport:
			# NVDA's public TextInfoRegion contract marks a pending caret update
			# when native terminal events arrive. In Braille exploration, the
			# real caret must not scroll the independently selected viewport.
			self.pendingCaretUpdate = False

	def _apply_plan(self, plan: BraillePlan, session_plan) -> None:
		self._plan = plan
		self._sourceLine = session_plan.source_line if session_plan is not None else ""
		self.rawText = plan.text
		self.cursorPos = plan.cursor
		self.selectionStart = plan.selection_start
		self.selectionEnd = plan.selection_end
		self.brailleSelectionStart = None
		self.brailleSelectionEnd = None

	def routeTo(self, braillePos):
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.should_suppress_braille(self.obj)
		except Exception:
			suppressed = False
		if service is not None:
			try:
				service.record_braille_route_attempt(braillePos, suppressed=suppressed)
			except Exception:
				pass
		if not suppressed:
			return
		if not 0 <= braillePos < len(self.brailleToRawPos):
			service.record_braille_route_rejection("outOfRange", braillePos)
			return
		expanded_offset = self.brailleToRawPos[braillePos]
		if self._plan.routing_byte_columns is not None:
			if not 0 <= expanded_offset < len(self._plan.routing_byte_columns):
				service.record_braille_route_rejection("semanticOutOfRange", braillePos)
				return
			byte_column = self._plan.routing_byte_columns[expanded_offset]
			if byte_column is None:
				service.record_braille_route_rejection("semanticStatus", braillePos)
				return
		else:
			source_offset = source_offset_for_expanded(self._plan, expanded_offset)
			byte_column = len(self._sourceLine[:source_offset].encode("utf-8"))
		service.route_braille_cursor(
			self.obj,
			byte_column,
			braille_position=braillePos,
		)

	def previousLine(self, start=False):
		self._navigate_line(
			"previous",
			target_column="preferred" if start else "end",
		)

	def nextLine(self):
		service = getTerminalIntegrationService()
		try:
			direct = service is not None and service.consume_direct_braille_next_line(self.obj)
		except Exception:
			direct = False
		self._navigate_line(
			"next",
			target_column="preferred" if direct else "start",
		)

	def _navigate_line(self, direction: str, *, target_column: str) -> None:
		service = getTerminalIntegrationService()
		try:
			if service is not None:
				service.navigate_braille_line(
					self.obj,
					direction,
					target_column=target_column,
				)
		except Exception:
			# A navigation failure must not escape into NVDA's gesture handling.
			pass


class StructuredTerminalBrailleOverlay:
	def _reportNewLines(self, lines):
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.suppress_terminal_live_text(self, len(lines))
		except Exception:
			suppressed = False
		if suppressed:
			return
		return super()._reportNewLines(lines)

	def getBrailleRegions(self, review=False):
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.should_suppress_braille(self)
		except Exception:
			suppressed = False
		if service is not None:
			try:
				service.record_braille_region_request(review=review, suppressed=suppressed)
			except Exception:
				pass
		if review or not suppressed:
			raise NotImplementedError
		# Return a concrete iterable. A yield would turn this into a generator
		# and defer NotImplementedError until outside NVDA's fallback try block.
		return (StructuredLineRegion(self),)
