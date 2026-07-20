"""Windows Terminal adapter for the structured Neovim accessibility add-on.

NVDA loads this AppModule only for Windows Terminal. Application events and
object overlays remain application-owned. The process-wide F12 decider exists
only while an instance of this AppModule is loaded and is inert unless the
exact focused AppModule and terminal control match.
"""

import api
import addonHandler
import appModuleHandler
import controlTypes
import inputCore
import queueHandler
import scriptHandler

from globalPlugins import NeovimAccessLink

addonHandler.initTranslation()


class AppModule(appModuleHandler.AppModule):
	scriptCategory = NeovimAccessLink._PRODUCT_NAME
	_observerAdapters = []
	_observerCallback = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._eventToken = object()
		cls = type(self)
		cls._observerAdapters.append(self)
		if cls._observerCallback is None:
			cls._observerCallback = cls._dispatchClaimGesture
			inputCore.decide_executeGesture.register(cls._observerCallback)

	def terminate(self):
		cls = type(self)
		if self in cls._observerAdapters:
			cls._observerAdapters.remove(self)
		if not cls._observerAdapters and cls._observerCallback is not None:
			inputCore.decide_executeGesture.unregister(cls._observerCallback)
			cls._observerCallback = None
		super().terminate()

	@classmethod
	def _dispatchClaimGesture(cls, gesture):
		if not cls._isClaimGesture(gesture):
			return True
		try:
			focus_obj = api.getFocusObject()
		except Exception:
			return True
		adapter = getattr(focus_obj, "appModule", None)
		if not any(adapter is candidate for candidate in tuple(cls._observerAdapters)):
			return True
		return adapter._decideExecuteGesture(gesture, focus_obj=focus_obj)

	@staticmethod
	def _isClaimGesture(gesture):
		return NeovimAccessLink._SESSION_CLAIM_GESTURE.lower() in (
			identifier.lower() for identifier in getattr(gesture, "normalizedIdentifiers", ())
		)

	def _service(self):
		return NeovimAccessLink.getTerminalIntegrationService()

	@staticmethod
	def _passThroughConfiguredTerminalScript(gesture):
		if gesture is not None:
			gesture.send()

	def _dispatchConfiguredTerminalScript(self, gesture, command):
		"""Run a configurable command only for this focused AppModule."""
		service = self._service()
		if service is None:
			self._passThroughConfiguredTerminalScript(gesture)
			return
		try:
			focus_obj = api.getFocusObject()
		except Exception:
			self._passThroughConfiguredTerminalScript(gesture)
			return
		try:
			handled = service.dispatch_command(
				command,
				gesture,
				focus_obj,
				self,
				self._eventToken,
			)
		except Exception:
			handled = False
		if not handled:
			self._passThroughConfiguredTerminalScript(gesture)

	@staticmethod
	def _shouldUseNativeEvent(service, obj, event_name):
		try:
			return service.should_use_native_event(obj, event_name)
		except Exception:
			return True

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		service = self._service()
		if service is None:
			return
		try:
			supported = service.supports_braille_overlay(obj)
		except Exception:
			supported = False
		if getattr(obj, "role", None) == controlTypes.Role.TERMINAL and supported:
			clsList.insert(0, NeovimAccessLink.StructuredTerminalBrailleOverlay)

	def event_gainFocus(self, obj, nextHandler):
		service = self._service()
		if service is None:
			nextHandler()
			return
		try:
			decision = service.prepare_focus(obj, self._eventToken, self)
		except Exception:
			decision = None
		nextHandler()
		if decision is None:
			return
		if service is not self._service():
			try:
				service.abandon_focus(decision)
			except Exception:
				pass
			return
		try:
			service.finish_focus(decision)
		except Exception:
			# Native focus handling already ran exactly once. The service owns
			# fail-open cleanup; never leak a secondary failure into NVDA's hook.
			pass

	def event_appModule_loseFocus(self):
		service = self._service()
		if service is not None:
			try:
				service.lose_focus(self._eventToken)
			except Exception:
				pass

	def event_textChange(self, obj, nextHandler):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "textChange"):
			nextHandler()

	def event_typedCharacter(self, obj, nextHandler, ch):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "typedCharacter"):
			nextHandler()

	def event_UIA_notification(self, obj, nextHandler, **kwargs):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "UIA_notification"):
			nextHandler()

	def event_liveRegionChange(self, obj, nextHandler):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "liveRegionChange"):
			nextHandler()

	def event_valueChange(self, obj, nextHandler):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "valueChange"):
			nextHandler()

	def event_nameChange(self, obj, nextHandler):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "nameChange"):
			nextHandler()

	def event_descriptionChange(self, obj, nextHandler):
		service = self._service()
		if service is None or self._shouldUseNativeEvent(service, obj, "descriptionChange"):
			nextHandler()

	@scriptHandler.script(
		description=_("Turn Neovim accessibility on or off and discover configured connections"),
		category=scriptCategory,
	)
	def script_toggleNeovimMode(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.TOGGLE_ACCESSIBILITY,
		)

	@scriptHandler.script(
		description=_("Read documentation for the selected Neovim completion item"),
		category=scriptCategory,
	)
	def script_readCompletionDocumentation(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.READ_COMPLETION_DOCUMENTATION,
		)

	@scriptHandler.script(
		description=_("Copy the active Neovim Visual selection to the Windows clipboard"),
		category=scriptCategory,
	)
	def script_copyNeovimSelection(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.COPY_VISUAL_SELECTION,
		)

	@scriptHandler.script(
		description=_("Copy Neovim's last yank to the Windows clipboard"),
		category=scriptCategory,
	)
	def script_copyLastNeovimYank(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.COPY_LAST_YANK,
		)

	@scriptHandler.script(
		description=_("Paste Windows clipboard text into the active Neovim buffer"),
		category=scriptCategory,
	)
	def script_pasteWindowsClipboard(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.PASTE_WINDOWS_CLIPBOARD,
		)

	@scriptHandler.script(
		description=_("Store Windows clipboard text in Neovim's unnamed register"),
		category=scriptCategory,
	)
	def script_setNeovimRegisterFromWindowsClipboard(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.SET_REGISTER_FROM_WINDOWS_CLIPBOARD,
		)

	@scriptHandler.script(
		description=_("Leave direct input in the active Neovim terminal"),
		category=scriptCategory,
	)
	def script_leaveDirectTerminalInput(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.LEAVE_DIRECT_TERMINAL_INPUT,
		)

	@scriptHandler.script(
		description=_("Choose a server and connect this terminal to a new Neovim session"),
		category=scriptCategory,
	)
	def script_startConnectionInstance(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.START_CONNECTION,
		)

	@scriptHandler.script(
		description=_("Disconnect the selected Neovim connection instance"),
		category=scriptCategory,
	)
	def script_disconnectConnectionInstance(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.DISCONNECT_CONNECTION,
		)

	@scriptHandler.script(
		description=_("Forget the temporary Neovim connection for the focused terminal"),
		category=scriptCategory,
	)
	def script_forgetTemporaryTerminalBinding(self, gesture):
		self._dispatchConfiguredTerminalScript(
			gesture,
			NeovimAccessLink.TerminalCommand.FORGET_TEMPORARY_BINDING,
		)

	@scriptHandler.script(
		description=_("Copy Neovim accessibility diagnostic report"),
		category=scriptCategory,
		gesture="kb:NVDA+alt+d",
	)
	def script_copyDiagnosticReport(self, gesture):
		service = self._service()
		if service is not None:
			try:
				service.copy_diagnostic_report(gesture)
			except Exception:
				pass

	def _decideExecuteGesture(self, gesture, focus_obj=None):
		if not self._isClaimGesture(gesture):
			return True
		if focus_obj is None:
			try:
				focus_obj = api.getFocusObject()
			except Exception:
				return True
		if getattr(focus_obj, "appModule", None) is not self:
			return True
		service = self._service()
		if service is None:
			return True
		try:
			authorization = service.authorize_session_claim(focus_obj, self)
		except Exception:
			return True
		if authorization is None:
			return True
		queueHandler.queueFunction(
			queueHandler.eventQueue,
			self._handleObservedClaimGesture,
			service,
			authorization,
		)
		return True

	def _handleObservedClaimGesture(self, originating_service, authorization):
		service = self._service()
		if service is None:
			try:
				originating_service.cancel_session_claim(authorization)
			except Exception:
				pass
			return
		if service is not originating_service:
			try:
				originating_service.cancel_session_claim(authorization)
			except Exception:
				pass
			return
		try:
			focus_obj = api.getFocusObject()
		except Exception:
			try:
				service.cancel_session_claim(authorization)
			except Exception:
				pass
			return
		try:
			service.complete_session_claim(
				authorization,
				focus_obj,
				self,
				self._eventToken,
			)
		except Exception:
			pass
