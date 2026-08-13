"""Stable public surface consumed by the Windows Terminal AppModule."""

from __future__ import annotations

from typing import Any, Protocol

from .core.exploration_state import ExplorationAction
from .core.held_context_state import HeldContextDirection, HeldContextKind
from .core.numbered_choice_state import NumberedChoiceDirection
from .nvda_braille import StructuredTerminalBrailleOverlay as StructuredTerminalBrailleOverlay
from .runtime_config import PRODUCT_NAME as PRODUCT_NAME
from .runtime_config import SESSION_CLAIM_GESTURE as SESSION_CLAIM_GESTURE
from .adapter_ports import BrailleAdapterPort as BrailleAdapterPort
from .service_registry import get_terminal_integration_service
from .terminal_integration import TerminalCommand


class TerminalAdapterPort(Protocol):
	"""Behavior the application-owned Windows Terminal adapter may invoke."""

	def prepare_focus(self, obj: Any, adapter_token: object, app_module: Any): ...

	def finish_focus(self, decision: Any) -> None: ...

	def abandon_focus(self, decision: Any) -> None: ...

	def lose_focus(self, adapter_token: object) -> None: ...

	def should_use_native_event(self, obj: Any, event_name: str) -> bool: ...

	def dispatch_command(
		self,
		command: TerminalCommand,
		gesture: Any,
		focus_obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def authorize_session_claim(self, obj: Any, app_module: Any): ...

	def complete_session_claim(
		self,
		authorization: Any,
		focus_obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def cancel_session_claim(self, authorization: Any) -> None: ...

	def exploration_script_available(self, obj: Any, app_module: Any, adapter_token: object) -> bool: ...

	def explore_text(self, action: ExplorationAction, obj: Any, app_module: Any, adapter_token: object): ...

	def release_exploration(self, obj: Any, app_module: Any, adapter_token: object) -> bool: ...

	def cancel_exploration(self, adapter_token: object) -> bool: ...

	def navigate_numbered_choice(
		self,
		direction: NumberedChoiceDirection,
		obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def release_numbered_choice(self, obj: Any, app_module: Any, adapter_token: object) -> bool: ...

	def cancel_numbered_choice(self, adapter_token: object) -> bool: ...

	def authorize_numbered_choice_accept(self, obj: Any, app_module: Any, adapter_token: object): ...

	def complete_numbered_choice_accept(
		self,
		authorization: Any,
		focus_obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def held_context_script_available(
		self,
		kind: HeldContextKind,
		obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def start_held_context(
		self,
		kind: HeldContextKind,
		obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def navigate_held_context(
		self,
		direction: HeldContextDirection,
		obj: Any,
		app_module: Any,
		adapter_token: object,
	) -> bool: ...

	def release_held_context(self, obj: Any, app_module: Any, adapter_token: object) -> bool: ...

	def cancel_held_context(self, adapter_token: object) -> bool: ...

	def copy_diagnostic_report(self, gesture: Any = None) -> None: ...

	def mark_direct_braille_next_line(self, obj: Any, app_module: Any, adapter_token: object): ...

	def clear_direct_braille_next_line(self, token: object) -> None: ...

	def record_braille_overlay_selected(self) -> None: ...


def get_terminal_integration() -> TerminalAdapterPort | None:
	"""Return the current published runtime through the AppModule port."""
	return get_terminal_integration_service()
