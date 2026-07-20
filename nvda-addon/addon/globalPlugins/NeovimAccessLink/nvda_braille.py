"""NVDA Braille regions and overlays for structured Neovim state."""

from __future__ import annotations

import braille as nvdaBraille
import config

from .core.braille import plan_braille, source_offset_for_expanded
from .service_registry import getTerminalIntegrationService


class StructuredLineRegion(nvdaBraille.Region):
	"""Let NVDA translate and decorate one structured Neovim line."""

	def __init__(self, obj):
		super().__init__()
		self.obj = obj
		self.focusToHardLeft = True

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
		self._plan = plan
		self._sourceLine = session_plan.source_line if session_plan is not None else ""
		self.rawText = plan.text
		self.cursorPos = plan.cursor
		self.selectionStart = plan.selection_start
		self.selectionEnd = plan.selection_end
		self.brailleSelectionStart = None
		self.brailleSelectionEnd = None
		super().update()

	def routeTo(self, braillePos):
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.should_suppress_braille(self.obj)
		except Exception:
			suppressed = False
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
		service.route_braille_cursor(self.obj, byte_column)


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
		if review or not suppressed:
			raise NotImplementedError
		# Return a concrete iterable. A yield would turn this into a generator
		# and defer NotImplementedError until outside NVDA's fallback try block.
		return (StructuredLineRegion(self),)
