"""NVDA dialog port used by connection workflows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import addonHandler

addonHandler.initTranslation()


class NvdaConnectionDialogs:
	"""Create connection dialogs while keeping wx out of workflow state transitions."""

	def __init__(
		self,
		*,
		deliver_result: Callable[..., bool],
		runtime_active: Callable[[], bool],
	) -> None:
		if not callable(deliver_result) or not callable(runtime_active):
			raise ValueError("runtime scheduling callbacks are required")
		self._deliverResult = deliver_result
		self._runtimeActive = runtime_active

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
				selection = dialog.GetSelection() if dialog.ShowModal() == wx.ID_OK else None
				self._deliverResult(on_result, selection)
			finally:
				dialog.Destroy()

		wx.CallAfter(show)

	def confirm(
		self,
		*,
		title: str,
		message: str,
		on_result: Callable[[bool], None],
		default_no: bool = True,
	) -> None:
		import gui
		import wx

		style = wx.YES_NO | wx.ICON_QUESTION
		if default_no:
			style |= wx.NO_DEFAULT

		def show() -> None:
			if not self._runtimeActive():
				return
			result = gui.messageBox(message, title, style)
			self._deliverResult(on_result, result == wx.YES)

		wx.CallAfter(show)

	@staticmethod
	def password(profile_name: str) -> str | None:
		import gui
		import wx

		dialog = wx.PasswordEntryDialog(
			gui.mainFrame,
			_("Enter the SSH password for {profile}. It will not be saved.").format(
				profile=profile_name,
			),
			_("Neovim SSH password"),
		)
		try:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.GetValue()
		finally:
			dialog.Destroy()
