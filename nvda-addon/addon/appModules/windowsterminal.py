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
import keyboardHandler
import queueHandler
import scriptHandler
import types

from globalPlugins import NeovimAccessLink

addonHandler.initTranslation()


# Translators: Input Help description for reading Neovim text without moving its real cursor.
@scriptHandler.script(description=_("Explore Neovim text without moving the cursor"))
def script_exploreText(app_module, gesture):
	app_module._executeExploration(gesture)


@scriptHandler.script()
def script_suppressExplorationRepeat(app_module, gesture):
	pass


class AppModule(appModuleHandler.AppModule):
	scriptCategory = NeovimAccessLink._PRODUCT_NAME
	_observerAdapters = []
	_observerCallback = None
	_rawKeyCallback = None

	_EXPLORATION_ACTIONS = {
		(frozenset({"nvda"}), "h"): NeovimAccessLink.ExplorationAction.CHARACTER_LEFT,
		(frozenset({"nvda"}), "l"): NeovimAccessLink.ExplorationAction.CHARACTER_RIGHT,
		(frozenset({"nvda"}), "k"): NeovimAccessLink.ExplorationAction.LINE_UP,
		(frozenset({"nvda"}), "j"): NeovimAccessLink.ExplorationAction.LINE_DOWN,
		(frozenset({"nvda", "shift"}), "h"): NeovimAccessLink.ExplorationAction.WORD_PREVIOUS,
		(frozenset({"nvda", "shift"}), "l"): NeovimAccessLink.ExplorationAction.WORD_NEXT,
	}
	_EXPLORATION_VK_CODES = frozenset({72, 74, 75, 76})

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._eventToken = object()
		self._explorationActive = False
		self._explorationHeldKeys = {}
		self._heldNvdaModifiers = set()
		self._physicallyHeldExplorationKeys = set()
		self._explorationScript = types.MethodType(script_exploreText, self)
		self._suppressExplorationRepeatScript = types.MethodType(
			script_suppressExplorationRepeat,
			self,
		)
		cls = type(self)
		cls._observerAdapters.append(self)
		if cls._observerCallback is None:
			cls._observerCallback = cls._dispatchClaimGesture
			inputCore.decide_executeGesture.register(cls._observerCallback)
		if cls._rawKeyCallback is None:
			cls._rawKeyCallback = cls._dispatchRawKey
			inputCore.decide_handleRawKey.register(cls._rawKeyCallback)

	def terminate(self):
		service = self._service()
		if service is not None:
			try:
				service.cancel_exploration(self._eventToken)
			except Exception:
				pass
		self._explorationActive = False
		self._explorationHeldKeys.clear()
		self._heldNvdaModifiers.clear()
		self._physicallyHeldExplorationKeys.clear()
		cls = type(self)
		if self in cls._observerAdapters:
			cls._observerAdapters.remove(self)
		if not cls._observerAdapters and cls._observerCallback is not None:
			inputCore.decide_executeGesture.unregister(cls._observerCallback)
			cls._observerCallback = None
		if not cls._observerAdapters and cls._rawKeyCallback is not None:
			inputCore.decide_handleRawKey.unregister(cls._rawKeyCallback)
			cls._rawKeyCallback = None
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

	@classmethod
	def _dispatchRawKey(cls, vkCode, scanCode, extended, pressed):
		"""Observe only key lifecycle facts; never consume or dispatch a gesture here."""
		for adapter in tuple(cls._observerAdapters):
			try:
				adapter._observeRawKey(vkCode, extended, pressed)
			except Exception:
				pass
		return True

	@staticmethod
	def _isClaimGesture(gesture):
		return NeovimAccessLink._SESSION_CLAIM_GESTURE.lower() in (
			identifier.lower() for identifier in getattr(gesture, "normalizedIdentifiers", ())
		)

	def _service(self):
		return NeovimAccessLink.getTerminalIntegrationService()

	@staticmethod
	def _physicalKey(gesture):
		vk_code = getattr(gesture, "vkCode", None)
		if not isinstance(vk_code, int):
			return None
		return vk_code, bool(getattr(gesture, "isExtended", False))

	@classmethod
	def _explorationAction(cls, gesture):
		main_key = getattr(gesture, "mainKeyName", "")
		if not isinstance(main_key, str):
			return None
		modifiers = getattr(gesture, "modifierNames", ())
		try:
			modifier_names = frozenset(name.lower() for name in modifiers if isinstance(name, str))
		except TypeError:
			return None
		return cls._EXPLORATION_ACTIONS.get((modifier_names, main_key.lower()))

	@staticmethod
	def _superScript(instance, gesture):
		return super(AppModule, instance).getScript(gesture)

	def _focusedExplorationContextAvailable(self, service, focus_obj, expected_identity=None):
		if getattr(focus_obj, "appModule", None) is not self:
			return False
		try:
			return bool(
				service.exploration_script_available(
					focus_obj,
					self,
					self._eventToken,
					expected_identity,
				)
			)
		except Exception:
			return False

	def getScript(self, gesture):
		"""Select contextual scripts through NVDA's standard gesture resolution."""
		action = self._explorationAction(gesture)
		physical_key = self._physicalKey(gesture)
		bare_repeat = (
			action is None
			and physical_key in self._explorationHeldKeys
			and not tuple(getattr(gesture, "modifierNames", ()))
		)
		if action is None and not bare_repeat:
			return self._superScript(self, gesture)
		if action is not None and not self._heldNvdaModifiers:
			return self._superScript(self, gesture)
		service = self._service()
		if service is None:
			return self._superScript(self, gesture)
		try:
			focus_obj = api.getFocusObject()
		except Exception:
			return self._superScript(self, gesture)
		expected_identity = self._explorationHeldKeys.get(physical_key) if bare_repeat else None
		if not self._focusedExplorationContextAvailable(service, focus_obj, expected_identity):
			return self._superScript(self, gesture)
		return self._suppressExplorationRepeatScript if bare_repeat else self._explorationScript

	def _observeRawKey(self, vk_code, extended, pressed):
		key = (vk_code, bool(extended))
		if keyboardHandler.isNVDAModifierKey(vk_code, bool(extended)):
			if pressed:
				self._heldNvdaModifiers.add(key)
				return
			self._heldNvdaModifiers.discard(key)
			if self._explorationActive and not self._heldNvdaModifiers:
				self._explorationActive = False
				service = self._service()
				if service is not None:
					queueHandler.queueFunction(
						queueHandler.eventQueue,
						self._handleExplorationModifierRelease,
						service,
					)
			return
		if vk_code in self._EXPLORATION_VK_CODES:
			if pressed:
				self._physicallyHeldExplorationKeys.add(key)
			else:
				self._physicallyHeldExplorationKeys.discard(key)
		if not pressed:
			self._explorationHeldKeys.pop(key, None)

	def _handleExplorationModifierRelease(self, originating_service):
		service = self._service()
		if service is not originating_service:
			try:
				originating_service.cancel_exploration(self._eventToken)
			except Exception:
				pass
			return
		try:
			focus_obj = api.getFocusObject()
		except Exception:
			focus_obj = None
		if focus_obj is None or not self._focusedExplorationContextAvailable(service, focus_obj):
			try:
				service.cancel_exploration(self._eventToken)
			except Exception:
				pass
			return
		try:
			service.release_exploration(focus_obj, self, self._eventToken)
		except Exception:
			try:
				service.cancel_exploration(self._eventToken)
			except Exception:
				pass

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
		self._explorationActive = False
		self._explorationHeldKeys.clear()
		self._physicallyHeldExplorationKeys.clear()
		self._heldNvdaModifiers.clear()
		service = self._service()
		if service is not None:
			try:
				service.cancel_exploration(self._eventToken)
			except Exception:
				pass
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

	def _executeExploration(self, gesture):
		action = self._explorationAction(gesture)
		service = self._service()
		try:
			focus_obj = api.getFocusObject()
		except Exception:
			focus_obj = None
		context_identity = None
		if action is not None and service is not None and focus_obj is not None:
			try:
				context_identity = service.explore_text(action, focus_obj, self, self._eventToken)
			except Exception:
				context_identity = None
		if context_identity is not None:
			physical_key = self._physicalKey(gesture)
			if physical_key in self._physicallyHeldExplorationKeys:
				self._explorationHeldKeys[physical_key] = context_identity
			self._explorationActive = bool(self._heldNvdaModifiers)
			if not self._explorationActive:
				try:
					service.release_exploration(focus_obj, self, self._eventToken)
				except Exception:
					try:
						service.cancel_exploration(self._eventToken)
					except Exception:
						pass
			return
		# This script was already selected for a confirmed Neovim pane. If the
		# context changed before execution, consuming the chord is safer than
		# forwarding a bare motion key that could move the real editor cursor.

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
