"""Windows Terminal adapter for the structured Neovim accessibility add-on.

NVDA loads this AppModule only for Windows Terminal.  Application events,
object overlays and input gestures therefore never participate in unrelated
applications.
"""

import api
import addonHandler
import appModuleHandler
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
            try:
                inputCore.decide_executeGesture.unregister(cls._observerCallback)
            except LookupError:
                pass
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
            identifier.lower()
            for identifier in getattr(gesture, "normalizedIdentifiers", ())
        )

    def _plugin(self):
        return NeovimAccessLink.getActivePlugin()

    def _prepareTerminalAction(self, plugin):
        plugin._refreshFocusedTerminalForAction(
            api.getFocusObject(), self, self._eventToken,
        )

    def _shouldUseNativeEvent(self, plugin, obj, event_name):
        try:
            return plugin._shouldUseNativeTerminalEvent(obj)
        except Exception as error:
            try:
                plugin._failOpenTerminalEvent(event_name, error)
            except Exception:
                pass
            return True

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        plugin = self._plugin()
        if plugin is None:
            return
        try:
            if (
                getattr(obj, "role", None) == NeovimAccessLink.controlTypes.Role.TERMINAL
                and plugin._identity(obj) is not None
            ):
                clsList.insert(0, NeovimAccessLink.StructuredTerminalBrailleOverlay)
        except Exception as error:
            try:
                plugin._failOpenTerminalEvent("chooseNVDAObjectOverlayClasses", error)
            except Exception:
                pass

    def event_gainFocus(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        try:
            decision = plugin._prepareTerminalFocus(
                obj, self._eventToken, app_module=self,
            )
        except Exception as error:
            try:
                plugin._failOpenTerminalEvent("gainFocus", error)
            except Exception:
                pass
            nextHandler()
            return
        nextHandler()
        try:
            plugin._finishTerminalFocus(decision)
        except Exception as error:
            try:
                plugin._failOpenTerminalEvent("gainFocusCompletion", error)
            except Exception:
                pass
            raise

    def event_appModule_loseFocus(self):
        plugin = self._plugin()
        if plugin is not None:
            try:
                plugin._terminalApplicationLostFocus(self._eventToken)
            except Exception as error:
                try:
                    plugin._failOpenTerminalEvent("appModuleLoseFocus", error)
                except Exception:
                    pass

    def event_textChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "textChange"):
            nextHandler()

    def event_typedCharacter(self, obj, nextHandler, ch):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "typedCharacter"):
            nextHandler()

    def event_UIA_notification(self, obj, nextHandler, **kwargs):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "UIA_notification"):
            nextHandler()

    def event_liveRegionChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "liveRegionChange"):
            nextHandler()

    def event_valueChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "valueChange"):
            nextHandler()

    def event_nameChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "nameChange"):
            nextHandler()

    def event_descriptionChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None or self._shouldUseNativeEvent(plugin, obj, "descriptionChange"):
            nextHandler()

    @scriptHandler.script(
        description=_("Copy Neovim accessibility diagnostic report"),
        category=scriptCategory,
        gesture="kb:NVDA+alt+d",
    )
    def script_copyDiagnosticReport(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            plugin.action_copyDiagnosticReport(gesture)

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
        plugin = self._plugin()
        if (
            plugin is None
            or not plugin._gate.manual_enabled
            or plugin._gate.focused is None
        ):
            return True
        identity = plugin._identity(focus_obj)
        if identity is None or identity != plugin._gate.focused:
            return True
        generation = plugin._captureObservedSessionClaim(identity)
        if generation is None:
            return True
        plugin._diagnostics.record(
            "sessionClaimGestureCaptured", source="decideExecuteGesture",
            terminal=plugin._identityFields(identity), generation=generation,
        )
        queueHandler.queueFunction(
            queueHandler.eventQueue, self._handleObservedClaimGesture,
            identity, generation,
        )
        return True

    def _handleObservedClaimGesture(self, identity, generation):
        plugin = self._plugin()
        if plugin is None:
            return
        self._prepareTerminalAction(plugin)
        plugin.action_claimFocusedNeovimSession(
            None, forward_gesture=False,
            expected_identity=identity, claim_generation=generation,
        )
