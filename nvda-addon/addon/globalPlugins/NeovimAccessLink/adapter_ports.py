"""Static consumer views of the published terminal integration service."""

from __future__ import annotations

from typing import Any, Protocol


class BrailleAdapterPort(Protocol):
	"""Operations used by structured Braille regions and terminal overlays."""

	def braille_plan(self, obj: Any, *, report_spelling: bool): ...

	def numbered_choice_braille_start(self) -> int: ...

	def should_suppress_braille(self, obj: Any) -> bool: ...

	def record_braille_route_attempt(self, braille_pos: int, *, suppressed: bool) -> None: ...

	def record_braille_route_rejection(self, reason: str, braille_pos: int) -> None: ...

	def route_braille_cursor(
		self,
		obj: Any,
		byte_column: int,
		*,
		braille_position: int | None = None,
	) -> bool: ...

	def consume_direct_braille_next_line(self, obj: Any) -> bool: ...

	def navigate_braille_line(self, obj: Any, direction: str, *, target_column: str) -> bool: ...

	def suppress_terminal_live_text(self, obj: Any, line_count: int) -> bool: ...

	def record_braille_region_request(self, *, review: bool, suppressed: bool) -> None: ...
