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

	def confirm(
		self,
		*,
		title: str,
		message: str,
		on_result: Callable[[bool, bool], None],
	) -> None:
		import gui
		import wx

		class RememberChoiceDialog(wx.Dialog):
			def __init__(self) -> None:
				super().__init__(gui.mainFrame, title=title)
				main_sizer = wx.BoxSizer(wx.VERTICAL)
				main_sizer.Add(
					wx.StaticText(self, label=message),
					border=12,
					flag=wx.ALL | wx.EXPAND,
				)
				# Translators: Checkbox in the temporary terminal binding question.
				self.rememberChoiceCheckbox = wx.CheckBox(
					self,
					label=_("Remember this decision in the current configuration profile"),
				)
				main_sizer.Add(
					self.rememberChoiceCheckbox,
					border=12,
					flag=wx.LEFT | wx.RIGHT | wx.BOTTOM,
				)
				main_sizer.Add(
					self.CreateButtonSizer(wx.YES_NO),
					border=12,
					flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT,
				)
				self.SetSizerAndFit(main_sizer)
				self.SetAffirmativeId(wx.ID_YES)
				self.SetEscapeId(wx.ID_NO)
				yes_button = self.FindWindow(wx.ID_YES)
				if yes_button is not None:
					yes_button.SetDefault()
					yes_button.SetFocus()

		dialog = RememberChoiceDialog()

		def show() -> None:
			try:
				if not self._runtimeActive():
					return
				result = self._displayModal(dialog)
				self._deliverResult(
					on_result,
					result == wx.ID_YES,
					result in (wx.ID_YES, wx.ID_NO) and dialog.rememberChoiceCheckbox.IsChecked(),
				)
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
