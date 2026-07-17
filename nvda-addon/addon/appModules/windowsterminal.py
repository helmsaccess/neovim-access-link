"""Windows Terminal adapter for the structured Neovim accessibility add-on.

NVDA loads this AppModule only for Windows Terminal.  Application events,
object overlays and input gestures therefore never participate in unrelated
applications.
"""

import api
import appModuleHandler
import inputCore
import queueHandler
import scriptHandler

from globalPlugins import nvimNvdaAccess


class AppModule(appModuleHandler.AppModule):
    scriptCategory = nvimNvdaAccess._PRODUCT_NAME
    _observerAdapters = []
    _observerCallback = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        plugin = nvimNvdaAccess.getActivePlugin()
        adapter = getattr(plugin, "_focusedAppModule", None) if plugin is not None else None
        if adapter not in cls._observerAdapters:
            adapter = cls._observerAdapters[-1] if len(cls._observerAdapters) == 1 else None
        return adapter._decideExecuteGesture(gesture) if adapter is not None else True

    def _plugin(self):
        return nvimNvdaAccess.getActivePlugin()

    def _prepareTerminalAction(self, plugin):
        plugin._refreshFocusedTerminalForAction(api.getFocusObject(), self)

    def _delegateEventFailOpen(self, plugin, method_name, nextHandler, *args, **kwargs):
        """Delegate an NVDA event while guaranteeing native handling once.

        An add-on failure must never prevent Windows Terminal's own event
        handler from starting or continuing LiveText output.  The guarded
        callback also avoids invoking ``nextHandler`` twice when an exception
        happens after the plug-in already delegated the event.
        """
        delegated = False

        def guardedNextHandler():
            nonlocal delegated
            if delegated:
                return
            delegated = True
            nextHandler()

        try:
            getattr(plugin, method_name)(*args, guardedNextHandler, **kwargs)
        except Exception as error:
            if delegated:
                raise
            try:
                plugin._failOpenTerminalEvent(method_name, error)
            except Exception:
                pass
            guardedNextHandler()

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        plugin = self._plugin()
        if plugin is not None:
            plugin._chooseNVDAObjectOverlayClasses(obj, clsList)

    def event_gainFocus(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(
            plugin, "_event_gainFocus", nextHandler, obj, app_module=self,
        )

    def event_appModule_loseFocus(self):
        plugin = self._plugin()
        if plugin is not None:
            plugin._event_appModule_loseFocus(self)

    def event_textChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(plugin, "_event_textChange", nextHandler, obj)

    def event_typedCharacter(self, obj, nextHandler, ch):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(
            plugin, "_event_typedCharacter", nextHandler, obj, ch=ch,
        )

    def event_UIA_notification(self, obj, nextHandler, **kwargs):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(
            plugin, "_event_UIA_notification", nextHandler, obj, **kwargs,
        )

    def event_liveRegionChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(plugin, "_event_liveRegionChange", nextHandler, obj)

    def event_valueChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(plugin, "_event_valueChange", nextHandler, obj)

    def event_nameChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(plugin, "_event_nameChange", nextHandler, obj)

    def event_descriptionChange(self, obj, nextHandler):
        plugin = self._plugin()
        if plugin is None:
            nextHandler()
            return
        self._delegateEventFailOpen(
            plugin, "_event_descriptionChange", nextHandler, obj,
        )

    @scriptHandler.script(
        description=_("Copy Neovim accessibility diagnostic report"),
        category=scriptCategory,
        gesture="kb:NVDA+alt+d",
    )
    def script_copyDiagnosticReport(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            plugin.action_copyDiagnosticReport(gesture)

    def _delegateLegacyConfiguredScript(self, gesture, action_name):
        """Keep user gestures saved against pre-dev.4 AppModule script IDs."""
        plugin = self._plugin()
        if plugin is not None:
            self._prepareTerminalAction(plugin)
            getattr(plugin, action_name)(gesture)

    # Deliberately undocumented: NVDA keeps resolving existing user gesture
    # assignments by these old AppModule script IDs, while the documented
    # global scripts provide the one always-visible configuration surface.
    def script_toggleNeovimMode(self, gesture):
        self._delegateLegacyConfiguredScript(gesture, "action_toggleNeovimMode")

    def script_readCompletionDocumentation(self, gesture):
        self._delegateLegacyConfiguredScript(
            gesture, "action_readCompletionDocumentation",
        )

    def script_copyNeovimSelection(self, gesture):
        self._delegateLegacyConfiguredScript(gesture, "action_copyNeovimSelection")

    def script_copyLastNeovimYank(self, gesture):
        self._delegateLegacyConfiguredScript(gesture, "action_copyLastNeovimYank")

    def script_pasteWindowsClipboard(self, gesture):
        self._delegateLegacyConfiguredScript(gesture, "action_pasteWindowsClipboard")

    def script_setNeovimRegisterFromWindowsClipboard(self, gesture):
        self._delegateLegacyConfiguredScript(
            gesture, "action_setNeovimRegisterFromWindowsClipboard",
        )

    def script_leaveDirectTerminalInput(self, gesture):
        self._delegateLegacyConfiguredScript(
            gesture, "action_leaveDirectTerminalInput",
        )

    def script_startConnectionInstance(self, gesture):
        self._delegateLegacyConfiguredScript(gesture, "action_startConnectionInstance")

    def script_disconnectConnectionInstance(self, gesture):
        self._delegateLegacyConfiguredScript(
            gesture, "action_disconnectConnectionInstance",
        )

    def script_forgetTemporaryTerminalBinding(self, gesture):
        self._delegateLegacyConfiguredScript(
            gesture, "action_forgetTemporaryTerminalBinding",
        )

    def _decideExecuteGesture(self, gesture):
        identifiers = tuple(
            identifier.lower()
            for identifier in getattr(gesture, "normalizedIdentifiers", ())
        )
        if nvimNvdaAccess._SESSION_CLAIM_GESTURE.lower() not in identifiers:
            return True
        plugin = self._plugin()
        if (
            plugin is None
            or not plugin._gate.manual_enabled
            or plugin._gate.focused is None
        ):
            return True
        identity = plugin._gate.focused
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
