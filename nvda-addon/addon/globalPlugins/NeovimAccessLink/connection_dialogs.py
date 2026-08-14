"""NVDA dialog port used by connection workflows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any
import addonHandler

addonHandler.initTranslation()


def _display_dialog_as_modal(dialog: Any) -> int:
	from gui.message import displayDialogAsModal

	return displayDialogAsModal(dialog)


class NvdaConnectionDialogs:
	"""Create connection dialogs while keeping wx out of workflow state transitions."""

	def __init__(
		self,
		*,
		deliver_result: Callable[..., bool],
		runtime_active: Callable[[], bool],
		display_modal: Callable[[Any], int] = _display_dialog_as_modal,
	) -> None:
		if not callable(deliver_result) or not callable(runtime_active) or not callable(display_modal):
			raise ValueError("runtime scheduling callbacks are required")
		self._deliverResult = deliver_result
		self._runtimeActive = runtime_active
		self._displayModal = display_modal

	def choose(
		self,
		*,
		title: str,
		message: str,
		choices: Sequence[str],
		on_result: Callable[[int | None], None],
		initial: int = 0,
	) -> None:
		import gui
		import wx

		dialog = wx.SingleChoiceDialog(gui.mainFrame, message, title, list(choices))
		if choices and 0 <= initial < len(choices):
			dialog.SetSelection(initial)

		def show() -> None:
			try:
				if not self._runtimeActive():
					return
				selection = dialog.GetSelection() if self._displayModal(dialog) == wx.ID_OK else None
				self._deliverResult(on_result, selection)
			finally:
				dialog.Destroy()

		wx.CallAfter(show)

	def password(self, profile_name: str) -> str | None:
		import gui
		import wx

		if not self._runtimeActive():
			return None
		dialog = wx.PasswordEntryDialog(
			gui.mainFrame,
			_("Enter the SSH password for {profile}. It will not be saved.").format(
				profile=profile_name,
			),
			_("Neovim SSH password"),
		)
		try:
			if self._displayModal(dialog) != wx.ID_OK or not self._runtimeActive():
				return None
			return dialog.GetValue()
		finally:
			dialog.Destroy()
