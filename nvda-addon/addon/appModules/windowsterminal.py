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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inputCore.decide_executeGesture.register(self._decideExecuteGesture)

    def terminate(self):
        try:
            inputCore.decide_executeGesture.unregister(self._decideExecuteGesture)
        except LookupError:
            pass
        super().terminate()

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
        description=_("Turn Neovim accessibility on or off and discover configured connections"),
        category=scriptCategory,
    )
    def script_toggleNeovimMode(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            self._prepareTerminalAction(plugin)
            plugin.action_toggleNeovimMode(gesture)

    @scriptHandler.script(
        description=_("Copy Neovim accessibility diagnostic report"),
        category=scriptCategory,
        gesture="kb:NVDA+alt+d",
    )
    def script_copyDiagnosticReport(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            plugin.action_copyDiagnosticReport(gesture)

    @scriptHandler.script(
        description=_("Read documentation for the selected Neovim completion item"),
        category=scriptCategory,
    )
    def script_readCompletionDocumentation(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            plugin.action_readCompletionDocumentation(gesture)

    @scriptHandler.script(
        description=_("Choose a server and connect this terminal to a new Neovim session"),
        category=scriptCategory,
    )
    def script_startConnectionInstance(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            self._prepareTerminalAction(plugin)
            plugin.action_startConnectionInstance(gesture)

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
        plugin._diagnostics.record(
            "sessionClaimGestureCaptured", source="decideExecuteGesture",
            terminal=plugin._identityFields(plugin._gate.focused),
        )
        queueHandler.queueFunction(
            queueHandler.eventQueue, self._handleObservedClaimGesture,
        )
        return True

    def _handleObservedClaimGesture(self):
        plugin = self._plugin()
        if plugin is None:
            return
        self._prepareTerminalAction(plugin)
        plugin.action_claimFocusedNeovimSession(None, forward_gesture=False)

    @scriptHandler.script(
        description=_("Disconnect the selected Neovim connection instance"),
        category=scriptCategory,
    )
    def script_disconnectConnectionInstance(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            plugin.action_disconnectConnectionInstance(gesture)

    @scriptHandler.script(
        description=_("Forget the temporary Neovim connection for the focused terminal"),
        category=scriptCategory,
    )
    def script_forgetTemporaryTerminalBinding(self, gesture):
        plugin = self._plugin()
        if plugin is not None:
            plugin.action_forgetTemporaryTerminalBinding(gesture)
