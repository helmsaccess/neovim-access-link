from __future__ import annotations

import builtins
import gettext
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import threading
import types
import unittest
import wave
from unittest import mock
import zipfile

from tools.build_nvda_addon import build, validate_manifest
from tools import build_user_package
import buildVars


def add_remote_instance(manager, target_id, session_id, label, client):
    from globalPlugins.NeovimAccessLink.core.connection_targets import remote_ssh_target

    return manager.add_target(
        remote_ssh_target(target_id, label), session_id, label, client,
    )


class BuiltAddonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.config_path = pathlib.Path(self.temporary.name) / "config"
        self.config_path.mkdir()
        self.extract_path = pathlib.Path(self.temporary.name) / "addon"
        with zipfile.ZipFile(build()) as archive:
            archive.extractall(self.extract_path)
        self.messages: list[str] = []
        self.spoken: list[str] = []
        self.speechTextCalls: list[tuple[str, dict]] = []
        self.spelled: list[str] = []
        self.beeps: list[tuple[int, int]] = []
        self.soundFeeds: list[bytes] = []
        self.brailleMessages: list[str] = []
        self.speechCancellations = 0
        self.clipboard = ""
        self.menuLabels: list[str] = []
        self.preferencesMenuLabels: list[str] = []
        self.toolsMenuLabels: list[str] = []
        self.toolsMenuHandlers: list[object] = []
        self.focus = types.SimpleNamespace(
            processID=100, windowHandle=200, role=3, parent=None,
            appModule=types.SimpleNamespace(appName="windowsterminal"),
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: (42, 200, 4, 6),
            ),
        )
        builtins._ = lambda text: text
        self._install_mocks()
        sys.path.insert(0, str(self.extract_path))

    def tearDown(self) -> None:
        sys.path.remove(str(self.extract_path))
        for name in list(sys.modules):
            if (
                name == "globalPlugins" or name.startswith("globalPlugins.")
                or name == "appModules" or name.startswith("appModules.")
            ):
                del sys.modules[name]
        if hasattr(builtins, "_"):
            del builtins._
        self.temporary.cleanup()

    def _focusPlugin(self, plugin, obj=None) -> None:
        obj = obj or self.focus
        plugin._gate.focused = plugin._identity(obj)
        plugin._focusedTerminalObject = obj

    @staticmethod
    def _settingsSnapshot(plugin) -> dict:
        return plugin._settingsService.snapshot()

    @classmethod
    def _updateSettings(cls, plugin, updates: dict) -> None:
        values = cls._settingsSnapshot(plugin)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(values.get(key), dict):
                values[key].update(value)
            else:
                values[key] = value
        plugin._settingsService.update(values)

    def _terminalAdapter(self):
        from appModules.windowsterminal import AppModule

        adapter = AppModule()
        self.addCleanup(adapter.terminate)
        return adapter

    def _install_mocks(self) -> None:
        addon_handler = types.ModuleType("addonHandler")
        addon_handler.initTranslation = lambda: None
        addon_handler.getCodeAddon = lambda: types.SimpleNamespace(manifest=buildVars.manifest())
        sys.modules["addonHandler"] = addon_handler

        api = types.ModuleType("api")
        api.getFocusObject = lambda: self.focus
        def copy_to_clip(text, notify=False):
            self.clipboard = text
            return True
        api.copyToClip = copy_to_clip
        api.getClipData = lambda: self.clipboard
        sys.modules["api"] = api

        build_version = types.ModuleType("buildVersion")
        build_version.version = "2026.1.1"
        sys.modules["buildVersion"] = build_version

        braille = types.ModuleType("braille")
        class Region:
            def __init__(self):
                self.rawText = ""
                self.cursorPos = self.selectionStart = self.selectionEnd = None
                self.brailleSelectionStart = self.brailleSelectionEnd = None
                self.brailleToRawPos = []
            def update(self):
                self.brailleToRawPos = list(range(len(self.rawText)))
        braille.Region = Region
        braille.handler = types.SimpleNamespace(
            handleGainFocus=lambda *_args, **_kwargs: None,
            handleUpdate=lambda *_: None,
            message=self.brailleMessages.append,
        )
        sys.modules["braille"] = braille

        control_types = types.ModuleType("controlTypes")
        control_types.Role = types.SimpleNamespace(TERMINAL=3)
        sys.modules["controlTypes"] = control_types

        config = types.ModuleType("config")
        self.configSaves = 0
        class ConfigMock(dict):
            def __init__(inner_self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                inner_self.spec = {}
            def __getitem__(inner_self, key):
                if key == "NeovimAccessLink" and key not in inner_self:
                    inner_self[key] = {
                        "connections": "[]",
                        "feedback": {
                            "global": 3, "mode": 3, "delete": 3, "replace": 3,
                            "lineBoundary": 2, "fileBoundary": 3,
                            "lineCrossed": 2, "matchingError": 3, "clipboard": 3,
                        },
                    }
                return super().__getitem__(key)
            def save(inner_self): self.configSaves += 1
        config.conf = ConfigMock({
            "keyboard": {
                "speakTypedCharacters": 2, "speakTypedWords": 0,
                "alertForSpellingErrors": True,
            },
            "documentFormatting": {
                "reportLineIndentation": 2, "indentToneDuration": 40,
                "reportSpellingErrors2": 7,
            },
            "presentation": {"reportAutoSuggestionsWithSound": True},
            "audio": {"outputDevice": "default"},
        })
        class Action:
            def __init__(inner_self): inner_self.handlers = []
            def register(inner_self, handler): inner_self.handlers.append(handler)
            def unregister(inner_self, handler): inner_self.handlers.remove(handler)
            def notify(inner_self, **kwargs):
                for handler in tuple(inner_self.handlers): handler(**kwargs)
        config.post_configProfileSwitch = Action()
        sys.modules["config"] = config

        log_handler = types.ModuleType("logHandler")
        log_handler.log = types.SimpleNamespace(
            debug=lambda *_args, **_kwargs: None,
            info=lambda *_args, **_kwargs: None,
            exception=lambda *_args, **_kwargs: None,
        )
        sys.modules["logHandler"] = log_handler

        global_plugin_handler = types.ModuleType("globalPluginHandler")
        class Base:
            def __init__(self): self._gestureMap = {}
            def bindGesture(self, gesture, script_name): self._gestureMap[gesture] = script_name
            def removeGestureBinding(self, gesture):
                if gesture not in self._gestureMap: raise LookupError(gesture)
                del self._gestureMap[gesture]
            def terminate(self): pass
        global_plugin_handler.GlobalPlugin = Base
        sys.modules["globalPluginHandler"] = global_plugin_handler

        app_module_handler = types.ModuleType("appModuleHandler")
        class AppModuleBase:
            def terminate(inner_self): pass
        app_module_handler.AppModule = AppModuleBase
        sys.modules["appModuleHandler"] = app_module_handler

        input_core = types.ModuleType("inputCore")
        class Decider:
            def __init__(inner_self): inner_self.handlers = []
            def register(inner_self, handler): inner_self.handlers.append(handler)
            def unregister(inner_self, handler): inner_self.handlers.remove(handler)
        self.inputDecider = input_core.decide_executeGesture = Decider()
        self.rawKeyDecider = input_core.decide_handleRawKey = Decider()
        sys.modules["inputCore"] = input_core

        global_vars = types.ModuleType("globalVars")
        global_vars.appArgs = types.SimpleNamespace(configPath=str(self.config_path))
        global_vars.appDir = str(self.config_path)
        waves = self.config_path / "waves"
        waves.mkdir()
        for file_name in (
            "suggestionsOpened.wav", "suggestionsClosed.wav", "textError.wav",
            "focusMode.wav", "browseMode.wav", "error.wav",
        ):
            with wave.open(str(waves / file_name), "wb") as sound:
                sound.setnchannels(1)
                sound.setsampwidth(2)
                sound.setframerate(8000)
                sound.writeframes(b"\0\0" * 8)
        sys.modules["globalVars"] = global_vars

        nvwave = types.ModuleType("nvwave")
        nvwave.AudioPurpose = types.SimpleNamespace(SOUNDS="sounds")
        outer = self
        class WavePlayer:
            def __init__(self, **_kwargs): pass
            def feed(self, frames): outer.soundFeeds.append(frames)
            def close(self): pass
        nvwave.WavePlayer = WavePlayer
        sys.modules["nvwave"] = nvwave

        queue_handler = types.ModuleType("queueHandler")
        queue_handler.eventQueue = object()
        queue_handler.queueFunction = lambda _queue, function, *args, **_kwargs: function(*args)
        sys.modules["queueHandler"] = queue_handler

        script_handler = types.ModuleType("scriptHandler")
        def script(**kwargs):
            def decorate(function):
                function._test_script_kwargs = kwargs
                return function
            return decorate
        script_handler.script = script
        sys.modules["scriptHandler"] = script_handler

        speech = types.ModuleType("speech")
        def cancel_speech():
            self.speechCancellations += 1
        speech.cancelSpeech = cancel_speech
        speech.clearTypedWordBuffer = lambda: None
        def speak_text(text, **kwargs):
            self.spoken.append(text)
            self.speechTextCalls.append((text, kwargs))
        speech.speakText = speak_text
        speech.speakTypedCharacters = lambda text: self.spoken.append(text)
        def speak_spelling(text, **_kwargs):
            self.spelled.append(text)
            self.spoken.append(text)
        speech.speakSpelling = speak_spelling
        speech.__path__ = []
        sys.modules["speech"] = speech
        priorities = types.ModuleType("speech.priorities")
        class NvdaPriority:
            NORMAL = 0
            NEXT = 1
            NOW = 2
        priorities.SpeechPriority = NvdaPriority
        sys.modules["speech.priorities"] = priorities

        tones = types.ModuleType("tones")
        tones.beep = lambda frequency, duration: self.beeps.append((frequency, duration))
        sys.modules["tones"] = tones

        ui = types.ModuleType("ui")
        ui.message = self.messages.append
        sys.modules["ui"] = ui

        wx = types.ModuleType("wx")
        wx.ID_ANY = -1
        wx.ID_OK = 1
        wx.ID_CANCEL = 0
        wx.YES = 2
        wx.YES_NO = 4
        wx.ICON_QUESTION = 8
        wx.OK = 16
        wx.CANCEL = 32
        wx.ICON_WARNING = 64
        wx.ICON_INFORMATION = 128
        wx.ALL = 256
        wx.EXPAND = 512
        wx.LEFT = 1024
        wx.RIGHT = 2048
        wx.BOTTOM = 4096
        wx.ALIGN_RIGHT = 8192
        wx.EVT_MENU = object()
        wx.EVT_CHECKBOX = object()
        wx.EVT_CHECKLISTBOX = object()
        wx.EVT_BUTTON = object()
        wx.EVT_CHOICE = object()
        wx.NOT_FOUND = -1
        wx.VERTICAL = 1
        wx.HORIZONTAL = 2
        class PanelControl:
            def __init__(self, *_args, **_kwargs): self.sizer = None
            def SetSizer(self, value): self.sizer = value
        class NotebookControl:
            def __init__(self, *_args, **_kwargs): self.pages = []
            def AddPage(self, page, label): self.pages.append((page, label))
        wx.Panel = PanelControl
        wx.Notebook = NotebookControl
        class SizerControl:
            def __init__(self, *_args, **_kwargs): self.items = []
            def Add(self, *args, **kwargs): self.items.append((args, kwargs))
        wx.BoxSizer = SizerControl
        self.staticBoxLabels = []
        def static_box_sizer(*_args, **kwargs):
            self.staticBoxLabels.append(kwargs.get("label", ""))
            return object()
        wx.StaticBoxSizer = static_box_sizer
        wx.Choice = object
        class CheckBoxControl:
            def __init__(inner_self, *_args, **kwargs):
                inner_self.checked = False
                inner_self.label = kwargs.get("label", "")
                inner_self.focused = False
                inner_self.handlers = {}
                self.checkBoxControls.append(inner_self)
            def SetValue(self, value): self.checked = bool(value)
            def IsChecked(self): return self.checked
            def Bind(self, event, handler): self.handlers[event] = handler
            def SetFocus(self): self.focused = True
        wx.CheckBox = CheckBoxControl
        self.checkBoxControls = []
        self.staticTexts = []
        class StaticTextControl:
            def __init__(inner_self, *_args, **kwargs):
                inner_self.label = kwargs.get("label", "")
                self.staticTexts.append(inner_self.label)
            def Wrap(self, _width): pass
        wx.StaticText = StaticTextControl
        self.checkListSelections = []
        self.checkListBoxes = []
        class CheckListBoxControl:
            def __init__(inner_self, *_args, **kwargs):
                inner_self.choices = list(kwargs.get("choices", []))
                inner_self.checked = set()
                inner_self.name = ""
                inner_self.handlers = {}
                self.checkListBoxes.append(inner_self)
            def SetName(inner_self, value): inner_self.name = value
            def Check(inner_self, index, value=True):
                if value: inner_self.checked.add(index)
                else: inner_self.checked.discard(index)
            def IsChecked(inner_self, index): return index in inner_self.checked
            def GetCheckedItems(inner_self): return tuple(sorted(inner_self.checked))
            def Bind(inner_self, event, handler): inner_self.handlers[event] = handler
        wx.CheckListBox = CheckListBoxControl
        nvda_controls = types.ModuleType("gui.nvdaControls")
        nvda_controls.CustomCheckListBox = CheckListBoxControl
        sys.modules["gui.nvdaControls"] = nvda_controls
        self.modalDialogResults = []
        self.dialogs = []
        class DialogControl:
            def __init__(inner_self, _parent, **kwargs):
                inner_self.title = kwargs.get("title", "")
                inner_self.sizer = None
                inner_self.minSize = None
                self.dialogs.append(inner_self)
            def CreateButtonSizer(inner_self, style): return ("buttons", style)
            def SetSizerAndFit(inner_self, value): inner_self.sizer = value
            def SetMinSize(inner_self, value): inner_self.minSize = value
            def ShowModal(inner_self):
                if self.checkListSelections and self.checkListBoxes:
                    for index in self.checkListSelections.pop(0):
                        self.checkListBoxes[-1].Check(index)
                return self.modalDialogResults.pop(0) if self.modalDialogResults else wx.ID_CANCEL
            def Destroy(inner_self): pass
        wx.Dialog = DialogControl
        self.messageDialogs = []
        class MessageDialogControl:
            def __init__(inner_self, _parent, message, title, *args, **kwargs):
                inner_self.message, inner_self.title = message, title
                inner_self.style = args[0] if args else kwargs.get("style", 0)
                inner_self.shown = False
                self.messageDialogs.append(inner_self)
            def Show(inner_self): inner_self.shown = True; return True
            def ShowModal(inner_self): return wx.ID_OK
            def Destroy(inner_self): pass
        wx.MessageDialog = MessageDialogControl
        self.singleChoiceDialogs = []
        self.singleChoiceSelections = []
        class SingleChoiceDialog:
            def __init__(inner_self, _parent, message, title, choices):
                inner_self.message = message
                inner_self.title = title
                inner_self.choices = list(choices)
                inner_self.selection = 0
                self.singleChoiceDialogs.append(inner_self)
            def SetSelection(inner_self, value): inner_self.selection = value
            def GetSelection(inner_self): return inner_self.selection
            def ShowModal(inner_self):
                if self.singleChoiceSelections:
                    inner_self.selection = self.singleChoiceSelections.pop(0)
                return wx.ID_OK
            def Destroy(inner_self): pass
        wx.SingleChoiceDialog = SingleChoiceDialog
        self.messageBoxAnswers = []
        self.messageBoxes = []
        def message_box(*args, **kwargs):
            self.messageBoxes.append((args, kwargs))
            return self.messageBoxAnswers.pop(0) if self.messageBoxAnswers else wx.YES
        wx.MessageBox = message_box
        wx.CallAfter = lambda function, *args, **kwargs: function(*args, **kwargs)
        wx.CallLater = lambda _delay, function, *args, **kwargs: function(*args, **kwargs)
        sys.modules["wx"] = wx

        class MenuItem:
            def __init__(self, identifier): self.identifier = identifier
            def GetId(self): return self.identifier

        class Menu:
            def __init__(inner_self, labels): inner_self.next_id = 1; inner_self.labels = labels
            def Append(inner_self, _identifier, label):
                self.menuLabels.append(label)
                inner_self.labels.append(label)
                item = MenuItem(inner_self.next_id)
                inner_self.next_id += 1
                return item
            def Remove(inner_self, _identifier): pass

        class Tray:
            def __init__(inner_self):
                inner_self.preferencesMenu = Menu(self.preferencesMenuLabels)
                inner_self.toolsMenu = Menu(self.toolsMenuLabels)
            def Bind(inner_self, _event, handler, _item):
                self.toolsMenuHandlers.append(handler)
            def Unbind(inner_self, *_args, **_kwargs): return True

        gui = types.ModuleType("gui")
        gui.__path__ = []
        gui.MessageDialog = MessageDialogControl
        self.settingsDialogsOpened = []
        gui.mainFrame = types.SimpleNamespace(
            sysTrayIcon=Tray(),
            popupSettingsDialog=lambda *args: self.settingsDialogsOpened.append(args),
        )
        def run_script_modal_dialog(dialog, callback):
            try:
                callback(dialog.ShowModal())
            finally:
                dialog.Destroy()
        gui.runScriptModalDialog = run_script_modal_dialog
        class ChoiceControl:
            def __init__(self): self.selection = 0; self.enabled = True
            def SetSelection(self, value): self.selection = value
            def GetSelection(self): return self.selection
            def Enable(self, value): self.enabled = bool(value)
            def Bind(self, *_args, **_kwargs): pass
            def SetItems(self, items): self.items = list(items)
        class ButtonControl:
            def __init__(self): self.enabled = True
            def Bind(self, *_args, **_kwargs): pass
            def Enable(self, value): self.enabled = bool(value)
        class ButtonHelper:
            def __init__(self, *_args, **_kwargs): self.buttons = []
            def addButton(self, *_args, **_kwargs):
                button = ButtonControl()
                self.buttons.append(button)
                return button
        class BoxSizerHelper:
            def __init__(self, *_args, **_kwargs): pass
            def addLabeledControl(self, *_args, **_kwargs): return ChoiceControl()
            def addItem(self, item): return item
        gui.guiHelper = types.SimpleNamespace(BoxSizerHelper=BoxSizerHelper, ButtonHelper=ButtonHelper)
        sys.modules["gui"] = gui
        settings_dialogs = types.ModuleType("gui.settingsDialogs")
        class SettingsPanel:
            def _validationErrorMessageBox(inner_self, *_args, **_kwargs): pass
        self.settingsCategoryClasses = []
        settings_dialogs.SettingsPanel = SettingsPanel
        settings_dialogs.NVDASettingsDialog = types.SimpleNamespace(categoryClasses=self.settingsCategoryClasses)
        sys.modules["gui.settingsDialogs"] = settings_dialogs

        global_plugins = types.ModuleType("globalPlugins")
        global_plugins.__path__ = [str(self.extract_path / "globalPlugins")]
        sys.modules["globalPlugins"] = global_plugins

        app_modules = types.ModuleType("appModules")
        app_modules.__path__ = [str(self.extract_path / "appModules")]
        sys.modules["appModules"] = app_modules

    def test_manifest_uses_scalar_strings_accepted_by_nvda_parser(self) -> None:
        manifest = validate_manifest(self.extract_path / "manifest.ini")
        self.assertEqual(buildVars.manifest(), dict(manifest))
        self.assertEqual("NeovimAccessLink", manifest["name"])
        self.assertEqual(buildVars.store_version(), manifest["version"])
        self.assertNotIn("dev", manifest["version"])

    def test_archive_contains_only_the_new_addon_identity(self) -> None:
        with zipfile.ZipFile(build()) as archive:
            names = archive.namelist()
        self.assertIn("globalPlugins/NeovimAccessLink/__init__.py", names)
        self.assertFalse(any(
            name.startswith("globalPlugins/nvimNvdaAccess/") for name in names
        ))

    def test_built_addon_local_discovery_does_not_open_probe_channels(self) -> None:
        core = self.extract_path / "globalPlugins" / "NeovimAccessLink" / "core"
        self.assertFalse((core / "registry_probe.py").exists())
        source = (core / "local_sessions.py").read_text(encoding="utf-8")
        self.assertNotIn("query_registry_nonce", source)

    def test_built_addon_uses_nvda_windows_adapters_without_private_dll_declarations(self) -> None:
        plugin = self.extract_path / "globalPlugins" / "NeovimAccessLink"
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (plugin / "__init__.py", plugin / "nvda_windows.py", plugin / "core" / "local_sessions.py")
        )
        self.assertNotIn("ctypes.WinDLL", sources)
        self.assertNotIn("import ctypes", sources)
        self.assertIn("from winBindings import kernel32", sources)
        self.assertIn("import winUser", sources)

    def test_nvda_ui_registration_and_component_management_are_separate_from_global_plugin(self) -> None:
        plugin = self.extract_path / "globalPlugins" / "NeovimAccessLink"
        global_source = (plugin / "__init__.py").read_text(encoding="utf-8")
        ui_source = (plugin / "nvda_ui.py").read_text(encoding="utf-8")
        settings_source = (plugin / "settings_service.py").read_text(encoding="utf-8")

        self.assertIn("class NvdaUiManager", ui_source)
        self.assertIn("class SettingsService", settings_source)
        self.assertNotIn("self._plugin", ui_source)
        self.assertNotIn("GlobalPlugin", ui_source)
        self.assertIn("self._nvdaUi.register()", global_source)
        self.assertIn("self._nvdaUi.unregister()", global_source)
        for implementation in (
            "def _registerSettingsPanel", "def _installMenus",
            "def _promptConnectionProfile", "def _showConnectionProfileDialog",
            "def _runServerInstalls", "def _runComponentRemovals",
        ):
            self.assertNotIn(implementation, global_source)
            self.assertIn(implementation, ui_source)

    def test_terminal_focus_state_has_one_non_global_owner(self) -> None:
        plugin = self.extract_path / "globalPlugins" / "NeovimAccessLink"
        global_source = (plugin / "__init__.py").read_text(encoding="utf-8")
        focus_source = (plugin / "terminal_focus.py").read_text(encoding="utf-8")
        facade_source = (plugin / "terminal_integration.py").read_text(encoding="utf-8")

        self.assertIn("class TerminalFocusService", focus_source)
        self.assertNotIn("GlobalPlugin", focus_source)
        for field in (
            "self._focusedTerminalObject =",
            "self._focusedAppModule =",
            "self._focusedAdapterToken =",
            "self._terminalFocusGeneration =",
            "self._terminalIdentityElements =",
            "self._terminalLifecycleCall =",
            "self._terminalLifecycleMisses =",
        ):
            self.assertNotIn(field, global_source)
        self.assertIn("self._focusService.prepare_focus", facade_source)
        self.assertIn("self._focusService.finish_focus", facade_source)
        self.assertIn("self._focusService.lose_focus", facade_source)
        self.assertNotIn("self._runtime._prepareTerminalFocus", facade_source)

    def test_session_claim_authorization_has_one_non_global_owner(self) -> None:
        plugin = self.extract_path / "globalPlugins" / "NeovimAccessLink"
        global_source = (plugin / "__init__.py").read_text(encoding="utf-8")
        claim_source = (plugin / "session_claim.py").read_text(encoding="utf-8")
        facade_source = (plugin / "terminal_integration.py").read_text(encoding="utf-8")

        self.assertIn("class SessionClaimService", claim_source)
        self.assertNotIn("GlobalPlugin", claim_source)
        self.assertNotIn("self._claimGestureGeneration =", global_source)
        self.assertNotIn("self._pendingObservedClaim = None", global_source)
        self.assertIn("self._claimService.authorize", facade_source)
        self.assertIn("self._claimService.cancel", facade_source)
        self.assertNotIn("self._runtime._captureObservedSessionClaim", facade_source)
        self.assertNotIn("self._runtime._cancelObservedSessionClaim", facade_source)
        self.assertIn("ThreadPoolExecutor", claim_source)
        self.assertIn("self._startWorker", claim_source)
        self.assertIn("self._queueMainThread", claim_source)
        self.assertIn("class ClaimTransition", claim_source)
        self.assertIn("self._sessionClaimService.consume_transition", global_source)
        self.assertNotIn("pairing_selected =", global_source)
        self.assertNotIn("self._sessionDiscoveryGeneration =", global_source)
        self.assertIn("def begin_discovery", claim_source)
        self.assertIn("self._sessionClaimService.is_discovery_current", global_source)
        self.assertIn("self._sessionClaimService.start_local_discovery", global_source)
        self.assertIn("self._sessionClaimService.start_remote_discovery", global_source)
        self.assertIn("class DiscoverySelection", claim_source)
        self.assertIn("self._sessionClaimService.resolve_local_discovery", global_source)
        self.assertIn("self._sessionClaimService.resolve_remote_discovery", global_source)
        self.assertIn("class ConnectionPlan", claim_source)
        self.assertIn("class ConnectionStartResult", claim_source)
        self.assertIn("self._sessionClaimService.plan_local_connection", global_source)
        self.assertIn("self._sessionClaimService.plan_remote_connection", global_source)
        self.assertIn("self._sessionClaimService.start_connection", global_source)
        self.assertIn("self._sessionClaimService.select_connection", global_source)
        self.assertIn("self._sessionClaimService.disconnect_connection", global_source)
        self.assertIn("self._sessionClaimService.activate_remembered_binding", global_source)
        self.assertIn("self._sessionClaimService.plan_remembered_state_request", global_source)
        self.assertNotIn("self._instanceManager.add_target(", global_source)
        self.assertNotIn("self._instanceManager.remove(", global_source)
        self.assertNotIn('name="nvim-nvda-local-session-list"', global_source)
        self.assertNotIn('name="nvim-nvda-session-list"', global_source)
        self.assertNotIn("ThreadPoolExecutor", global_source)

    def test_nvda_ui_manager_accepts_only_narrow_dependencies(self) -> None:
        from globalPlugins.NeovimAccessLink.nvda_ui import NvdaUiManager

        class FakeSettings:
            def snapshot(inner_self):
                return {"connections": [], "feedback": {}, "focusAnnouncement": 2}

            def update(inner_self, _values):
                return types.SimpleNamespace(claim_inventory_started=False)

            def save(inner_self):
                pass

        settings = FakeSettings()
        diagnostics = []
        password = lambda _profile: ""
        askpass = lambda: "askpass.cmd"
        manager = NvdaUiManager(
            settings,
            record_diagnostic=lambda *args, **kwargs: diagnostics.append((args, kwargs)),
            password_for_profile=password,
            askpass_path=askpass,
            product_name=buildVars.manifest()["summary"],
            package_dir="package",
            feedback_defaults={"global": 3},
            focus_announcement_default=2,
        )

        self.assertIs(settings, manager._settingsService)
        self.assertIs(password, manager._passwordForProfile)
        self.assertIs(askpass, manager._askpassPath)
        self.assertFalse(hasattr(manager, "_plugin"))

        manager.register()
        manager.register()
        self.assertEqual(2, len(manager._menuItems))
        self.assertEqual(1, len(self.settingsCategoryClasses))
        manager.unregister()
        manager.unregister()
        self.assertEqual([], manager._menuItems)
        self.assertEqual([], self.settingsCategoryClasses)

    def test_nvda_presentation_delivery_is_separate_from_global_plugin(self) -> None:
        plugin = self.extract_path / "globalPlugins" / "NeovimAccessLink"
        global_source = (plugin / "__init__.py").read_text(encoding="utf-8")
        presentation_source = (plugin / "nvda_presentation.py").read_text(
            encoding="utf-8",
        )

        self.assertIn("class NvdaPresentation", presentation_source)
        self.assertIn("self._presentation.deliver_actions(", global_source)
        self.assertNotIn("def _play_action_sound", global_source)
        self.assertIn("def _play_action_sound", presentation_source)
        self.assertNotIn("SuggestionSoundCache(", global_source)
        self.assertIn("SuggestionSoundCache(", presentation_source)

    def test_global_plugin_composes_connection_coordinator_without_duplicate_state(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_coordinator import ConnectionCoordinator

        plugin = GlobalPlugin()

        self.assertIsInstance(plugin._connectionCoordinator, ConnectionCoordinator)
        self.assertIs(plugin._instanceManager, plugin._connectionCoordinator.instances)
        self.assertIs(plugin._gate, plugin._connectionCoordinator.gate)
        self.assertIs(plugin._planner, plugin._connectionCoordinator.planner)
        self.assertIs(plugin._currentState, plugin._connectionCoordinator.current_state)
        self.assertIs(plugin._typedWord, plugin._connectionCoordinator.typed_word)
        self.assertIs(
            plugin._rememberedTerminalBindings,
            plugin._connectionCoordinator.remembered_terminal_bindings,
        )
        for legacy_field in (
            "_client", "_connected", "_lastConnectionState", "_instanceManager",
            "_rememberedTerminalBindings", "_rememberOfferInstances",
            "_authenticatedInstances", "_instanceTerminalPassthrough",
            "_activeInstanceId", "_instanceRuntimeStates", "_pendingInstanceFullStates",
            "_gate", "_planner", "_pendingFocusContexts", "_pendingClipboardRequests",
            "_pendingTerminalControlRequests", "_transportCapabilities",
            "_focusContextRequestId", "_clipboardRequestId", "_terminalControlRequestId",
            "_currentState", "_lastMode", "_typedWord", "_typedPosition",
            "_menuDocumentation",
        ):
            self.assertNotIn(legacy_field, vars(plugin))

        plugin.terminate()

    def test_service_registration_survives_stale_plugin_termination(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, getTerminalIntegrationService
        from globalPlugins.NeovimAccessLink.terminal_integration import TerminalIntegrationService

        first = GlobalPlugin()
        first_service = getTerminalIntegrationService()
        self.assertIsInstance(first_service, TerminalIntegrationService)
        self.assertIsNot(first, first_service)

        second = GlobalPlugin()
        second_service = getTerminalIntegrationService()
        self.assertIsInstance(second_service, TerminalIntegrationService)
        self.assertIsNot(second, second_service)
        self.assertIsNot(first_service, second_service)

        first.terminate()
        self.assertIs(second_service, getTerminalIntegrationService())

        second.terminate()
        self.assertIsNone(getTerminalIntegrationService())

    def test_service_is_published_only_after_process_wide_ui_and_config_registration(self) -> None:
        import config
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        observed = []
        original_publish = addon_module._serviceRegistrar.publish

        def publish(service):
            observed.append({
                "service": service,
                "menus": len(self.toolsMenuLabels),
                "settingsPanels": len(self.settingsCategoryClasses),
                "profileHandlers": len(config.post_configProfileSwitch.handlers),
            })
            return original_publish(service)

        with mock.patch.object(addon_module._serviceRegistrar, "publish", side_effect=publish):
            plugin = GlobalPlugin()

        self.assertEqual(1, len(observed))
        self.assertIs(plugin._terminalIntegrationService, observed[0]["service"])
        self.assertIsNot(plugin, observed[0]["service"])
        self.assertEqual(2, observed[0]["menus"])
        self.assertEqual(1, observed[0]["settingsPanels"])
        self.assertEqual(1, observed[0]["profileHandlers"])
        plugin.terminate()

    def test_global_teardown_unpublishes_before_opening_gate_and_shared_cleanup(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        order = []
        original_unpublish = addon_module._serviceRegistrar.unpublish
        original_disable = plugin._gate.disable
        original_stop_client = plugin._stopClient
        original_unregister = plugin._nvdaUi.unregister
        original_close = plugin._presentation.close

        with (
            mock.patch.object(
                addon_module._serviceRegistrar,
                "unpublish",
                side_effect=lambda *args: order.append("unpublish") or original_unpublish(*args),
            ),
            mock.patch.object(
                plugin._gate,
                "disable",
                side_effect=lambda: order.append("gate") or original_disable(),
            ),
            mock.patch.object(
                plugin,
                "_stopClient",
                side_effect=lambda: order.append("client") or original_stop_client(),
            ),
            mock.patch.object(
                plugin._nvdaUi,
                "unregister",
                side_effect=lambda: order.append("ui") or original_unregister(),
            ),
            mock.patch.object(
                plugin._presentation,
                "close",
                side_effect=lambda: order.append("presentation") or original_close(),
            ),
        ):
            plugin.terminate()

        self.assertEqual(["unpublish", "gate", "client", "ui", "presentation"], order)

    def test_service_replacement_during_native_focus_keeps_new_service_current_and_open(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin, getTerminalIntegrationService

        first = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        replacement = []
        native = []

        def replace_during_native_focus():
            native.append(True)
            replacement.append(GlobalPlugin())

        adapter.event_gainFocus(self.focus, replace_during_native_focus)

        second = replacement[0]
        self.assertEqual([True], native)
        self.assertIs(second._terminalIntegrationService, getTerminalIntegrationService())
        self.assertIsNone(second._gate.focused)
        self.assertFalse(second._gate.suppression_active)
        self.assertFalse(first._gate.suppression_active)
        first.terminate()
        self.assertIs(second._terminalIntegrationService, getTerminalIntegrationService())
        adapter.terminate()
        second.terminate()

    def test_nvda_window_identity_adapter_is_conclusive_only_for_matching_live_window(self) -> None:
        from globalPlugins.NeovimAccessLink import nvda_windows
        from globalPlugins.NeovimAccessLink.core.gate import TerminalIdentity

        identity = TerminalIdentity(100, 200, "windowsTerminal", (42, 200, 4, 6))
        live = types.SimpleNamespace(
            isWindow=lambda _handle: True,
            getWindowThreadProcessID=lambda _handle: (100, 7),
        )
        wrong_process = types.SimpleNamespace(
            isWindow=lambda _handle: True,
            getWindowThreadProcessID=lambda _handle: (101, 7),
        )
        closed = types.SimpleNamespace(
            isWindow=lambda _handle: False,
            getWindowThreadProcessID=lambda _handle: (_ for _ in ()).throw(AssertionError()),
        )
        uncertain = types.SimpleNamespace(
            isWindow=lambda _handle: (_ for _ in ()).throw(OSError()),
        )
        self.assertTrue(nvda_windows.windowIdentityExists(identity, _winUser=live))
        self.assertFalse(nvda_windows.windowIdentityExists(identity, _winUser=wrong_process))
        self.assertFalse(nvda_windows.windowIdentityExists(identity, _winUser=closed))
        self.assertIsNone(nvda_windows.windowIdentityExists(identity, _winUser=uncertain))

    def test_nvda_process_adapter_distinguishes_live_ended_denied_and_unknown(self) -> None:
        from globalPlugins.NeovimAccessLink import nvda_windows

        handles = {1: 101, 2: 102, 3: 0, 4: 0, 5: 0}
        errors = {3: 5, 4: 87, 5: 123}
        active_pid = [0]
        closed = []

        def open_process(_access, _inherit, pid):
            active_pid[0] = pid
            return handles[pid]

        kernel32 = types.SimpleNamespace(
            OpenProcess=open_process,
            GetLastError=lambda: errors.get(active_pid[0], 0),
        )
        win_kernel = types.SimpleNamespace(
            GetExitCodeProcess=lambda handle: 259 if handle == 101 else 0,
            closeHandle=closed.append,
        )
        check = lambda pid: nvda_windows.processAlive(
            pid,
            _kernel32=kernel32,
            _winKernel=win_kernel,
        )
        self.assertTrue(check(1))
        self.assertFalse(check(2))
        self.assertIsNone(check(3), "access denied is uncertain")
        self.assertFalse(check(4), "an invalid PID is conclusively dead")
        self.assertIsNone(check(5), "an unknown OpenProcess failure is uncertain")
        self.assertEqual([101, 102], closed)

    def test_local_session_lister_receives_nvda_process_adapter(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module

        callbacks = []

        class Lister:
            def __init__(self, *, process_alive):
                callbacks.append(process_alive)

        with mock.patch.object(addon_module, "LocalSessionLister", Lister):
            self.assertIsInstance(addon_module._localSessionLister(), Lister)
        self.assertEqual([addon_module.processAlive], callbacks)

    def test_bundled_neovim_plugin_supports_old_and_new_utfindex_signatures(self) -> None:
        lua = (
            self.extract_path / "globalPlugins" / "NeovimAccessLink" / "resources"
            / "neovim-plugin" / "lua" / "nvim_nvda" / "state.lua"
        ).read_text(encoding="utf-8")
        self.assertIn('vim.fn.has("nvim-0.11")', lua)
        self.assertIn('vim.str_utfindex(line, "utf-32", byte_column, false)', lua)
        self.assertIn("vim.str_utfindex(line, byte_column)", lua)

    def test_bundled_snapshot_failure_closes_rpc_channel_fail_open(self) -> None:
        lua = (
            self.extract_path / "globalPlugins" / "NeovimAccessLink" / "resources"
            / "neovim-plugin" / "lua" / "nvim_nvda" / "init.lua"
        ).read_text(encoding="utf-8")
        self.assertIn("pcall(state.snapshot, reason)", lua)
        self.assertIn("pcall(vim.fn.chanclose, channel)", lua)

    def test_bundled_key_observer_contains_errors_and_records_only_f12_metadata(self) -> None:
        lua = (
            self.extract_path / "globalPlugins" / "NeovimAccessLink" / "resources"
            / "neovim-plugin" / "lua" / "nvim_nvda" / "init.lua"
        ).read_text(encoding="utf-8")
        self.assertIn("local observer_ok, observer_result = pcall(function()", lua)
        self.assertIn("local claim_ok, claim_error = pcall", lua)
        self.assertIn("key_observer_diagnostics.translatedTyped = typed_translated", lua)
        self.assertIn("key_observer_diagnostics.claimKeyConsumed", lua)
        self.assertIn('vim.keymap.set("i", component_config.sessionClaim.neovimKey', lua)
        self.assertIn('return ""', lua)
        self.assertIn("key_observer_diagnostics.promptClass", lua)
        self.assertNotIn("key_observer_diagnostics.promptText", lua)
        setup_body = lua.split("function M.setup()", 1)[1].split("vim.on_key", 1)[0]
        register_body = lua.split("function M.register_channel", 1)[1].split(
            "function M.unregister_channel", 1,
        )[0]
        self.assertNotIn("setup_ui_events()", setup_body)
        self.assertIn("setup_ui_events()", register_body)
        self.assertIn('claim_mode:sub(1, 1) == "r"', lua)
        self.assertNotIn("key_observer_diagnostics.normalKey", lua)

    def test_built_plugin_imports_without_source_protocol_registry_package(self) -> None:
        real_import = builtins.__import__

        def isolated_import(name, *args, **kwargs):
            if name == "nvim_nvda_protocol.registry_probe":
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)

        with mock.patch.object(builtins, "__import__", side_effect=isolated_import):
            from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self.assertIsNotNone(plugin)
        plugin.terminate()

    def test_product_metadata_drives_archive_name_and_has_one_source_literal(self) -> None:
        archive = build()
        metadata = buildVars.manifest()
        self.assertEqual(
            f"{metadata['name']}-{buildVars.artifact_version()}.nvda-addon",
            archive.name,
        )
        self.assertEqual(
            f"{buildVars.product_slug()}-{buildVars.artifact_version()}-user.tar.gz",
            build_user_package.build().name,
        )
        with mock.patch.object(buildVars, "development_build", 1):
            self.assertRegex(
                buildVars.development_version(include_metadata=False),
                r"^\d+\.\d+\.\d+-dev\.\d+$",
            )
        for pattern in ("*.py", "*.sh"):
            for source in pathlib.Path(".").rglob(pattern):
                if source == pathlib.Path("buildVars.py") or any(
                    part in {"dist", "build", ".git"} for part in source.parts
                ):
                    continue
                contents = source.read_text(encoding="utf-8")
                self.assertNotIn(metadata["summary"], contents, source)
                self.assertNotIn(metadata["author"], contents, source)
                self.assertNotIn(metadata["version"], contents, source)

    def test_built_addon_keeps_store_and_diagnostic_versions_separate(self) -> None:
        build_info = (
            self.extract_path / "globalPlugins" / "NeovimAccessLink" / "build_info.py"
        ).read_text(encoding="utf-8")
        self.assertIn(repr(buildVars.artifact_version()), build_info)
        with mock.patch.object(buildVars, "development_build", 1):
            self.assertNotEqual(buildVars.store_version(), buildVars.artifact_version())
        with mock.patch.object(buildVars, "development_build", None):
            self.assertEqual(buildVars.store_version(), buildVars.artifact_version())

    def test_linux_package_rejects_mismatched_claim_gestures(self) -> None:
        config_path = pathlib.Path(self.temporary.name) / "bad-linux-components.json"
        config_path.write_text(
            '{"format":1,"sessionClaim":{"neovimKey":"<F9>","nvdaGesture":"kb:f12"}}',
            encoding="utf-8",
        )
        with mock.patch.object(build_user_package, "COMPONENT_CONFIG", config_path):
            with self.assertRaisesRegex(RuntimeError, "inconsistent"):
                build_user_package.linux_component_config()

    def test_shared_component_config_changes_the_claim_function_key(self) -> None:
        config_path = (
            self.extract_path / "globalPlugins" / "NeovimAccessLink" / "resources"
            / "linux-components.json"
        )
        config_path.write_text(
            '{"format":1,"sessionClaim":{"neovimKey":"<F9>","nvdaGesture":"kb:f9"}}',
            encoding="utf-8",
        )
        from globalPlugins import NeovimAccessLink

        self.assertEqual("kb:f9", NeovimAccessLink._SESSION_CLAIM_GESTURE)

    def test_addon_reuses_nvda_sounds_and_bundles_only_cc0_editor_earcons(self) -> None:
        with zipfile.ZipFile(build()) as archive:
            waves = sorted(name.rsplit("/", 1)[-1] for name in archive.namelist() if name.endswith(".wav"))
            self.assertEqual([
                "delete.wav", "fileEnd.wav", "fileStart.wav", "lineCrossed.wav",
                "lineEnd.wav", "lineStart.wav", "replace.wav",
            ], waves)
            self.assertIn("globalPlugins/NeovimAccessLink/resources/sounds/LICENSE.txt", archive.namelist())
            self.assertIn("LICENSE", archive.namelist())
            self.assertIn("globalPlugins/NeovimAccessLink/resources/ssh-askpass.cmd", archive.namelist())

    def test_built_addon_contains_compiled_german_gettext_catalog_only(self) -> None:
        locale = self.extract_path / "locale" / "de"
        mo_path = locale / "LC_MESSAGES" / "nvda.mo"
        self.assertTrue(mo_path.is_file())
        self.assertTrue((locale / "manifest.ini").is_file())
        self.assertFalse(any(self.extract_path.rglob("*.po")))
        self.assertFalse(any(self.extract_path.rglob("*.pot")))
        with mo_path.open("rb") as stream:
            translations = gettext.GNUTranslations(stream)
        self.assertEqual("Verbindungen", translations.gettext("Connections"))
        self.assertEqual(
            "Lokale Neovim-Sitzungen konnten nicht aufgelistet werden",
            translations.gettext("Could not list local Neovim sessions"),
        )

    def test_addon_contains_complete_linux_package_and_shared_configuration(self) -> None:
        with zipfile.ZipFile(build()) as archive:
            resource = "globalPlugins/NeovimAccessLink/resources/"
            config_bytes = archive.read(resource + "linux-components.json")
            package_bytes = archive.read(resource + "server-user.tar.gz")
            addon_names = archive.namelist()
        self.assertIn(resource + "neovim-plugin/plugin/nvim_nvda.lua", addon_names)
        self.assertIn(resource + "neovim-plugin/lua/nvim_nvda/session.lua", addon_names)
        self.assertFalse(any("neovim-plugin/tests/" in name for name in addon_names))
        config = json.loads(config_bytes)
        self.assertEqual(1, config["format"])
        self.assertEqual("<F12>", config["sessionClaim"]["neovimKey"])
        self.assertEqual("kb:f12", config["sessionClaim"]["nvdaGesture"])
        with tarfile.open(fileobj=io.BytesIO(package_bytes), mode="r:gz") as package:
            names = package.getnames()
            config_member = next(name for name in names if name.endswith("/config/linux-components.json"))
            packaged_config = package.extractfile(config_member)
            self.assertIsNotNone(packaged_config)
            self.assertEqual(config_bytes, packaged_config.read())
            self.assertTrue(any(name.endswith("/bin/nvim-nvda-bridge") for name in names))
            self.assertTrue(any(name.endswith("/install.py") for name in names))
            self.assertTrue(any(name.endswith("/plugin/nvim_nvda.lua") for name in names))
            self.assertTrue(any(name.endswith("/LICENSE") for name in names))
            extraction = pathlib.Path(self.temporary.name) / "linux-package"
            package.extractall(extraction, filter="data")
        source = next(extraction.iterdir())
        prefix = pathlib.Path(self.temporary.name) / "linux-prefix"
        subprocess.run(
            [sys.executable, str(source / "install.py"), "--prefix", str(prefix)],
            check=True, capture_output=True, text=True,
        )
        installed_config = prefix / "share" / "nvim-nvda" / "linux-components.json"
        installed_plugin_config = (
            prefix / "share" / "nvim" / "site" / "pack" / "nvim-nvda" / "start"
            / "nvim-nvda" / "config" / "linux-components.json"
        )
        self.assertEqual(config_bytes, installed_config.read_bytes())
        self.assertEqual(config_bytes, installed_plugin_config.read_bytes())

    def test_addon_frontend_policy_enables_only_windows_terminal(self) -> None:
        policy_path = (
            self.extract_path / "globalPlugins" / "NeovimAccessLink" / "resources"
            / "frontend-policy.json"
        )
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        statuses = {entry["kind"]: entry["status"] for entry in policy["frontends"]}
        self.assertEqual("enabled", statuses["windowsTerminal"])
        self.assertEqual("planned", statuses["putty"])
        self.assertEqual(
            "windowsterminal",
            next(
                entry["appModule"] for entry in policy["frontends"]
                if entry["kind"] == "windowsTerminal"
            ),
        )

    def test_editor_earcons_remain_playable_after_source_files_are_removed(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        for sound in (self.config_path / "waves").glob("*.wav"):
            sound.unlink()
        bundled = self.extract_path / "globalPlugins" / "NeovimAccessLink" / "resources" / "sounds"
        for sound in bundled.glob("*.wav"):
            sound.unlink()

        cues = (
            "insertMode", "normalMode", "matchingError", "delete", "replace",
            "lineStart", "lineEnd", "fileStart", "fileEnd", "lineCrossed",
        )
        for cue in cues:
            self.assertTrue(plugin._editorSounds.play(cue), cue)
        self.assertEqual(len(cues), len(self.soundFeeds))
        plugin.terminate()

    def test_toggle_has_no_collision_prone_default_gesture(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin, _PRODUCT_NAME

        configurable_scripts = (
            "script_toggleNeovimMode",
            "script_readCompletionDocumentation",
            "script_copyNeovimSelection",
            "script_copyLastNeovimYank",
            "script_pasteWindowsClipboard",
            "script_setNeovimRegisterFromWindowsClipboard",
            "script_leaveDirectTerminalInput",
            "script_startConnectionInstance",
            "script_disconnectConnectionInstance",
            "script_forgetTemporaryTerminalBinding",
        )
        for name in configurable_scripts:
            metadata = getattr(AppModule, name)._test_script_kwargs
            self.assertNotIn("gesture", metadata, name)
            self.assertEqual(_PRODUCT_NAME, metadata["category"], name)
            self.assertTrue(metadata["description"], name)
            self.assertFalse(hasattr(GlobalPlugin, name), name)
        self.assertNotIn("scriptCategory", vars(GlobalPlugin))
        self.assertFalse(hasattr(GlobalPlugin, "script_selectConnection"))
        self.assertFalse(hasattr(GlobalPlugin, "script_nextConnection"))
        self.assertIn(
            "choose a server",
            AppModule.script_startConnectionInstance._test_script_kwargs["description"].lower(),
        )
        self.assertEqual(
            "kb:NVDA+alt+d",
            AppModule.script_copyDiagnosticReport._test_script_kwargs["gesture"],
        )
        self.assertFalse(hasattr(AppModule, "script_claimFocusedNeovimSession"))
        self.assertTrue(hasattr(AppModule, "_decideExecuteGesture"))

    def test_configured_app_module_gesture_passes_through_after_focus_race(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        self._focusPlugin(plugin)
        previous = plugin._gate.focused
        self.focus = types.SimpleNamespace(
            processID=300, windowHandle=400, role=3, parent=None,
            appModule=types.SimpleNamespace(appName="explorer"),
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: (42, 400, 4, 1),
            ),
        )
        forwarded = []
        gesture = types.SimpleNamespace(send=lambda: forwarded.append(True))

        adapter.script_toggleNeovimMode(gesture)

        self.assertEqual([True], forwarded)
        self.assertEqual(previous, plugin._gate.focused)
        self.assertEqual([], self.messages)
        report = plugin._diagnostics.report()
        self.assertIn('"category": "configuredGesturePassedThrough"', report)
        self.assertIn('"action": "action_toggleNeovimMode"', report)
        adapter.terminate()
        plugin.terminate()

    def test_configured_app_module_gesture_fails_open_without_shared_service(self) -> None:
        from appModules.windowsterminal import AppModule

        adapter = AppModule()
        self.focus.appModule = adapter
        forwarded = []

        adapter.script_toggleNeovimMode(
            types.SimpleNamespace(send=lambda: forwarded.append(True)),
        )

        self.assertEqual([True], forwarded)
        adapter.terminate()

    def test_configured_app_module_gesture_rejects_non_terminal_control(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        self.focus.UIAElement.cachedClassName = "OtherControl"
        forwarded = []
        handled = []
        plugin.action_toggleNeovimMode = lambda gesture: handled.append(gesture)

        adapter.script_toggleNeovimMode(
            types.SimpleNamespace(send=lambda: forwarded.append(True)),
        )

        self.assertEqual([True], forwarded)
        self.assertEqual([], handled)
        self.assertIsNone(plugin._gate.focused)
        adapter.terminate()
        plugin.terminate()

    def test_configured_app_module_gesture_uses_only_exact_focused_adapter(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        first = AppModule()
        second = AppModule()
        self.focus.appModule = first
        self._focusPlugin(plugin)
        handled = []
        plugin.action_toggleNeovimMode = lambda gesture: handled.append(gesture)
        forwarded = []
        gesture = types.SimpleNamespace(send=lambda: forwarded.append(True))

        second.script_toggleNeovimMode(gesture)
        first.script_toggleNeovimMode(gesture)

        self.assertEqual([True], forwarded)
        self.assertEqual([gesture], handled)
        first.terminate()
        second.terminate()
        plugin.terminate()

    def test_app_module_termination_removes_the_shared_claim_observer_only_once(self) -> None:
        from appModules.windowsterminal import AppModule

        adapter = AppModule()
        self.assertEqual(1, len(self.inputDecider.handlers))

        adapter.terminate()
        adapter.terminate()

        self.assertEqual([], self.inputDecider.handlers)

    def test_every_configurable_app_module_script_dispatches_its_action(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        scripts_and_actions = (
            ("script_toggleNeovimMode", "action_toggleNeovimMode"),
            ("script_readCompletionDocumentation", "action_readCompletionDocumentation"),
            ("script_copyNeovimSelection", "action_copyNeovimSelection"),
            ("script_copyLastNeovimYank", "action_copyLastNeovimYank"),
            ("script_pasteWindowsClipboard", "action_pasteWindowsClipboard"),
            (
                "script_setNeovimRegisterFromWindowsClipboard",
                "action_setNeovimRegisterFromWindowsClipboard",
            ),
            ("script_leaveDirectTerminalInput", "action_leaveDirectTerminalInput"),
            ("script_startConnectionInstance", "action_startConnectionInstance"),
            ("script_disconnectConnectionInstance", "action_disconnectConnectionInstance"),
            (
                "script_forgetTemporaryTerminalBinding",
                "action_forgetTemporaryTerminalBinding",
            ),
        )
        plugin = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        handled = []
        marker = object()
        for _script_name, action_name in scripts_and_actions:
            setattr(
                plugin, action_name,
                lambda gesture, action_name=action_name: handled.append(
                    (action_name, gesture),
                ),
            )

        for script_name, _action_name in scripts_and_actions:
            getattr(adapter, script_name)(marker)

        self.assertEqual(
            [(action_name, marker) for _script_name, action_name in scripts_and_actions],
            handled,
        )
        adapter.terminate()
        plugin.terminate()

    def test_f12_observer_keeps_original_gesture_unbound_and_starts_claim_resolution(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        self.focus = types.SimpleNamespace(
            processID=1001, windowHandle=2001, role=3, parent=None,
            appModule=types.SimpleNamespace(appName="windowsterminal"),
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: (42, 2001, 4, 6),
            ),
        )
        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {
            "connections": [{
                "id": "work", "name": "Work", "host": "host", "user": "remote",
                "port": 22, "identityFile": "", "authentication": "openSsh",
            }],
        })
        order = []
        adapter = AppModule()
        self.focus.appModule = adapter
        adapter.event_gainFocus(self.focus, lambda: None)
        plugin._claimInventoryReady = True
        original_refresh = plugin._terminalFocusService.refresh_for_action

        def refresh(*args, **kwargs):
            order.append(("focus", args))
            return original_refresh(*args, **kwargs)

        plugin._terminalFocusService.refresh_for_action = refresh
        gesture = types.SimpleNamespace(
            normalizedIdentifiers=("kb:f12",),
            send=lambda: order.append(("send", gesture)),
        )
        plugin.action_claimFocusedNeovimSession = lambda current, forward_gesture=True, **kwargs: (
            order.append(("claim", plugin, current, forward_gesture, kwargs))
        )

        allowed = adapter._decideExecuteGesture(gesture)

        self.assertTrue(allowed)
        self.assertEqual(["focus", "claim"], [item[0] for item in order])
        self.assertIs(plugin, order[1][1])
        self.assertIsNone(order[1][2])
        self.assertFalse(order[1][3])
        self.assertEqual(plugin._identity(self.focus), order[1][4]["expected_identity"])
        adapter.terminate()
        plugin.terminate()

    def test_f12_observer_passes_through_without_active_plugin(self) -> None:
        from appModules.windowsterminal import AppModule

        adapter = AppModule()
        self.focus.appModule = adapter
        gesture = types.SimpleNamespace(normalizedIdentifiers=("kb:f12",))

        allowed = adapter._decideExecuteGesture(gesture)

        self.assertTrue(allowed)
        adapter.terminate()

    def test_f12_observer_is_inert_while_support_is_disabled(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = False
        adapter = AppModule()
        self.focus.appModule = adapter
        handled = []
        adapter._handleObservedClaimGesture = lambda: handled.append(True)

        allowed = adapter._decideExecuteGesture(
            types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
        )

        self.assertTrue(allowed)
        self.assertEqual([], handled)
        adapter.terminate()
        plugin.terminate()

    def test_f12_observer_authorizes_the_focused_control_while_support_is_enabled(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        adapter = AppModule()
        self.focus.appModule = adapter
        handled = []
        plugin.action_claimFocusedNeovimSession = lambda *_args, **kwargs: handled.append(kwargs)

        allowed = adapter._decideExecuteGesture(
            types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
        )

        self.assertTrue(allowed)
        self.assertEqual(1, len(handled))
        self.assertEqual(plugin._gate.focused, handled[0]["expected_identity"])
        self.assertGreater(handled[0]["claim_generation"], 0)
        self.assertIn("sessionClaimGestureCaptured", plugin._diagnostics.report())
        adapter.terminate()
        plugin.terminate()

    def test_f12_authorization_is_exact_one_shot_and_observer_registration_is_shared(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin, TerminalIdentity

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        first_identity = plugin._gate.focused
        other = TerminalIdentity(
            first_identity.process_id + 1, first_identity.window_handle + 1,
            first_identity.frontend_kind,
            (42, first_identity.window_handle + 1, 4, 99),
        )
        first, second = AppModule(), AppModule()
        self.assertEqual(1, len(self.inputDecider.handlers))
        gesture = types.SimpleNamespace(normalizedIdentifiers=("kb:f12",))
        handled = []
        plugin.action_claimFocusedNeovimSession = lambda *_args, **kwargs: handled.append(kwargs)

        self.focus.appModule = first
        self.assertTrue(self.inputDecider.handlers[0](gesture))
        self.assertEqual(1, len(handled))
        self.assertEqual(first_identity, handled[0]["expected_identity"])

        second_focus = types.SimpleNamespace(
            processID=other.process_id, windowHandle=other.window_handle,
            role=3, parent=None, appModule=second,
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: other.runtime_id,
            ),
        )
        self.focus = second_focus
        plugin._gate.focused = other
        self.assertTrue(self.inputDecider.handlers[0](gesture))
        self.assertEqual(2, len(handled))
        self.assertEqual(other, handled[1]["expected_identity"])
        self.assertNotEqual(
            handled[0]["claim_generation"], handled[1]["claim_generation"],
        )

        first.terminate()
        self.assertEqual(1, len(self.inputDecider.handlers))
        second.terminate()
        self.assertEqual(0, len(self.inputDecider.handlers))
        plugin.terminate()

    def test_claim_observer_queries_focus_only_for_f12_and_fails_open_on_focus_error(self) -> None:
        from appModules.windowsterminal import AppModule
        import api

        adapter = AppModule()
        focus_queries = []
        original_get_focus = api.getFocusObject
        api.getFocusObject = lambda: focus_queries.append(True) or self.focus
        try:
            self.assertTrue(self.inputDecider.handlers[0](
                types.SimpleNamespace(normalizedIdentifiers=("kb:a",)),
            ))
            self.assertEqual([], focus_queries)
            api.getFocusObject = lambda: (_ for _ in ()).throw(RuntimeError("focus unavailable"))
            self.assertTrue(self.inputDecider.handlers[0](
                types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
            ))
        finally:
            api.getFocusObject = original_get_focus
        adapter.terminate()

    def test_f12_observer_has_no_single_adapter_fallback_outside_its_focused_app_module(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        adapter = AppModule()
        handled = []
        plugin.action_claimFocusedNeovimSession = lambda *_args, **kwargs: handled.append(kwargs)
        self.focus.appModule = types.SimpleNamespace(appName="explorer")

        allowed = self.inputDecider.handlers[0](
            types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
        )

        self.assertTrue(allowed)
        self.assertEqual([], handled)
        self.assertIsNone(plugin._pendingObservedClaim)
        adapter.terminate()
        plugin.terminate()

    def test_f12_observer_rejects_a_stale_terminal_identity_before_authorization(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        adapter = AppModule()
        self.focus.appModule = adapter
        self.focus.UIAElement = types.SimpleNamespace(
            cachedClassName="TermControl", getRuntimeId=lambda: (42, 200, 4, 99),
        )
        scheduled = []
        plugin._scheduleMainThreadCall = lambda *args: scheduled.append(args)

        allowed = self.inputDecider.handlers[0](
            types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
        )

        self.assertTrue(allowed)
        self.assertEqual([], scheduled)
        self.assertIsNone(plugin._pendingObservedClaim)
        adapter.terminate()
        plugin.terminate()

    def test_queued_f12_from_previous_terminal_is_rejected_after_rapid_focus_change(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import queueHandler

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        adapter = AppModule()
        self.focus.appModule = adapter
        queued = []
        original_queue_function = queueHandler.queueFunction
        queueHandler.queueFunction = lambda _queue, function, *args, **_kwargs: queued.append(
            (function, args)
        )
        scheduled = []
        plugin._scheduleMainThreadCall = lambda *args: scheduled.append(args)
        try:
            self.assertTrue(self.inputDecider.handlers[0](
                types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
            ))
            self.assertEqual(1, len(queued))
            self.focus = types.SimpleNamespace(
                processID=900, windowHandle=901, role=1, parent=None,
                appModule=types.SimpleNamespace(appName="explorer"), UIAElement=None,
            )
            queued[0][0](*queued[0][1])
        finally:
            queueHandler.queueFunction = original_queue_function

        self.assertEqual([], scheduled)
        self.assertIsNone(plugin._pendingObservedClaim)
        adapter.terminate()
        plugin.terminate()

    def test_f12_without_a_fresh_claim_is_silent_and_fails_open(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryGeneration = 4
        before = list(self.messages)

        plugin._finishAutomaticClaimResolution(
            4, [], plugin._gate.focused,
        )

        self.assertEqual(before, self.messages)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIn('"candidates": 0', plugin._diagnostics.report())
        plugin.terminate()

    def test_queued_f12_is_rejected_after_switching_terminal_controls(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, TerminalIdentity

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        original = plugin._gate.focused
        generation = plugin._captureObservedSessionClaim(original)
        plugin._gate.focused = TerminalIdentity(
            original.process_id, original.window_handle, original.frontend_kind,
            (42, original.window_handle, 4, 101),
        )
        scheduled = []
        plugin._scheduleMainThreadCall = lambda *args: scheduled.append(args)

        plugin.action_claimFocusedNeovimSession(
            None, forward_gesture=False,
            expected_identity=original, claim_generation=generation,
        )

        self.assertEqual([], scheduled)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIn("notAuthorizedOrFocusChanged", plugin._diagnostics.report())
        plugin.terminate()

    def test_delayed_claim_callback_is_retained_until_execution(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import wx

        class PendingCall:
            def __init__(inner_self, callback):
                inner_self.callback = callback
                inner_self.stopped = False
            def Stop(inner_self): inner_self.stopped = True

        pending = []
        original_call_later = wx.CallLater
        wx.CallLater = lambda _delay, callback: pending.append(PendingCall(callback)) or pending[-1]
        try:
            plugin = GlobalPlugin()
            executed = []
            call = plugin._scheduleMainThreadCall(250, executed.append, "claim")
            self.assertIn(call, plugin._pendingMainThreadCalls)
            self.assertEqual([], executed)

            call.callback()

            self.assertEqual(["claim"], executed)
            self.assertNotIn(call, plugin._pendingMainThreadCalls)
            plugin.terminate()
        finally:
            wx.CallLater = original_call_later

    def test_observed_f12_is_not_synthetically_reinjected(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        scheduled = []
        plugin._scheduleMainThreadCall = lambda delay, callback, *args: scheduled.append(
            (delay, callback, args)
        )
        plugin.action_claimFocusedNeovimSession(None, forward_gesture=False)

        self.assertEqual([250], [call[0] for call in scheduled])
        self.assertEqual("_beginAutomaticClaimResolution", scheduled[0][1].__name__)
        plugin.terminate()

    def test_f12_before_inventory_ready_is_inert_until_pairing_is_ready(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = False
        inventories = []
        plugin._beginClaimInventory = lambda: inventories.append(True)
        sent = []
        plugin.action_claimFocusedNeovimSession(
            types.SimpleNamespace(send=lambda: sent.append(True)),
        )
        self.assertEqual([], inventories)
        self.assertEqual([True], sent)
        self.assertTrue(plugin._gate.manual_enabled)
        self.assertFalse(plugin._claimInventoryReady)
        plugin.terminate()

    def test_explicit_local_discovery_can_fall_back_to_a_selected_ssh_profile(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        fallbacks = []
        plugin._beginSessionSelection = lambda *args: fallbacks.append(args)
        plugin._sessionDiscoveryGeneration = 4
        plugin._finishLocalSessionDiscovery(
            4, identity, [], None, True, True, True, profile,
        )
        self.assertEqual((profile, identity, True, True, True), fallbacks[0])
        self.assertFalse(any("No local" in message for message in self.messages))
        plugin.terminate()

    def test_claim_service_resolves_local_and_remote_discovery_outcomes(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession
        from globalPlugins.NeovimAccessLink.session_claim import DiscoverySelectionKind

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        plugin._sessionDiscoveryGeneration = 9
        stale = LocalWindowsSession(
            "1", "Stale", "C:/one", "127.0.0.1", 41001, 1,
            claim_age_ms=10, claimed_monotonic_ns=4_000,
        )
        fresh = LocalWindowsSession(
            "2", "Fresh", "C:/two", "127.0.0.1", 41002, 2,
            claim_age_ms=20, claimed_monotonic_ns=6_000,
        )

        stale_result = plugin._sessionClaimService.resolve_local_discovery(
            8, identity, [fresh], None,
            require_recent_claim=True, has_fallback=False, claim_not_before_ns=5_000,
        )
        local_result = plugin._sessionClaimService.resolve_local_discovery(
            9, identity, [stale, fresh], None,
            require_recent_claim=True, has_fallback=False, claim_not_before_ns=5_000,
        )
        fallback_result = plugin._sessionClaimService.resolve_local_discovery(
            9, identity, [], None,
            require_recent_claim=False, has_fallback=True, claim_not_before_ns=0,
        )
        remote_sessions = [
            RemoteSession("one", "One", "/one"),
            RemoteSession("two", "Two", "/two"),
        ]
        remote_result = plugin._sessionClaimService.resolve_remote_discovery(
            9, identity, remote_sessions, None,
            require_recent_claim=False, preserve_dialog_identity=False,
        )

        self.assertEqual(DiscoverySelectionKind.STALE, stale_result.kind)
        self.assertEqual(DiscoverySelectionKind.SELECT, local_result.kind)
        self.assertEqual("2", local_result.session.identifier)
        self.assertEqual(DiscoverySelectionKind.FALLBACK, fallback_result.kind)
        self.assertEqual(DiscoverySelectionKind.CHOOSE, remote_result.kind)
        self.assertEqual(("one", "two"), tuple(item.identifier for item in remote_result.sessions))
        plugin.terminate()

    def test_inventory_baselines_local_and_every_reachable_ssh_profile(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        local = LocalWindowsSession(
            "77", "Local", "C:/work", "127.0.0.1", 45678, 77, claim_sequence=2,
        )
        remote = RemoteSession("88", "Remote", "/work", claim_sequence=7)
        plugin._claimInventoryGeneration = 3
        plugin._finishClaimInventory(3, [
            ("localWindowsTcp", "local-windows", None, [local], None),
            ("remoteSsh", "work", profile, [remote], None),
            ("remoteSsh", "offline", None, [], RuntimeError("offline")),
        ])
        self.assertTrue(plugin._claimInventoryReady)
        self.assertEqual(2, plugin._claimBaselines[(
            "localWindowsTcp", "local-windows", "77",
        )])
        self.assertEqual(7, plugin._claimBaselines[("remoteSsh", "work", "88")])
        self.assertEqual({
            ("localWindowsTcp", "local-windows"), ("remoteSsh", "work"),
        }, plugin._claimEligibleTargets)
        self.assertIn("could not be checked", self.messages[-1])
        plugin.terminate()

    def test_f12_resolves_changed_claim_across_all_targets_not_a_default(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        first = parse_profile({
            "id": "one", "name": "One", "host": "one", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        second = parse_profile({
            "id": "two", "name": "Two", "host": "two", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        plugin._claimBaselines = {
            ("localWindowsTcp", "local-windows", "77"): 2,
            ("remoteSsh", "one", "88"): 4,
            ("remoteSsh", "two", "99"): 6,
        }
        plugin._claimInventoryGeneration = 9
        connected = []
        plugin._connectAutomaticClaim = lambda terminal, candidate: connected.append(
            (terminal, candidate)
        )
        plugin._finishAutomaticClaimResolution(9, [
            ("localWindowsTcp", "local-windows", None, [LocalWindowsSession(
                "77", "Local", "C:/work", "127.0.0.1", 45678, 77, claim_sequence=2,
            )], None),
            ("remoteSsh", "one", first, [RemoteSession(
                "88", "Remote one", "/one", claim_sequence=5,
            )], None),
            ("remoteSsh", "two", second, [RemoteSession(
                "99", "Remote two", "/two", claim_sequence=6,
            )], None),
        ], identity)
        self.assertEqual("one", connected[0][1][1].identifier)
        self.assertEqual("88", connected[0][1][2].identifier)
        self.assertEqual(5, plugin._claimBaselines[("remoteSsh", "one", "88")])
        plugin.terminate()

    def test_local_f12_claim_does_not_wait_for_ssh_scans(self) -> None:
        from globalPlugins import NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        profile = parse_profile({
            "id": "slow", "name": "Slow", "host": "slow", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        local = LocalWindowsSession(
            "77", "Local", "C:/work", "127.0.0.1", 45678, 77, claim_sequence=2,
        )
        completed = []
        plugin._finishAutomaticClaimResolution = lambda *args: completed.append(args)

        class LocalLister:
            def __init__(inner_self, **_kwargs): pass
            def list(inner_self): return [local]

        class UnexpectedSshLister:
            def list(inner_self, *_args, **_kwargs):
                raise AssertionError("a conclusive local claim must not start SSH discovery")

        with mock.patch.object(addon_module, "LocalSessionLister", LocalLister), mock.patch.object(
            addon_module, "SshSessionLister", UnexpectedSshLister,
        ):
            plugin._scanAutomaticClaimTargets(
                5, [profile], {}, identity,
                {("localWindowsTcp", "local-windows", "77"): 1},
            )

        self.assertEqual(1, len(completed))
        self.assertEqual("localWindowsTcp", completed[0][1][0][0])
        plugin.terminate()

    def test_automatic_local_claim_retries_an_initial_pre_claim_snapshot(self) -> None:
        from globalPlugins import NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        snapshots = [
            LocalWindowsSession(
                "77", "Local", "C:/work", "127.0.0.1", 45678, 77, claim_sequence=1,
            ),
            LocalWindowsSession(
                "77", "Local", "C:/work", "127.0.0.1", 45678, 77, claim_sequence=2,
            ),
        ]
        calls = []

        class DelayedLocalLister:
            def __init__(inner_self, **_kwargs): pass
            def list(inner_self):
                calls.append(True)
                return [snapshots[min(len(calls) - 1, 1)]]

        completed = []
        plugin._finishAutomaticClaimResolution = lambda *args: completed.append(args)
        with mock.patch.object(addon_module, "LocalSessionLister", DelayedLocalLister), mock.patch.object(
            addon_module.time, "sleep", lambda _seconds: None,
        ):
            plugin._scanAutomaticClaimTargets(
                6, [], {}, identity,
                {("localWindowsTcp", "local-windows", "77"): 1},
            )

        self.assertEqual(2, len(calls))
        self.assertEqual(1, len(completed))
        self.assertEqual(2, completed[0][1][0][3][0].claim_sequence)
        plugin.terminate()

    def test_automatic_local_claim_accepts_f12_timestamp_when_baseline_sequence_is_equal(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        plugin._claimInventoryGeneration = 7
        plugin._claimBaselines = {
            ("localWindowsTcp", "local-windows", "77"): 2,
        }
        session = LocalWindowsSession(
            "77", "Local", "C:/work", "127.0.0.1", 45678, 77,
            claim_age_ms=5, claimed_monotonic_ns=1_001, claim_sequence=2,
        )
        connected = []
        plugin._connectAutomaticClaim = lambda terminal, candidate: connected.append(
            (terminal, candidate)
        )

        plugin._finishAutomaticClaimResolution(
            7,
            [("localWindowsTcp", "local-windows", None, [session], None)],
            identity,
            1_000,
        )

        self.assertEqual(1, len(connected))
        self.assertEqual("77", connected[0][1][2].identifier)
        plugin.terminate()

    def test_explicit_local_claim_retries_until_registry_write_arrives(self) -> None:
        from globalPlugins import NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        stale = LocalWindowsSession(
            "77", "Local", "C:/work", "127.0.0.1", 45678, 77,
            claim_age_ms=100, claimed_monotonic_ns=4_000, claim_sequence=1,
        )
        fresh = LocalWindowsSession(
            "77", "Local", "C:/work", "127.0.0.1", 45678, 77,
            claim_age_ms=10, claimed_monotonic_ns=6_000, claim_sequence=2,
        )
        calls = []

        class DelayedLocalLister:
            def __init__(inner_self, **_kwargs): pass
            def list(inner_self):
                calls.append(True)
                return [[stale], [fresh]][min(len(calls) - 1, 1)]

        completed = []
        plugin._finishLocalSessionDiscovery = lambda *args: completed.append(args)
        with mock.patch.object(addon_module, "LocalSessionLister", DelayedLocalLister), mock.patch.object(
            addon_module.time, "sleep", lambda _seconds: None,
        ):
            plugin._sessionClaimService.discover_local_sessions(
                7, identity, True, True, True, None, 5_000,
                plugin._finishLocalSessionDiscovery,
            )

        self.assertEqual(2, len(calls))
        self.assertEqual("77", completed[0][2][0].identifier)
        self.assertEqual(2, completed[0][2][0].claim_sequence)
        plugin.terminate()

    def test_multiple_changed_claims_require_explicit_accessible_choice(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        plugin._claimBaselines = {
            ("localWindowsTcp", "local-windows", "77"): 1,
            ("remoteSsh", "work", "88"): 3,
        }
        plugin._claimInventoryGeneration = 12
        choices = []
        plugin._showAutomaticClaimChoice = lambda *args: choices.append(args)
        plugin._finishAutomaticClaimResolution(12, [
            ("localWindowsTcp", "local-windows", None, [LocalWindowsSession(
                "77", "Local", "C:/work", "127.0.0.1", 45678, 77,
                claim_sequence=2,
            )], None),
            ("remoteSsh", "work", profile, [RemoteSession(
                "88", "Remote", "/work", claim_sequence=4,
            )], None),
        ], identity)
        self.assertEqual(1, len(choices))
        self.assertEqual(2, len(choices[0][2]))
        plugin.terminate()

    def test_activation_inventories_local_and_all_saved_connections_before_f12(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        self.focus = types.SimpleNamespace(
            processID=1001, windowHandle=2001, role=3, parent=None,
            appModule=types.SimpleNamespace(appName="windowsterminal"),
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: (42, 2001, 4, 6),
            ),
        )
        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        self._updateSettings(plugin, {
            "connections": [{
                "id": "work", "name": "editor@example-host", "host": "example-host", "user": "editor",
                "port": 22, "identityFile": "", "authentication": "openSsh",
            }],
        })
        discoveries = []
        plugin._beginClaimInventory = lambda: discoveries.append(True)
        plugin._toggleNeovimMode()
        self.assertTrue(plugin._gate.manual_enabled)
        self.assertEqual([True], discoveries)
        self.assertIn("local and saved", self.messages[-1])
        plugin.terminate()

    def test_terminal_actions_refresh_focus_without_a_new_gain_focus_event(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin, TerminalIdentity

        plugin = GlobalPlugin()
        stale = TerminalIdentity(100, 200, "windowsTerminal", (42, 200, 4, 53))
        plugin._gate.focused = stale
        plugin._focusedTerminalObject = None
        inventories = []
        plugin._beginClaimInventory = lambda: inventories.append(plugin._gate.focused)
        adapter = AppModule()
        self.focus.appModule = adapter

        adapter.script_toggleNeovimMode(None)

        expected = plugin._identity(self.focus)
        self.assertEqual(expected, plugin._gate.focused)
        self.assertIs(self.focus, plugin._focusedTerminalObject)
        self.assertEqual([expected], inventories)
        self.assertIn('"category": "terminalActionFocusRefreshed"', plugin._diagnostics.report())
        adapter.terminate()
        plugin.terminate()

    def test_activation_in_unbound_second_control_still_disables_globally(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, TerminalIdentity

        class Client:
            def __init__(inner_self): inner_self.stops = 0
            def start(inner_self): pass
            def stop(inner_self): inner_self.stops += 1

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        first_identity = plugin._gate.focused
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "work", "one", "Work", client)
        plugin._instanceManager.bind(first_identity, instance.identifier)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        plugin._gate.focused = TerminalIdentity(
            first_identity.process_id, first_identity.window_handle,
            first_identity.frontend_kind, (42, 200, 4, 12),
        )

        plugin._toggleNeovimMode()

        self.assertFalse(plugin._gate.manual_enabled)
        self.assertEqual(1, client.stops)
        self.assertEqual([], plugin._instanceManager.list())
        self.assertIn("off", self.messages[-1])
        plugin.terminate()

    def test_activation_in_bound_tab_still_turns_accessibility_off(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(inner_self): inner_self.stops = 0
            def start(inner_self): pass
            def stop(inner_self): inner_self.stops += 1

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "work", "one", "Work", client)
        plugin._instanceManager.bind(plugin._gate.focused, instance.identifier)
        plugin._gate.manual_enabled = True

        plugin._toggleNeovimMode()

        self.assertFalse(plugin._gate.manual_enabled)
        self.assertEqual(1, client.stops)
        self.assertEqual([], plugin._instanceManager.list())
        self.assertIn("off", self.messages[-1])
        plugin.terminate()

    def test_terminal_events_and_configurable_scripts_stay_in_app_module(self) -> None:
        with zipfile.ZipFile(build()) as archive:
            names = set(archive.namelist())
            global_source = archive.read(
                "globalPlugins/NeovimAccessLink/__init__.py"
            ).decode("utf-8")
            service_source = archive.read(
                "globalPlugins/NeovimAccessLink/terminal_integration.py"
            ).decode("utf-8")
            app_module_source = archive.read(
                "appModules/windowsterminal.py"
            ).decode("utf-8")
        self.assertIn("appModules/windowsterminal.py", names)
        self.assertIn(
            "globalPlugins/NeovimAccessLink/terminal_integration.py",
            names,
        )
        self.assertNotIn("_dispatchConfiguredTerminalScript", global_source)
        self.assertIn("_dispatchConfiguredTerminalScript", app_module_source)
        self.assertIn("getFocusObject", app_module_source)
        self.assertIn("getTerminalIntegrationService", app_module_source)
        self.assertNotIn("getActivePlugin", global_source)
        self.assertNotIn("getActivePlugin", app_module_source)
        self.assertIn("class TerminalIntegrationService", service_source)
        self.assertIn("class TerminalCommand(Enum)", service_source)
        self.assertNotIn("getattr(plugin, action_name)", app_module_source)
        self.assertIn("import controlTypes", app_module_source)
        self.assertNotIn("NeovimAccessLink.controlTypes", app_module_source)
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        self.assertTrue(hasattr(AppModule, "event_gainFocus"))
        self.assertTrue(hasattr(AppModule, "chooseNVDAObjectOverlayClasses"))
        self.assertTrue(hasattr(AppModule, "_decideExecuteGesture"))
        self.assertFalse(hasattr(AppModule, "script_claimFocusedNeovimSession"))
        self.assertFalse(hasattr(GlobalPlugin, "event_gainFocus"))
        self.assertFalse(hasattr(GlobalPlugin, "chooseNVDAObjectOverlayClasses"))
        self.assertNotIn("nextHandler", global_source)
        self.assertNotIn("_chooseNVDAObjectOverlayClasses", global_source)
        for event_name in (
            "_event_gainFocus", "_event_textChange", "_event_typedCharacter",
            "_event_UIA_notification", "_event_liveRegionChange",
            "_event_valueChange", "_event_nameChange", "_event_descriptionChange",
        ):
            self.assertNotIn(event_name, global_source)
        self.assertFalse(hasattr(GlobalPlugin, "script_toggleNeovimMode"))
        self.assertTrue(hasattr(AppModule, "script_toggleNeovimMode"))
        self.assertEqual(
            [
                "script_copyDiagnosticReport",
                "script_copyLastNeovimYank",
                "script_copyNeovimSelection",
                "script_disconnectConnectionInstance",
                "script_forgetTemporaryTerminalBinding",
                "script_leaveDirectTerminalInput",
                "script_pasteWindowsClipboard",
                "script_readCompletionDocumentation",
                "script_setNeovimRegisterFromWindowsClipboard",
                "script_startConnectionInstance",
                "script_toggleNeovimMode",
            ],
            sorted(
                name for name, value in vars(AppModule).items()
                if name.startswith("script_")
                and hasattr(value, "_test_script_kwargs")
            ),
        )

    def test_app_module_uses_only_the_public_terminal_service_contract(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from appModules.windowsterminal import AppModule

        order = []
        focus_decision = object()

        class StrictService:
            def prepare_focus(inner_self, obj, token, app_module):
                order.append(("prepare", obj, token, app_module))
                return focus_decision

            def finish_focus(inner_self, decision):
                order.append(("finish", decision))

            def abandon_focus(inner_self, decision):
                raise AssertionError(f"unexpected abandoned focus: {decision!r}")

            def lose_focus(inner_self, token):
                order.append(("lose", token))

            def should_use_native_event(inner_self, obj, event_name):
                order.append(("native", obj, event_name))
                return False

            def supports_braille_overlay(inner_self, obj):
                order.append(("overlay", obj))
                return True

            def dispatch_command(inner_self, command, gesture, obj, app_module, token):
                order.append(("command", command, gesture, obj, app_module, token))
                return True

            def copy_diagnostic_report(inner_self, gesture):
                order.append(("diagnostics", gesture))

        service = StrictService()
        original_getter = addon_module.getTerminalIntegrationService
        addon_module.getTerminalIntegrationService = lambda: service
        adapter = AppModule()
        self.focus.appModule = adapter
        native_focus = []
        native_text = []
        classes = [object]
        gesture = object()
        try:
            adapter.event_gainFocus(self.focus, lambda: native_focus.append(True))
            adapter.event_textChange(self.focus, lambda: native_text.append(True))
            adapter.chooseNVDAObjectOverlayClasses(self.focus, classes)
            adapter.script_toggleNeovimMode(gesture)
            adapter.script_copyDiagnosticReport(gesture)
            adapter.event_appModule_loseFocus()
        finally:
            adapter.terminate()
            addon_module.getTerminalIntegrationService = original_getter

        self.assertEqual([True], native_focus)
        self.assertEqual([], native_text)
        self.assertIs(addon_module.StructuredTerminalBrailleOverlay, classes[0])
        self.assertEqual(
            ["prepare", "finish", "native", "overlay", "command", "diagnostics", "lose"],
            [item[0] for item in order],
        )
        self.assertIs(
            addon_module.TerminalCommand.TOGGLE_ACCESSIBILITY,
            next(item for item in order if item[0] == "command")[1],
        )

    def test_unknown_terminal_command_fails_open_and_forwards_gesture_once(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        forwarded = []
        gesture = types.SimpleNamespace(send=lambda: forwarded.append(True))

        adapter._dispatchConfiguredTerminalScript(gesture, "action_notAllowed")

        self.assertEqual([True], forwarded)
        self.assertIn('"action": "unknown"', plugin._diagnostics.report())
        adapter.terminate()
        plugin.terminate()

    def test_partially_initialized_terminal_service_fails_open_in_app_module(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from appModules.windowsterminal import AppModule

        class BrokenService:
            def __getattr__(inner_self, name):
                raise RuntimeError(f"broken service operation: {name}")

        original_getter = addon_module.getTerminalIntegrationService
        addon_module.getTerminalIntegrationService = lambda: BrokenService()
        adapter = AppModule()
        self.focus.appModule = adapter
        focus_native = []
        text_native = []
        forwarded = []
        classes = [object]
        gesture = types.SimpleNamespace(
            normalizedIdentifiers=("kb:f12",),
            send=lambda: forwarded.append(True),
        )
        try:
            adapter.event_gainFocus(self.focus, lambda: focus_native.append(True))
            adapter.event_textChange(self.focus, lambda: text_native.append(True))
            adapter.chooseNVDAObjectOverlayClasses(self.focus, classes)
            adapter.script_toggleNeovimMode(gesture)
            adapter.script_copyDiagnosticReport(gesture)
            self.assertTrue(adapter._decideExecuteGesture(gesture, focus_obj=self.focus))
            adapter.event_appModule_loseFocus()
        finally:
            adapter.terminate()
            addon_module.getTerminalIntegrationService = original_getter

        self.assertEqual([True], focus_native)
        self.assertEqual([True], text_native)
        self.assertEqual([True], forwarded)
        self.assertEqual([object], classes)

    def test_partially_initialized_terminal_service_fails_open_in_braille_overlay(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module

        class BrokenService:
            def should_suppress_braille(inner_self, _obj):
                raise RuntimeError("broken Braille service")

        original_getter = addon_module.getTerminalIntegrationService
        addon_module.getTerminalIntegrationService = lambda: BrokenService()
        overlay = addon_module.StructuredTerminalBrailleOverlay()
        try:
            with self.assertRaises(NotImplementedError):
                overlay.getBrailleRegions()
        finally:
            addon_module.getTerminalIntegrationService = original_getter

    def test_terminal_focus_and_claim_results_are_immutable(self) -> None:
        from dataclasses import FrozenInstanceError
        from globalPlugins.NeovimAccessLink import SessionClaimAuthorization, TerminalFocusDecision
        from globalPlugins.NeovimAccessLink.session_claim import (
            ClaimTransition,
            ClaimTransitionKind,
            ConnectionPlan,
            ConnectionPlanKind,
            ConnectionDisconnectResult,
            ConnectionReuseResult,
            ConnectionSelectionResult,
            ConnectionStartResult,
            DiscoverySelection,
            DiscoverySelectionKind,
            RememberedBindingActivation,
            RememberedBindingActivationKind,
            RememberedStateRequest,
            RememberedStateRequestKind,
        )

        focus = TerminalFocusDecision(object(), 1, None, None, None, False)
        claim = SessionClaimAuthorization(object(), 1, object())
        transition = ClaimTransition(ClaimTransitionKind.AUTOMATIC, object())
        selection = DiscoverySelection(DiscoverySelectionKind.EMPTY)
        plan = ConnectionPlan(ConnectionPlanKind.START)
        reuse = ConnectionReuseResult(object())
        start = ConnectionStartResult()
        connection_selection = ConnectionSelectionResult()
        disconnect = ConnectionDisconnectResult()
        activation = RememberedBindingActivation(RememberedBindingActivationKind.STALE)
        state_request = RememberedStateRequest(RememberedStateRequestKind.SKIP)

        with self.assertRaises(FrozenInstanceError):
            focus.generation = 2
        with self.assertRaises(FrozenInstanceError):
            claim.generation = 2
        with self.assertRaises(FrozenInstanceError):
            transition.target_id = "changed"
        with self.assertRaises(FrozenInstanceError):
            selection.kind = DiscoverySelectionKind.SELECT
        with self.assertRaises(FrozenInstanceError):
            plan.replace_instance_id = "changed"
        with self.assertRaises(FrozenInstanceError):
            reuse.displaced_identities = ()
        with self.assertRaises(FrozenInstanceError):
            start.error = "changed"
        with self.assertRaises(FrozenInstanceError):
            connection_selection.error = "changed"
        with self.assertRaises(FrozenInstanceError):
            disconnect.error = "changed"
        with self.assertRaises(FrozenInstanceError):
            activation.kind = RememberedBindingActivationKind.ACTIVATE
        with self.assertRaises(FrozenInstanceError):
            state_request.request_id = 1

    def test_session_claim_service_plans_reuse_and_replacement_without_client_transition(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession
        from globalPlugins.NeovimAccessLink.session_claim import ConnectionPlanKind

        events = []

        class Client:
            def __init__(inner_self, name):
                inner_self.name = name

            def start(inner_self):
                events.append(f"start-{inner_self.name}")

            def stop(inner_self):
                events.append(f"stop-{inner_self.name}")

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        first = add_remote_instance(
            plugin._instanceManager, "work", "22", "First", Client("first"),
        )
        second = add_remote_instance(
            plugin._instanceManager, "work", "22", "Second", Client("second"),
        )
        plugin._instanceManager.bind(identity, second.identifier)
        displaced_identity = type(identity)(
            process_id=identity.process_id,
            window_handle=identity.window_handle,
            frontend_kind=identity.frontend_kind,
            runtime_id=(42, identity.window_handle, 4, 53),
        )
        plugin._instanceManager.bind(displaced_identity, second.identifier)
        session = RemoteSession("22", "project", "/work")

        reuse = plugin._sessionClaimService.plan_remote_connection(
            identity,
            "work",
            session,
            allow_reuse=True,
            replace_existing=False,
        )
        replacement = plugin._sessionClaimService.plan_remote_connection(
            identity,
            "work",
            session,
            allow_reuse=False,
            replace_existing=True,
        )
        applied = plugin._sessionClaimService.apply_connection_reuse(identity, reuse)

        self.assertEqual(ConnectionPlanKind.REUSE, reuse.kind)
        self.assertEqual(second, reuse.instance)
        self.assertEqual(second, applied.instance)
        self.assertEqual((displaced_identity,), applied.displaced_identities)
        self.assertIsNone(plugin._instanceManager.selected_for(displaced_identity))
        self.assertEqual(second, plugin._instanceManager.selected_for(identity))
        self.assertEqual(ConnectionPlanKind.START, replacement.kind)
        self.assertEqual(second.identifier, replacement.replace_instance_id)
        self.assertEqual(["start-first", "start-second"], events)
        self.assertEqual([first, second], plugin._instanceManager.list())
        plugin.terminate()

    def test_session_claim_service_rolls_back_a_client_that_cannot_be_selected(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_targets import remote_ssh_target

        events = []

        class Client:
            def start(inner_self):
                events.append("start")

            def stop(inner_self):
                events.append("stop")

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        plugin._stopManagedClientAsync = lambda _instance_id, client: client.stop()
        with mock.patch.object(
            plugin._connectionCoordinator,
            "select_instance",
            side_effect=RuntimeError("cannot select"),
        ):
            result = plugin._sessionClaimService.start_connection(
                identity,
                remote_ssh_target("work", "Work"),
                "22",
                "Work, project",
                Client(),
            )

        self.assertIsNone(result.instance)
        self.assertEqual("RuntimeError", result.error_type)
        self.assertEqual([], plugin._instanceManager.list())
        self.assertEqual(["start", "stop"], events)
        plugin.terminate()

    def test_session_claim_service_restores_previous_binding_after_selection_failure(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(inner_self):
                pass

            def stop(inner_self):
                pass

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        first = add_remote_instance(plugin._instanceManager, "one", "11", "First", Client())
        second = add_remote_instance(plugin._instanceManager, "two", "22", "Second", Client())
        plugin._instanceManager.bind(identity, first.identifier)
        original_select = plugin._connectionCoordinator.select_instance
        original_select(first.identifier, identity, plugin._newInstanceRuntime)

        def select(instance_id, terminal, create_runtime):
            if instance_id == second.identifier:
                raise RuntimeError("cannot select")
            return original_select(instance_id, terminal, create_runtime)

        with mock.patch.object(plugin._connectionCoordinator, "select_instance", side_effect=select):
            result = plugin._sessionClaimService.select_connection(identity, second.identifier)

        self.assertIsNone(result.instance)
        self.assertEqual("RuntimeError", result.error_type)
        self.assertEqual(first, plugin._instanceManager.selected_for(identity))
        self.assertIs(plugin._instanceManager.client_for(first.identifier), plugin._client)
        plugin.terminate()

    def test_disconnect_connection_instance_stops_client_asynchronously_and_fails_open(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        events = []

        class Client:
            def start(inner_self):
                events.append("start")

            def stop(inner_self):
                events.append("stop")

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "work", "22", "Work", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._connectionCoordinator.select_instance(
            instance.identifier,
            identity,
            plugin._newInstanceRuntime,
        )
        plugin._rememberedTerminalBindings.add(identity)
        plugin._gate.bound_terminal = identity
        plugin._gate.manual_enabled = True
        plugin._gate.authenticated = True
        plugin._gate.nvim_active = True
        plugin._stopManagedClientAsync = lambda _instance_id, selected_client: selected_client.stop()

        plugin.action_disconnectConnectionInstance(None)

        self.assertEqual(["start", "stop"], events)
        self.assertEqual([], plugin._instanceManager.list())
        self.assertIsNone(plugin._client)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertNotIn(identity, plugin._rememberedTerminalBindings)
        self.assertIn("Neovim connection disconnected", self.messages[-1])
        plugin.terminate()

    def test_remembered_binding_service_prepares_fail_open_correlated_context_request(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.session_claim import (
            RememberedBindingActivationKind,
            RememberedStateRequestKind,
        )

        class Client:
            def start(inner_self):
                pass

            def stop(inner_self):
                pass

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "work", "22", "Work", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._rememberedTerminalBindings.add(identity)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._gate.focused = identity
        plugin._gate.manual_enabled = True

        activation = plugin._sessionClaimService.activate_remembered_binding(
            identity,
            instance.identifier,
            focus_regained=True,
        )
        request = plugin._sessionClaimService.plan_remembered_state_request(
            identity,
            instance.identifier,
        )

        self.assertEqual(RememberedBindingActivationKind.ACTIVATE, activation.kind)
        self.assertEqual(instance, activation.instance)
        self.assertIs(client, activation.client)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIsNone(plugin._gate.bound_terminal)
        self.assertEqual(RememberedStateRequestKind.FOCUS_CONTEXT, request.kind)
        self.assertIs(client, request.client)
        self.assertTrue(
            plugin._connectionCoordinator.matches_focus_context(
                instance.identifier,
                request.request_id,
                identity,
            )
        )
        plugin.terminate()

    def test_queued_f12_authorization_is_cancelled_after_service_replacement(self) -> None:
        import queueHandler
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin, getTerminalIntegrationService

        first = GlobalPlugin()
        self._focusPlugin(first)
        first._gate.manual_enabled = True
        first._claimInventoryReady = True
        adapter = AppModule()
        self.focus.appModule = adapter
        queued = []
        original_queue_function = queueHandler.queueFunction
        queueHandler.queueFunction = lambda _queue, function, *args, **_kwargs: queued.append(
            (function, args)
        )
        try:
            adapter._decideExecuteGesture(
                types.SimpleNamespace(normalizedIdentifiers=("kb:f12",)),
            )
            self.assertEqual(1, len(queued))
            second = GlobalPlugin()
            queued[0][0](*queued[0][1])
        finally:
            queueHandler.queueFunction = original_queue_function

        self.assertIsNone(first._pendingObservedClaim)
        self.assertIs(second._terminalIntegrationService, getTerminalIntegrationService())
        self.assertIsNone(second._pendingObservedClaim)
        self.assertIn("frontendScopeChanged", first._diagnostics.report())
        first.terminate()
        adapter.terminate()
        second.terminate()

    def test_windows_terminal_overlay_hook_inserts_only_for_a_terminal_control(self) -> None:
        import controlTypes
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredTerminalBrailleOverlay

        plugin = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        classes = [object]

        adapter.chooseNVDAObjectOverlayClasses(self.focus, classes)

        self.assertIs(StructuredTerminalBrailleOverlay, classes[0])
        non_terminal = types.SimpleNamespace(role=controlTypes.Role.TERMINAL + 1)
        unchanged = [object]
        adapter.chooseNVDAObjectOverlayClasses(non_terminal, unchanged)
        self.assertEqual([object], unchanged)
        adapter.terminate()
        plugin.terminate()

    def test_windows_terminal_overlay_hook_fails_open_on_identity_error(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        self.focus.appModule = adapter
        plugin._gate.manual_enabled = True
        plugin._gate.authenticated = True
        plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._identity(self.focus)
        plugin._gate.bound_terminal = plugin._gate.focused
        plugin._terminalFocusService._identityForObject = (
            lambda _obj: (_ for _ in ()).throw(RuntimeError("identity failed"))
        )
        classes = []

        adapter.chooseNVDAObjectOverlayClasses(self.focus, classes)

        self.assertEqual([], classes)
        self.assertFalse(plugin._gate.suppression_active)
        report = plugin._diagnostics.report()
        self.assertIn('"category": "terminalEventFailedOpen"', report)
        self.assertIn('"event": "chooseNVDAObjectOverlayClasses"', report)
        adapter.terminate()
        plugin.terminate()

    def test_windows_terminal_events_fail_open_exactly_once(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        plugin._gate.manual_enabled = True
        plugin._gate.authenticated = True
        plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._identity(self.focus)
        plugin._gate.bound_terminal = plugin._gate.focused
        native = []

        def broken(_obj):
            raise RuntimeError("frontend failed")

        plugin._terminalFocusService.should_suppress = broken
        adapter.event_textChange(self.focus, lambda: native.append("native"))

        self.assertEqual(["native"], native)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIn(
            '"category": "terminalEventFailedOpen"',
            plugin._diagnostics.report(),
        )
        plugin.terminate()

    def test_windows_terminal_does_not_repeat_native_handler_after_late_failure(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        native = []

        def broken_after_delegation(_decision):
            raise RuntimeError("late frontend failure")

        plugin._terminalFocusService.finish_focus = broken_after_delegation
        adapter.event_gainFocus(self.focus, lambda: native.append("native"))
        self.assertEqual(["native"], native)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIn("gainFocusCompletion", plugin._diagnostics.report())
        plugin.terminate()

    def test_early_focus_failure_calls_native_once_when_diagnostics_also_fail(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        adapter = AppModule()
        identity = plugin._identity(self.focus)
        plugin._gate.manual_enabled = True
        plugin._gate.authenticated = True
        plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._client = object()
        plugin._terminalFocusService.prepare_focus = mock.Mock(side_effect=RuntimeError("focus failed"))
        original_record = plugin._diagnostics.record
        plugin._diagnostics.record = mock.Mock(side_effect=RuntimeError("diagnostics failed"))
        native = []
        try:
            adapter.event_gainFocus(self.focus, lambda: native.append(True))
        finally:
            plugin._diagnostics.record = original_record

        self.assertEqual([True], native)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIsNone(plugin._client)
        adapter.terminate()
        plugin.terminate()

    def test_global_service_does_not_inspect_focus_and_app_module_clears_scope(self) -> None:
        import api
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        focus_queries = []
        api.getFocusObject = lambda: focus_queries.append(True) or self.focus
        plugin = GlobalPlugin()
        self.assertEqual([], focus_queries)
        adapter = AppModule()
        adapter.event_gainFocus(self.focus, lambda: None)
        self.assertIsNotNone(plugin._gate.focused)
        adapter.event_appModule_loseFocus()
        self.assertIsNone(plugin._gate.focused)
        self.assertFalse(plugin._gate.suppression_active)
        spoken_before = list(self.spoken)
        sounds_before = list(self.soundFeeds)
        plugin._handleScopedNetworkEvent({
            "type": "modeChanged",
            "payload": {"mode": "insert", "lineText": "foreign", "cursor": {"line": 1}},
        })
        self.assertEqual(spoken_before, self.spoken)
        self.assertEqual(sounds_before, self.soundFeeds)
        plugin.terminate()

    def test_stale_lose_focus_from_first_wt_cannot_clear_second_wt(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        second_focus = types.SimpleNamespace(
            processID=9000, windowHandle=9001, role=3, parent=None,
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: (42, 9001, 4, 6),
            ),
        )
        plugin = GlobalPlugin()
        first_adapter = AppModule()
        second_adapter = AppModule()
        first_adapter.event_gainFocus(self.focus, lambda: None)
        second_adapter.event_gainFocus(second_focus, lambda: None)
        second_identity = plugin._identity(second_focus)
        self.assertEqual(second_identity, plugin._gate.focused)

        # NVDA may deliver this after the second WT has already gained focus.
        first_adapter.event_appModule_loseFocus()
        self.assertEqual(second_identity, plugin._gate.focused)
        self.assertIs(second_focus, plugin._focusedTerminalObject)
        second_adapter.event_appModule_loseFocus()
        self.assertIsNone(plugin._gate.focused)
        plugin.terminate()

    def test_reentrant_focus_keeps_new_scope_and_defers_old_pending_state(self) -> None:
        from appModules.windowsterminal import AppModule
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        second_focus = types.SimpleNamespace(
            processID=9000, windowHandle=9001, role=3, parent=None,
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: (42, 9001, 4, 6),
            ),
        )
        client = types.SimpleNamespace(
            start=lambda: None, stop=lambda: None,
            send_control=lambda *_args: True,
        )
        plugin = GlobalPlugin()
        first_identity = plugin._identity(self.focus)
        instance = add_remote_instance(
            plugin._instanceManager, "work", "one", "Work", client,
        )
        plugin._instanceManager.bind(first_identity, instance.identifier)
        pending = {
            "type": "fullState",
            "payload": {
                "mode": "normal", "lineText": "first pending",
                "cursor": {"line": 1, "byteColumn": 0},
            },
        }
        plugin._pendingInstanceFullStates[instance.identifier] = pending
        first_adapter = AppModule()
        second_adapter = AppModule()
        native = []
        cancellations_before = self.speechCancellations

        def first_native():
            native.append("first")
            second_adapter.event_gainFocus(
                second_focus, lambda: native.append("second"),
            )

        first_adapter.event_gainFocus(self.focus, first_native)

        self.assertEqual(["first", "second"], native)
        self.assertEqual(plugin._identity(second_focus), plugin._gate.focused)
        self.assertIs(pending, plugin._pendingInstanceFullStates[instance.identifier])
        self.assertEqual(cancellations_before, self.speechCancellations)
        self.assertIn(
            '"category": "staleTerminalFocusCompletionIgnored"',
            plugin._diagnostics.report(),
        )
        plugin.terminate()

    def test_all_open_ssh_connections_are_automatic_without_a_default(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        self._updateSettings(plugin, {
            "connections": [
                {"id": "one", "name": "One", "host": "one", "user": "u", "port": 22,
                 "identityFile": "", "authentication": "openSsh"},
                {"id": "two", "name": "Two", "host": "two", "user": "v", "port": 22,
                 "identityFile": "", "authentication": "openSsh"},
            ],
        })
        self.assertEqual(["one", "two"], [
            profile.identifier for profile in plugin._automaticClaimProfiles()
        ])
        self.assertNotIn("activeConnection", self._settingsSnapshot(plugin))
        plugin.terminate()

    def test_parallel_identical_instances_speak_only_when_explicitly_bound(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        clients = []
        class FakeStdioClient:
            def __init__(inner_self, _target, on_event, on_state, **_kwargs):
                inner_self.on_event = on_event
                inner_self.on_state = on_state
                inner_self.starts = inner_self.stops = 0
                clients.append(inner_self)
            def start(inner_self): inner_self.starts += 1
            def stop(inner_self): inner_self.stops += 1
            def send_control(inner_self, *_args): return True

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {
            "connections": [{
                "id": "same", "name": "Same target", "host": "example-host", "user": "editor",
                "port": 22, "identityFile": "", "authentication": "openSsh",
            }],
        })
        with mock.patch.object(addon_module, "SshStdioClient", FakeStdioClient):
            plugin._startManagedInstance("same", "111")
            plugin._startManagedInstance("same", "111")
        instances = plugin._instanceManager.list()
        self.assertEqual(2, len(instances))
        self.assertNotEqual(instances[0].identifier, instances[1].identifier)
        self.assertEqual([1, 1], [client.starts for client in clients])

        plugin._bindManagedInstance(instances[1].identifier)
        self.spoken.clear()
        clients[0].on_event({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "wrong", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertEqual([], self.spoken)
        clients[1].on_event({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "right", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertIn("right", self.spoken)
        plugin.terminate()
        self.assertEqual([1, 1], [client.stops for client in clients])

    def test_remote_session_ids_stay_internal_and_single_session_is_selected_automatically(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        started = []
        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work server", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        plugin._sessionDiscoveryGeneration = 7
        plugin._startManagedInstance = lambda profile_id, session_id, **kwargs: started.append(
            (profile_id, session_id, kwargs)
        )
        session = RemoteSession("9842", "project", "/srv/project")
        plugin._finishSessionDiscovery(7, profile, plugin._identity(self.focus), [session], None)
        self.assertEqual(("work", "9842"), started[0][:2])
        self.assertEqual("project, working directory /srv/project", started[0][2]["session_label"])
        self.assertFalse(any("9842" in message for message in self.messages))
        plugin.terminate()

    def test_multiple_remote_sessions_use_friendly_choice_and_stale_results_are_ignored(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        sessions = [
            RemoteSession("11", "first", "/one"), RemoteSession("22", "second", "/two"),
        ]
        started = []
        plugin._startManagedInstance = lambda profile_id, session_id, **kwargs: started.append(session_id)
        plugin._sessionDiscoveryGeneration = 4
        plugin._finishSessionDiscovery(3, profile, plugin._identity(self.focus), sessions, None)
        self.assertEqual([], started)
        self.singleChoiceSelections.append(1)
        plugin._finishSessionDiscovery(4, profile, plugin._identity(self.focus), sessions, None)
        self.assertEqual(["22"], started)
        self.assertEqual(["first, working directory /one", "second, working directory /two"],
                         self.singleChoiceDialogs[-1].choices)
        self.assertTrue(any("multiple" in message.lower() for message in self.messages))
        plugin.terminate()

    def test_f12_pairing_selects_only_the_newest_fresh_claim(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        sessions = [
            RemoteSession("11", "same", "/same", claim_age_ms=1400),
            RemoteSession("22", "same", "/same", claim_age_ms=180),
            RemoteSession("33", "same", "/same", claim_age_ms=-1),
        ]
        started = []
        plugin._startManagedInstance = lambda profile_id, session_id, **kwargs: started.append(session_id)
        plugin._sessionDiscoveryGeneration = 5
        plugin._finishSessionDiscovery(
            5, profile, plugin._identity(self.focus), sessions, None,
            require_recent_claim=True,
        )
        self.assertEqual(["22"], started)
        self.assertEqual([], self.singleChoiceDialogs)
        plugin.terminate()

    def test_f12_pairing_rejects_unclaimed_and_old_sessions(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        plugin._sessionDiscoveryGeneration = 6
        plugin._startManagedInstance = lambda *args, **kwargs: self.fail("must not connect")
        plugin._finishSessionDiscovery(
            6, profile, plugin._identity(self.focus), [
                RemoteSession("11", "unclaimed", "/one"),
                RemoteSession("22", "old", "/two", claim_age_ms=15001),
            ], None, require_recent_claim=True,
        )
        self.assertTrue(any("did not confirm" in message.lower() for message in self.messages))
        plugin.terminate()

    def test_repeated_f12_reuses_the_existing_claimed_session_transport(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload):
                self.controls.append((kind, payload))
                return True

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "work", "22", "Work, project", client)
        identity = plugin._identity(self.focus)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._sessionDiscoveryGeneration = 8
        plugin._startManagedInstance = lambda *args, **kwargs: self.fail("must reuse transport")
        plugin._finishSessionDiscovery(
            8, profile, identity,
            [RemoteSession("22", "project", "/work", claim_age_ms=100)],
            None, require_recent_claim=True,
        )
        self.assertEqual(1, len(plugin._instanceManager.list()))
        self.assertEqual(instance.identifier, plugin._instanceManager.selected_for(identity).identifier)
        self.assertEqual("requestFocusContext", client.controls[-1][0])
        plugin.terminate()

    def test_same_directory_sessions_have_names_time_ordinals_and_status(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        class Client:
            def start(self): pass
            def stop(self): pass

        plugin = GlobalPlugin()
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        unnamed = [
            RemoteSession("11", "", "/same", 1_700_000_000),
            RemoteSession("22", "", "/same", 1_700_000_060),
        ]
        labels = plugin._remoteSessionLabels(profile, unnamed)
        self.assertIn("session 1 of 2", labels[0])
        self.assertIn("session 2 of 2", labels[1])
        self.assertIn("started", labels[0])
        named = [
            RemoteSession("11", "Documentation", "/same", 1_700_000_000),
            RemoteSession("22", "Programming", "/same", 1_700_000_060),
        ]
        self.assertEqual([
            "Documentation, working directory /same",
            "Programming, working directory /same",
        ], plugin._remoteSessionLabels(profile, named))
        instance = add_remote_instance(plugin._instanceManager, "work", "11", "Documentation", Client())
        self.assertIn("already connected", plugin._remoteSessionLabels(profile, named)[0])
        plugin._instanceManager.remove(instance.identifier)
        plugin.terminate()

    def test_closed_terminal_prunes_binding_and_stops_client_off_main_thread(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        stopped = threading.Event()
        stop_threads = []

        class Client:
            def start(self): pass
            def stop(self):
                stop_threads.append(threading.current_thread().name)
                stopped.set()

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        identity = plugin._identity(self.focus)
        instance = add_remote_instance(plugin._instanceManager, "work", "22", "Work", Client())
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._gate.manual_enabled = True
        plugin._gate.bound_terminal = identity
        plugin._gate.authenticated = True
        plugin._gate.focused = None
        with mock.patch.object(plugin._terminalFocusService, "_identityExists", return_value=False):
            self.assertEqual(set(), plugin._pruneClosedTerminalBindings())
            self.assertEqual({instance.identifier}, plugin._pruneClosedTerminalBindings())
        self.assertTrue(stopped.wait(1))
        self.assertEqual([], plugin._instanceManager.list())
        self.assertIsNone(plugin._gate.focused)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertEqual(["nvim-nvda-managed-client-stop"], stop_threads)
        plugin.terminate()

    def test_closed_terminal_pruning_preserves_other_window_and_client(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.gate import TerminalIdentity

        class Client:
            def __init__(self): self.stops = 0
            def start(self): pass
            def stop(self): self.stops += 1

        plugin = GlobalPlugin()
        dead = TerminalIdentity(100, 200, "windowsTerminal", (1,))
        live = TerminalIdentity(100, 200, "windowsTerminal", (2,))
        dead_client, live_client = Client(), Client()
        dead_instance = add_remote_instance(plugin._instanceManager, "one", "1", "One", dead_client)
        live_instance = add_remote_instance(plugin._instanceManager, "two", "2", "Two", live_client)
        plugin._instanceManager.bind(dead, dead_instance.identifier)
        plugin._instanceManager.bind(live, live_instance.identifier)
        with mock.patch.object(
            plugin._terminalFocusService, "_identityExists",
            side_effect=lambda identity, _element=None: identity == live,
        ):
            self.assertEqual(set(), plugin._pruneClosedTerminalBindings())
            self.assertEqual({dead_instance.identifier}, plugin._pruneClosedTerminalBindings())
        self.assertEqual([live_instance], plugin._instanceManager.list())
        self.assertEqual(live_instance, plugin._instanceManager.selected_for(live))
        self.assertEqual(0, live_client.stops)
        plugin.terminate()

    def test_whole_closed_window_prunes_all_its_tabs_but_not_other_window(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.gate import TerminalIdentity

        class Client:
            def start(self): pass
            def stop(self): pass

        plugin = GlobalPlugin()
        closed_instances = []
        for index in range(6):
            identity = TerminalIdentity(100, 200, "windowsTerminal", (42, 200, 4, index))
            instance = add_remote_instance(plugin._instanceManager, "target", str(index), f"Closed {index}", Client())
            plugin._instanceManager.bind(identity, instance.identifier)
            closed_instances.append(instance.identifier)
        survivor_identity = TerminalIdentity(101, 201, "windowsTerminal", (42, 201, 4, 1))
        survivor = add_remote_instance(plugin._instanceManager, "other", "live", "Live", Client())
        plugin._instanceManager.bind(survivor_identity, survivor.identifier)
        with mock.patch.object(
            plugin._terminalFocusService, "_identityExists",
            side_effect=lambda identity, _element=None: identity.window_handle == 201,
        ):
            self.assertEqual(set(), plugin._pruneClosedTerminalBindings())
            self.assertEqual(set(closed_instances), plugin._pruneClosedTerminalBindings())
        self.assertEqual([survivor], plugin._instanceManager.list())
        self.assertEqual(survivor, plugin._instanceManager.selected_for(survivor_identity))
        plugin.terminate()

    def test_terminal_lifecycle_sweep_repeats_and_prunes_idle_closed_tab(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(self): pass
            def stop(self): pass

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        identity = plugin._identity(self.focus)
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "Idle local", Client())
        plugin._instanceManager.bind(identity, instance.identifier)
        scheduled = []

        def schedule(delay, callback, *args):
            scheduled.append((delay, callback, args))
            return object()

        plugin._terminalFocusService._scheduleMainThreadCall = schedule
        plugin._ensureTerminalLifecycleSweep()
        self.assertEqual(1, len(scheduled))
        self.assertEqual(addon_module._TERMINAL_LIFECYCLE_INTERVAL_MS, scheduled[0][0])
        plugin._gate.focused = None
        plugin._terminalLifecycleScheduledAt -= addon_module._TERMINAL_LIFECYCLE_INTERVAL_MS / 1_000
        with mock.patch.object(plugin._terminalFocusService, "_identityExists", return_value=False):
            scheduled[0][1](*scheduled[0][2])
            self.assertEqual([instance], plugin._instanceManager.list())
            self.assertEqual(2, len(scheduled))
            plugin._terminalLifecycleScheduledAt -= addon_module._TERMINAL_LIFECYCLE_INTERVAL_MS / 1_000
            scheduled[1][1](*scheduled[1][2])
        self.assertEqual([], plugin._instanceManager.list())
        plugin.terminate()

    def test_terminal_lifecycle_never_prunes_focused_tab_on_negative_uia_result(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(self): pass
            def stop(self): pass

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        identity = plugin._gate.focused
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "Focused local", Client())
        plugin._instanceManager.bind(identity, instance.identifier)
        with mock.patch.object(plugin._terminalFocusService, "_identityExists", return_value=False) as exists:
            self.assertEqual(set(), plugin._pruneClosedTerminalBindings())
            self.assertEqual(set(), plugin._pruneClosedTerminalBindings())
        exists.assert_not_called()
        self.assertEqual([instance], plugin._instanceManager.list())
        plugin.terminate()

    def test_editor_and_action_paths_do_not_run_terminal_lifecycle_pruning(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._pruneClosedTerminalBindings = mock.Mock(
            side_effect=AssertionError("lifecycle pruning must only run in its timer"),
        )
        plugin._refreshFocusedTerminalForAction(self.focus)
        plugin._handleManagedState("missing", "disconnected")
        plugin._handleManagedEvent("missing", {"type": "modeChanged", "payload": {}})
        plugin._pruneClosedTerminalBindings.assert_not_called()
        plugin.terminate()

    def test_terminal_lifecycle_failure_drops_suppression_and_does_not_repeat(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(self): pass
            def stop(self): pass

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        identity = plugin._gate.focused
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "Local", Client())
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._gate.manual_enabled = True
        plugin._gate.authenticated = True
        plugin._gate.nvim_active = True
        plugin._gate.bound_terminal = identity
        self.assertTrue(plugin._gate.suppression_active)
        scheduled = []
        plugin._terminalFocusService._scheduleMainThreadCall = (
            lambda *args: scheduled.append(args) or object()
        )
        plugin._terminalFocusService.prune_closed_bindings = mock.Mock(
            side_effect=RuntimeError("broken UIA"),
        )

        plugin._runTerminalLifecycleSweep()

        self.assertFalse(plugin._gate.suppression_active)
        self.assertEqual([], scheduled)
        self.assertIn(
            '"category": "terminalLifecycleFailedOpen"',
            plugin._diagnostics.report(),
        )
        plugin.terminate()

    def test_connect_command_explicitly_selects_profile_without_exposing_ids(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"connections": [
            {"id": "internal-one", "name": "editor@example-host", "host": "example-host", "user": "editor",
             "port": 22, "identityFile": "", "authentication": "openSsh"},
            {"id": "internal-two", "name": "admin@example-host-2", "host": "example-host-2", "user": "admin",
             "port": 22, "identityFile": "", "authentication": "openSsh"},
        ]})
        self.singleChoiceSelections.append(2)
        identity = plugin._gate.focused
        plugin.action_startConnectionInstance(None)
        self.assertEqual([
            "This computer - local Neovim", "editor@example-host", "admin@example-host-2",
        ], self.singleChoiceDialogs[-1].choices)
        self.assertNotIn("internal-two", self.singleChoiceDialogs[-1].choices)
        self.assertEqual(("remoteSsh", "internal-two"), plugin._pendingClaimTargets[identity])
        self.assertTrue(any("press F12" in message for message in self.messages))
        scheduled = []
        plugin._scheduleMainThreadCall = lambda delay, callback, *args: scheduled.append(
            (delay, callback, args)
        )
        plugin.action_claimFocusedNeovimSession(
            types.SimpleNamespace(send=lambda: None),
        )
        self.assertEqual(250, scheduled[0][0])
        self.assertEqual("_beginSessionSelection", scheduled[0][1].__name__)
        self.assertEqual("internal-two", scheduled[0][2][0].identifier)
        self.assertEqual(identity, scheduled[0][2][1])
        self.assertEqual((True, True, True), scheduled[0][2][2:])
        plugin.terminate()

    def test_connect_command_can_select_local_target_without_persisted_ids(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_targets import LOCAL_WINDOWS_TCP

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        self.singleChoiceSelections.append(0)
        plugin.action_startConnectionInstance(None)
        self.assertEqual((LOCAL_WINDOWS_TCP, ""), plugin._pendingClaimTargets[identity])
        self.assertTrue(any("press F12" in message for message in self.messages))
        self.assertFalse(any("local-windows" in message for message in self.messages))
        plugin.terminate()

    def test_local_f12_pairs_only_fresh_claim(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_targets import LOCAL_WINDOWS_TCP
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        plugin._pendingClaimTargets[identity] = (LOCAL_WINDOWS_TCP, "")
        selections = []
        plugin._beginLocalSessionSelection = lambda *args: selections.append(args)
        sent = []
        plugin.action_claimFocusedNeovimSession(
            types.SimpleNamespace(send=lambda: sent.append(True)),
        )
        self.assertEqual([True], sent)
        self.assertEqual((identity, True, True, True, None), selections[0][:5])
        self.assertGreater(selections[0][5], 0)

        stale = LocalWindowsSession("1", "stale", "C:/one", "127.0.0.1", 41001, 1,
                                    claim_age_ms=15_001)
        fresh = LocalWindowsSession("2", "fresh", "C:/two", "127.0.0.1", 41002, 2,
                                    claim_age_ms=120)
        started = []
        plugin._sessionDiscoveryGeneration = 8
        plugin._startLocalSession = lambda terminal, session, **kwargs: started.append(
            (terminal, session, kwargs)
        )
        plugin._finishLocalSessionDiscovery(
            8, identity, [stale, fresh], None, True, True, True,
        )
        self.assertEqual("2", started[0][1].identifier)
        self.assertTrue(started[0][2]["replace_existing"])
        plugin.terminate()

    def test_f12_ignores_a_local_claim_from_before_the_current_keypress(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        previous_claim = LocalWindowsSession(
            "77", "Local", "C:/work", "127.0.0.1", 45678, 77,
            claim_age_ms=100, claimed_monotonic_ns=4_000,
        )
        fallbacks = []
        plugin._beginSessionSelection = lambda *args: fallbacks.append(args)
        plugin._sessionDiscoveryGeneration = 5
        plugin._finishLocalSessionDiscovery(
            5, identity, [previous_claim], None, True, True, True, profile, 5_000,
        )
        self.assertEqual((profile, identity, True, True, True), fallbacks[0])
        plugin.terminate()

    def test_local_instance_uses_typed_transport_and_coexists_with_ssh(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_targets import LOCAL_WINDOWS_TCP
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        class Client:
            created = []
            def __init__(
                inner_self, host, port, on_event, on_state, on_diagnostic,
                session_nonce=None,
            ):
                inner_self.host, inner_self.port = host, port
                inner_self.session_nonce = session_nonce
                inner_self.on_event, inner_self.on_state = on_event, on_state
                inner_self.starts = inner_self.stops = 0
                Client.created.append(inner_self)
            def start(inner_self): inner_self.starts += 1
            def stop(inner_self): inner_self.stops += 1
            def send_control(inner_self, _kind, _payload): return True

        class SshClient:
            def start(inner_self): pass
            def stop(inner_self): pass

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        remote = add_remote_instance(plugin._instanceManager, "work", "ssh-session", "Work", SshClient())
        local_identity = plugin._gate.focused
        local = LocalWindowsSession(
            "77", "Local docs", "C:/docs", "127.0.0.1", 45678, 77, claim_age_ms=10,
            session_nonce="a" * 32,
        )
        with mock.patch.object(addon_module, "LocalTcpClient", Client):
            plugin._startLocalManagedInstance(local, local_identity, "Local docs")
        instances = plugin._instanceManager.list()
        self.assertEqual(2, len(instances))
        local_instance = plugin._instanceManager.selected_for(local_identity)
        self.assertEqual(LOCAL_WINDOWS_TCP, local_instance.transport_kind)
        plugin._authenticatedInstances.add(local_instance.identifier)
        self.assertFalse(hasattr(local_instance, "profile_id"))
        self.assertEqual(("127.0.0.1", 45678, 1), (
            Client.created[0].host, Client.created[0].port, Client.created[0].starts,
        ))
        self.assertEqual("a" * 32, Client.created[0].session_nonce)
        self.assertIn(remote.identifier, [instance.identifier for instance in instances])
        pairings = []
        plugin._beginLocalSessionSelection = lambda *args: pairings.append(args)
        sent = []
        plugin.action_claimFocusedNeovimSession(
            types.SimpleNamespace(send=lambda: sent.append(True)),
        )
        self.assertEqual([True], sent)
        self.assertEqual((local_identity, True, True, True, None), pairings[0][:5])
        self.assertGreater(pairings[0][5], 0)
        plugin.terminate()

    def test_disconnected_local_binding_does_not_block_fresh_remote_claim_resolution(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_targets import local_windows_target

        class Client:
            def start(self): pass
            def stop(self): pass

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        plugin._claimInventoryReady = True
        identity = plugin._gate.focused
        instance = plugin._instanceManager.add_target(
            local_windows_target("Local"), "old-local", "Local", Client(),
        )
        plugin._instanceManager.bind(identity, instance.identifier)
        self.assertNotIn(instance.identifier, plugin._authenticatedInstances)
        scheduled = []
        plugin._scheduleMainThreadCall = lambda delay, callback, *args: scheduled.append(
            (delay, callback, args)
        )
        sent = []

        plugin.action_claimFocusedNeovimSession(
            types.SimpleNamespace(send=lambda: sent.append(True)),
        )

        self.assertEqual([True], sent)
        self.assertEqual(250, scheduled[0][0])
        self.assertEqual("_beginAutomaticClaimResolution", scheduled[0][1].__name__)
        self.assertEqual(identity, scheduled[0][2][0])
        self.assertGreater(scheduled[0][2][1], 0)
        report = plugin._diagnostics.report()
        self.assertIn('"selected": true', report)
        self.assertIn('"selectedAuthenticated": false', report)
        plugin.terminate()

    def test_two_local_sessions_bind_independently_and_coexist_with_ssh(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.gate import TerminalIdentity
        from globalPlugins.NeovimAccessLink.core.local_sessions import LocalWindowsSession

        class Client:
            created = []
            def __init__(
                inner_self, host, port, on_event, on_state, on_diagnostic,
                session_nonce=None,
            ):
                inner_self.host, inner_self.port = host, port
                inner_self.session_nonce = session_nonce
                inner_self.starts = inner_self.stops = 0
                Client.created.append(inner_self)
            def start(inner_self): inner_self.starts += 1
            def stop(inner_self): inner_self.stops += 1
            def send_control(inner_self, _kind, _payload): return True

        class SshClient:
            def start(inner_self): pass
            def stop(inner_self): pass

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        add_remote_instance(plugin._instanceManager, "work", "ssh-session", "Work", SshClient())
        first_identity = plugin._gate.focused
        second_identity = TerminalIdentity(
            first_identity.process_id, first_identity.window_handle,
            "windowsTerminal", (42, first_identity.window_handle, 4, 53),
        )
        first = LocalWindowsSession(
            "77", "Local docs", "C:/docs", "127.0.0.1", 45678, 77, claim_age_ms=10,
            session_nonce="a" * 32,
        )
        second = LocalWindowsSession(
            "88", "Local code", "C:/code", "127.0.0.1", 45679, 88, claim_age_ms=20,
            session_nonce="b" * 32,
        )
        with mock.patch.object(addon_module, "LocalTcpClient", Client):
            plugin._startLocalManagedInstance(first, first_identity, "Local docs")
            plugin._startLocalManagedInstance(second, second_identity, "Local code")
        instances = plugin._instanceManager.list()
        self.assertEqual(3, len(instances))
        self.assertEqual("77", plugin._instanceManager.selected_for(first_identity).session_id)
        self.assertEqual("88", plugin._instanceManager.selected_for(second_identity).session_id)
        self.assertEqual([45678, 45679], [client.port for client in Client.created])
        self.assertEqual(["a" * 32, "b" * 32], [client.session_nonce for client in Client.created])
        self.assertEqual([1, 1], [client.starts for client in Client.created])
        plugin.terminate()

    def test_explicit_connection_survives_modal_focus_gap_for_second_wt_window(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        identity = plugin._gate.focused
        profile = parse_profile({
            "id": "root", "name": "admin@example-host", "host": "example-host", "user": "admin",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        started = []
        plugin._startManagedInstance = lambda profile_id, session_id, **kwargs: started.append(
            (profile_id, session_id, kwargs.get("identity"))
        )

        # A modal wx dialog moves focus away from the Windows Terminal AppModule.
        plugin._gate.focused = None
        plugin._sessionDiscoveryGeneration = 3
        plugin._finishSessionDiscovery(
            3, profile, identity, [RemoteSession("session", "root", "/root")], None,
            replace_existing=True, offer_remember=True, preserve_dialog_identity=True,
        )

        self.assertEqual([("root", "session", identity)], started)
        plugin.terminate()

    def test_windows_terminal_runtime_id_is_stable_and_distinguishes_tabs(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        def terminal(runtime_id):
            element = types.SimpleNamespace(
                cachedClassName="TermControl", getRuntimeId=lambda: runtime_id,
            )
            return types.SimpleNamespace(
                processID=1001, windowHandle=2001, UIAElement=element, parent=None,
                appModule=types.SimpleNamespace(appName="windowsterminal"),
            )

        first = GlobalPlugin._identity(terminal((42, 2001, 4, 6)))
        first_again = GlobalPlugin._identity(terminal((42, 2001, 4, 6)))
        second = GlobalPlugin._identity(terminal((42, 2001, 4, 53)))
        self.assertEqual(first, first_again)
        self.assertNotEqual(first, second)
        self.assertEqual("windowsTerminal", first.frontend_kind)

    def test_terminal_identity_checks_exact_runtime_id_with_conservative_errors(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink.core.gate import TerminalIdentity

        live = (42, 2001, 4, 6)
        closed = (42, 2001, 4, 53)

        class Root:
            def findFirst(self, scope, condition):
                self.scope = scope
                return object() if condition == live else None

        root = Root()
        client = types.SimpleNamespace(
            elementFromHandle=lambda handle: root,
            createPropertyCondition=lambda prop, value: tuple(value),
        )
        uia = types.SimpleNamespace(
            handler=types.SimpleNamespace(clientObject=client),
            UIA_RuntimeIdPropertyId=30000, TreeScope_Subtree=7,
        )
        with mock.patch.object(addon_module, "_windowIdentityExists", return_value=True), \
                mock.patch.dict(sys.modules, {"UIAHandler": uia}):
            self.assertTrue(addon_module._terminalIdentityExists(
                TerminalIdentity(1001, 2001, "windowsTerminal", live),
            ))
            self.assertFalse(addon_module._terminalIdentityExists(
                TerminalIdentity(1001, 2001, "windowsTerminal", closed),
            ))
            inactive_element = types.SimpleNamespace(getRuntimeId=lambda: closed)
            self.assertTrue(addon_module._terminalIdentityExists(
                TerminalIdentity(1001, 2001, "windowsTerminal", closed), inactive_element,
            ), "a directly live hidden tab is retained even when subtree search misses it")
        with mock.patch.object(addon_module, "_windowIdentityExists", return_value=False):
            self.assertFalse(addon_module._terminalIdentityExists(
                TerminalIdentity(1001, 2001, "windowsTerminal", live),
            ))
        client.elementFromHandle = lambda _handle: (_ for _ in ()).throw(OSError())
        with mock.patch.object(addon_module, "_windowIdentityExists", return_value=True), \
                mock.patch.dict(sys.modules, {"UIAHandler": uia}):
            self.assertTrue(addon_module._terminalIdentityExists(
                TerminalIdentity(1001, 2001, "windowsTerminal", closed),
            ), "uncertain UIA failure must retain the binding")

    def test_frontend_identity_relies_only_on_appmodule_internal_tab_constraints(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        def terminal(class_name="TermControl", runtime_id=(42, 2001, 4, 6)):
            return types.SimpleNamespace(
                processID=1001, windowHandle=2001, role=3, parent=None,
                UIAElement=types.SimpleNamespace(
                    cachedClassName=class_name, getRuntimeId=lambda: runtime_id,
                ),
            )

        self.assertIsNotNone(GlobalPlugin._identity(terminal()))
        self.assertIsNone(GlobalPlugin._identity(terminal("OtherControl")))
        self.assertIsNone(GlobalPlugin._identity(terminal(runtime_id=())))

    def test_activation_is_fail_open_outside_windows_terminal(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        self.focus = types.SimpleNamespace(
            processID=900, windowHandle=901, role=3, parent=None,
            appModule=types.SimpleNamespace(appName="putty"),
        )
        plugin = GlobalPlugin()
        plugin._toggleNeovimMode()
        self.assertFalse(plugin._gate.manual_enabled)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertIn("unavailable", self.messages[-1])
        plugin.terminate()

    def test_successful_explicit_connection_can_be_remembered_for_tab(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        element = types.SimpleNamespace(
            cachedClassName="TermControl", getRuntimeId=lambda: (42, 2001, 4, 6),
        )
        self.focus.UIAElement = element
        self.focus.parent = None
        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "work", "42", "editor@example-host", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._rememberOfferInstances.add(instance.identifier)
        plugin._handleManagedEvent(instance.identifier, {
            "type": "fullState", "payload": {
                "mode": "normal", "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        self.assertIn(identity, plugin._rememberedTerminalBindings)
        self.assertTrue(plugin._gate.suppression_active)
        self.assertEqual([], client.controls)
        self.assertTrue(any("remembered" in message.lower() for message in self.messages))
        plugin.terminate()

    def test_first_full_state_waits_for_terminal_focus_after_session_dialog(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(self): pass
            def stop(self): pass
            def send_control(self, *_args): return True

        terminal = types.SimpleNamespace(
            processID=1001, windowHandle=2001, role=3, parent=None,
            appModule=types.SimpleNamespace(appName="windowsterminal"),
            UIAElement=types.SimpleNamespace(
                cachedClassName="TermControl",
                getRuntimeId=lambda: (42, 2001, 4, 6),
            ),
        )
        dialog = types.SimpleNamespace(processID=1001, windowHandle=999999, role=4, parent=None)
        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        identity = plugin._identity(terminal)
        instance = add_remote_instance(plugin._instanceManager, "work", "42", "editor@example-host", Client())
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._rememberOfferInstances.add(instance.identifier)

        self.focus = dialog
        plugin._handleManagedEvent(instance.identifier, {
            "type": "fullState", "payload": {
                "mode": "normal", "lineText": "ready",
                "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        self.assertIn(instance.identifier, plugin._pendingInstanceFullStates)
        self.assertIn(instance.identifier, plugin._rememberOfferInstances)
        self.assertFalse(plugin._gate.suppression_active)

        self.focus = terminal
        native_focus = []
        adapter = self._terminalAdapter()
        adapter.event_gainFocus(terminal, lambda: native_focus.append(True))
        self.assertEqual([True], native_focus)
        self.assertNotIn(instance.identifier, plugin._pendingInstanceFullStates)
        self.assertIn(instance.identifier, plugin._authenticatedInstances)
        self.assertTrue(plugin._gate.suppression_active)
        self.assertIn("ready", self.spoken)
        plugin.terminate()

    def test_activity_from_another_session_never_rebinds_an_unbound_control(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        def terminal(runtime_id):
            return types.SimpleNamespace(
                processID=1002, windowHandle=2002, role=3, parent=None,
                appModule=types.SimpleNamespace(appName="windowsterminal"),
                UIAElement=types.SimpleNamespace(
                    cachedClassName="TermControl", getRuntimeId=lambda: runtime_id,
                ),
            )

        wrong_obj = terminal((42, 2002, 4, 26))
        active_obj = terminal((42, 2002, 4, 6))
        plugin = GlobalPlugin()
        self._focusPlugin(plugin, active_obj)
        plugin._gate.manual_enabled = True
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "legacy", "session", "editor@example-host", client)
        wrong_id, active_id = plugin._identity(wrong_obj), plugin._identity(active_obj)
        plugin._instanceManager.bind(wrong_id, instance.identifier)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._rememberedTerminalBindings.add(wrong_id)

        self.focus = active_obj
        plugin._handleManagedEvent(instance.identifier, {"type": "characterMoved", "payload": {
            "mode": "normal", "lineText": "hello",
            "cursor": {"line": 1, "byteColumn": 1},
        }})
        self.assertEqual(
            instance.identifier,
            plugin._instanceManager.selected_for(wrong_id).identifier,
        )
        self.assertIsNone(plugin._instanceManager.selected_for(active_id))
        self.assertIn(wrong_id, plugin._rememberedTerminalBindings)
        self.assertNotIn(active_id, plugin._rememberedTerminalBindings)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertEqual([], client.controls)
        self.assertFalse(any("move" in message.lower() for message in self.messages))
        plugin.terminate()

    def test_focus_switch_reactivates_only_opted_in_terminal_tabs(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        def terminal(runtime_id):
            return types.SimpleNamespace(
                processID=1001, windowHandle=2001, role=3, parent=None,
                appModule=types.SimpleNamespace(appName="windowsterminal"),
                UIAElement=types.SimpleNamespace(
                    cachedClassName="TermControl", getRuntimeId=lambda: runtime_id,
                ),
            )

        first_obj = terminal((42, 2001, 4, 6))
        second_obj = terminal((42, 2001, 4, 53))
        unbound_obj = terminal((42, 2001, 4, 99))
        plugin = GlobalPlugin()
        first_id, second_id = plugin._identity(first_obj), plugin._identity(second_obj)
        first_client, second_client = Client(), Client()
        first = add_remote_instance(plugin._instanceManager, "one", "1", "First", first_client)
        second = add_remote_instance(plugin._instanceManager, "two", "2", "Second", second_client)
        plugin._instanceManager.bind(first_id, first.identifier)
        plugin._instanceManager.bind(second_id, second.identifier)
        plugin._rememberedTerminalBindings.update((first_id, second_id))
        plugin._authenticatedInstances.update((first.identifier, second.identifier))
        plugin._gate.focused = plugin._gate.bound_terminal = first_id
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._client = first_client
        adapter = self._terminalAdapter()
        self.focus = second_obj
        native_focus_announcements = []
        adapter.event_gainFocus(second_obj, lambda: native_focus_announcements.append("second"))
        self.assertIsNone(plugin._gate.bound_terminal)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertEqual("requestFocusContext", second_client.controls[0][0])
        second_request = second_client.controls[0][1]["requestId"]
        plugin._handleManagedEvent(second.identifier, {"type": "focusContext", "payload": {
            "_focusRequestId": second_request, "bufferName": "/work/second.lua",
            "mode": "insert",
        }})
        self.assertEqual(second_id, plugin._gate.bound_terminal)
        self.assertTrue(plugin._gate.suppression_active)
        self.assertIn("file second.lua, insert mode, on Second", self.spoken)
        self.focus = first_obj
        adapter.event_gainFocus(first_obj, lambda: native_focus_announcements.append("first"))
        self.assertIsNone(plugin._gate.bound_terminal)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertEqual("requestFocusContext", first_client.controls[0][0])
        first_request = first_client.controls[0][1]["requestId"]
        # The late reply from the no-longer-focused second tab is discarded.
        sounds_before_stale_reply = len(self.soundFeeds)
        plugin._handleManagedEvent(second.identifier, {"type": "focusContext", "payload": {
            "_focusRequestId": second_request, "bufferName": "/work/stale.lua",
            "mode": "normal",
        }})
        self.assertNotIn("stale.lua, normal mode", self.spoken)
        self.assertEqual(sounds_before_stale_reply, len(self.soundFeeds))
        plugin._handleManagedEvent(first.identifier, {"type": "focusContext", "payload": {
            "_focusRequestId": first_request, "bufferName": "/work/first.lua",
            "mode": "normal",
        }})
        self.assertEqual(first_id, plugin._gate.bound_terminal)
        self.assertTrue(plugin._gate.suppression_active)
        previous_controls = (list(first_client.controls), list(second_client.controls))
        self.focus = unbound_obj
        adapter.event_gainFocus(unbound_obj, lambda: native_focus_announcements.append("unbound"))
        self.assertEqual(previous_controls, (first_client.controls, second_client.controls))
        self.assertEqual(["second", "first", "unbound"], native_focus_announcements)
        self.assertFalse(plugin._gate.suppression_active)
        plugin.terminate()

    def test_return_from_another_application_requests_context_for_same_wt_control(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "one", "1", "First", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._rememberedTerminalBindings.add(identity)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._activeInstanceId = instance.identifier
        plugin._client = client

        adapter = self._terminalAdapter()
        adapter.event_appModule_loseFocus()
        self.assertIsNone(plugin._gate.focused)
        self.assertFalse(plugin._gate.suppression_active)
        adapter.event_gainFocus(self.focus, lambda: None)

        self.assertEqual("requestFocusContext", client.controls[-1][0])
        self.assertFalse(plugin._gate.suppression_active)
        request_id = client.controls[-1][1]["requestId"]
        plugin._handleManagedEvent(instance.identifier, {"type": "focusContext", "payload": {
            "_focusRequestId": request_id, "bufferName": "/work/returned.lua",
            "mode": "normal",
        }})
        self.assertTrue(plugin._gate.suppression_active)
        self.assertIn("file returned.lua, normal mode, on First", self.spoken)
        plugin.terminate()

    def test_focus_announcement_choices_keep_mode_sounds_independent(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        payload = {
            "bufferName": "/work/example.lua", "mode": "insert",
            "lineText": "\tprint('Grüße 👋')", "cursor": {"line": 7, "byteColumn": 1},
            "_connectionLabel": "Example",
        }
        cases = (
            (0, None, None),
            (1, "\tprint('Grüße 👋')", "\tprint('Grüße 👋')"),
            (
                2,
                "file example.lua, insert mode, on Example",
                "file example.lua, insert mode, on Example",
            ),
        )
        for setting, expected_speech, expected_braille in cases:
            with self.subTest(focusAnnouncement=setting):
                self._updateSettings(plugin, {"focusAnnouncement": setting})
                plugin._planner.reset()
                self.spoken.clear()
                self.brailleMessages.clear()
                self.soundFeeds.clear()

                plugin._handleEvent({"type": "focusContext", "payload": payload})

                self.assertEqual(
                    [] if expected_speech is None else [expected_speech], self.spoken,
                )
                self.assertEqual(
                    [] if expected_braille is None else [expected_braille], self.brailleMessages,
                )
                self.assertEqual(1, len(self.soundFeeds))

        self._updateSettings(plugin, {"focusAnnouncement": 0, "feedback": {"mode": 1}})
        self.spoken.clear()
        self.soundFeeds.clear()
        plugin._handleEvent({"type": "focusContext", "payload": {**payload, "mode": "normal"}})
        self.assertEqual([], self.spoken)
        self.assertEqual([], self.soundFeeds)
        plugin.terminate()

    def test_in_place_buffer_switch_uses_focus_setting_and_connection_label(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): return True

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "one", "1", "Example", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._activeInstanceId = instance.identifier
        plugin._client = client
        plugin._handleManagedEvent(instance.identifier, {
            "type": "fullState", "payload": {
                "bufferId": 1, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/one.lua", "mode": "normal",
                "lineText": "first line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })

        self.spoken.clear()
        self.brailleMessages.clear()
        self._updateSettings(plugin, {"focusAnnouncement": 0})
        plugin._handleManagedEvent(instance.identifier, {
            "type": "contextChanged", "payload": {
                "bufferId": 2, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/two.lua", "mode": "normal",
                "lineText": "second line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        self.assertEqual([], self.spoken)
        self.assertEqual([], self.brailleMessages)

        self._updateSettings(plugin, {"focusAnnouncement": 1})
        plugin._handleManagedEvent(instance.identifier, {
            "type": "textChanged", "payload": {
                "bufferId": 3, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/three.lua", "mode": "normal", "modeRaw": "n",
                "lineText": "third line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        plugin._handleManagedEvent(instance.identifier, {
            "type": "modeChanged", "payload": {
                "bufferId": 3, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/three.lua", "mode": "normal", "modeRaw": "n",
                "lineText": "third line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        plugin._handleManagedEvent(instance.identifier, {
            "type": "contextChanged", "payload": {
                "bufferId": 3, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/three.lua", "mode": "normal",
                "lineText": "third line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        plugin._handleManagedEvent(instance.identifier, {
            "type": "contextChanged", "payload": {
                "bufferId": 3, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/three.lua", "mode": "normal",
                "lineText": "third line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        plugin._handleManagedEvent(instance.identifier, {
            "type": "cursorMoved", "payload": {
                "bufferId": 3, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/three.lua", "mode": "normal",
                "lineText": "third line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        self.assertEqual(["third line"], self.spoken)
        self.assertEqual(["third line"], self.brailleMessages)

        self.spoken.clear()
        self.brailleMessages.clear()
        self._updateSettings(plugin, {"focusAnnouncement": 2})
        plugin._handleManagedEvent(instance.identifier, {
            "type": "contextChanged", "payload": {
                "bufferId": 4, "windowId": 10, "tabpageId": 20,
                "bufferName": "/work/four.lua", "mode": "normal",
                "lineText": "fourth line", "cursor": {"line": 1, "byteColumn": 0},
            },
        })
        self.assertEqual(["file four.lua, normal mode, on Example"], self.spoken)
        self.assertEqual(self.spoken, self.brailleMessages)
        plugin.terminate()

    def test_context_choice_coalesces_window_switch_mode_and_target(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"focusAnnouncement": 2})
        text_window = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "windowIndex": 1, "windowCount": 2,
            "bufferName": "/work/T", "buftype": "", "modified": True,
            "lineText": "Text", "cursor": {"line": 1, "byteColumn": 0},
            "_connectionLabel": "Example",
        }
        terminal_window = {
            "bufferId": 2, "windowId": 11, "tabpageId": 20,
            "windowIndex": 2, "windowCount": 2,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "prompt", "cursor": {"line": 1, "byteColumn": 0},
            "_connectionLabel": "Example",
        }
        plugin._handleEvent({"type": "fullState", "payload": {
            **text_window, "mode": "normal", "modeRaw": "n",
        }})
        self.spoken.clear()
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **terminal_window, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "contextChanged", "payload": {
            **terminal_window, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **text_window, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleEvent({"type": "contextChanged", "payload": {
            **text_window, "mode": "normal", "modeRaw": "n",
        }})

        self.assertEqual([
            "window 2 of 2, terminal-normal mode, on Example",
            "window 1 of 2, file T, modified, normal mode, on Example",
        ], self.spoken)
        plugin.terminate()

    def test_buffer_command_keeps_one_sound_and_suppresses_return_mode_speech(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): return True

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "one", "1", "Example", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._activeInstanceId = instance.identifier
        plugin._client = client
        self._updateSettings(plugin, {"focusAnnouncement": 0})
        played: list[str] = []
        plugin._editorSounds.play = lambda cue: played.append(cue) or True
        source = {
            "bufferId": 2, "windowId": 10, "tabpageId": 20,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "shell prompt", "cursor": {"line": 1, "byteColumn": 0},
        }
        target = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "bufferName": "/work/target.txt", "buftype": "",
            "lineText": "target line", "cursor": {"line": 1, "byteColumn": 0},
        }
        plugin._handleManagedEvent(instance.identifier, {"type": "fullState", "payload": {
            **source, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        self.spoken.clear()
        self.brailleMessages.clear()
        played.clear()
        plugin._handleManagedEvent(instance.identifier, {"type": "commandLineChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
            "commandLine": "", "commandLineType": ":", "commandLinePosition": 0,
        }})
        plugin._handleManagedEvent(instance.identifier, {"type": "modeChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
        }})
        self.assertIn("command-line mode", self.spoken)
        plugin._handleManagedEvent(instance.identifier, {"type": "commandLineChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
            "commandLine": "bp", "commandLineType": ":", "commandLinePosition": 2,
        }})
        self.spoken.clear()
        self.brailleMessages.clear()
        plugin._handleManagedEvent(instance.identifier, {"type": "modeChanged", "payload": {
            **source, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleManagedEvent(instance.identifier, {"type": "modeChanged", "payload": {
            **target, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleManagedEvent(instance.identifier, {"type": "textChanged", "payload": {
            **target, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleManagedEvent(instance.identifier, {"type": "contextChanged", "payload": {
            **target, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleManagedEvent(instance.identifier, {"type": "cursorMoved", "payload": {
            **target, "mode": "normal", "modeRaw": "n",
        }})

        self.assertEqual([], self.spoken)
        self.assertEqual([], self.brailleMessages)
        self.assertEqual(["normalMode"], played)
        plugin.terminate()

    def test_terminal_entry_obeys_focus_choice_then_reads_line_on_direct_input(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"focusAnnouncement": 0})
        played: list[str] = []
        plugin._editorSounds.play = lambda cue: played.append(cue) or True
        source = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "bufferName": "/work/source.txt", "buftype": "",
            "lineText": "source", "cursor": {"line": 1, "byteColumn": 0},
        }
        target_blank = {
            "bufferId": 2, "windowId": 10, "tabpageId": 20,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }
        target_ready = {
            **target_blank, "lineText": "shell prompt", "changedtick": 4,
            "cursor": {"line": 1, "byteColumn": 12},
        }
        target_final = {
            **target_blank, "lineText": "ready prompt", "changedtick": 5,
            "cursor": {"line": 2, "byteColumn": 12},
        }
        plugin._handleEvent({"type": "fullState", "payload": {
            **source, "mode": "normal", "modeRaw": "n",
        }})
        self.spoken.clear()
        played.clear()
        plugin._handleEvent({"type": "commandLineChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
            "commandLine": "terminal", "commandLineType": ":", "commandLinePosition": 8,
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
        }})
        self.spoken.clear()
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **source, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "contextChanged", "payload": {
            **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "cursorMoved", "payload": {
            **target_blank, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            **target_ready, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "cursorMoved", "payload": {
            **target_ready, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            **target_final, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "cursorMoved", "payload": {
            **target_final, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        self.assertEqual([], self.spoken)
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **target_final, "mode": "terminal", "modeRaw": "t",
        }})

        self.assertEqual(["ready prompt"], self.spoken)
        self.assertEqual(["normalMode", "insertMode"], played)
        self.assertTrue(plugin._gate.terminal_passthrough)
        plugin.terminate()

    def test_terminal_context_setting_suppresses_late_initial_character(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"focusAnnouncement": 2})
        source = {
            "bufferId": 1, "windowId": 10, "tabpageId": 20,
            "bufferName": "/work/source.txt", "buftype": "",
            "lineText": "source", "cursor": {"line": 1, "byteColumn": 0},
        }
        terminal = {
            "bufferId": 2, "windowId": 10, "tabpageId": 20,
            "bufferName": "term://shell", "buftype": "terminal",
            "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }
        plugin._handleEvent({"type": "fullState", "payload": {
            **source, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleEvent({"type": "commandLineChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
            "commandLine": "terminal", "commandLineType": ":",
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **source, "mode": "commandLine", "modeRaw": "c",
        }})
        self.spoken.clear()
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **source, "mode": "normal", "modeRaw": "n",
        }})
        plugin._handleEvent({"type": "contextChanged", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
            "_connectionLabel": "Example",
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
            "lineText": "Terminal heading", "changedtick": 4,
            "cursor": {"line": 1, "byteColumn": 8},
        }})
        plugin._handleEvent({"type": "cursorMoved", "payload": {
            **terminal, "mode": "terminalNormal", "modeRaw": "nt",
            "lineText": "Terminal heading", "changedtick": 4,
            "cursor": {"line": 1, "byteColumn": 8},
        }})

        self.assertEqual(
            ["terminal-normal mode, on Example"], self.spoken,
        )
        plugin.terminate()

    def test_events_remain_silent_while_remembered_control_awaits_focus_context(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "one", "1", "First", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._rememberedTerminalBindings.add(identity)
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._gate.manual_enabled = True
        plugin._gate.focused = None

        self._terminalAdapter().event_gainFocus(self.focus, lambda: None)
        plugin._handleManagedEvent(instance.identifier, {"type": "lineChanged", "payload": {
            "mode": "normal", "lineText": "must remain silent",
            "cursor": {"line": 1, "byteColumn": 0},
        }})

        self.assertFalse(plugin._gate.suppression_active)
        self.assertNotIn("must remain silent", self.spoken)
        self.assertIn('"reason": "foregroundUnconfirmed"', plugin._diagnostics.report())
        plugin.terminate()

    def test_focus_switch_between_separate_wt_windows_restores_each_binding(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        def terminal(pid, handle, runtime_id):
            return types.SimpleNamespace(
                processID=pid, windowHandle=handle, role=3, parent=None,
                appModule=types.SimpleNamespace(appName="windowsterminal"),
                UIAElement=types.SimpleNamespace(
                    cachedClassName="TermControl", getRuntimeId=lambda: runtime_id,
                ),
            )

        first_obj = terminal(1001, 2001, (42, 2001, 4, 6))
        second_obj = terminal(1002, 2002, (42, 2002, 4, 6))
        plugin = GlobalPlugin()
        first_id, second_id = plugin._identity(first_obj), plugin._identity(second_obj)
        first_client, second_client = Client(), Client()
        first = add_remote_instance(plugin._instanceManager, "one", "1", "First", first_client)
        second = add_remote_instance(plugin._instanceManager, "two", "2", "Second", second_client)
        plugin._instanceManager.bind(first_id, first.identifier)
        plugin._instanceManager.bind(second_id, second.identifier)
        plugin._rememberedTerminalBindings.update((first_id, second_id))
        plugin._authenticatedInstances.update((first.identifier, second.identifier))
        plugin._gate.manual_enabled = True

        adapters = {
            first_obj.processID: self._terminalAdapter(),
            second_obj.processID: self._terminalAdapter(),
        }

        for obj, identity, instance, client in (
            (second_obj, second_id, second, second_client),
            (first_obj, first_id, first, first_client),
        ):
            self.focus = obj
            adapters[obj.processID].event_gainFocus(obj, lambda: None)
            self.assertFalse(plugin._gate.suppression_active)
            request_id = client.controls[-1][1]["requestId"]
            plugin._handleManagedEvent(instance.identifier, {
                "type": "focusContext", "payload": {
                    "_focusRequestId": request_id, "bufferName": "/work/file.lua",
                    "mode": "normal",
                },
            })
            self.assertEqual(identity, plugin._gate.bound_terminal)
            self.assertTrue(plugin._gate.suppression_active)

        self.assertEqual(2, len(plugin._instanceManager.list()))
        plugin.terminate()

    def test_parallel_tabs_restore_independent_speech_and_typing_runtime(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(self): self.controls = []
            def start(self): pass
            def stop(self): pass
            def send_control(self, kind, payload): self.controls.append((kind, payload)); return True

        def terminal(runtime_id):
            return types.SimpleNamespace(
                processID=1001, windowHandle=2001, role=3, parent=None,
                appModule=types.SimpleNamespace(appName="windowsterminal"),
                UIAElement=types.SimpleNamespace(
                    cachedClassName="TermControl", getRuntimeId=lambda: runtime_id,
                ),
            )

        first_obj = terminal((42, 2001, 4, 6))
        second_obj = terminal((42, 2001, 4, 53))
        plugin = GlobalPlugin()
        self._focusPlugin(plugin, first_obj)
        plugin._gate.manual_enabled = True
        first_client, second_client = Client(), Client()
        first = add_remote_instance(plugin._instanceManager, "same", "one", "First", first_client)
        second = add_remote_instance(plugin._instanceManager, "same", "two", "Second", second_client)
        first_id, second_id = plugin._identity(first_obj), plugin._identity(second_obj)
        plugin._instanceManager.bind(first_id, first.identifier)
        plugin._instanceManager.bind(second_id, second.identifier)

        self.focus = first_obj
        self._focusPlugin(plugin, first_obj)
        plugin._handleManagedEvent(first.identifier, {"type": "fullState", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "first",
            "cursor": {"line": 1, "byteColumn": 5},
        }})
        first_planner = plugin._planner
        plugin._typedWord = ["firstPending"]

        self.focus = second_obj
        self._focusPlugin(plugin, second_obj)
        plugin._handleManagedEvent(second.identifier, {"type": "fullState", "payload": {
            "mode": "normal", "bufferId": 1, "lineText": "second",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        second_planner = plugin._planner
        self.assertIsNot(first_planner, second_planner)
        plugin._typedWord = ["secondPending"]
        plugin._rememberedTerminalBindings.update((first_id, second_id))
        adapter = self._terminalAdapter()

        self.focus = first_obj
        adapter.event_gainFocus(first_obj, lambda: None)
        first_request = first_client.controls[-1][1]["requestId"]
        plugin._handleManagedEvent(first.identifier, {"type": "focusContext", "payload": {
            "_focusRequestId": first_request, "bufferName": "/work/first.lua",
            "mode": "insert",
        }})
        plugin._handleManagedEvent(first.identifier, {"type": "characterMoved", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "first",
            "cursor": {"line": 1, "byteColumn": 4},
        }})
        self.assertIs(first_planner, plugin._planner)
        self.assertEqual(["firstPending"], plugin._typedWord)

        self.focus = second_obj
        adapter.event_gainFocus(second_obj, lambda: None)
        second_request = second_client.controls[-1][1]["requestId"]
        plugin._handleManagedEvent(second.identifier, {"type": "focusContext", "payload": {
            "_focusRequestId": second_request, "bufferName": "/work/second.lua",
            "mode": "normal",
        }})
        plugin._handleManagedEvent(second.identifier, {"type": "characterMoved", "payload": {
            "mode": "normal", "bufferId": 1, "lineText": "second",
            "cursor": {"line": 1, "byteColumn": 1},
        }})
        self.assertIs(second_planner, plugin._planner)
        self.assertEqual(["secondPending"], plugin._typedWord)
        plugin.terminate()

    def test_declined_or_stale_tab_binding_never_auto_reconnects(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.gate import TerminalIdentity

        class Client:
            def start(self): pass
            def stop(self): pass
            def send_control(self, *_args): return True

        def terminal(runtime_id):
            return types.SimpleNamespace(
                processID=1001, windowHandle=2001, role=3, parent=None,
                appModule=types.SimpleNamespace(appName="windowsterminal"),
                UIAElement=types.SimpleNamespace(
                    cachedClassName="TermControl", getRuntimeId=lambda: runtime_id,
                ),
            )

        first_obj = terminal((42, 2001, 4, 6))
        second_obj = terminal((42, 2001, 4, 53))
        plugin = GlobalPlugin()
        first_id = plugin._identity(first_obj)
        instance = add_remote_instance(plugin._instanceManager, "one", "1", "First", Client())
        plugin._instanceManager.bind(first_id, instance.identifier)
        self.messageBoxAnswers.append(0)
        plugin._offerTemporaryTerminalBinding(first_id, instance.identifier)
        self.assertNotIn(first_id, plugin._rememberedTerminalBindings)
        adapter = self._terminalAdapter()
        plugin._gate.focused = first_id
        adapter.event_gainFocus(second_obj, lambda: None)
        # Declining persistence means that focus alone never reactivates the
        # binding.  Keep the dormant in-memory mapping, however: destroying it
        # on a transient UIA focus identity change loses suppression and makes
        # subsequent events from the still-running client unselectable.
        self.assertEqual(instance.identifier, plugin._instanceManager.selected_for(first_id).identifier)

        stale_id = plugin._identity(second_obj)
        plugin._rememberedTerminalBindings.add(stale_id)
        plugin._gate.focused = TerminalIdentity(1, 2)
        adapter.event_gainFocus(second_obj, lambda: None)
        self.assertNotIn(stale_id, plugin._rememberedTerminalBindings)
        plugin.terminate()

    def test_explicit_session_replacement_starts_new_before_stopping_old_client(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile
        from globalPlugins.NeovimAccessLink.core.ssh_sessions import RemoteSession

        order = []
        class Client:
            def __init__(inner_self, *_args, **_kwargs): inner_self.instance = "new"
            def start(inner_self): order.append(f"start-{inner_self.instance}")
            def stop(inner_self): order.append(f"stop-{inner_self.instance}")
            def send_control(inner_self, *_args): return True

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile_value = {
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        }
        self._updateSettings(plugin, {"connections": [profile_value]})
        identity = plugin._identity(self.focus)
        old = Client()
        old.instance = "old"
        old_instance = add_remote_instance(plugin._instanceManager, "work", "1", "old", old)
        plugin._instanceManager.bind(identity, old_instance.identifier)
        plugin._client = old
        plugin._stopManagedClientAsync = lambda _instance_id, client: client.stop()
        plugin._sessionDiscoveryGeneration = 9
        with mock.patch.object(addon_module, "SshStdioClient", Client):
            plugin._finishSessionDiscovery(
                9, parse_profile(profile_value), identity,
                [RemoteSession("2", "new", "/new")], None, True,
            )
        self.assertEqual(["start-old", "start-new", "stop-old"], order)
        self.assertEqual(["2"], [item.session_id for item in plugin._instanceManager.list()])
        plugin.terminate()

    def test_remote_session_discovery_reports_empty_and_failure_without_starting(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profile

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        profile = parse_profile({
            "id": "work", "name": "Work", "host": "host", "user": "remote",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        })
        plugin._sessionDiscoveryGeneration = 2
        plugin._startManagedInstance = lambda *_args, **_kwargs: self.fail("must not start")
        plugin._finishSessionDiscovery(2, profile, plugin._identity(self.focus), [], None)
        self.assertIn("No active Neovim session", self.messages[-1])
        plugin._finishSessionDiscovery(2, profile, plugin._identity(self.focus), [], RuntimeError("offline"))
        self.assertIn("Could not list", self.messages[-1])
        plugin.terminate()

    def test_parallel_ipv4_and_ipv6_hosts_keep_terminal_events_separate(self) -> None:
        import globalPlugins.NeovimAccessLink as addon_module
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        clients = []
        class FakeStdioClient:
            def __init__(inner_self, target, on_event, _on_state, **kwargs):
                inner_self.target = target
                inner_self.on_event = on_event
                inner_self.kwargs = kwargs
                inner_self.stops = 0
                clients.append(inner_self)
            def start(inner_self): pass
            def stop(inner_self): inner_self.stops += 1
            def send_control(inner_self, *_args): return True

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"connections": [
            {"id": "v4", "name": "IPv4 host", "host": "127.0.0.1", "user": "editor",
             "port": 22, "identityFile": "", "authentication": "openSsh"},
            {"id": "v6", "name": "IPv6 host", "host": "::1", "user": "editor",
             "port": 22, "identityFile": "", "authentication": "openSsh"},
        ]})
        with mock.patch.object(addon_module, "SshStdioClient", FakeStdioClient):
            plugin._startManagedInstance("v4", "101")
            self.focus.windowHandle = 201
            self._focusPlugin(plugin)
            plugin._startManagedInstance("v6", "202")
        self.assertEqual(["editor@127.0.0.1", "editor@::1"], [client.target for client in clients])

        self.spoken.clear()
        clients[0].on_event({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "ipv4 hidden", "cursor": {"line": 1, "byteColumn": 0},
        }})
        clients[1].on_event({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "ipv6 visible", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertNotIn("ipv4 hidden", self.spoken)
        self.assertIn("ipv6 visible", self.spoken)

        self.focus.windowHandle = 200
        self._focusPlugin(plugin)
        self.spoken.clear()
        clients[0].on_event({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "ipv4 visible", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertIn("ipv4 visible", self.spoken)
        plugin.terminate()
        self.assertEqual([1, 1], [client.stops for client in clients])

    def test_tools_menu_exposes_component_install_and_removal_and_settings_remain_native(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self.assertFalse(any("Neovim" in label for label in self.preferencesMenuLabels))
        addon_tools = [label for label in self.toolsMenuLabels if label.startswith(
            buildVars.addon_info["summary"] + ":"
        )]
        self.assertEqual(2, len(addon_tools))
        self.assertTrue(any("Install or update components" in label for label in addon_tools))
        self.assertTrue(any("Remove components" in label for label in addon_tools))
        self.assertFalse(any("SSH target" in label for label in self.menuLabels))
        self.assertEqual(1, len(self.settingsCategoryClasses))
        panel = self.settingsCategoryClasses[0]()
        panel.makeSettings(object())
        self.assertEqual(("General", "Feedback", "Connections"), panel.settingsTabLabels)
        self.assertEqual([
            "Global action feedback", "Session focus", "Individual actions", "Saved SSH connections",
        ], self.staticBoxLabels)
        self.assertEqual(9, len(panel.feedbackControls))
        self.assertEqual(2, panel.focusAnnouncement.GetSelection())
        panel.focusAnnouncement.SetSelection(1)
        panel.feedbackControls["delete"].SetSelection(2)
        panel.onSave()
        self.assertEqual(1, self._settingsSnapshot(plugin)["focusAnnouncement"])
        self.assertEqual(1, __import__("config").conf["NeovimAccessLink"]["focusAnnouncement"])
        self.assertEqual(2, self._settingsSnapshot(plugin)["feedback"]["delete"])
        self.assertEqual(2, __import__("config").conf["NeovimAccessLink"]["feedback"]["delete"])
        self.assertIn("NeovimAccessLink", __import__("config").conf.spec)
        self.assertFalse((self.config_path / "NeovimAccessLink.json").exists())
        plugin.terminate()

    def test_ui_keeps_tools_when_settings_registration_fails_and_cleanup_is_idempotent(self) -> None:
        from gui.settingsDialogs import NVDASettingsDialog
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class RejectingCategories(list):
            def append(self, _value):
                raise RuntimeError("settings unavailable")

        original_categories = NVDASettingsDialog.categoryClasses
        NVDASettingsDialog.categoryClasses = RejectingCategories()
        try:
            plugin = GlobalPlugin()
            self.assertEqual(2, len(plugin._nvdaUi._menuItems))
            self.assertIsNone(plugin._nvdaUi._settingsPanelClass)
            self.assertIn("settingsPanelUnavailable", plugin._diagnostics.report())

            plugin._nvdaUi.unregister()
            plugin._nvdaUi.unregister()

            self.assertEqual([], plugin._nvdaUi._menuItems)
            plugin.terminate()
        finally:
            NVDASettingsDialog.categoryClasses = original_categories

    def test_german_tools_menu_is_distinct_and_both_handlers_open_their_forms(self) -> None:
        mo_path = self.extract_path / "locale" / "de" / "LC_MESSAGES" / "nvda.mo"
        with mo_path.open("rb") as stream:
            translations = gettext.GNUTranslations(stream)
        builtins._ = translations.gettext
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        product = buildVars.addon_info["summary"]
        self.assertEqual([
            product + ": Komponenten installieren oder aktualisieren...",
            product + ": Komponenten entfernen...",
        ], self.toolsMenuLabels)
        self.assertEqual(2, len(self.toolsMenuHandlers))
        for handler in self.toolsMenuHandlers:
            handler(None)
        self.assertEqual([
            "Neovim-Komponenten installieren oder aktualisieren",
            "Neovim-Komponenten entfernen",
        ], [dialog.title for dialog in self.dialogs])
        self.assertEqual([
            "Wählen Sie ein oder mehrere Ziele aus. Administratorrechte sind nicht erforderlich.",
            "Zu aktualisierende Verbindungen:",
            "Schließen Sie Neovim auf den ausgewählten Zielen und wählen Sie dann aus, wo die "
            "Komponenten entfernt werden sollen. Andere Neovim-Plugins und Konfigurationen "
            "bleiben erhalten.",
            "Verbindungen, von denen Komponenten entfernt werden:",
        ], self.staticTexts)
        self.assertEqual(
            ["Alle Verbindungen auswählen", "Alle Verbindungen auswählen"],
            [control.label for control in self.checkBoxControls],
        )
        self.assertEqual(
            ["Zu aktualisierende Verbindungen", "Verbindungen, von denen Komponenten entfernt werden"],
            [control.name for control in self.checkListBoxes],
        )
        plugin.terminate()
        self.assertEqual([], self.settingsCategoryClasses)
        self.assertEqual([], plugin._nvdaUi._menuItems)

    def test_nvda_profile_switch_reloads_native_addon_settings(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import config

        plugin = GlobalPlugin()
        inventories = []
        plugin._beginClaimInventory = lambda: inventories.append(True)
        config.conf["NeovimAccessLink"] = {
            "focusAnnouncement": 0,
            "connections": json.dumps([{
                "id": "quiet", "name": "Quiet server", "host": "host", "user": "user",
                "port": 22, "identityFile": "", "authentication": "openSsh",
            }]),
            "feedback": {
                "global": 1, "mode": 0, "delete": 2, "replace": 3,
                "lineBoundary": 2, "fileBoundary": 1,
                "lineCrossed": 0, "matchingError": 3,
            },
        }
        config.post_configProfileSwitch.notify()
        self.assertEqual(0, self._settingsSnapshot(plugin)["focusAnnouncement"])
        self.assertEqual(0, self._settingsSnapshot(plugin)["feedback"]["mode"])
        self.assertEqual(0, plugin._feedbackMode("mode"))
        self.assertEqual("user@host", plugin._connectionProfileById("quiet").ssh_target)
        self.assertEqual([], inventories)

        plugin._gate.manual_enabled = True
        config.conf["NeovimAccessLink"]["connections"] = "[]"
        config.post_configProfileSwitch.notify()
        self.assertEqual([True], inventories)
        self.assertEqual(1, len(config.post_configProfileSwitch.handlers))
        plugin.terminate()
        self.assertEqual(0, len(config.post_configProfileSwitch.handlers))

    def test_clipboard_actions_are_correlated_to_the_bound_foreground_session(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        class Client:
            def __init__(inner_self): inner_self.controls = []
            def start(inner_self): pass
            def stop(inner_self): pass
            def send_control(inner_self, kind, payload):
                inner_self.controls.append((kind, payload))
                return True

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        client = Client()
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "This computer", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._activeInstanceId = instance.identifier
        plugin._client = client
        plugin._transportCapabilities = frozenset({"clipboardTransfer"})
        base = {
            "bufferId": 1, "windowId": 1000, "tabpageId": 1, "changedtick": 9,
            "mode": "visualCharacter", "modeRaw": "v", "modeBlocking": False,
            "buftype": "", "modifiable": True, "readonly": False,
            "fileManager": None, "lineText": "selected",
            "cursor": {"line": 1, "byteColumn": 7},
        }
        plugin._currentState = base

        plugin.action_copyNeovimSelection(None)
        kind, request = client.controls[-1]
        self.assertEqual("copyTextRequest", kind)
        self.assertEqual("visualSelection", request["source"])
        plugin._handleManagedEvent(instance.identifier, {
            "type": "copyTextResult", "payload": {
                **base, "requestId": request["requestId"], "ok": True,
                "resultCode": "copied", "clipboardText": "private selection",
                "copiedCharacterCount": 17, "copiedLineCount": 1,
            },
        })
        self.assertEqual("private selection", self.clipboard)
        self.assertIn("Copied from Neovim", self.spoken)
        self.assertNotIn("private selection", plugin._diagnostics.report())

        self.clipboard = "Windows text 😀\nsecond line"
        plugin._currentState = {**base, "mode": "normal", "modeRaw": "n"}
        plugin.action_pasteWindowsClipboard(None)
        kind, request = client.controls[-1]
        self.assertEqual("pasteTextRequest", kind)
        self.assertEqual(self.clipboard, request["text"])
        plugin._handleManagedEvent(instance.identifier, {
            "type": "pasteTextResult", "payload": {
                **plugin._currentState, "requestId": request["requestId"], "ok": True,
                "resultCode": "pasted", "insertedBytes": 29, "insertedLines": 2,
            },
        })
        self.assertIn("Pasted into Neovim", self.spoken)
        self.assertNotIn("Windows text", plugin._diagnostics.report())

        self.clipboard = "new unnamed register\r\n"
        plugin.action_setNeovimRegisterFromWindowsClipboard(None)
        kind, request = client.controls[-1]
        self.assertEqual("setRegisterRequest", kind)
        self.assertEqual(self.clipboard, request["text"])
        plugin._handleManagedEvent(instance.identifier, {
            "type": "setRegisterResult", "payload": {
                **plugin._currentState, "requestId": request["requestId"], "ok": True,
                "resultCode": "registerStored", "registerType": "V",
                "storedBytes": 21, "storedLineCount": 1,
            },
        })
        self.assertTrue(any("unnamed register" in item for item in self.spoken))
        self.assertNotIn("new unnamed register", plugin._diagnostics.report())
        plugin.terminate()

    def test_clipboard_reply_after_focus_loss_is_discarded(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        controls = []
        client = types.SimpleNamespace(
            start=lambda: None, stop=lambda: None,
            send_control=lambda kind, payload: controls.append((kind, payload)) or True,
        )
        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "This computer", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._activeInstanceId = instance.identifier
        plugin._client = client
        plugin._transportCapabilities = frozenset({"clipboardTransfer"})
        plugin._currentState = {
            "bufferId": 1, "windowId": 2, "tabpageId": 3, "changedtick": 4,
            "mode": "normal", "modeRaw": "n", "modeBlocking": False,
            "buftype": "", "modifiable": True, "readonly": False, "fileManager": None,
        }
        plugin.action_copyLastNeovimYank(None)
        request = controls[-1][1]
        self.clipboard = "unchanged"
        self._terminalAdapter().event_appModule_loseFocus()
        plugin._handleManagedEvent(instance.identifier, {
            "type": "copyTextResult", "payload": {
                **plugin._currentState, "requestId": request["requestId"], "ok": True,
                "resultCode": "copied", "clipboardText": "must not escape",
            },
        })
        self.assertEqual("unchanged", self.clipboard)
        self.assertNotIn("must not escape", plugin._diagnostics.report())
        plugin.terminate()

    def test_leave_terminal_input_is_scoped_correlated_and_needs_no_changedtick(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        controls = []
        client = types.SimpleNamespace(
            start=lambda: None, stop=lambda: None,
            send_control=lambda kind, payload: controls.append((kind, payload)) or True,
        )
        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "This computer", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._gate.terminal_passthrough = True
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._activeInstanceId = instance.identifier
        plugin._client = client
        plugin._transportCapabilities = frozenset({"terminalControl"})
        plugin._currentState = {
            "bufferId": 1, "windowId": 2, "tabpageId": 3,
            "mode": "terminal", "modeRaw": "t", "modeBlocking": False,
            "buftype": "terminal",
        }

        plugin.action_leaveDirectTerminalInput(None)
        kind, request = controls[-1]
        self.assertEqual("leaveTerminalInputRequest", kind)
        self.assertNotIn("changedtick", request)
        plugin._handleManagedEvent(instance.identifier, {
            "type": "leaveTerminalInputResult", "payload": {
                **plugin._currentState, "mode": "terminalNormal", "modeRaw": "nt",
                "requestId": request["requestId"], "ok": True, "resultCode": "ok",
            },
        })
        self.assertEqual({}, plugin._pendingTerminalControlRequests)
        self.assertNotIn("requestId", plugin._currentState)

        plugin._currentState = {**plugin._currentState, "mode": "normal", "modeRaw": "n"}
        plugin.action_leaveDirectTerminalInput(None)
        self.assertIn("Neovim is not in direct terminal input", self.messages)
        self.assertEqual(1, len(controls))
        plugin.terminate()

    def test_pending_clipboard_requests_are_bounded(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        for request_id in range(40):
            plugin._rememberClipboardRequest(
                request_id,
                ("instance", identity, "copyTextRequest"),
            )

        self.assertEqual(32, len(plugin._pendingClipboardRequests))
        self.assertNotIn(0, plugin._pendingClipboardRequests)
        self.assertIn(39, plugin._pendingClipboardRequests)
        self.assertIn('"reason": "queueLimit"', plugin._diagnostics.report())
        plugin.terminate()

    def test_paste_result_after_focus_loss_has_no_feedback_in_new_context(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        controls = []
        client = types.SimpleNamespace(
            start=lambda: None, stop=lambda: None,
            send_control=lambda kind, payload: controls.append((kind, payload)) or True,
        )
        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        instance = add_remote_instance(plugin._instanceManager, "local", "1", "This computer", client)
        plugin._instanceManager.bind(identity, instance.identifier)
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._authenticatedInstances.add(instance.identifier)
        plugin._activeInstanceId = instance.identifier
        plugin._client = client
        plugin._transportCapabilities = frozenset({"clipboardTransfer"})
        plugin._currentState = {
            "bufferId": 1, "windowId": 2, "tabpageId": 3, "changedtick": 4,
            "mode": "normal", "modeRaw": "n", "modeBlocking": False,
            "buftype": "", "modifiable": True, "readonly": False, "fileManager": None,
        }
        self.clipboard = "one authorized paste"
        plugin.action_pasteWindowsClipboard(None)
        request = controls[-1][1]
        spoken_before = len(self.spoken)

        self._terminalAdapter().event_appModule_loseFocus()
        plugin._handleManagedEvent(instance.identifier, {
            "type": "pasteTextResult", "payload": {
                **plugin._currentState, "requestId": request["requestId"], "ok": True,
                "resultCode": "pasted", "insertedBytes": 20, "insertedLines": 1,
            },
        })

        self.assertNotIn("Pasted into Neovim", self.spoken[spoken_before:])
        self.assertEqual({}, plugin._pendingClipboardRequests)
        plugin.terminate()

    def test_nvda_profile_switch_does_not_interrupt_an_active_connection(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import config

        class Client:
            def __init__(inner_self): inner_self.stops = 0
            def stop(inner_self): inner_self.stops += 1

        plugin = GlobalPlugin()
        client = Client()
        plugin._client = client
        plugin._connected = True
        plugin._gate.manual_enabled = True
        config.conf["NeovimAccessLink"]["feedback"]["global"] = 0

        config.post_configProfileSwitch.notify()

        self.assertIs(client, plugin._client)
        self.assertEqual(0, client.stops)
        self.assertTrue(plugin._connected)
        self.assertEqual(0, self._settingsSnapshot(plugin)["feedback"]["global"])
        plugin.terminate()
        self.assertEqual(1, client.stops)

    def test_connection_profile_buttons_add_duplicate_targets_edit_and_remove(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        panel = self.settingsCategoryClasses[0]()
        panel.makeSettings(object())
        queued = [
            {"id": "example-host-one", "name": "Example host one", "host": "example-host", "user": "editor", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "example-host-two", "name": "Example host two", "host": "example-host", "user": "editor", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
        ]
        plugin._nvdaUi._promptConnectionProfile = lambda _existing, _profiles: queued.pop(0)
        panel._onAddConnection(None)
        panel._onAddConnection(None)
        self.assertEqual(["editor@example-host", "editor@example-host"], [
            f"{profile['user']}@{profile['host']}" for profile in panel.connectionProfiles
        ])
        self.assertEqual([
            "Example host one — editor@example-host", "Example host two — editor@example-host",
        ], panel.connectionChoice.items)
        panel.connectionChoice.SetSelection(1)
        plugin._nvdaUi._promptConnectionProfile = lambda existing, _profiles: {
            **existing, "name": "Edited", "port": 2222,
        }
        panel._onEditConnection(None)
        self.assertEqual(("Edited", 2222), (
            panel.connectionProfiles[1]["name"], panel.connectionProfiles[1]["port"],
        ))
        panel._onRemoveConnection(None)
        self.assertEqual(["example-host-one"], [profile["id"] for profile in panel.connectionProfiles])
        panel.connectionChoice.SetSelection(0)
        inventories = []
        plugin._gate.manual_enabled = True
        plugin._beginClaimInventory = lambda: inventories.append(True)
        panel.onSave()
        self.assertNotIn("activeConnection", self._settingsSnapshot(plugin))
        self.assertEqual([True], inventories)
        plugin.terminate()

    def test_connection_profile_form_is_single_transaction_and_uses_plain_authentication_labels(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        shown = []
        plugin._nvdaUi._showConnectionProfileDialog = lambda values: shown.append(dict(values)) or {
            "name": "Work", "host": "host.example", "user": "linux-user", "port": "2222",
            "identityFile": r"C:\keys\work key", "authentication": "openSsh",
        }
        profile = plugin._nvdaUi._promptConnectionProfile(None, [])
        self.assertEqual(("linux-user@host.example", 2222, r"C:\keys\work key"), (
            f"{profile['user']}@{profile['host']}", profile["port"], profile["identityFile"],
        ))
        self.assertEqual([{}], shown)
        choices = plugin._nvdaUi._authenticationChoices()
        self.assertIn("recommended", choices[0])
        self.assertIn("not saved", choices[1])
        self.assertNotIn("openSsh", " ".join(choices))

        plugin._nvdaUi._showConnectionProfileDialog = lambda _values: None
        self.assertIsNone(plugin._nvdaUi._promptConnectionProfile(profile, [profile]))

        attempts = iter((
            {"name": "Bad", "host": "-option", "user": "user", "port": "22",
             "identityFile": "", "authentication": "openSsh"},
            {"name": "Password host", "host": "server", "user": "remote", "port": "22",
             "identityFile": r"C:\unused-key", "authentication": "password"},
        ))
        plugin._nvdaUi._showConnectionProfileDialog = lambda _values: next(attempts)
        password_profile = plugin._nvdaUi._promptConnectionProfile(None, [])
        self.assertEqual("password", password_profile["authentication"])
        self.assertEqual("", password_profile["identityFile"])
        self.assertTrue(any("connection settings are invalid" in message for message in self.messages))
        plugin.terminate()

    def test_local_discovery_is_implicit_and_not_a_default_setting(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_targets import LOCAL_WINDOWS_TCP

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        panel = self.settingsCategoryClasses[0]()
        panel.makeSettings(object())
        panel.onSave()
        self.assertEqual([], panel.connectionProfiles)
        self.assertNotIn("activeConnection", self._settingsSnapshot(plugin))
        self.assertNotIn("activeTargetKind", self._settingsSnapshot(plugin))
        plugin.terminate()

    def test_linux_installation_selects_multiple_saved_profiles_with_accessible_labels(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._updateSettings(plugin, {
            "connections": [
                {"id": "key", "name": "Production", "host": "prod", "user": "alice", "port": 22,
                 "identityFile": r"C:\keys\prod", "authentication": "openSsh"},
                {"id": "pw", "name": "Test server", "host": "test", "user": "bob", "port": 2222,
                 "identityFile": "", "authentication": "password"},
            ],
        })
        self.checkListSelections.append([1, 2])
        self.modalDialogResults.append(sys.modules["wx"].ID_OK)
        selected = plugin._nvdaUi._chooseInstallProfiles()
        self.assertEqual(["key", "pw"], [profile.identifier for profile in selected])
        connection_list = self.checkListBoxes[-1]
        self.assertEqual("Connections to update", connection_list.name)
        self.assertIn("This computer: local Windows Neovim plugin", connection_list.choices[0])
        self.assertIn("Production: alice@prod, port 22, OpenSSH keys or configuration", connection_list.choices[1])
        self.assertIn("Test server: bob@test, port 2222, password prompt", connection_list.choices[2])
        self.assertFalse(any("Nothing is selected" in label for label in self.staticTexts))
        select_all = next(control for control in self.checkBoxControls if control.label == "Select all connections")
        self.assertTrue(select_all.focused)
        self.assertFalse(select_all.IsChecked())

        calls = []
        plugin._nvdaUi._chooseInstallProfiles = lambda: selected
        plugin._nvdaUi._passwordForProfile = (
            lambda profile: "temporary password" if profile.identifier == "pw" else ""
        )
        plugin._nvdaUi._runServerInstalls = lambda *args: calls.append(args)
        class ImmediateThread:
            def __init__(inner_self, target, args, daemon):
                inner_self.target, inner_self.args, inner_self.daemon = target, args, daemon
            def start(inner_self): inner_self.target(*inner_self.args)
        with mock.patch("threading.Thread", ImmediateThread):
            plugin._nvdaUi._onInstallServer(None)
        jobs, package, immediate_results, local_plugin = calls[0]
        self.assertEqual(["key", "pw"], [profile.identifier for profile, _password in jobs])
        self.assertEqual(["", "temporary password"], [password for _profile, password in jobs])
        self.assertTrue(package.endswith("server-user.tar.gz"))
        self.assertTrue(local_plugin.endswith("neovim-plugin"))
        self.assertEqual([], immediate_results)
        self.assertIn("Updating Neovim components on 2 targets", self.messages[-1])
        plugin.terminate()

    def test_linux_installation_select_all_checkbox_checks_every_connection(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._updateSettings(plugin, {"connections": [
            {"id": "one", "name": "One", "host": "one", "user": "alice", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "two", "name": "Two", "host": "two", "user": "bob", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
        ]})
        self.modalDialogResults.append(sys.modules["wx"].ID_OK)
        original_show = sys.modules["wx"].Dialog.ShowModal
        def select_all_then_show(dialog):
            select_all = next(control for control in self.checkBoxControls if control.label == "Select all connections")
            select_all.SetValue(True)
            select_all.handlers[sys.modules["wx"].EVT_CHECKBOX](None)
            return original_show(dialog)
        with mock.patch.object(sys.modules["wx"].Dialog, "ShowModal", select_all_then_show):
            selected = plugin._nvdaUi._chooseInstallProfiles()
        self.assertEqual(["local-windows", "one", "two"], [profile.identifier for profile in selected])
        plugin.terminate()

    def test_linux_installation_manual_checks_synchronize_select_all(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._updateSettings(plugin, {"connections": [
            {"id": "one", "name": "One", "host": "one", "user": "alice", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "two", "name": "Two", "host": "two", "user": "bob", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
        ]})
        self.modalDialogResults.append(sys.modules["wx"].ID_OK)
        synchronized = []
        original_show = sys.modules["wx"].Dialog.ShowModal
        def manually_check_then_show(dialog):
            connection_list = self.checkListBoxes[-1]
            select_all = next(control for control in self.checkBoxControls if control.label == "Select all connections")
            event = types.SimpleNamespace(Skip=lambda: None)
            connection_list.Check(0, True)
            connection_list.handlers[sys.modules["wx"].EVT_CHECKLISTBOX](event)
            synchronized.append(select_all.IsChecked())
            connection_list.Check(1, True)
            connection_list.handlers[sys.modules["wx"].EVT_CHECKLISTBOX](event)
            synchronized.append(select_all.IsChecked())
            connection_list.Check(2, True)
            connection_list.handlers[sys.modules["wx"].EVT_CHECKLISTBOX](event)
            synchronized.append(select_all.IsChecked())
            connection_list.Check(0, False)
            connection_list.handlers[sys.modules["wx"].EVT_CHECKLISTBOX](event)
            synchronized.append(select_all.IsChecked())
            connection_list.Check(0, True)
            return original_show(dialog)
        with mock.patch.object(sys.modules["wx"].Dialog, "ShowModal", manually_check_then_show):
            selected = plugin._nvdaUi._chooseInstallProfiles()
        self.assertEqual([False, False, True, False], synchronized)
        self.assertEqual(["local-windows", "one", "two"], [profile.identifier for profile in selected])
        plugin.terminate()

    def test_linux_installation_requires_an_explicit_selection(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._updateSettings(plugin, {"connections": [{
            "id": "one", "name": "One", "host": "one", "user": "alice", "port": 22,
            "identityFile": "", "authentication": "openSsh",
        }]})
        self.modalDialogResults.extend((sys.modules["wx"].ID_OK, sys.modules["wx"].ID_CANCEL))
        self.assertIsNone(plugin._nvdaUi._chooseInstallProfiles())
        self.assertTrue(self.messageBoxes)
        self.assertIn("Select at least one target", self.messageBoxes[-1][0][0])
        self.assertEqual((), self.checkListBoxes[-1].GetCheckedItems())
        plugin.terminate()

    def test_linux_installation_reports_each_success_failure_and_cancelled_password(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profiles
        from globalPlugins.NeovimAccessLink.core.ssh_install import InstallResult

        plugin = GlobalPlugin()
        profiles = parse_profiles([
            {"id": "ok", "name": "Documentation", "host": "example-host", "user": "editor", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "bad", "name": "Production", "host": "example-host-2", "user": "admin", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "cancel", "name": "Password server", "host": "pw", "user": "tester", "port": 22,
             "identityFile": "", "authentication": "password"},
        ])
        results = [
            (profiles[0], InstallResult(True, "installed")),
            (profiles[1], InstallResult(False, "SSH package upload failed")),
            (profiles[2], InstallResult(False, "SSH password entry cancelled")),
        ]
        summary = plugin._nvdaUi._installResultSummary(results)
        self.assertIn("Successful: 1", summary)
        self.assertIn("Documentation (editor@example-host)", summary)
        self.assertIn("Failed: 2", summary)
        self.assertIn("Production (admin@example-host-2): SSH package upload failed", summary)
        self.assertIn("Password server (tester@pw): SSH password entry cancelled", summary)
        plugin._nvdaUi._finishServerInstalls(results)
        self.assertEqual("Neovim component update results", self.messageDialogs[-1].title)
        self.assertEqual(summary, self.messageDialogs[-1].message)
        self.assertTrue(self.messageDialogs[-1].shown)
        self.assertIn("1 successful, 2 failed", self.messages[-1])
        plugin.terminate()

    def test_linux_installation_runs_all_selected_jobs_and_records_each_result(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profiles
        from globalPlugins.NeovimAccessLink.core.ssh_install import InstallResult

        plugin = GlobalPlugin()
        profiles = parse_profiles([
            {"id": "one", "name": "One", "host": "one", "user": "alice", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "two", "name": "Two", "host": "two", "user": "bob", "port": 2222,
             "identityFile": r"C:\keys\two", "authentication": "password"},
        ])
        calls = []
        results = iter((OSError("ssh unavailable"), InstallResult(True, "installed")))
        installer = mock.Mock()
        def install(*args):
            calls.append(args)
            result = next(results)
            if isinstance(result, Exception):
                raise result
            return result
        installer.install.side_effect = install
        finished = []
        plugin._nvdaUi._finishServerInstalls = finished.extend
        with mock.patch(
                "globalPlugins.NeovimAccessLink.nvda_ui.SshUserInstaller",
                return_value=installer,
        ), \
                mock.patch.object(plugin._nvdaUi, "_recordDiagnostic") as record:
            plugin._nvdaUi._runServerInstalls(
                [(profiles[0], ""), (profiles[1], "temporary password")], "/tmp/package.tar.gz",
            )
        self.assertEqual(2, len(calls))
        self.assertEqual(("alice@one", 22, ""), (calls[0][0], calls[0][2], calls[0][3]))
        self.assertEqual(("bob@two", 2222, r"C:\keys\two", "temporary password"),
                         (calls[1][0], calls[1][2], calls[1][3], calls[1][4]))
        self.assertEqual(["one", "two"], [profile.identifier for profile, _result in finished])
        self.assertEqual([False, True], [result.success for _profile, result in finished])
        self.assertEqual("Unexpected installation error", finished[0][1].message)
        self.assertEqual(["one", "two"], [call.kwargs["targetId"] for call in record.call_args_list])
        plugin.terminate()

    def test_component_removal_uses_matching_accessible_multi_target_dialog(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._updateSettings(plugin, {"connections": [
            {"id": "one", "name": "One", "host": "one", "user": "alice", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "two", "name": "Two", "host": "two", "user": "bob", "port": 2222,
             "identityFile": "", "authentication": "password"},
        ]})
        self.checkListSelections.append([0, 2])
        self.modalDialogResults.append(sys.modules["wx"].ID_OK)

        selected = plugin._nvdaUi._chooseUninstallProfiles()

        self.assertEqual(["local-windows", "two"], [target.identifier for target in selected])
        connection_list = self.checkListBoxes[-1]
        self.assertEqual("Connections to remove components from", connection_list.name)
        self.assertTrue(any("Close Neovim" in label for label in self.staticTexts))
        self.assertTrue(any("Connections to remove components from:" == label for label in self.staticTexts))
        select_all = next(control for control in self.checkBoxControls if control.label == "Select all connections")
        self.assertTrue(select_all.focused)
        self.assertFalse(select_all.IsChecked())
        plugin.terminate()

    def test_component_removal_runs_local_and_remote_jobs_in_background(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profiles
        from globalPlugins.NeovimAccessLink.core.connection_targets import local_windows_target
        from globalPlugins.NeovimAccessLink.core.ssh_install import InstallResult

        plugin = GlobalPlugin()
        remote = parse_profiles([{
            "id": "remote", "name": "Remote", "host": "host", "user": "user", "port": 2222,
            "identityFile": r"C:\keys\remote", "authentication": "password",
        }])[0]
        local = local_windows_target("This computer")
        plugin._nvdaUi._chooseUninstallProfiles = lambda: [local, remote]
        plugin._nvdaUi._passwordForProfile = lambda _profile: "temporary password"
        calls = []
        run_removals = plugin._nvdaUi._runComponentRemovals
        plugin._nvdaUi._runComponentRemovals = lambda *args: calls.append(args)
        class ImmediateThread:
            def __init__(inner_self, target, args, daemon):
                inner_self.target, inner_self.args, inner_self.daemon = target, args, daemon
            def start(inner_self): inner_self.target(*inner_self.args)
        with mock.patch("threading.Thread", ImmediateThread):
            plugin._nvdaUi._onRemoveComponents(None)
        self.assertEqual(["local-windows", "remote"], [target.identifier for target, _password in calls[0][0]])
        self.assertEqual(["", "temporary password"], [password for _target, password in calls[0][0]])
        self.assertIn("Removing Neovim components from 2 targets", self.messages[-1])

        local_installer = mock.Mock()
        local_installer.uninstall.return_value = InstallResult(True, "local removed")
        ssh_installer = mock.Mock()
        ssh_installer.uninstall.return_value = InstallResult(True, "remote removed")
        finished = []
        plugin._nvdaUi._runComponentRemovals = run_removals
        plugin._nvdaUi._finishComponentRemovals = finished.extend
        with mock.patch(
                "globalPlugins.NeovimAccessLink.nvda_ui.LocalPluginInstaller",
                return_value=local_installer,
        ), mock.patch(
                "globalPlugins.NeovimAccessLink.nvda_ui.SshUserInstaller",
                return_value=ssh_installer,
        ), \
                mock.patch.object(plugin._nvdaUi, "_recordDiagnostic") as record:
            plugin._nvdaUi._runComponentRemovals([(local, ""), (remote, "temporary password")])
        local_installer.uninstall.assert_called_once_with()
        ssh_installer.uninstall.assert_called_once_with(
            "user@host", 2222, r"C:\keys\remote", "temporary password", plugin._askpassPath(),
        )
        self.assertEqual(["local-windows", "remote"], [target.identifier for target, _result in finished])
        self.assertEqual(["componentRemoval", "componentRemoval"], [call.args[0] for call in record.call_args_list])
        plugin.terminate()

    def test_component_removal_summary_reports_every_target_without_changing_settings(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.core.connection_profiles import parse_profiles
        from globalPlugins.NeovimAccessLink.core.ssh_install import InstallResult

        plugin = GlobalPlugin()
        profiles = parse_profiles([
            {"id": "ok", "name": "Documentation", "host": "example", "user": "editor", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
            {"id": "bad", "name": "Production", "host": "prod", "user": "admin", "port": 22,
             "identityFile": "", "authentication": "openSsh"},
        ])
        results = [
            (profiles[0], InstallResult(True, "removed")),
            (profiles[1], InstallResult(False, "permission denied")),
        ]
        before = list(self._settingsSnapshot(plugin)["connections"])

        summary = plugin._nvdaUi._componentRemovalResultSummary(results)
        plugin._nvdaUi._finishComponentRemovals(results)

        self.assertIn("Successful: 1", summary)
        self.assertIn("Documentation (editor@example)", summary)
        self.assertIn("Failed: 1", summary)
        self.assertIn("Production (admin@prod): permission denied", summary)
        self.assertEqual("Neovim component removal results", self.messageDialogs[-1].title)
        self.assertTrue(self.messageDialogs[-1].shown)
        self.assertEqual(before, self._settingsSnapshot(plugin)["connections"])
        plugin.terminate()

    def test_password_is_prompted_once_per_activation_and_never_persisted(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._updateSettings(plugin, {
            "connections": [{
                "id": "password-host", "name": "Password host", "host": "host",
                "user": "remote", "port": 22, "identityFile": "", "authentication": "password",
            }],
        })
        profile = plugin._connectionProfileById("password-host")
        self.assertEqual([], plugin._automaticClaimProfiles())
        prompts = []
        plugin._promptPassword = lambda name: prompts.append(name) or "not-saved secret"
        self.assertEqual("not-saved secret", plugin._passwordForProfile(profile))
        self.assertEqual("not-saved secret", plugin._passwordForProfile(profile))
        self.assertEqual(["Password host"], prompts)
        self.assertEqual(["password-host"], [
            item.identifier for item in plugin._automaticClaimProfiles()
        ])
        plugin._settingsService.save()
        saved = __import__("config").conf["NeovimAccessLink"]["connections"]
        self.assertNotIn("not-saved secret", saved)
        plugin._clearSessionPasswords()
        self.assertEqual({}, plugin._sessionPasswords)
        plugin._promptPassword = lambda _name: None
        self.assertIsNone(plugin._passwordForProfile(profile))
        plugin.terminate()

    def test_toggle_never_activates_or_deactivates_an_nvda_profile(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._beginClaimInventory = lambda: None
        plugin._toggleNeovimMode()
        plugin._toggleNeovimMode()
        self.assertFalse(hasattr(plugin, "_nvdaProfileActive"))
        self.assertFalse(hasattr(plugin, "_activateNvdaProfile"))
        self.assertFalse(hasattr(plugin, "_deactivateNvdaProfile"))
        source = (self.extract_path / "globalPlugins" / "NeovimAccessLink" / "__init__.py").read_text(
            encoding="utf-8",
        )
        self.assertNotIn("manualActivateProfile", source)
        self.assertNotIn("listProfiles", source)
        plugin.terminate()

    def test_built_plugin_loads_toggles_and_fails_open(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._beginClaimInventory = lambda: None
        called: list[bool] = []
        self._terminalAdapter().event_textChange(self.focus, lambda: called.append(True))
        self.assertEqual([True], called)
        plugin.action_toggleNeovimMode(None)
        self.assertIn("local and saved", self.messages[-1])
        self.assertFalse(plugin._gate.suppression_active)
        plugin.terminate()

    def test_inactive_braille_overlay_raises_at_call_time_for_nvda_fallback(self) -> None:
        from globalPlugins.NeovimAccessLink import StructuredTerminalBrailleOverlay

        overlay = StructuredTerminalBrailleOverlay()
        overlay.processID = 100
        overlay.windowHandle = 200
        with self.assertRaises(NotImplementedError):
            overlay.getBrailleRegions()

    def test_authenticated_full_state_binds_only_focused_terminal(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._beginClaimInventory = lambda: None
        plugin.action_toggleNeovimMode(None)
        plugin._handleEvent({
            "type": "fullState",
            "payload": {"modeRaw": "n", "lineText": "hello", "cursor": {"line": 1, "byteColumn": 0}},
        })
        self.assertTrue(plugin._gate.suppression_active)
        called: list[bool] = []
        adapter = self._terminalAdapter()
        cancellations_before_modes = self.speechCancellations
        for mode in (
            "normal", "insert", "visualCharacter", "visualLine", "visualBlock",
            "operatorPending", "commandLine", "replace",
        ):
            plugin._currentState["mode"] = mode
            adapter.event_gainFocus(self.focus, lambda: called.append(True))
            adapter.event_textChange(self.focus, lambda: called.append(True))
            adapter.event_typedCharacter(self.focus, lambda: called.append(True), "x")
            adapter.event_UIA_notification(self.focus, lambda: called.append(True))
            for handler in (
                adapter.event_liveRegionChange, adapter.event_valueChange,
                adapter.event_nameChange, adapter.event_descriptionChange,
            ):
                handler(self.focus, lambda: called.append(True))
        # gainFocus must continue through NVDA so Terminal starts LiveText and
        # editable-text monitoring. Its native speech is cancelled; every
        # content event remains blocked in all structured editor modes.
        self.assertEqual([True] * 8, called)
        self.assertEqual(cancellations_before_modes + 8, self.speechCancellations)
        called.clear()
        other = types.SimpleNamespace(processID=100, windowHandle=201)
        adapter.event_textChange(other, lambda: called.append(True))
        self.assertEqual([True], called)
        plugin._onNetworkState("disconnected")
        adapter.event_textChange(self.focus, lambda: called.append(True))
        self.assertEqual([True, True], called)
        plugin.terminate()

    def test_event_diagnostics_expose_safe_key_observer_and_blocking_state(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._handleEvent({
            "type": "fullState",
            "payload": {
                "mode": "unknown",
                "modeRaw": "r?",
                "modeBlocking": True,
                "currentErrorCode": "E565",
                "currentErrorKind": "other",
                "keyObserverDiagnostics": {
                    "observerErrorCount": 0,
                    "observerErrorKind": "",
                    "claimErrorKind": "",
                    "claimKeyConsumed": True,
                    "modeAfterClaim": "r?",
                    "translatedKey": "<F12>",
                    "translatedTyped": "<F12>",
                    "keyByteLength": 3,
                    "typedByteLength": 3,
                    "promptActive": True,
                    "promptKind": "confirm",
                    "promptClass": "unsavedChanges",
                    "promptLength": 42,
                },
            },
        })
        report = plugin._diagnostics.report()
        self.assertIn('"modeBlocking": true', report)
        self.assertIn('"currentErrorCode": "E565"', report)
        self.assertIn('"keyTranslated": "<F12>"', report)
        self.assertIn('"keyClaimConsumed": true', report)
        self.assertIn('"keyModeAfterClaim": "r?"', report)
        self.assertIn('"keyPromptKind": "confirm"', report)
        self.assertIn('"keyPromptClass": "unsavedChanges"', report)
        self.assertNotIn("promptText", report)
        plugin.terminate()

    def test_terminal_buffer_temporarily_restores_native_terminal_output(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        identity = plugin._identity(self.focus)
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        played: list[tuple[str, bool]] = []
        plugin._editorSounds.play = lambda cue: played.append(
            (cue, plugin._gate.terminal_passthrough)
        ) or True
        self.assertTrue(plugin._gate.suppression_active)
        plugin._handleEvent({"type": "contextChanged", "payload": {
            "mode": "terminal", "modeRaw": "t", "buftype": "terminal",
            "bufferId": 2, "lineText": "shell output", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertTrue(plugin._gate.terminal_passthrough)
        self.assertFalse(plugin._gate.suppression_active)
        self.assertEqual(("insertMode", True), played[-1])
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "terminalNormal", "modeRaw": "nt", "buftype": "terminal",
            "bufferId": 2, "lineText": "shell output", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertFalse(plugin._gate.terminal_passthrough)
        self.assertTrue(plugin._gate.suppression_active)
        self.assertEqual(("normalMode", False), played[-1])
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "terminal", "modeRaw": "t", "buftype": "terminal",
            "bufferId": 2, "lineText": "shell output", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertTrue(plugin._gate.terminal_passthrough)
        self.assertEqual(("insertMode", True), played[-1])
        report = plugin._diagnostics.report()
        self.assertIn('"mode": "terminal"', report)
        self.assertIn('"category": "normalModeSound"', report)
        self._updateSettings(plugin, {"feedback": {"mode": 1}})
        sounds_before_speech_only = len(played)
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "terminalNormal", "modeRaw": "nt", "buftype": "terminal",
            "bufferId": 2, "lineText": "shell output", "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "terminal", "modeRaw": "t", "buftype": "terminal",
            "bufferId": 2, "lineText": "shell output", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertEqual(sounds_before_speech_only, len(played))
        plugin.terminate()

    def test_command_line_mode_and_following_message_remain_spoken(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"feedback": {"mode": 0}})
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "normal", "modeRaw": "n", "lineText": "",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.spoken.clear()
        self.brailleMessages.clear()
        plugin._handleEvent({"type": "commandLineChanged", "payload": {
            "mode": "commandLine", "modeRaw": "c", "commandLine": "",
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "commandLine", "modeRaw": "c", "commandLine": "",
        }})
        for position, command_line in enumerate((
            "t", "te", "ter", "term", "termi", "termin", "termina", "terminal",
        ), start=1):
            plugin._handleEvent({"type": "commandLineChanged", "payload": {
                "mode": "commandLine", "modeRaw": "c", "bufferId": 1,
                "commandLine": command_line, "commandLinePosition": position,
                "cursor": {"line": 1, "byteColumn": 0},
            }})
        plugin._handleEvent({"type": "messageReceived", "payload": {
            "mode": "normal", "modeRaw": "n", "message": "command completed",
        }})
        self.assertEqual(
            ["command-line mode", *list("terminal"), "command completed"],
            self.spoken,
        )
        self.assertEqual(list("terminal"), self.spelled)
        self.assertEqual(["command completed"], self.brailleMessages)
        plugin.terminate()

    def test_terminal_command_line_has_distinct_enter_and_return_sounds(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        played: list[str] = []
        plugin._editorSounds.play = lambda cue: played.append(cue) or True
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "terminalNormal", "modeRaw": "nt", "buftype": "terminal",
            "bufferId": 2, "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "commandLineChanged", "payload": {
            "mode": "commandLine", "modeRaw": "c", "buftype": "terminal",
            "bufferId": 2, "commandLine": "", "commandLinePosition": 0,
        }})
        self.assertEqual((600, 30), self.beeps[-1])
        beep_count = len(self.beeps)
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "commandLine", "modeRaw": "c", "buftype": "terminal",
            "bufferId": 2, "commandLine": "", "commandLinePosition": 0,
        }})
        self.assertEqual(beep_count, len(self.beeps))
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "terminalNormal", "modeRaw": "nt", "buftype": "terminal",
            "bufferId": 2, "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertEqual(["normalMode"], played)
        report = plugin._diagnostics.report()
        self.assertIn('"category": "commandLineModeSound"', report)
        plugin.terminate()

    def test_message_command_return_plays_mode_sound_and_uses_focus_choice(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        for setting, expected in (
            (0, "saved"),
            (1, "saved; Draft opening"),
            (2, "saved; file draft.md, normal mode, on Example"),
        ):
            with self.subTest(focusAnnouncement=setting):
                plugin = GlobalPlugin()
                plugin._gate.manual_enabled = True
                self._updateSettings(plugin, {"focusAnnouncement": setting})
                played: list[str] = []
                plugin._editorSounds.play = lambda cue: played.append(cue) or True
                base = {
                    "bufferId": 1, "windowId": 10, "tabpageId": 20,
                    "bufferName": "/work/draft.md", "buftype": "",
                    "lineText": "Draft opening", "cursor": {"line": 1, "byteColumn": 0},
                }
                plugin._handleEvent({"type": "fullState", "payload": {
                    **base, "mode": "normal", "modeRaw": "n",
                }})
                self.spoken.clear()
                plugin._handleEvent({"type": "commandLineChanged", "payload": {
                    **base, "mode": "commandLine", "modeRaw": "c",
                    "commandLine": "write", "commandLineType": ":",
                }})
                plugin._handleEvent({"type": "modeChanged", "payload": {
                    **base, "mode": "commandLine", "modeRaw": "c",
                }})
                plugin._handleEvent({"type": "modeChanged", "payload": {
                    **base, "mode": "normal", "modeRaw": "n",
                }})
                plugin._handleEvent({"type": "messageReceived", "payload": {
                    **base, "mode": "normal", "modeRaw": "n", "message": "saved",
                    "commandLineReturn": True, "_connectionLabel": "Example",
                }})

                self.assertEqual(["normalMode"], played)
                self.assertEqual(expected, self.spoken[-1])
                plugin.terminate()

    def test_terminal_command_creating_terminal_plays_one_normal_cue(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        played: list[str] = []
        plugin._editorSounds.play = lambda cue: played.append(cue) or True
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "normal", "modeRaw": "n", "buftype": "", "bufferId": 1,
            "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "commandLineChanged", "payload": {
            "mode": "commandLine", "modeRaw": "c", "buftype": "", "bufferId": 1,
            "commandLine": "", "commandLinePosition": 0,
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "commandLine", "modeRaw": "c", "buftype": "", "bufferId": 1,
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "normal", "modeRaw": "n", "buftype": "", "bufferId": 1,
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "terminalNormal", "modeRaw": "nt", "buftype": "terminal",
            "bufferId": 1, "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertEqual(["normalMode"], played)
        plugin.terminate()

    def test_command_line_echo_uses_utf8_command_position_not_editor_cursor(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        for text, position in (("ä", 2), ("äx", 3)):
            plugin._handleEvent({"type": "commandLineChanged", "payload": {
                "mode": "commandLine", "modeRaw": "c", "bufferId": 1,
                "commandLine": text, "commandLinePosition": position,
                "cursor": {"line": 9, "byteColumn": 27},
            }})
        self.assertEqual(["ä", "x"], self.spelled)
        plugin.terminate()

    def test_structured_braille_region_preserves_indent_cursor_and_selection(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        plugin = GlobalPlugin()
        self._focusPlugin(plugin)
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        plugin._gate.bound_terminal = plugin._gate.focused
        plugin._currentState = {
            "lineText": "\t界🙂z",
            "tabstop": 4,
            "cursor": {"byteColumn": 8},
            "selection": {"currentLine": {"startByteColumn": 1, "endByteColumn": 8}},
        }
        region = StructuredLineRegion(self.focus)
        region.update()
        self.assertEqual("    界🙂z", region.rawText)
        self.assertEqual((4, 6), (region.selectionStart, region.selectionEnd))
        self.assertIsNone(region.cursorPos)

    def test_file_manager_braille_region_is_semantic_and_routes_only_the_name(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        plugin = GlobalPlugin()
        controls: list[tuple[str, dict]] = []
        plugin._client = types.SimpleNamespace(
            send_control=lambda kind, payload: controls.append((kind, payload)) or True,
            stop=lambda: None,
        )
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        identity = plugin._identity(self.focus)
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._currentState = {
            "bufferId": 1, "windowId": 1000, "changedtick": 9,
            "lineText": "   café/", "cursor": {"line": 3, "byteColumn": 8},
            "fileManager": {"name": "tree", "entry": {
                "name": "café", "type": "directory", "expanded": True,
            }},
            "_transport": {"capabilities": ["cursorRouting"]},
        }
        region = StructuredLineRegion(self.focus)
        region.update()
        self.assertEqual("café, directory, expanded", region.rawText)
        region.routeTo(3)
        region.routeTo(len("café"))
        self.assertEqual(9, controls[0][1]["byteColumn"])
        self.assertEqual(1, len(controls))
        self.assertIn('"reason": "semanticStatus"', plugin._diagnostics.report())
        plugin.terminate()

    def test_visual_line_delta_uses_interruptible_nvda_speech(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        plugin._handleEvent({"type": "selectionChanged", "payload": {
            "mode": "visualLine", "lineText": "Petra war gestern einkaufen.",
            "cursor": {"line": 1, "byteColumn": 0},
            "selection": {
                "kind": "line", "text": "Petra war gestern einkaufen.",
                "selectedLines": [{"line": 1, "text": "Petra war gestern einkaufen."}],
            },
        }})
        self.assertEqual("Petra war gestern einkaufen. selected", self.spoken[-1])
        self.assertEqual(1, self.speechCancellations)
        plugin.terminate()

    def test_visual_symbols_ignore_nvda_punctuation_level_and_spaces_are_named(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        for text, expected in (("?", "? selected"), (" ", "space selected")):
            plugin._planner.reset()
            plugin._handleEvent({"type": "selectionChanged", "payload": {
                "mode": "visualCharacter", "lineText": text,
                "cursor": {"line": 1, "byteColumn": len(text.encode("utf-8"))},
                "selection": {"kind": "character", "text": text},
            }})
            self.assertEqual(expected, self.speechTextCalls[-1][0])
            self.assertEqual(300, self.speechTextCalls[-1][1].get("symbolLevel"))
        plugin.terminate()

    def test_missing_matching_pair_uses_nvda_speech_and_error_tone(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        plugin._handleEvent({"type": "matchingPairNotFound", "payload": {
            "mode": "normal", "lineText": "plain text",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertEqual("no matching pair", self.spoken[-1])
        self.assertEqual(1, len(self.soundFeeds))
        self.assertEqual([], self.beeps)
        plugin.terminate()

    def test_spelling_uses_nvda_config_cached_sound_and_braille_markers(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._focusPlugin(plugin)
        state = {
            "mode": "normal", "lineText": "mispelled word", "tabstop": 4,
            "cursor": {"line": 1, "byteColumn": 1, "characterColumn": 1},
            "spellingError": {
                "kind": "spelling", "startByteColumn": 0, "endByteColumn": 9,
            },
            "spellingErrors": [{
                "kind": "spelling", "startByteColumn": 0, "endByteColumn": 9,
            }],
        }
        plugin._handleEvent({"type": "fullState", "payload": state})
        self.assertIn("spelling error", self.spoken)
        self.assertEqual(1, len(self.soundFeeds))
        region = StructuredLineRegion(self.focus)
        region.update()
        self.assertEqual("⠑mispelled⡑ word", region.rawText)
        plugin._handleEvent({
            "type": "spellingErrorTyped", "payload": {**state, "spellingError": state["spellingError"]},
        })
        self.assertEqual(2, len(self.soundFeeds))
        plugin.terminate()

    def test_spelling_off_and_sound_only_follow_nvda_formatting_mode(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        config.conf["documentFormatting"]["reportSpellingErrors2"] = 0
        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._focusPlugin(plugin)
        state = {
            "mode": "normal", "lineText": "mispelled", "cursor": {"line": 1, "byteColumn": 1},
            "spellingError": {"kind": "spelling", "startByteColumn": 0, "endByteColumn": 9},
            "spellingErrors": [{"kind": "spelling", "startByteColumn": 0, "endByteColumn": 9}],
        }
        plugin._handleEvent({"type": "fullState", "payload": state})
        self.assertNotIn("spelling error", self.spoken)
        self.assertEqual(0, len(self.soundFeeds))
        region = StructuredLineRegion(self.focus)
        region.update()
        self.assertEqual("mispelled", region.rawText)

        config.conf["documentFormatting"]["reportSpellingErrors2"] = 2
        moved = {**state, "cursor": {"line": 2, "byteColumn": 1}}
        plugin._handleEvent({"type": "lineChanged", "payload": moved})
        self.assertNotIn("spelling error", self.spoken)
        self.assertEqual(1, len(self.soundFeeds))
        plugin.terminate()

    def test_insert_mode_sound_and_copyable_redacted_diagnostics(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        insert = {
            "type": "modeChanged",
            "sessionId": "session-a",
            "sequence": 4,
            "payload": {
                "mode": "insert",
                "modeRaw": "i",
                "lineText": "private source",
                "cursor": {"line": 1, "byteColumn": 0},
            },
        }
        plugin._handleEvent(insert)
        plugin._handleEvent(insert)
        self.assertEqual(1, len(self.soundFeeds))
        self.assertEqual([], self.beeps)
        plugin._handleEvent({
            "type": "modeChanged",
            "payload": {"mode": "normal", "modeRaw": "n", "lineText": "x", "cursor": {"line": 1, "byteColumn": 0}},
        })
        self.assertEqual(2, len(self.soundFeeds))
        self.assertEqual([], self.beeps)
        plugin.action_copyDiagnosticReport(None)
        self.assertTrue(self.clipboard.startswith(buildVars.addon_info["summary"] + " diagnostic report"))
        self.assertIn('"addonVersion": "' + buildVars.artifact_version() + '"', self.clipboard)
        self.assertNotIn("private source", self.clipboard)
        self.assertIn("session-a", self.clipboard)
        plugin.terminate()

    def test_structured_typing_uses_nvda_typing_echo_api(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        plugin._handleEvent({
            "type": "fullState",
            "payload": {"mode": "insert", "lineText": "", "cursor": {"line": 1, "byteColumn": 0}},
        })
        plugin._handleEvent({
            "type": "textChanged",
            "payload": {"mode": "insert", "lineText": "ab", "cursor": {"line": 1, "byteColumn": 2}},
        })
        self.assertEqual(["blank", "a", "b"], self.spoken[-3:])
        plugin.terminate()

    def test_line_cursor_character_uses_spelling_not_abbreviation_speech(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "old",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "lineChanged", "payload": {
            "mode": "normal", "lineText": "moin", "character": "m",
            "indentation": 0, "shiftwidth": 4,
            "cursor": {"line": 2, "byteColumn": 0},
        }})
        self.assertEqual(["m"], self.spelled)
        self.assertEqual(["moin", "m"], self.spoken[-2:])
        plugin.terminate()

    def test_completion_menu_uses_cached_nvda_sounds_speech_and_braille(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        with mock.patch(
            "globalPlugins.NeovimAccessLink.suggestion_sounds.wave.open",
            side_effect=AssertionError("menu playback must not reopen WAV files"),
        ):
            plugin._handleEvent({"type": "menuOpened", "payload": {
                "mode": "insert", "itemCount": 5,
            }})
            plugin._handleEvent({"type": "menuSelectionChanged", "payload": {
                "mode": "insert", "itemIndex": 1, "itemCount": 5,
                "item": {
                    "label": "printf", "kind": "function", "parameters": "format, ...",
                    "documentation": "Print formatted output",
                },
            }})
            plugin.action_readCompletionDocumentation(None)
            plugin._handleEvent({"type": "menuClosed", "payload": {"mode": "insert"}})
        expected = "printf, 1 of 5, function, parameter format, ..."
        self.assertIn(expected, self.spoken)
        self.assertIn("Print formatted output", self.spoken)
        self.assertEqual(expected, self.brailleMessages[-1])
        self.assertEqual(2, len(self.soundFeeds))
        plugin.terminate()

    def test_completion_sounds_follow_nvda_setting_and_missing_files_fail_open(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        from globalPlugins.NeovimAccessLink.suggestion_sounds import SuggestionSoundCache

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        config.conf["presentation"]["reportAutoSuggestionsWithSound"] = False
        plugin._handleEvent({"type": "menuOpened", "payload": {"mode": "insert", "itemCount": 2}})
        self.assertEqual([], self.soundFeeds)
        self.assertIn("suggestionSoundSuppressed", plugin._diagnostics.report())
        diagnostics = []
        config.conf["presentation"]["reportAutoSuggestionsWithSound"] = True
        missing = SuggestionSoundCache(
            str(self.config_path / "missing"),
            on_diagnostic=lambda category, **fields: diagnostics.append((category, fields)),
        )
        self.assertFalse(missing.play("open"))
        self.assertEqual(2, sum(category == "suggestionSoundLoadError" for category, _ in diagnostics))
        self.assertTrue(any(category == "suggestionSoundUnavailable" for category, _ in diagnostics))
        missing.close()
        plugin.terminate()

    def test_linewise_delete_speaks_result_line_with_nvda_indent_tone(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        plugin._handleEvent({"type": "textDeleted", "payload": {
            "mode": "normal", "beforeText": "old", "lineText": "    next",
            "linewise": True, "cursor": {"line": 1, "byteColumn": 4},
        }})
        self.assertEqual(["deleted old", "    next"], self.spoken[-2:])
        self.assertIn((round(220 * (2 ** (4 / 24.0))), 40), self.beeps)
        plugin.terminate()

    def test_indentation_follows_nvda_document_formatting_mode(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        config.conf["documentFormatting"]["reportLineIndentation"] = 1
        plugin._reportIndentation(8, 2)
        self.assertEqual("indentation level 2", self.spoken[-1])
        self.assertEqual([], self.beeps)

        config.conf["documentFormatting"]["reportLineIndentation"] = 2
        plugin._reportIndentation(0, 0)
        self.assertEqual((220, 40), self.beeps[-1])
        self.assertNotEqual("no indent", self.spoken[-1])

        config.conf["documentFormatting"]["reportLineIndentation"] = 3
        plugin._reportIndentation(4, 1)
        self.assertEqual("indentation level 1", self.spoken[-1])
        self.assertEqual((round(220 * (2 ** (4 / 24.0))), 40), self.beeps[-1])
        plugin.terminate()

    def test_structured_typing_honors_echo_switches_but_forces_punctuation_names(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "insert", "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }})
        config.conf["keyboard"] = {"speakTypedCharacters": 2, "speakTypedWords": 0}
        plugin._handleEvent({"type": "textChanged", "payload": {
            "mode": "insert", "lineText": "?", "cursor": {"line": 1, "byteColumn": 1},
        }})
        self.assertEqual("?", self.spoken[-1])
        config.conf["keyboard"] = {"speakTypedCharacters": 0, "speakTypedWords": 2}
        plugin._planner.reset()
        plugin._typedWord = []
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "insert", "lineText": "", "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            "mode": "insert", "lineText": "ab ", "cursor": {"line": 1, "byteColumn": 3},
        }})
        self.assertEqual("ab", self.spoken[-1])
        plugin.terminate()

    def test_typed_word_buffer_resets_when_cursor_state_contains_unreported_gap(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        config.conf["keyboard"] = {"speakTypedCharacters": 0, "speakTypedWords": 2}
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "old",
            "cursor": {"line": 1, "byteColumn": 3},
        }})
        # Neovim can report the intervening space in a navigation/state event,
        # leaving the next text diff with letters only.
        plugin._handleEvent({"type": "cursorMoved", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "old ",
            "cursor": {"line": 1, "byteColumn": 4},
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "old new ",
            "cursor": {"line": 1, "byteColumn": 8},
        }})
        self.assertEqual("new", self.spoken[-1])
        self.assertNotIn("oldnew", self.spoken)
        plugin.terminate()

    def test_coalesced_typing_diff_does_not_repeat_processed_prefix(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        config.conf["keyboard"] = {"speakTypedCharacters": 2, "speakTypedWords": 2}
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            "mode": "insert", "bufferId": 1, "lineText": "ab",
            "cursor": {"line": 1, "byteColumn": 2},
        }})
        self.spoken.clear()
        # A coalesced/stale diff may repeat "ab" while only "c " is new.
        plugin._speakStructuredTyping("abc ", {
            "mode": "insert", "bufferId": 1, "lineText": "abc ",
            "cursor": {"line": 1, "byteColumn": 4},
        })
        self.assertEqual(["c", "abc", " "], self.spoken)
        plugin.terminate()

    def test_typed_word_buffer_survives_insert_submode_but_not_reconnect(self) -> None:
        import config
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        config.conf["keyboard"] = {"speakTypedCharacters": 0, "speakTypedWords": 2}
        base = {"mode": "insert", "bufferId": 1, "lineText": "", "cursor": {"line": 1, "byteColumn": 0}}
        plugin._handleEvent({"type": "fullState", "payload": base})
        plugin._handleEvent({"type": "textChanged", "payload": {
            **base, "lineText": "word", "cursor": {"line": 1, "byteColumn": 4},
        }})
        plugin._handleEvent({"type": "modeChanged", "payload": {
            **base, "modeRaw": "ic", "lineText": "word", "cursor": {"line": 1, "byteColumn": 4},
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            **base, "lineText": "word ", "cursor": {"line": 1, "byteColumn": 5},
        }})
        self.assertEqual("word", self.spoken[-1])

        plugin._handleEvent({"type": "textChanged", "payload": {
            **base, "lineText": "word old", "cursor": {"line": 1, "byteColumn": 8},
        }})
        plugin._lastConnectionState = "connected"
        plugin._handleConnectionState("disconnected")
        plugin._handleEvent({"type": "fullState", "payload": {
            **base, "lineText": "word old", "cursor": {"line": 1, "byteColumn": 8},
        }})
        plugin._handleEvent({"type": "textChanged", "payload": {
            **base, "lineText": "word oldnew ", "cursor": {"line": 1, "byteColumn": 12},
        }})
        self.assertEqual("new", self.spoken[-1])
        self.assertNotIn("oldnew", self.spoken)
        plugin.terminate()

    def test_action_feedback_modes_gate_only_addon_owned_speech_and_sounds(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"feedback": {
            "global": 3, "mode": 2, "delete": 1, "replace": 3,
            "lineBoundary": 2, "fileBoundary": 3, "lineCrossed": 2, "matchingError": 3,
        }})
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "ab", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.spoken.clear()
        self.soundFeeds.clear()
        plugin._handleEvent({"type": "textChanged", "payload": {
            "mode": "insert", "lineText": "a", "cursor": {"line": 1, "byteColumn": 1},
        }})
        self.assertEqual("deleted b", self.spoken[-1])
        self.assertEqual([], self.soundFeeds)

        plugin._planner.reset()
        plugin._lastMode = "normal"
        self.spoken.clear()
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "insert", "modeRaw": "i", "lineText": "a", "cursor": {"line": 1, "byteColumn": 1},
        }})
        self.assertEqual([], self.spoken)
        self.assertEqual(1, len(self.soundFeeds))

        # Completion sounds remain governed by NVDA's own suggestion setting,
        # even when all Add-on-owned feedback is globally disabled.
        self._updateSettings(plugin, {"feedback": {"global": 0}})
        plugin._handleEvent({"type": "menuOpened", "payload": {
            "mode": "insert", "lineText": "a", "cursor": {"line": 1, "byteColumn": 1},
        }})
        self.assertEqual(2, len(self.soundFeeds))
        plugin.terminate()

    def test_feedback_mode_uses_complete_nvda_style_bitmask_matrix(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        for global_mode in range(4):
            for local_mode in range(4):
                self._updateSettings(
                    plugin,
                    {"feedback": {"global": global_mode, "delete": local_mode}},
                )
                self.assertEqual(global_mode & local_mode, plugin._feedbackMode("delete"))
        plugin.terminate()

    def test_every_feedback_setting_controls_its_real_speech_and_sound_path(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        cases = {
            "mode": (
                {"type": "fullState", "payload": {"mode": "normal", "lineText": "x", "cursor": {"line": 1, "byteColumn": 0}}},
                {"type": "modeChanged", "payload": {"mode": "insert", "modeRaw": "i", "lineText": "x", "cursor": {"line": 1, "byteColumn": 0}}},
                "insert mode",
            ),
            "delete": (
                {"type": "fullState", "payload": {"mode": "insert", "lineText": "ab", "cursor": {"line": 1, "byteColumn": 2}}},
                {"type": "textChanged", "payload": {"mode": "insert", "lineText": "a", "cursor": {"line": 1, "byteColumn": 1}}},
                "deleted b",
            ),
            "replace": (
                {"type": "fullState", "payload": {"mode": "normal", "lineText": "old", "cursor": {"line": 1, "byteColumn": 0}}},
                {"type": "textReplaced", "payload": {"mode": "normal", "beforeText": "old", "lineText": "new", "cursor": {"line": 1, "byteColumn": 0}}},
                "replaced old",
            ),
            "lineBoundary": (
                {"type": "fullState", "payload": {"mode": "normal", "lineText": "abc", "cursor": {"line": 1, "byteColumn": 1}}},
                {"type": "lineStart", "payload": {"mode": "normal", "lineText": "abc", "cursor": {"line": 1, "byteColumn": 0}}},
                "line start",
            ),
            "fileBoundary": (
                {"type": "fullState", "payload": {"mode": "normal", "lineText": "abc", "cursor": {"line": 2, "byteColumn": 0}}},
                {"type": "fileStart", "payload": {"mode": "normal", "lineText": "abc", "character": "a", "cursor": {"line": 1, "byteColumn": 0}}},
                "beginning of file, abc",
            ),
            "matchingError": (
                {"type": "fullState", "payload": {"mode": "normal", "lineText": "(", "cursor": {"line": 1, "byteColumn": 0}}},
                {"type": "matchingPairNotFound", "payload": {"mode": "normal", "lineText": "(", "cursor": {"line": 1, "byteColumn": 0}}},
                "no matching pair",
            ),
        }
        for key, (initial, event_to_test, expected_speech) in cases.items():
            for output_mode in range(4):
                with self.subTest(setting=key, outputMode=output_mode):
                    plugin = GlobalPlugin()
                    plugin._gate.manual_enabled = True
                    self._updateSettings(plugin, {"feedback": {**{
                        "global": 3, "mode": 3, "delete": 3, "replace": 3,
                        "lineBoundary": 2, "fileBoundary": 3,
                        "lineCrossed": 2, "matchingError": 3,
                    }, key: output_mode}})
                    plugin._handleEvent(initial)
                    self.spoken.clear()
                    self.soundFeeds.clear()
                    plugin._handleEvent(event_to_test)
                    self.assertEqual(bool(output_mode & 1), expected_speech in self.spoken)
                    self.assertEqual(bool(output_mode & 2), bool(self.soundFeeds))
                    plugin.terminate()

        for output_mode in range(4):
            with self.subTest(setting="lineCrossed", outputMode=output_mode):
                plugin = GlobalPlugin()
                plugin._gate.manual_enabled = True
                self._updateSettings(plugin, {"feedback": {**{
                    "global": 3, "mode": 3, "delete": 3, "replace": 3,
                    "lineBoundary": 2, "fileBoundary": 3,
                    "lineCrossed": output_mode, "matchingError": 3,
                }}})
                plugin._handleEvent({"type": "fullState", "payload": {
                    "mode": "normal", "lineText": "a", "character": "a",
                    "cursor": {"line": 1, "byteColumn": 0},
                }})
                self.spoken.clear()
                self.soundFeeds.clear()
                plugin._handleEvent({"type": "characterMoved", "payload": {
                    "mode": "normal", "lineText": "x", "character": "x",
                    "cursor": {"line": 2, "byteColumn": 0},
                }})
                self.assertIn("x", self.spoken)
                self.assertEqual(bool(output_mode & 1), "new line" in self.spoken)
                self.assertEqual(bool(output_mode & 2), bool(self.soundFeeds))
                plugin.terminate()

        plugin = GlobalPlugin()
        plugin._gate.manual_enabled = True
        self._updateSettings(plugin, {"feedback": {"global": 3, "mode": 0}})
        plugin._handleEvent({"type": "fullState", "payload": {
            "mode": "normal", "lineText": "x", "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.spoken.clear()
        plugin._handleEvent({"type": "modeChanged", "payload": {
            "mode": "visualCharacter", "modeRaw": "v", "lineText": "x",
            "cursor": {"line": 1, "byteColumn": 0},
        }})
        self.assertIn("visual character mode", self.spoken)
        plugin.terminate()

    def test_old_addon_identity_configuration_is_ignored(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import config

        path = self.config_path / "nvimNvdaAccess.json"
        path.write_text(json.dumps({
            "connections": [{
                "id": "obsolete", "name": "Obsolete", "host": "obsolete.example.invalid", "user": "editor",
                "port": 22, "identityFile": "", "authentication": "openSsh",
            }],
            "feedback": {"global": 0},
        }), encoding="utf-8")
        old_section = {
            "connections": "[]",
            "feedback": {
                "global": 0, "mode": 0, "delete": 0, "replace": 0,
                "lineBoundary": 2, "fileBoundary": 3,
                "lineCrossed": 2, "matchingError": 3,
            },
        }
        config.conf["nvimNvdaAccess"] = old_section

        plugin = GlobalPlugin()

        settings = self._settingsSnapshot(plugin)
        self.assertEqual([], settings["connections"])
        self.assertEqual(3, settings["feedback"]["global"])
        self.assertEqual(2, settings["focusAnnouncement"])
        self.assertEqual(0, self.configSaves)
        self.assertTrue(path.exists())
        self.assertIs(old_section, config.conf["nvimNvdaAccess"])
        plugin.terminate()

    def test_settings_write_uses_only_aggregated_section_supported_operations(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import config

        class AggregatedSectionLike:
            """Minimal public mapping surface exposed by NVDA AggregatedSection."""
            def __init__(inner_self):
                inner_self.values = {"feedback": {}}
            def __getitem__(inner_self, key):
                return inner_self.values[key]
            def __setitem__(inner_self, key, value):
                inner_self.values[key] = value

        plugin = GlobalPlugin()
        section = AggregatedSectionLike()
        config.conf["NeovimAccessLink"] = section
        plugin._settingsService.save()
        self.assertNotIn("schemaVersion", section.values)
        self.assertEqual(2, section.values["focusAnnouncement"])
        self.assertIsInstance(section.values["connections"], str)
        self.assertEqual(
            set(self._settingsSnapshot(plugin)["feedback"]),
            set(section.values["feedback"]),
        )
        plugin.terminate()

    def test_invalid_focus_announcement_falls_back_to_existing_context(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin

        plugin = GlobalPlugin()
        normalized = plugin._settingsService.normalize({
            "connections": [], "feedback": {}, "focusAnnouncement": 99,
        })

        self.assertEqual(2, normalized["focusAnnouncement"])
        self.assertIn('"option": "focusAnnouncement"', plugin._diagnostics.report())
        plugin.terminate()

    def test_settings_service_snapshots_and_connection_notifications_are_transactional(self) -> None:
        from dataclasses import FrozenInstanceError
        from globalPlugins.NeovimAccessLink.settings_service import SettingsService

        section = {
            "connections": "[]",
            "focusAnnouncement": 2,
            "feedback": {"global": 3, "mode": 3},
        }
        notifications = []
        service = SettingsService(
            {"NeovimAccessLink": section},
            section_name="NeovimAccessLink",
            feedback_defaults={"global": 3, "mode": 3},
            focus_announcement_values=("none", "line", "context"),
            focus_announcement_default=2,
            record_diagnostic=lambda *_args, **_kwargs: None,
            on_connections_changed=lambda: notifications.append(True) or True,
        )
        detached = service.snapshot()
        detached["feedback"]["global"] = 0
        self.assertEqual(3, service.snapshot()["feedback"]["global"])

        unchanged = service.update(service.snapshot())
        self.assertFalse(unchanged.connections_changed)
        self.assertEqual([], notifications)
        values = service.snapshot()
        values["connections"] = [{
            "id": "work", "name": "Work", "host": "host", "user": "user",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        }]
        changed = service.update(values)
        self.assertTrue(changed.connections_changed)
        self.assertTrue(changed.claim_inventory_started)
        self.assertEqual([True], notifications)
        with self.assertRaises(FrozenInstanceError):
            changed.connections_changed = False

    def test_settings_service_normalizes_missing_incomplete_and_invalid_configuration(self) -> None:
        from globalPlugins.NeovimAccessLink.settings_service import SettingsService

        diagnostics = []
        service = SettingsService(
            {},
            section_name="NeovimAccessLink",
            feedback_defaults={"global": 3, "mode": 3},
            focus_announcement_values=("none", "line", "context"),
            focus_announcement_default=2,
            record_diagnostic=lambda *args, **kwargs: diagnostics.append((args, kwargs)),
            on_connections_changed=lambda: False,
        )
        self.assertEqual({
            "connections": [],
            "feedback": {"global": 3, "mode": 3},
            "focusAnnouncement": 2,
        }, service.snapshot())
        self.assertTrue(diagnostics)

        normalized = service.normalize({
            "connections": [{"id": "incomplete"}],
            "feedback": {"global": 7},
            "focusAnnouncement": "line",
        })
        self.assertEqual([], normalized["connections"])
        self.assertEqual({"global": 3, "mode": 3}, normalized["feedback"])
        self.assertEqual(2, normalized["focusAnnouncement"])

    def test_profile_switch_notifies_only_for_changed_connections(self) -> None:
        from globalPlugins.NeovimAccessLink.settings_service import SettingsService

        root = {"NeovimAccessLink": {
            "connections": "[]",
            "focusAnnouncement": 2,
            "feedback": {"global": 3},
        }}
        notifications = []
        service = SettingsService(
            root,
            section_name="NeovimAccessLink",
            feedback_defaults={"global": 3},
            focus_announcement_values=("none", "line", "context"),
            focus_announcement_default=2,
            record_diagnostic=lambda *_args, **_kwargs: None,
            on_connections_changed=lambda: notifications.append(True) or True,
        )

        unchanged = service.reload()
        self.assertFalse(unchanged.connections_changed)
        root["NeovimAccessLink"]["connections"] = json.dumps([{
            "id": "work", "name": "Work", "host": "host", "user": "user",
            "port": 22, "identityFile": "", "authentication": "openSsh",
        }])
        changed = service.reload()

        self.assertTrue(changed.connections_changed)
        self.assertTrue(changed.claim_inventory_started)
        self.assertEqual([True], notifications)

    def test_settings_service_keeps_current_snapshot_when_persistence_fails(self) -> None:
        from globalPlugins.NeovimAccessLink.settings_service import SettingsService

        class FailingSection(dict):
            fail_writes = False

            def __setitem__(inner_self, key, value):
                if inner_self.fail_writes and key == "connections":
                    raise OSError("configuration unavailable")
                super().__setitem__(key, value)

        section = FailingSection(
            connections="[]",
            focusAnnouncement=2,
            feedback={"global": 3},
        )
        service = SettingsService(
            {"NeovimAccessLink": section},
            section_name="NeovimAccessLink",
            feedback_defaults={"global": 3},
            focus_announcement_values=("none", "line", "context"),
            focus_announcement_default=2,
            record_diagnostic=lambda *_args, **_kwargs: None,
            on_connections_changed=lambda: True,
        )
        before = service.snapshot()
        section.fail_writes = True

        with self.assertRaisesRegex(OSError, "configuration unavailable"):
            service.update({**before, "focusAnnouncement": 0})

        self.assertEqual(before, service.snapshot())

    def test_settings_read_uses_aggregated_section_items(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin
        import config

        class AggregatedSectionLike:
            def __init__(inner_self, values): inner_self.values = values
            def get(inner_self, key, default=None): return inner_self.values.get(key, default)
            def items(inner_self): return inner_self.values.items()
            def __iter__(inner_self): return iter(inner_self.values)

        feedback = AggregatedSectionLike({
            "global": 1, "mode": 2, "delete": 3, "replace": 3,
            "lineBoundary": 2, "fileBoundary": 3,
            "lineCrossed": 2, "matchingError": 3,
        })
        config.conf["NeovimAccessLink"] = AggregatedSectionLike({
            "connections": "[]",
            "focusAnnouncement": 1,
            "feedback": feedback,
        })

        plugin = GlobalPlugin()

        settings = self._settingsSnapshot(plugin)
        self.assertEqual(1, settings["feedback"]["global"])
        self.assertEqual(2, settings["feedback"]["mode"])
        self.assertEqual(1, settings["focusAnnouncement"])
        self.assertEqual([], settings["connections"])
        plugin.terminate()

    def test_braille_routing_sends_only_validated_cursor_control(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        plugin = GlobalPlugin()
        controls: list[tuple[str, dict]] = []
        plugin._client = types.SimpleNamespace(
            send_control=lambda kind, payload: controls.append((kind, payload)) or True,
            stop=lambda: None,
        )
        plugin._gate.manual_enabled = plugin._gate.authenticated = plugin._gate.nvim_active = True
        identity = plugin._identity(self.focus)
        plugin._gate.focused = plugin._gate.bound_terminal = identity
        plugin._currentState = {
            "bufferId": 1,
            "windowId": 1000,
            "changedtick": 9,
            "lineText": "\t界z",
            "tabstop": 4,
            "cursor": {"line": 3, "byteColumn": 0},
            "_transport": {"capabilities": ["cursorRouting"]},
        }
        region = StructuredLineRegion(self.focus)
        region.update()
        region.routeTo(4)
        self.assertEqual("routeCursor", controls[0][0])
        self.assertEqual(1, controls[0][1]["byteColumn"])
        plugin.terminate()

    def test_braille_routing_ignores_valid_state_without_confirmed_terminal_gate(self) -> None:
        from globalPlugins.NeovimAccessLink import GlobalPlugin, StructuredLineRegion

        plugin = GlobalPlugin()
        controls: list[tuple[str, dict]] = []
        plugin._client = types.SimpleNamespace(
            send_control=lambda kind, payload: controls.append((kind, payload)) or True,
            stop=lambda: None,
        )
        plugin._currentState = {
            "bufferId": 1,
            "windowId": 1000,
            "changedtick": 9,
            "lineText": "safe",
            "cursor": {"line": 1, "byteColumn": 0},
            "_transport": {"capabilities": ["cursorRouting"]},
        }
        region = StructuredLineRegion(self.focus)
        region.update()

        region.routeTo(0)

        self.assertEqual([], controls)
        plugin.terminate()


if __name__ == "__main__":
    unittest.main()
