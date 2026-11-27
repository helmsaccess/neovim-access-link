"""Observe the focused Windows Terminal control from inside portable NVDA."""

import json
import os
from pathlib import Path

import addonHandler
import api
import buildVersion
import core
import globalPluginHandler
import winUser
import wx
from comtypes import COMError


WORK = Path(os.environ["NAL_HOSTED_FOCUS_WORK"])


def write_result(name, payload):
    pending = WORK / f"{name}.tmp"
    pending.write_text(json.dumps(payload), encoding="utf-8")
    pending.replace(WORK / name)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.timer = None
        core.postNvdaStartup.register(self.observe)

    def terminate(self):
        core.postNvdaStartup.unregister(self.observe)
        if self.timer is not None:
            self.timer.Stop()
        super().terminate()

    def observe(self):
        focused = self.focused_terminal()
        if focused is not None:
            ready = WORK / "nvda-focus.json"
            if not ready.exists():
                write_result(ready.name, focused)
            if (WORK / "key-received.txt").is_file():
                write_result("nvda-result.json", focused)
                return
        self.timer = wx.CallLater(100, self.observe)

    @staticmethod
    def focused_terminal():
        obj = api.getFocusObject()
        hwnd = winUser.getForegroundWindow()
        title = os.environ["NAL_HOSTED_FOCUS_TITLE"]
        if not obj or not hwnd or title not in winUser.getWindowText(hwnd):
            return None
        window_class = winUser.getClassName(hwnd)
        pid = winUser.getWindowThreadProcessID(hwnd)[0]
        if window_class != "CASCADIA_HOSTING_WINDOW_CLASS" or pid != getattr(obj, "processID", None):
            return None
        element = getattr(obj, "UIAElement", None)
        try:
            if element is None or element.cachedClassName != "TermControl" or not element.CurrentHasKeyboardFocus:
                return None
        except COMError:
            return None

        if not any(addon.name == "NeovimAccessLink" for addon in addonHandler.getRunningAddons()):
            return None
        from appModules import windowsterminal

        candidate_app = WORK / "profile" / "addons" / "NeovimAccessLink" / "appModules"
        if (not isinstance(obj.appModule, windowsterminal.AppModule)
                or not Path(windowsterminal.__file__).resolve().is_relative_to(candidate_app.resolve())):
            return None
        return {"nvda": buildVersion.version, "terminalPid": pid, "windowClass": window_class,
                "uiaClass": "TermControl", "keyboardFocus": True, "candidateAppModule": True}
