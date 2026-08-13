"""User-triggered clipboard, terminal, and diagnostic actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import addonHandler
import api
import speech
import tones
import ui
from speech.priorities import SpeechPriority as NvdaSpeechPriority

from .core.clipboard import MAX_CLIPBOARD_TEXT_BYTES, valid_clipboard_text
from .editor_session import ControlReplyKind, ControlRequestRejection

addonHandler.initTranslation()


class TerminalActions:
	"""Own editor controls initiated explicitly by the NVDA user."""

	def __init__(
		self,
		*,
		coordinator: Any,
		editor_session: Any,
		control_dispatcher: Any,
		presentation: Any,
		diagnostics: Any,
		addon_version: str,
		product_name: str,
		nvda_version: Callable[[], str],
	) -> None:
		self._coordinator = coordinator
		self._editorSession = editor_session
		self._controlDispatcher = control_dispatcher
		self._presentation = presentation
		self._diagnostics = diagnostics
		self._addonVersion = addon_version
		self._productName = product_name
		self._nvdaVersion = nvda_version

	def copy_diagnostic_report(self, _gesture: Any = None) -> None:
		report = self._diagnostics.report(
			{
				"addonVersion": self._addonVersion,
				"nvdaVersion": self._nvdaVersion(),
				"manualEnabled": self._coordinator.gate.manual_enabled,
				"suppressionActive": self._coordinator.gate.suppression_active,
				"connected": self._coordinator.connected,
				"brailleExplorationEnabled": self._editorSession.braille_exploration_enabled(),
			},
			product_name=self._productName,
		)
		if api.copyToClip(report):
			ui.message(_("Neovim diagnostic report copied"))
		else:
			ui.message(_("Could not copy Neovim diagnostic report"))

	def copy_selection(self, _gesture: Any = None) -> None:
		self._request_copy("visualSelection")

	def copy_last_yank(self, _gesture: Any = None) -> None:
		self._request_copy("yankRegister")

	def paste_windows_clipboard(self, _gesture: Any = None) -> None:
		context = self._clipboard_context()
		if context is None:
			return
		identity, instance_id, client = context
		rejection = self._editorSession.validate_clipboard_request("pasteTextRequest")
		if rejection is not None:
			self._report_clipboard_rejection(rejection)
			return
		text = self._read_windows_clipboard_text()
		if text is None:
			return
		plan = self._editorSession.plan_clipboard_request(
			instance_id,
			identity,
			"pasteTextRequest",
		)
		if not plan.ready:
			self._report_clipboard_rejection(plan.rejection)
			return
		self._record_discarded("clipboard", plan.discarded_request_ids)
		self._dispatch(
			client,
			plan.control,
			{**plan.payload, "text": text},
			on_result=lambda accepted, error_type: self._finish_clipboard_dispatch(
				"clipboardPasteRequested",
				plan.request_id,
				accepted,
				error_type,
				failure_message=_("Could not send text to the active Neovim session"),
				bytes=len(text.encode("utf-8")),
			),
		)

	def set_register_from_windows_clipboard(self, _gesture: Any = None) -> None:
		context = self._clipboard_context()
		if context is None:
			return
		identity, instance_id, client = context
		rejection = self._editorSession.validate_clipboard_request("setRegisterRequest")
		if rejection is not None:
			self._report_clipboard_rejection(rejection)
			return
		text = self._read_windows_clipboard_text()
		if text is None:
			return
		plan = self._editorSession.plan_clipboard_request(
			instance_id,
			identity,
			"setRegisterRequest",
		)
		if not plan.ready:
			self._report_clipboard_rejection(plan.rejection)
			return
		self._record_discarded("clipboard", plan.discarded_request_ids)
		self._dispatch(
			client,
			plan.control,
			{**plan.payload, "text": text},
			on_result=lambda accepted, error_type: self._finish_clipboard_dispatch(
				"clipboardRegisterRequested",
				plan.request_id,
				accepted,
				error_type,
				failure_message=_("Could not send text to the active Neovim session"),
				bytes=len(text.encode("utf-8")),
			),
		)

	def leave_direct_terminal_input(self, _gesture: Any = None) -> None:
		context = self._bound_context()
		if context is None:
			ui.message(_("No active Neovim session is bound to this terminal"))
			return
		identity, instance_id, client = context
		plan = self._editorSession.plan_leave_terminal_input_request(instance_id, identity)
		if not plan.ready:
			self._report_terminal_rejection(plan.rejection)
			return
		self._record_discarded("terminalControl", plan.discarded_request_ids)
		self._dispatch(
			client,
			plan.control,
			dict(plan.payload),
			on_result=lambda accepted, error_type: self._finish_terminal_dispatch(
				plan.request_id,
				instance_id,
				accepted,
				error_type,
			),
		)

	def read_completion_documentation(self, _gesture: Any = None) -> None:
		documentation = self._editorSession.completion_documentation()
		if documentation:
			speech.speakText(documentation, priority=NvdaSpeechPriority.NOW)
		else:
			ui.message(_("No completion or hover documentation available"))

	def handle_clipboard_result(self, instance_id: str, identity: Any, event: dict) -> dict | None:
		reply = self._editorSession.consume_clipboard_reply(instance_id, identity, event)
		if reply.kind == ControlReplyKind.INVALID_REQUEST_ID:
			self._diagnostics.record(
				"clipboardResultIgnored",
				instanceId=instance_id,
				reason="invalidRequestId",
			)
			return None
		if reply.kind == ControlReplyKind.STALE_OR_UNBOUND:
			self._diagnostics.record(
				"clipboardResultIgnored",
				instanceId=instance_id,
				requestId=reply.request_id,
				reason="staleOrUnbound",
			)
			return None
		clipboard_written = True
		if reply.requires_clipboard_write:
			try:
				clipboard_written = bool(api.copyToClip(reply.clipboard_text))
			except Exception as error:
				clipboard_written = False
				self._diagnostics.record("clipboardWriteFailed", errorType=type(error).__name__)
		reply = self._editorSession.finish_clipboard_reply(
			reply,
			clipboard_written=clipboard_written,
		)
		if reply.event_type == "copyTextResult" and reply.ok:
			self._clipboard_success(_("Copied from Neovim"))
		elif reply.event_type == "pasteTextResult" and reply.ok:
			self._clipboard_success(_("Pasted into Neovim"))
		elif reply.event_type == "setRegisterResult" and reply.ok:
			self._clipboard_success(_("Stored the Windows clipboard in Neovim's unnamed register"))
		if not reply.ok:
			self._clipboard_failure(self._clipboard_error_message(reply.result_code))
		safe_payload = reply.safe_payload or {}
		self._diagnostics.record(
			"clipboardResult",
			instanceId=instance_id,
			requestId=reply.request_id,
			type=reply.event_type,
			ok=reply.ok,
			resultCode=reply.result_code,
			copiedCharacterCount=safe_payload.get("copiedCharacterCount"),
			copiedLineCount=safe_payload.get("copiedLineCount"),
			insertedBytes=safe_payload.get("insertedBytes"),
			insertedLines=safe_payload.get("insertedLines"),
			storedBytes=safe_payload.get("storedBytes"),
			storedLineCount=safe_payload.get("storedLineCount"),
		)
		return dict(reply.safe_event) if reply.safe_event is not None else None

	def handle_terminal_control_result(
		self,
		instance_id: str,
		identity: Any,
		event: dict,
	) -> dict | None:
		reply = self._editorSession.consume_terminal_control_reply(instance_id, identity, event)
		if reply.kind == ControlReplyKind.INVALID_REQUEST_ID:
			self._diagnostics.record(
				"terminalControlResultIgnored",
				instanceId=instance_id,
				reason="invalidRequestId",
			)
			return None
		if reply.kind == ControlReplyKind.STALE_OR_UNBOUND:
			self._diagnostics.record(
				"terminalControlResultIgnored",
				instanceId=instance_id,
				requestId=reply.request_id,
				reason="staleOrUnbound",
			)
			return None
		if not reply.ok:
			message = (
				_("Neovim changed before terminal input could be left; try again")
				if reply.result_code == "staleState"
				else _("Neovim could not leave direct terminal input")
			)
			ui.message(message)
		self._diagnostics.record(
			"terminalControlResult",
			instanceId=instance_id,
			requestId=reply.request_id,
			ok=reply.ok,
			resultCode=reply.result_code,
		)
		return dict(reply.safe_event) if reply.safe_event is not None else None

	def discard_requests(self, *, instance_id: str | None = None) -> None:
		self._editorSession.discard_clipboard_requests(instance_id)
		self._editorSession.discard_terminal_control_requests(instance_id)

	def _request_copy(self, source: str) -> None:
		context = self._clipboard_context()
		if context is None:
			return
		identity, instance_id, client = context
		plan = self._editorSession.plan_clipboard_request(
			instance_id,
			identity,
			"copyTextRequest",
			source=source,
		)
		if not plan.ready:
			self._report_clipboard_rejection(plan.rejection)
			return
		self._record_discarded("clipboard", plan.discarded_request_ids)
		self._dispatch(
			client,
			plan.control,
			dict(plan.payload),
			on_result=lambda accepted, error_type: self._finish_clipboard_dispatch(
				"clipboardCopyRequested",
				plan.request_id,
				accepted,
				error_type,
				failure_message=_("Could not request text from the active Neovim session"),
				source=source,
			),
		)

	def _dispatch(self, client: Any, kind: str, payload: dict, *, on_result: Callable) -> bool:
		queued = self._controlDispatcher.submit(client, kind, payload, on_result=on_result)
		if not queued:
			on_result(False, "QueueUnavailable")
		return queued

	def _finish_clipboard_dispatch(
		self,
		category: str,
		request_id: int,
		accepted: bool,
		error_type: str | None,
		*,
		failure_message: str,
		**fields: Any,
	) -> None:
		if not accepted:
			self._editorSession.cancel_clipboard_request(request_id)
			self._clipboard_failure(failure_message)
		self._diagnostics.record(
			category,
			requestId=request_id,
			accepted=accepted,
			errorType=error_type,
			**fields,
		)

	def _finish_terminal_dispatch(
		self,
		request_id: int,
		instance_id: str,
		accepted: bool,
		error_type: str | None,
	) -> None:
		if not accepted:
			self._editorSession.cancel_terminal_control_request(request_id)
			ui.message(_("Could not ask Neovim to leave direct terminal input"))
		self._diagnostics.record(
			"leaveTerminalInputRequested",
			requestId=request_id,
			accepted=accepted,
			errorType=error_type,
			instanceId=instance_id,
		)

	def _read_windows_clipboard_text(self) -> str | None:
		try:
			text = api.getClipData()
		except Exception as error:
			self._diagnostics.record("clipboardReadFailed", errorType=type(error).__name__)
			self._clipboard_failure(_("Could not read text from the Windows clipboard"))
			return None
		if not valid_clipboard_text(text):
			reason = (
				"tooLarge"
				if isinstance(text, str) and len(text.encode("utf-8", "ignore")) > MAX_CLIPBOARD_TEXT_BYTES
				else "emptyOrInvalid"
			)
			self._diagnostics.record("clipboardTextRejected", reason=reason)
			self._clipboard_failure(_("The Windows clipboard does not contain supported text"))
			return None
		return text

	def _bound_context(self) -> tuple[Any, str, Any] | None:
		gate = self._coordinator.gate
		identity = gate.focused
		selected = self._coordinator.instances.selected_for(identity) if identity else None
		if (
			identity is None
			or selected is None
			or self._coordinator.active_client is None
			or selected.identifier != self._coordinator.active_instance_id
			or not gate.manual_enabled
			or not gate.authenticated
			or not gate.nvim_active
			or gate.bound_terminal != identity
		):
			return None
		return identity, selected.identifier, self._coordinator.active_client

	def _clipboard_context(self) -> tuple[Any, str, Any] | None:
		context = self._bound_context()
		if context is None or not self._coordinator.gate.suppression_active:
			self._clipboard_failure(_("No active Neovim session is bound to this terminal"))
			return None
		return context

	def _report_clipboard_rejection(self, rejection: ControlRequestRejection) -> None:
		messages = {
			ControlRequestRejection.CAPABILITY_MISSING: _(
				"The connected Neovim components do not support copy and paste"
			),
			ControlRequestRejection.VISUAL_SELECTION_REQUIRED: _(
				"Select text in Neovim Visual mode before copying"
			),
			ControlRequestRejection.PASTE_MODE_UNAVAILABLE: _(
				"Paste is available only in Normal or Insert mode"
			),
			ControlRequestRejection.BUFFER_NOT_EDITABLE: _(
				"The current Neovim buffer cannot be edited by this command"
			),
		}
		self._clipboard_failure(
			messages.get(rejection, _("The active Neovim state is incomplete; try again"))
		)

	@staticmethod
	def _report_terminal_rejection(rejection: ControlRequestRejection) -> None:
		if rejection == ControlRequestRejection.CAPABILITY_MISSING:
			message = _("The connected Neovim components do not support terminal control")
		elif rejection == ControlRequestRejection.NOT_DIRECT_TERMINAL:
			message = _("Neovim is not in direct terminal input")
		else:
			message = _("The active Neovim state is incomplete; try again")
		ui.message(message)

	def _record_discarded(self, channel: str, request_ids: tuple[int, ...]) -> None:
		category = (
			"clipboardRequestDiscarded" if channel == "clipboard" else "terminalControlRequestDiscarded"
		)
		for request_id in request_ids:
			self._diagnostics.record(category, requestId=request_id, reason="queueLimit")

	@staticmethod
	def _clipboard_error_message(result_code: str) -> str:
		messages = {
			"staleState": _("Neovim changed before the copy or paste completed; try again"),
			"visualSelectionRequired": _("The Neovim Visual selection is no longer available"),
			"selectionUnavailable": _("The Neovim Visual selection is no longer available"),
			"bufferNotEditable": _("The current Neovim context does not accept this paste"),
			"unsupportedContext": _("The current Neovim context does not accept this paste"),
			"unsupportedMode": _("The current Neovim context does not accept this paste"),
			"textTooLarge": _("The selected Neovim text is too large to copy"),
			"emptyText": _("There is no Neovim text to copy"),
			"clipboardWriteFailed": _("Could not write text to the Windows clipboard"),
			"registerRejected": _("Neovim could not replace its unnamed register"),
		}
		return messages.get(result_code, _("Neovim could not complete the copy or paste command"))

	def _clipboard_success(self, message: str) -> None:
		mode = self._presentation.feedback_mode("clipboard")
		if mode & 2:
			tones.beep(660, 25)
		if mode & 1:
			speech.speakText(message, priority=NvdaSpeechPriority.NEXT)

	def _clipboard_failure(self, message: str) -> None:
		if self._presentation.feedback_mode("clipboard") & 2:
			tones.beep(220, 35)
		ui.message(message)
