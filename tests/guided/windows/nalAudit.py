"""Observe real NVDA and Terminal behavior from inside a disposable Windows guest."""
import ctypes
from ctypes import wintypes
import json
import os
import re
import sys
from pathlib import Path
import shutil
import subprocess
import time
import traceback

import addonHandler
import api
import braille
import buildVersion
import core
import config
import louisHelper
from comtypes import COMError
import globalPluginHandler
import inputCore
from speech.extensions import pre_speech
import textInfos
import winUser
import winsound
import UIAHandler
import wx

try:
    from braille.display import DisplayDimensions
    from braille.display.gesture import BrailleDisplayGesture
    from braille.extensions import filter_displayDimensions, pre_writeCells
except ModuleNotFoundError:
    from braille import BrailleDisplayGesture, DisplayDimensions, filter_displayDimensions, pre_writeCells

WORK = Path(os.environ["NAL_FOCUS_AUDIT"])
TERMINAL = Path(os.environ["NAL_FOCUS_TERMINAL"])
CMD = Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"


class AuditPanGesture(BrailleDisplayGesture):
    source = "nalAudit"
    model = None

    def __init__(self, name):
        self.id = name


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.steps = []
        self.speech = []
        self.cells = []
        self.braille_buffer_paths = []
        self.pending = ""
        self.expected_window_title = None
        self.dismissed_shell_overlay = False
        self.last_structured_line = None
        self.last_native_probe = None
        core.postNvdaStartup.register(self.start)

    @staticmethod
    def log(message):
        with (WORK / "steps.log").open("a", encoding="ascii", errors="backslashreplace") as handle:
            print(message, file=handle)

    def speech_output(self, speechSequence):
        self.speech.append("".join(item for item in speechSequence if isinstance(item, str)))

    def braille_output(self, cells, rawText):
        self.cells.append((tuple(cells), rawText or ""))
        if os.environ.get("NAL_FOCUS_GUIDED") == "lazy-p1":
            self.braille_buffer_paths.append(braille.handler.buffer is braille.handler.mainBuffer)

    def dimensions(self, _dimensions):
        guided = os.environ.get("NAL_FOCUS_GUIDED")
        native_completion = guided == "audio-c1" and os.environ.get("ACCESS_LINK_HUMAN_PROFILE") == "native"
        width = 80 if guided in {"held-d2", "lsp-l2", "lazy-p1"} or native_completion else 40
        return DisplayDimensions(numRows=1, numCols=width)

    def start(self):
        filter_displayDimensions.register(self.dimensions)
        pre_writeCells.register(self.braille_output)
        pre_speech.register(self.speech_output)
        try:
            from globalPlugins.NeovimAccessLink import GlobalPlugin as AccessLinkPlugin
            from globalPlugins.NeovimAccessLink.adapter_api import get_terminal_integration_service

            (addon,) = [item for item in globalPluginHandler.runningPlugins if isinstance(item, AccessLinkPlugin)]
            if not (any(item.name == "NeovimAccessLink" for item in addonHandler.getRunningAddons())):
                raise AssertionError('any(item.name == "NeovimAccessLink" for item in addonHandler.getRunningAddons())')
            self.service = get_terminal_integration_service()
            self.claims = addon._runtime.session_claim
            self.product_diagnostics = addon._runtime.diagnostics
            self.editor = shutil.which("nvim.exe")
            if not (self.editor):
                raise AssertionError('self.editor')
            scenario = {
                "1": self.guided_s1,
                "audio-c1": self.guided_c1_audio,
                "audio-d1": self.guided_d1_audio,
                "audio-d3": self.guided_external_diagnostics_audio,
                "audio-d4": self.guided_external_diagnostics_audio,
                "held-d2": self.guided_d2,
                "held-l3": self.guided_l3,
                "lsp-l1": self.guided_l1,
                "lsp-l2": self.guided_l2,
                "lsp-l4": self.guided_l4,
                "lsp-l5": self.guided_multi_buffer_operation,
                "lsp-l6": self.guided_multi_buffer_operation,
                "lazy-p1": self.guided_lazy_window,
                "lazy-p2": self.guided_lazy_operation,
                "lazy-p3": self.guided_lazy_operation,
                "lazy-p4": self.guided_lazy_operation,
            }.get(os.environ.get("NAL_FOCUS_GUIDED"), self.scenario)
            self.work = scenario()
            self.advance()
        except Exception:
            self.finish(False, traceback.format_exc())

    def advance(self):
        try:
            action = next(self.work)
        except StopIteration:
            self.finish(True)
        except Exception:
            self.finish(False, traceback.format_exc())
        else:
            self.pending, predicate = action
            self.log("NAL_WAIT " + self.pending)
            self.foreground_retry = time.monotonic() + 2
            self.deadline = time.monotonic() + 70
            wx.CallLater(100, self.check, predicate)

    def check(self, predicate):
        try:
            if predicate():
                self.steps.append(self.pending)
                self.log("NAL_PASS " + self.pending)
                self.advance()
                return
            if self.expected_window_title and time.monotonic() >= self.foreground_retry:
                self.foreground_retry = time.monotonic() + 4
                self.activate_window(self.expected_window_title)
            if not (time.monotonic() < self.deadline):
                raise AssertionError((self.pending, self.focus_details()))
            wx.CallLater(100, self.check, predicate)
        except Exception:
            self.finish(False, traceback.format_exc())

    def finish(self, ok, failure=None):
        result = {"ok": ok, "steps": self.steps, "pending": self.pending, "error": failure}
        result.update(terminal=TERMINAL.name, pythonOptimize=sys.flags.optimize, nvda=buildVersion.version)
        if not ok:
            result["lastStructuredLine"] = self.last_structured_line
            result["recentBraille"] = [text for _, text in self.cells[-6:]]
            result["nativeProbe"] = self.last_native_probe
            if os.environ.get("NAL_FOCUS_GUIDED", "").startswith(("audio-", "held-", "lsp-", "lazy-")):
                result["editorState"] = self.audio_editor_state()
                result["recentSpeech"] = self.speech[-8:]
            if os.environ.get("NAL_FOCUS_GUIDED") == "held-l3":
                result["recentBrailleCells"] = [cells for cells, _ in self.cells[-6:]]
        if hasattr(self, "diagnostic_audio"):
            result["diagnosticAudio"] = self.diagnostic_audio
            result["diagnosticCase"] = os.environ["ACCESS_LINK_HUMAN_TEST_ID"]
        if hasattr(self, "held_diagnostic_evidence"):
            result["heldDiagnosticEvidence"] = self.held_diagnostic_evidence
        if hasattr(self, "signature_evidence"):
            result["signatureEvidence"] = self.signature_evidence
        if hasattr(self, "completion_evidence"):
            result["completionEvidence"] = self.completion_evidence
        if hasattr(self, "lsp_evidence"):
            result["lspEvidence"] = self.lsp_evidence
        if hasattr(self, "focus_evidence"):
            result["focusEvidence"] = self.focus_evidence
        if hasattr(self, "lazy_evidence"):
            result["lazyEvidence"] = self.lazy_evidence
        if not ok and hasattr(self, "product_diagnostics") and os.environ.get("NAL_FOCUS_GUIDED") == "lazy-p1":
            entries = [json.loads(line) for line in self.product_diagnostics.report().splitlines()
                       if line.startswith("{")]
            fields = ("elapsedMs", "type", "mode", "bufferId", "windowId", "changedtick", "cursor", "lineText")
            result["lastProductEvents"] = [
                {field: entry[field] for field in fields if field in entry}
                for entry in entries if entry["category"] == "eventDispatch"
            ][-20:]
        report = WORK / "result.tmp"
        report.write_text(json.dumps(result), encoding="utf-8")
        report.replace(WORK / "result.json")
        pre_speech.unregister(self.speech_output)
        pre_writeCells.unregister(self.braille_output)
        filter_displayDimensions.unregister(self.dimensions)
        wx.CallLater(1200, core.triggerNVDAExit)

    def press(self, action):
        self.log("NAL_KEY " + action)

    def term(self, name, *arguments):
        return subprocess.Popen((str(TERMINAL), "--window", name, *map(str, arguments)),
                                cwd=TERMINAL.parent)

    def nvim(self, action, marker):
        init = WORK / "init.lua"
        if not init.exists():
            init.write_text(
                'vim.opt.loadplugins = false\n'
                'vim.opt.rtp:prepend(vim.env.NAL_FOCUS_RUNTIME)\n'
                'vim.cmd("runtime plugin/nvim_nvda.lua")\n',
                encoding="utf-8",
            )
        fixture = WORK / (marker[-1] + ".txt")
        fixture.write_text(marker + "\n", encoding="utf-8")
        self.term("NalPrimary", *action, "--inheritEnvironment", self.editor,
                  "-u", init, "-i", "NONE", "-n", fixture)

    def activate_window(self, title):
        hwnd = winUser.getTopWindow(0)
        for _ in range(250):
            if not hwnd:
                return
            if (
                winUser.isWindowVisible(hwnd)
                and winUser.getClassName(hwnd) == "CASCADIA_HOSTING_WINDOW_CLASS"
                and title in winUser.getWindowText(hwnd)
            ):
                before = winUser.getForegroundWindow()
                if (before and before != hwnd and winUser.getWindowText(before) == "Search"
                        and winUser.getClassName(before) == "Windows.UI.Core.CoreWindow"
                        and not self.dismissed_shell_overlay):
                    self.dismissed_shell_overlay = True
                    self.press("dismiss-shell-overlay")
                if before != hwnd:
                    winUser.setForegroundWindow(hwnd)
                foreground = winUser.getForegroundWindow()
                self.log(f"NAL_FOCUS window={hwnd} prior={before} foreground={foreground}")
                if foreground != hwnd:
                    # Foreground locking can reject an in-process Win32 request. A physical
                    # Alt+Tab from the isolated desktop follows the operating system's input path.
                    self.press("focus-switch")
                    return
                if self.terminal_focus() is None:
                    self.focus_terminal_control(hwnd)
                return
            try:
                hwnd = winUser.getWindow(hwnd, winUser.GW_HWNDNEXT)
            except OSError:
                return

    def focus_terminal_control(self, hwnd):
        try:
            handler = UIAHandler.handler
            automation = handler.clientObject
            window = automation.ElementFromHandle(hwnd)
            condition = automation.CreatePropertyCondition(UIAHandler.UIA_ClassNamePropertyId, "TermControl")
            target = window.FindFirstBuildCache(
                UIAHandler.TreeScope_Descendants, condition, handler.baseCacheRequest,
            )
            if target:
                native_focus = automation.GetFocusedElementBuildCache(handler.baseCacheRequest)
                if (
                    native_focus.cachedClassName == "TermControl"
                    and native_focus.cachedProcessId == winUser.getWindowThreadProcessID(hwnd)[0]
                ):
                    target = native_focus
                if target.CurrentHasKeyboardFocus:
                    title = winUser.getWindowText(hwnd)
                    tab = automation.CreatePropertyCondition(
                        UIAHandler.UIA_ControlTypePropertyId, UIAHandler.UIA_TabItemControlTypeId,
                    )
                    tabs = window.FindAllBuildCache(UIAHandler.TreeScope_Descendants, tab, handler.baseCacheRequest)
                    for index in range(tabs.length):
                        item = tabs.GetElement(index)
                        if item.cachedName and item.cachedName in title:
                            try:
                                item.SetFocus()
                            except COMError:
                                pass
                            break
                target.SetFocus()
                native_focus = automation.GetFocusedElementBuildCache(handler.baseCacheRequest)
                self.log(
                    f"NAL_UIA targetFocused={target.CurrentHasKeyboardFocus} "
                    f"rawFocusClass={native_focus.cachedClassName} observed={self.focus_details()}"
                )
                return
        except Exception as problem:
            self.log(f"NAL_UIA {type(problem).__name__}: {problem}")
        self.click_window(hwnd)

    @staticmethod
    def click_window(hwnd):
        # The Windows guest is disposable and its test window can be raised
        # for an actual pointer click. Keep the operating system's focus path.
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        user.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, wintypes.UINT)
        user.WindowFromPoint.argtypes = (wintypes.POINT,)
        user.WindowFromPoint.restype = wintypes.HWND
        rect = wintypes.RECT()
        if not user.GetWindowRect(hwnd, ctypes.byref(rect)):
            return
        user.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0013)
        x = min(rect.left + 240, rect.right - 20)
        y = min(rect.top + 140, rect.bottom - 20)
        pointed = user.WindowFromPoint(wintypes.POINT(x, y))
        if pointed and winUser.isDescendantWindow(hwnd, pointed):
            winUser.setCursorPos(x, y)
            winUser.mouse_event(0x0002, 0, 0, 0, 0)
            winUser.mouse_event(0x0004, 0, 0, 0, 0)
        user.SetWindowPos(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, 0x0013)

    @staticmethod
    def focus_details():
        obj = api.getFocusObject()
        hwnd = winUser.getForegroundWindow()
        element = getattr(obj, "UIAElement", None)
        return (
            hwnd, getattr(obj, "windowHandle", None), type(obj).__name__, winUser.getClassName(hwnd),
            winUser.getWindowText(hwnd), getattr(getattr(obj, "appModule", None), "appName", None),
            getattr(element, "cachedClassName", None), getattr(obj, "processID", None),
        )

    def terminal_focus(self):
        obj = api.getFocusObject()
        hwnd = winUser.getForegroundWindow()
        if not obj or not hwnd or winUser.getClassName(hwnd) != "CASCADIA_HOSTING_WINDOW_CLASS":
            return None
        if winUser.getWindowThreadProcessID(hwnd)[0] != getattr(obj, "processID", None):
            return None
        try:
            element = getattr(obj, "UIAElement", None)
            if element is None or element.cachedClassName != "TermControl" or not element.CurrentHasKeyboardFocus:
                return None
        except COMError:
            return None
        if obj.appModule.appName.lower() != "windowsterminal":
            raise AssertionError(obj.appModule.appName)
        return obj

    def native(self, different_from=None):
        obj = self.terminal_focus()
        if obj is None or obj == different_from:
            return False
        if not self.service.should_use_native_event(obj, "textChange"):
            return False
        called = []
        obj.appModule.event_textChange(obj, lambda: called.append(True))
        if not (called == [True]):
            raise AssertionError(called)
        return True

    def bound(self, marker):
        obj = self.terminal_focus()
        if obj is None or self.service.should_use_native_event(obj, "textChange"):
            return False
        plan = self.service.braille_plan(obj, report_spelling=False)
        self.last_structured_line = plan.source_line if plan else None
        if not plan or marker not in plan.source_line:
            return False
        called = []
        obj.appModule.event_textChange(obj, lambda: called.append(True))
        if not (not called):
            raise AssertionError('not called')
        return True

    def audio_editor_state(self):
        source = Path(os.environ["NAL_FOCUS_EDITOR_STATE"])
        try:
            return json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def audio_marker(self, name):
        marker = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"]) / f"{name}.wav"
        winsound.PlaySound(str(marker), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        self.log("NAL_AUDIO marker " + name)

    def guided_lsp_bound(self, case, marker="from typing import overload", pyright=True, first_line=True):
        self.expected_window_title = "NAL Editor A"
        required_editor = "pyright" if pyright else "native_editor"
        yield f"{case}_live_terminal_and_{required_editor}", lambda: (
            self.terminal_focus() is not None
            and self.expected_window_title in winUser.getWindowText(winUser.getForegroundWindow())
            and (editor := self.audio_editor_state()).get("filetype") == "python"
            and (not pyright or editor.get("attached"))
        )
        self.expected_window_title = None
        if first_line:
            self.press("guided-first-line")
        self.press("toggle")
        yield f"{case}_inventory_ready", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.press("guided-claim")
        yield f"{case}_claimed_python_editor", lambda: (
            self.audio_editor_state().get("filetype") == "python" and self.bound(marker)
        )

    def guided_l1(self):
        fixture = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"]) / "lsp_features.py"
        original = fixture.read_bytes()
        yield from self.guided_lsp_bound("l1")
        self.lsp_evidence = {"status": []}
        for phase, clients, expected in (
            ("enabled", ["pyright"], "LSP clients: pyright"),
            ("disabled", [], "No LSP client attached"),
        ):
            if phase == "disabled":
                self.press("lsp-stop")
                yield "l1_pyright_actually_detached", lambda: (
                    self.audio_editor_state().get("attached") is False
                    and not self.audio_editor_state().get("clients")
                )
            status_start = len(self.speech)
            before = self.audio_editor_state()
            if (before.get("clients") or []) != clients:
                raise AssertionError(before)
            self.press("lsp-query")
            yield f"l1_{phase}_native_status_spoken", lambda: any(
                " ".join(text.split()).casefold() == expected.casefold() for text in self.speech[status_start:]
            )
            until = time.monotonic() + 0.6
            yield f"l1_{phase}_status_observation_window", lambda: time.monotonic() >= until
            emitted = [text for text in self.speech[status_start:] if text.strip()]
            if [" ".join(text.split()).casefold() for text in emitted] != [expected.casefold()]:
                raise AssertionError(emitted)
            self.lsp_evidence["status"].append({"clients": clients, "speech": emitted})
        self.press("guided-exit")
        yield "l1_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if fixture.read_bytes() != original:
            raise AssertionError("L1 changed its fixture")

    def guided_l2(self):
        workspace = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        fixture = workspace / "lsp_features.py"
        original = fixture.read_bytes()
        disabled = (workspace / "lsp-hints-disabled.txt").exists()
        yield from self.guided_lsp_bound("l2")
        table = config.conf["braille"]["translationTable"]
        if table != "en-us-comp8-ext.utb":
            raise AssertionError(table)

        def parameter_speech(offset):
            return [text.strip() for text in self.speech[offset:] if text.strip().lower().startswith("parameter ")]

        def braille_source(line):
            dots, *_ = louisHelper.translate([table, "braille-patterns.cti"], line)
            frame = tuple(dots + [0] * (80 - len(dots)))
            return bool(self.cells) and self.cells[-1][0] == frame and self.cells[-1][1].strip() == line

        def has_parameter(offset, number, name):
            prefix = f"parameter {number} of 3: {name}:"
            return any(text.startswith(prefix) for text in parameter_speech(offset))

        self.lsp_evidence = {"hintsDisabled": disabled, "actions": []}
        for step, (key, args, number, name) in enumerate((
            ("lsp-query", "", 1, "price"),
            ("lsp-first-argument", "3.5, ", 2, "quantity"),
            ("lsp-second-argument", "3.5, 2, ", 3, "discount"),
            ("lsp-third-argument", "3.5, 2, 0.1", None, None),
        ), start=1):
            line = f"automatic_total = calculate_total({args})"
            previous = self.audio_editor_state()["signatureCompleted"]
            offset = len(self.speech)
            started = time.monotonic()
            self.press(key)
            yield f"l2_action_{step}_provider_response_and_source_cells", lambda: (
                (state := self.audio_editor_state()).get("mode") == "i"
                and state.get("line") == line and state.get("signatureCompleted", 0) > previous
                and braille_source(line)
                and (disabled or number is None or has_parameter(offset, number, name))
            )
            observation_seconds = round(time.monotonic() - started, 3)
            time_limit = time.monotonic() + 0.7
            yield f"l2_action_{step}_presentation_window", lambda: time.monotonic() >= time_limit
            speech = parameter_speech(offset)
            expected_count = 0 if disabled or number is None else 1
            if len(speech) != expected_count:
                raise AssertionError(speech)
            self.lsp_evidence["actions"].append({
                "key": key, "hints": speech, "observationSeconds": observation_seconds,
            })

        def move(key, label, expected):
            before = self.audio_editor_state()
            self.press(key)
            yield f"l2_{label}_provider_response_and_source_cells", lambda: (
                (state := self.audio_editor_state()).get("line") == line
                and state.get("signatureCompleted", 0) > before["signatureCompleted"]
                and expected(state["byteColumn"], before["byteColumn"]) and braille_source(line)
            )
            return self.audio_editor_state()["byteColumn"]

        first = line.index("3.5")
        offset = len(self.speech)
        column = self.audio_editor_state()["byteColumn"]
        for step in range(len("3.5, 2, 0.1")):
            if column < first + 3:
                break
            column = yield from move("lsp-previous-word", f"previous_word_{step}", lambda now, before: now < before)
        if column not in range(first, first + 3):
            raise AssertionError((line, column))
        deadline = time.monotonic() + 0.7
        yield "l2_return_price_hint", lambda: (
            time.monotonic() >= deadline and (disabled or has_parameter(offset, 1, "price"))
        )
        returned = parameter_speech(offset)
        if disabled and returned:
            raise AssertionError(returned)
        self.lsp_evidence["actions"].append({"key": "lsp-previous-word", "hints": returned})
        if column == first:
            yield from move("lsp-right", "center_first_argument", lambda now, before: now == before + 1)
        for direction, delta in (("left", -1), ("right", 1)):
            offset = len(self.speech)
            actual = yield from move(f"lsp-{direction}", direction, lambda now, before: now == before + delta)
            if actual not in range(first, first + 3):
                raise AssertionError(actual)
            time_limit = time.monotonic() + 0.8
            yield f"l2_{direction}_same_argument_window", lambda: time.monotonic() >= time_limit
            if parameter_speech(offset):
                raise AssertionError(parameter_speech(offset))
            self.lsp_evidence["actions"].append({"key": f"lsp-{direction}", "hints": [], "byteColumn": actual})
        self.press("guided-exit")
        yield "l2_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if fixture.read_bytes() != original:
            raise AssertionError("L2 changed its fixture on disk")

    def guided_l4(self):
        root = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        pattern = "calculate_tip"
        abort = (root / "l4-abort.txt").exists()
        names = ("lsp_features.py", "lsp_rename_consumer.py")
        originals = {name: (root / name).read_bytes() for name in names}
        lines = {name: raw.decode("utf-8").splitlines() for name, raw in originals.items()}
        results = [{"filename": name, "row": i, "column": line.index(pattern) + 1, "text": line}
                   for name in names for i, line in enumerate(lines[name], 1) if pattern in line]
        if len(results) != 4:
            raise AssertionError(results)
        yield from self.guided_lsp_bound("l4", pyright=False)
        self.lsp_evidence = {"quickfixSelections": [], "search": [], "prompts": [], "aborted": abort}

        def heard_since(offset, predicate):
            return [text for text in self.speech[offset:] if predicate(" ".join(text.split()))]

        def source_match(text):
            return any(item["text"].strip() in text for item in results[:2]) and "of 2" in text

        start = len(self.speech)
        self.press("l4-search")
        yield "l4_native_incremental_search_and_spoken_preview", lambda: (
            (state := self.audio_editor_state()).get("commandType") == "/"
            and state.get("commandText") == pattern
            and bool(heard_since(start, lambda text: text.startswith("search preview,") and source_match(text)))
        )
        self.lsp_evidence["search"].append({
            "command": self.audio_editor_state()["commandText"],
            "speech": heard_since(start, lambda text: text.startswith("search preview,")),
        })
        match_rows = []
        for name, key in (("accepted", "lsp-accept"), ("next", "l4-next-match")):
            start = len(self.speech)
            self.press(key)
            yield f"l4_{name}_native_match_and_spoken_location", lambda: (
                (state := self.audio_editor_state()).get("commandType") == ""
                and state.get("row") in {item["row"] for item in results[:2]} - set(match_rows)
                and bool(heard_since(start, lambda text: not text.startswith("search preview,") and source_match(text)))
            )
            match_rows.append(self.audio_editor_state()["row"])
            self.lsp_evidence["search"].append({
                "row": match_rows[-1], "speech": heard_since(start, source_match),
            })
        self.lsp_evidence["searchRows"] = match_rows

        quickfix_identity = None

        def result_position(index):
            state = self.audio_editor_state()
            quickfix = state.get("quickfix", {})
            identity = quickfix.get("id"), quickfix.get("window")
            return (
                quickfix.get("index") == index and quickfix.get("items") == results
                and all(identity) and identity[1] == state.get("activeWindow")
                and state.get("filetype") == "qf" and state.get("row") == index
                and (quickfix_identity is None or quickfix_identity == identity)
            )

        def result_speech(index):
            row = self.audio_editor_state().get("line", "")
            return " ".join(f"{row}, result {index} of 4".split())

        def observe_quickfix(label, offset, index, expected, optional=()):
            deadline = time.monotonic() + 0.65
            yield f"l4_{label}_speech_window", lambda: time.monotonic() >= deadline
            speech = [" ".join(text.split()) for text in self.speech[offset:] if text.strip()]
            presented = [text for text in speech if text in expected]
            if (
                not result_position(index) or len(presented) != 1
                or len(speech) != len(set(speech))
                or any(text not in expected and text not in optional for text in speech)
            ):
                raise AssertionError((index, expected, speech, self.audio_editor_state()))
            self.lsp_evidence["quickfixSelections"].append({
                "key": label, "index": index, "speech": speech,
            })

        start = len(self.speech)
        self.press("lsp-query")
        yield "l4_real_quickfix_list_and_spoken_count", lambda: (
            result_position(1)
            and bool(heard_since(start, lambda text: text == "quickfix, 4 results, result 1 of 4"))
        )
        quickfix = self.audio_editor_state()["quickfix"]
        quickfix_identity = quickfix["id"], quickfix["window"]
        self.lsp_evidence["quickfix"] = quickfix
        yield from observe_quickfix(
            "open", start, 1, ("quickfix, 4 results, result 1 of 4",),
            (f"quickfix, {result_speech(1)}",),
        )
        for direction, key, indexes, boundary in (
            ("next", "lsp-report", (2, 3, 4), "Already at the last Quickfix result."),
            ("previous", "l4-prev-result", (3, 2, 1), "Already at the first Quickfix result."),
        ):
            for index in indexes:
                item = results[index - 1]
                expected_line = item["text"].strip()
                start = len(self.speech)
                self.press(key)
                yield f"l4_{direction}_real_result_and_full_spoken_row_{index}", lambda: (
                    result_position(index)
                    and expected_line in self.audio_editor_state().get("line", "")
                    and bool(heard_since(start, lambda text: text in (
                        result_speech(index), f"quickfix, {result_speech(index)}",
                    )))
                )
                expected = result_speech(index)
                yield from observe_quickfix(
                    f"{direction}_{index}", start, index, (expected, f"quickfix, {expected}"),
                )
            start = len(self.speech)
            self.press(key)
            yield f"l4_{direction}_boundary", lambda: (
                result_position(indexes[-1]) and bool(heard_since(start, lambda text: text == boundary))
            )
            yield from observe_quickfix(f"{direction}_boundary", start, indexes[-1], (boundary,))

        operation_start = start = len(self.speech)
        self.press("l4-substitute")
        answers = ((0, "q"), (2, "q")) if abort else ((0, "y"), (1, "n"), (2, "a"))
        for index, answer in answers:
            item = results[index]
            prompt = "Replace this match? Y yes, N no, A all, Q quit, L last"
            spoken = f'{item["text"].strip()}, line {item["row"]}, column {item["column"]}, {prompt}'
            yield f"l4_native_and_spoken_prompt_{index + 1}", lambda: (
                (state := self.audio_editor_state()).get("mode") == "r?"
                and state.get("activeName") == item["filename"] and state.get("row") == item["row"]
                and state.get("byteColumn") == item["column"] - 1
                and bool(heard_since(start, lambda text: text == spoken))
            )
            if len(actual := heard_since(start, lambda text: text == spoken)) != 1:
                raise AssertionError(self.speech[start:])
            self.lsp_evidence["prompts"].append({"speech": actual[0], "answer": answer})
            start = len(self.speech)
            self.press(f"l4-answer-{answer}")

        target = {name: values.copy() for name, values in lines.items()}
        if not abort:
            for item in (results[0], *results[2:]):
                target[item["filename"]][item["row"] - 1] = item["text"].replace(pattern, "calculate_tip_checked")
        summary = "2 buffers changed; 2 changed buffers remain unsaved"

        def expected_edits():
            state = self.audio_editor_state()
            buffers = state.get("buffers", {})
            return state.get("mode") == "n" and set(buffers) == set(names) and all(
                buffers[name]["lines"] == target[name] and buffers[name]["modified"] == (not abort)
                for name in names
            )

        yield "l4_exact_changed_and_preserved_source_lines", lambda: (
            expected_edits() and (abort or bool(heard_since(start, lambda text: text.endswith(summary))))
        )
        deadline = time.monotonic() + 0.9
        yield "l4_aggregate_observation_window", lambda: time.monotonic() >= deadline
        summaries = heard_since(start, lambda text: text.endswith(summary))
        if len(summaries) != (0 if abort else 1):
            raise AssertionError(self.speech[start:])
        focus_output = heard_since(operation_start, lambda text: text.casefold().startswith(("file ", "window ", "tab ")))
        if focus_output:
            raise AssertionError(focus_output)
        self.lsp_evidence["summary"] = summaries
        self.lsp_evidence["buffers"] = self.audio_editor_state()["buffers"]
        self.press("guided-exit")
        yield "l4_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if any((root / name).read_bytes() != raw for name, raw in originals.items()):
            raise AssertionError("L4 saved the fixture on disk")

    def guided_multi_buffer_operation(self):
        root = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        case = os.environ["ACCESS_LINK_HUMAN_TEST_ID"].lower()
        rename = case == "l5"
        incomplete = (root / "lsp-missing-reference.txt").exists()
        names = ("lsp_features.py", "lsp_rename_consumer.py")
        originals = {name: (root / name).read_bytes() for name in names}
        replacement = "calculate_gratuity" if rename else "calculate_tip_buffered"
        initial_lines = {name: data.decode("utf-8").splitlines() for name, data in originals.items()}
        final_lines = {
            name: [line.replace("calculate_tip", replacement) for line in lines]
            for name, lines in initial_lines.items()
        }
        changed = {name for name in names if final_lines[name] != initial_lines[name]}
        if len(changed) != (1 if incomplete else 2):
            raise AssertionError(changed)
        yield from self.guided_lsp_bound(
            case, marker="calculate_tip" if rename else "from typing import overload",
            pyright=rename, first_line=not rename,
        )
        before = self.audio_editor_state()
        identity = before["activeBuffer"]

        def buffers_match(state, expected, unsaved):
            buffers = state.get("buffers", {})
            return set(buffers) == set(names) and all(
                buffers[name]["lines"] == expected[name] and buffers[name]["modified"] == (name in unsaved)
                for name in names
            )

        if not buffers_match(before, initial_lines, ()) or before["commandType"]:
            raise AssertionError(before)
        self.lsp_evidence = {"operation": "rename" if rename else "bufdo", "changedBuffers": sorted(changed),
                             "incomplete": incomplete, "reports": []}
        if rename:
            self.lsp_evidence["prompts"] = []
            if not before["line"][before["byteColumn"]:].startswith("calculate_tip"):
                raise AssertionError(before)
            for phase in ("cancel", "accept"):
                offset = len(self.speech)
                self.press("lsp-query")
                yield f"l5_{phase}_empty_native_prompt_and_announcement", lambda: (
                    (state := self.audio_editor_state()).get("commandType") == "@"
                    and state.get("commandText") == ""
                    and any("New Name:" in text for text in self.speech[offset:])
                )
                self.lsp_evidence["prompts"].append({
                    "phase": phase, "commandText": self.audio_editor_state()["commandText"],
                    "speech": [text for text in self.speech[offset:] if "New Name:" in text],
                })
                if phase == "cancel":
                    offset = len(self.speech)
                    self.press("lsp-cancel")
                    deadline = time.monotonic() + 0.7
                    yield "l5_cancel_preserves_both_buffers_without_rename", lambda: (
                        time.monotonic() >= deadline
                        and (state := self.audio_editor_state()).get("commandType") == ""
                        and state.get("renameCompleted") == before["renameCompleted"]
                        and state.get("activeBuffer") == identity
                        and buffers_match(state, initial_lines, ())
                    )
                    if any("rename completed" in text.casefold() for text in self.speech[offset:]):
                        raise AssertionError(self.speech[offset:])
                    self.lsp_evidence["cancelPreservedBuffers"] = True
            self.press("l5-name")
            yield "l5_typed_name_reaches_native_prompt", lambda: (
                self.audio_editor_state().get("commandText") == replacement
            )
        offset = len(self.speech)
        self.press("lsp-accept" if rename else "lsp-query")
        count = len(changed)
        summary = ("1 buffer changed; 1 changed buffer remains unsaved" if count == 1
                   else "2 buffers changed; 2 changed buffers remain unsaved")
        summary = f"{'rename completed' if rename else 'text replaced'}; {summary}"
        yield f"{case}_real_edit_and_aggregate_announcement", lambda: (
            buffers_match((state := self.audio_editor_state()), final_lines, changed)
            and (not rename or state.get("renameCompleted", 0) > before["renameCompleted"])
            and any(text.strip() == summary for text in self.speech[offset:])
        )
        deadline = time.monotonic() + 0.9
        yield f"{case}_aggregate_is_the_only_operation_announcement", lambda: time.monotonic() >= deadline
        after = self.audio_editor_state()
        emitted = [text.strip() for text in self.speech[offset:] if text.strip()]
        prompt_exit = {"normal mode", f"selected {replacement}"} if (
            rename and after.get("commandType") == "" and after.get("mode") == "n"
        ) else set()
        transitions = emitted[:-1]
        if (not emitted or emitted[-1] != summary or len(transitions) != len(set(transitions))
                or any(text not in prompt_exit for text in transitions)):
            raise AssertionError((emitted, after.get("mode"), after.get("commandType")))
        self.lsp_evidence["operationSpeech"] = emitted
        self.lsp_evidence["summary"] = emitted[-1]
        self.lsp_evidence["buffers"] = after["buffers"]
        position_fields = ("activeBuffer", "activeWindow", "row", "byteColumn", "cursorMoves",
                           "bufferEnters", "windowEnters")

        def stable_report_position(state):
            return all(state.get(field) == after[field] for field in position_fields)

        if rename:
            references = [(line, text) for line, text in enumerate(final_lines[names[1]], 1) if replacement in text]
            reports = [f"Renamed reference {i} of {len(references)}, line {line}: {text}"
                       for i, (line, text) in enumerate(references, 1)]
        elif incomplete:
            reports = ["The prepared buffer replacement is not fully visible."]
        else:
            reports = [f"Changed buffer {i} of 2, {name}: 2 occurrences of {replacement}"
                       for i, name in enumerate(names, 1)]
        for i, expected in enumerate(reports, 1):
            offset = len(self.speech)
            self.press("lsp-report")
            yield f"{case}_verified_f4_report_{i}", lambda: (
                any(text.strip() == expected for text in self.speech[offset:])
                and stable_report_position(state := self.audio_editor_state())
                and buffers_match(state, final_lines, changed)
            )
            deadline = time.monotonic() + 0.65
            yield f"{case}_verified_f4_report_{i}_output_window", lambda: time.monotonic() >= deadline
            actual = [text.strip() for text in self.speech[offset:] if text.strip()]
            state = self.audio_editor_state()
            if actual != [expected] or not stable_report_position(state) or not buffers_match(state, final_lines, changed):
                raise AssertionError((actual, state))
            self.lsp_evidence["reports"].append({
                "speech": actual[0], "position": {field: state[field] for field in position_fields},
            })
        if rename and after["activeBuffer"] != identity:
            raise AssertionError(after)
        self.press("guided-exit")
        yield f"{case}_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if any((root / name).read_bytes() != data for name, data in originals.items()):
            raise AssertionError("The operation saved a fixture on disk")

    def guided_open_lazy(self, case, filename, marker, initial_check):
        self.expected_window_title = "NAL Editor A"
        yield f"{case}_real_terminal_and_independent_initial_state", lambda: (
            self.terminal_focus() is not None
            and self.expected_window_title in winUser.getWindowText(winUser.getForegroundWindow())
            and self.audio_editor_state().get("activeName") == filename
            and initial_check()
        )
        self.expected_window_title = None
        self.press("guided-first-line")
        self.press("toggle")
        yield f"{case}_inventory_ready", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.press("guided-claim")
        yield f"{case}_claimed_isolated_fixture", lambda: self.bound(marker)
        initial_buffer = self.audio_editor_state()["activeBuffer"]
        offset = len(self.speech)
        self.press("lsp-query")
        yield f"{case}_real_lazy_window", lambda: (
            bool(self.audio_editor_state().get("lazyLines"))
            and any("Help (?)" in row for row in self.audio_editor_state()["lazyLines"])
        )
        return initial_buffer, offset

    def guided_lazy_window(self):
        root = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        fixture = root / "lazy-test.txt"
        original = fixture.read_bytes()
        marker = original.decode("utf-8").splitlines()[0]
        skipped = (root / "lazy-skip-operation.txt").exists()
        initial_buffer, offset = yield from self.guided_open_lazy("p1", fixture.name, marker, lambda: True)
        lazy_speech_start = offset
        opened = self.audio_editor_state()
        lines = opened["lazyLines"]
        window = opened["lazyWindow"]
        expected_context = (
            f"window {window['index']} of {window['count']}, lazy.nvim plugin manager, normal mode, on local"
        )
        command_pattern = r"\b[A-Za-z]+ \([A-Za-z?]\)"
        command_rows = [(row, re.findall(command_pattern, line)) for row, line in enumerate(lines, 1)]
        command_rows = [(row, labels) for row, labels in command_rows if labels]
        commands = [label for _, labels in command_rows for label in labels]
        if not commands or "Install (I)" not in commands or "Help (?)" not in commands:
            raise AssertionError(lines)

        def speech_with_labels(start, labels):
            return next((text for text in self.speech[start:] if all(label in text for label in labels)), None)

        yield "p1_native_command_bar_spoken_in_full", lambda: speech_with_labels(offset, commands) is not None
        opened_until = time.monotonic() + 0.65
        yield "p1_full_command_bar_output_window", lambda: time.monotonic() >= opened_until
        overview = [text for text in self.speech[offset:] if all(label in text for label in commands)]
        if len(overview) != 1:
            raise AssertionError(overview)
        opening_end = len(self.speech)
        self.lazy_evidence = {"overview": overview[0], "held": [], "rows": [],
                              "expansionSkipped": skipped, "expansion": []}

        def move_to(row, name):
            for step in range(len(lines)):
                current = self.audio_editor_state()["row"]
                if current == row:
                    return
                self.press("d2-next" if current < row else "d2-previous")
                yield f"p1_{name}_move_{step}", lambda: self.audio_editor_state().get("row") != current
            raise AssertionError((row, self.audio_editor_state()))

        command_row, lower_labels = command_rows[-1]
        upper_labels = re.findall(command_pattern, lines[command_row - 2])
        if not upper_labels:
            upper_labels = re.findall(r"[A-Za-z][A-Za-z.]+", lines[command_row - 2])
        if command_row < 2 or not upper_labels:
            raise AssertionError(("command rows", lines))
        yield from move_to(command_row, "command_bar")
        anchor = self.audio_editor_state()
        self.press("lazy-hold")
        for key, labels in (("d2-previous", upper_labels), ("d2-next", lower_labels)):
            offset = len(self.speech)
            self.press(key)
            yield f"p1_held_{key}_reads_native_line_without_cursor_motion", lambda: (
                speech_with_labels(offset, labels) is not None
                and all(self.audio_editor_state().get(field) == anchor[field]
                        for field in ("row", "byteColumn", "cursorMoves", "activeBuffer"))
            )
            self.lazy_evidence["held"].append({
                "key": key, "speech": speech_with_labels(offset, labels),
                "row": anchor["row"], "byteColumn": anchor["byteColumn"], "cursorMoves": anchor["cursorMoves"],
            })
        self.press("d2-release")

        spec = json.loads(Path(os.environ["ACCESS_LINK_HUMAN_LAZY_FIXTURE"]).read_text(encoding="utf-8"))
        table = config.conf["braille"]["translationTable"]
        if table != "en-us-comp8-ext.utb":
            raise AssertionError(table)

        def matches_braille(text, beginning, marker):
            display = text.rstrip() + " " + marker
            dots, *_ = louisHelper.translate([table, "braille-patterns.cti"], display)
            if len(dots) > 80:
                raise AssertionError(display)
            expected = tuple(dots + [0] * (80 - len(dots)))
            return (len(self.cells) > beginning and self.cells[-1][0] == expected
                    and self.cells[-1][1].rstrip() == display and self.braille_buffer_paths[-1])

        entries = spec["plugins"]
        if len(entries) < 2:
            raise AssertionError(entries)
        for entry in (*entries, entries[0]):
            name = entry["name"]
            row = next(i for i, line in enumerate(lines, 1) if name in line)
            start_cells = len(self.cells)
            start_speech = len(self.speech)
            yield from move_to(row, name)
            yield f"p1_{name}_collapsed_speech_and_main_braille", lambda: (
                speech_with_labels(start_speech, [name, "collapsed"]) is not None
                and matches_braille(lines[row - 1], start_cells, "+")
            )
            self.lazy_evidence["rows"].append({"row": row, "speech": speech_with_labels(start_speech, [name, "collapsed"]),
                                                "nativeText": lines[row - 1], "cells": self.cells[-1][0]})

        for expanded in ((False,) if skipped else (True, False)):
            status = "expanded" if expanded else "collapsed"
            offset = len(self.speech)
            start_cells = len(self.cells)
            deadline = time.monotonic() + 0.8
            if not skipped:
                self.press("lsp-accept")
            yield f"p1_{status}_verified_by_native_detail_and_main_braille", lambda: (
                (live := self.audio_editor_state()).get("row") == row
                and any(re.match(r"^\s*dir\s+", item) for item in live["lazyLines"][row:row + 1]) == expanded
                and (time.monotonic() >= deadline and self.cells[-1][1].endswith(" +") if skipped else (
                    speech_with_labels(offset, [status]) is not None
                    and matches_braille(live["lazyLines"][row - 1], start_cells, "-" if expanded else "+")
                ))
            )
            until = time.monotonic() + 0.65
            yield f"p1_{status}_stable_braille_output_window", lambda: time.monotonic() >= until
            live = self.audio_editor_state()
            if live.get("row") != row or (
                not skipped and not matches_braille(live["lazyLines"][row - 1], start_cells, "-" if expanded else "+")
            ):
                raise AssertionError((live, self.cells[-1]))
            if not all(self.braille_buffer_paths[start_cells:]):
                raise AssertionError("A transient NVDA Braille message hid the native plugin row")
            if skipped and any(text.rstrip().endswith(" -") for _, text in self.cells[start_cells:]):
                raise AssertionError("The omitted expansion produced an expanded Braille marker")
            spoken = [text for text in self.speech[offset:] if text.strip()]
            if spoken != ([] if skipped else [status]):
                raise AssertionError(spoken)
            self.lazy_evidence["expansion"].append({"expanded": expanded, "speech": spoken, "cells": self.cells[-1][0]})
        for opened in (True, False):
            self.press("lazy-help")
            yield f"p1_native_help_{'open' if opened else 'closed'}", lambda: (
                any("Keyboard Shortcuts" in row for row in self.audio_editor_state().get("lazyLines", [])) == opened
            )
        until = time.monotonic() + 0.65
        yield "p1_closed_help_output_window", lambda: time.monotonic() >= until
        unexpected = [
            text for index, text in enumerate(self.speech[lazy_speech_start:], lazy_speech_start)
            if marker in text or (
                text.strip().casefold().startswith(("file ", "window ", "tab "))
                and not (index < opening_end and text == expected_context)
            )
        ]
        if unexpected:
            raise AssertionError(unexpected)
        context = self.speech[lazy_speech_start:opening_end].count(expected_context)
        if context > 1:
            raise AssertionError("Repeated announcement of the Lazy window on opening")
        self.lazy_evidence["openingWindow"] = window
        self.lazy_evidence["openingContextCount"] = context
        self.press("lazy-close")
        yield "p1_closed_lazy_and_returned_to_fixture", lambda: (
            self.audio_editor_state().get("activeBuffer") == initial_buffer and self.bound(marker)
        )
        self.press("guided-exit")
        yield "p1_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if fixture.read_bytes() != original:
            raise AssertionError("The Lazy window card changed its fixture")

    def guided_lazy_operation(self):
        root = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        spec = json.loads(Path(os.environ["ACCESS_LINK_HUMAN_LAZY_FIXTURE"]).read_text(encoding="utf-8"))
        fixture = root / "lazy-test.txt"
        original = fixture.read_bytes()
        marker = original.decode("utf-8").splitlines()[0]
        case = os.environ["ACCESS_LINK_HUMAN_TEST_ID"].lower()
        skipped = (root / "lazy-skip-operation.txt").exists()
        initial = spec["initial"]
        expected = {item["name"]: item["expectedRevision"] for item in spec["plugins"]}
        expected.update((Path(path).name, None) for path in spec["absent"])
        if set(initial) != set(expected) or initial == expected:
            raise AssertionError(spec)

        def git_snapshot(phase):
            path = WORK / f"lazy-git-{phase}.json"
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}

        def git_matches(phase, revisions):
            actual = git_snapshot(phase)
            return actual == {
                name: {"revision": revision, "clean": True} if revision else None
                for name, revision in revisions.items()
            }

        def spoken_since(offset):
            return [" ".join(text.split()) for text in self.speech[offset:] if text.strip()]

        initial_buffer, _ = yield from self.guided_open_lazy(
            case, fixture.name, marker, lambda: git_matches("before", initial),
        )
        for name in sorted(initial):
            state = self.audio_editor_state()
            rows = [index for index, line in enumerate(state["lazyLines"], 1) if name in line]
            if not rows:
                raise AssertionError((name, state["lazyLines"]))
            row = rows[0]
            offset = len(self.speech)
            if state["row"] == row:
                self.press("d2-previous")
                yield f"{case}_{name}_leave_row_before_reading", lambda: self.audio_editor_state().get("row") != row
            for step in range(len(state["lazyLines"])):
                current = self.audio_editor_state()["row"]
                if current == row:
                    break
                self.press("d2-next" if current < row else "d2-previous")
                yield f"{case}_{name}_navigation_{step}", lambda: self.audio_editor_state().get("row") != current
            yield f"{case}_{name}_spoken_native_row", lambda: (
                self.audio_editor_state().get("row") == row
                and any(name in text for text in spoken_since(offset))
            )
        label = {"p2": "installation", "p3": "update", "p4": "synchronization"}[case]
        started = f"lazy.nvim plugin manager: {label} started"
        finished = f"lazy.nvim plugin manager: {label} finished; check the plugin manager for results"
        offset = len(self.speech)
        if not skipped:
            self.press("lazy-operation")
            yield f"{case}_operation_start_and_completion_spoken", lambda: (
                started in spoken_since(offset) and finished in spoken_since(offset)
            )
        cutoff = time.monotonic() + 1
        yield f"{case}_observe_extra_operation_announcements", lambda: time.monotonic() >= cutoff
        utterances = spoken_since(offset)
        if utterances != ([] if skipped else [started, finished]):
            raise AssertionError(utterances)
        self.log("NAL_GIT snapshot-after")
        yield f"{case}_independent_final_git_state", lambda: git_matches("after", initial if skipped else expected)
        offset = len(self.speech)
        self.press("lazy-verify")
        problems = []
        for name, revision in expected.items():
            if skipped and initial[name] != revision:
                issue = "still present" if revision is None else ("missing" if initial[name] is None else "revision mismatch")
                problems.append(f"{name} {issue}")
        def correct_verification(text):
            if skipped:
                return text.startswith("Lazy test state is not complete yet:") and all(issue in text for issue in problems)
            return (
                text.startswith("Installed at the expected Git revision:")
                and all(name in text for name, revision in expected.items() if revision)
                and all("Expected removal confirmed:" in text and name in text
                        for name, revision in expected.items() if not revision)
            )

        verification_step = "rejects_unchanged_repositories" if skipped else "confirms_the_observed_repositories"
        yield f"{case}_verification_{verification_step}", lambda: any(
            correct_verification(text) for text in spoken_since(offset)
        )
        until = time.monotonic() + 0.65
        yield f"{case}_verification_single_output_window", lambda: time.monotonic() >= until
        verification = spoken_since(offset)
        if len(verification) != 1 or not correct_verification(verification[0]):
            raise AssertionError(verification)
        self.lazy_evidence = {
            "case": case, "operationSkipped": skipped, "before": git_snapshot("before"),
            "after": git_snapshot("after"), "expected": expected,
            "operationSpeech": utterances, "verificationSpeech": verification,
        }
        self.press("lazy-close")
        yield f"{case}_closed_lazy_and_returned_to_fixture", lambda: (
            self.audio_editor_state().get("activeBuffer") == initial_buffer and self.bound(marker)
        )
        self.press("guided-exit")
        yield f"{case}_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if fixture.read_bytes() != original:
            raise AssertionError("The Lazy card changed its fixture")

    def guided_c1_audio(self):
        case = os.environ["ACCESS_LINK_HUMAN_TEST_ID"].lower()
        profile = os.environ["ACCESS_LINK_HUMAN_PROFILE"]
        native = profile == "native"
        original = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"]) / "lsp_features.py"
        contents = original.read_bytes()
        self.completion_evidence = {"case": case, "provider": profile, "selection": []}
        self.expected_window_title = "NAL Editor A"
        yield f"{case}_real_terminal_and_pyright_ready", lambda: (
            self.terminal_focus() is not None and self.audio_editor_state().get("attached")
            and self.expected_window_title in winUser.getWindowText(winUser.getForegroundWindow())
        )
        self.expected_window_title = None
        self.press("guided-first-line")
        self.press("toggle")
        yield f"{case}_inventory_ready", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.press("guided-claim")
        yield f"{case}_claimed_editor", lambda: self.bound("from typing import overload")
        self.press("c1-insert")
        yield f"{case}_actual_insert_position", lambda: (
            (editor := self.audio_editor_state()).get("mode") == "i"
            and editor.get("line") == "completion_probe = calculate_"
            and not editor["visible"]
        )

        self.audio_marker("begin")
        initial = self.audio_editor_state()
        self.press("c1-next")
        before_open = time.monotonic() + 0.75
        yield f"{case}_pre_menu_key_keeps_editor_state", lambda: (
            time.monotonic() >= before_open
            and (editor := self.audio_editor_state()).get("line") == initial["line"]
            and editor.get("byteColumn") == initial["byteColumn"] and editor.get("mode") == "i"
            and not editor["visible"]
        )
        self.audio_marker("before-open")
        self.press("c1-open")
        labels = {"calculate_total", "calculate_tax", "calculate_tip"}
        yield f"{case}_provider_popup_with_three_items", lambda: (
            (editor := self.audio_editor_state()).get("visible")
            and set(editor["items"]) == labels and len(editor["items"]) == 3
            and editor["selected"] == -1
        )
        ordered = self.audio_editor_state()["items"]
        self.completion_evidence["items"] = ordered
        before_selection = time.monotonic() + 0.75
        yield f"{case}_open_render_window", lambda: time.monotonic() >= before_selection
        self.audio_marker("before-selection")
        def selection_matches(index):
            state = self.audio_editor_state()
            return state.get("visible") and state.get("items") == ordered and state.get("selected") == index

        forward = (0, 1, 2, -1, 0) if native else (0, 1, 2)
        accepted = 2 if native else 1
        backward = (-1, accepted) if native else (accepted,)
        transitions = [("c1-next", index) for index in forward] + [("c1-previous", index) for index in backward]
        for step, (key, index) in enumerate(transitions, start=1):
            speech_start = len(self.speech)
            speech_prefix = ("No completion selected" if index == -1
                             else f"{ordered[index]}, {index + 1} of {len(ordered)}, function")
            self.press(key)
            yield f"{case}_provider_selection_{step}", lambda: (
                selection_matches(index) and any(
                    " ".join(text.split()).startswith(speech_prefix) for text in self.speech[speech_start:]
                )
            )
            spoken = next(text for text in self.speech[speech_start:]
                          if " ".join(text.split()).startswith(speech_prefix))
            self.completion_evidence["selection"].append({"index": index, "speech": spoken})
        before_accept = time.monotonic() + 0.75
        yield f"{case}_selection_render_window", lambda: time.monotonic() >= before_accept
        self.audio_marker("before-accept")
        cells_start = len(self.cells)
        self.press("c1-accept")
        line = f"completion_probe = {ordered[accepted]}()"
        def accepted_provider_text():
            editor = self.audio_editor_state()
            column = editor.get("byteColumn")
            if editor.get("line") != line or column != line.index(")") or editor["visible"] or not self.bound(line):
                return False
            self.completion_evidence["accepted"] = {
                "line": editor["line"], "byteColumn": column, "character": editor["line"][column],
            }
            return True

        yield f"{case}_provider_acceptance", accepted_provider_text
        if native:
            table = config.conf["braille"]["translationTable"]
            if table != "en-us-comp8-ext.utb":
                raise AssertionError(table)
            dots, *_ = louisHelper.translate([table, "braille-patterns.cti"], line)
            if not 0 < len(dots) <= 80:
                raise AssertionError(dots)
            expected_cells = tuple(dots + [0] * (80 - len(dots)))
            yield "c1_accepted_native_line_reaches_braille", lambda: any(
                text.strip() == line and cells == expected_cells
                for cells, text in self.cells[cells_start:]
            )
            cells, text = next(
                (cells, text) for cells, text in self.cells[cells_start:]
                if text.strip() == line and cells == expected_cells
            )
            state = self.audio_editor_state()
            column = state["byteColumn"]
            if state["line"] != line or column != line.index(")"):
                raise AssertionError((line, column, state))
            self.completion_evidence["accepted"].update(brailleText=text, cells=cells)
        mark_after = time.monotonic() + 1
        yield f"{case}_end_of_observation_window", lambda: time.monotonic() >= mark_after
        self.audio_marker("end")
        self.press("guided-exit")
        yield f"{case}_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if original.read_bytes() != contents:
            raise AssertionError("The completion fixture changed on disk")

    def guided_diagnostic_fixture(self, case):
        self.expected_window_title = "NAL Editor A"
        yield f"{case}_real_terminal_and_pyright_ready", lambda: (
            self.terminal_focus() is not None and self.audio_editor_state().get("attached")
        )
        self.expected_window_title = None
        self.press("toggle")
        yield f"{case}_inventory_ready", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.press("guided-claim")
        yield f"{case}_claimed_diagnostic_fixture", lambda: self.bound("from os import path, sep")
        self.press("d1-run")
        yield f"{case}_real_ruff_and_pyright_findings", lambda: (
            any("Diagnostics ready" in sequence for sequence in self.speech)
            and {item["source"].casefold() for item in self.audio_editor_state().get("diagnostics", ())}
            == {"ruff", "pyright"}
        )
        return self.audio_editor_state()["diagnostics"]

    def guided_d1_audio(self):
        original = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"]) / "diagnostics.py"
        original_content = original.read_bytes()
        native = yield from self.guided_diagnostic_fixture("d1")
        expected_ruff = json.loads(
            (Path(os.environ["NAL_FOCUS_GUIDED_ROOT"]) / "expected-ruff.json").read_text(encoding="utf-8"),
        )
        expected_locations = sorted((
            item["code"], item["location"]["row"], item["location"]["column"] - 1,
            item["end_location"]["row"], item["end_location"]["column"] - 1,
        ) for item in expected_ruff)
        actual_locations = sorted((
            item["code"], item["row"], item["byteColumn"], item["endRow"], item["endByteColumn"],
        ) for item in native if item["source"].casefold() == "ruff")
        if expected_locations != actual_locations:
            raise AssertionError((expected_locations, actual_locations))
        pyright_codes = {item["code"] for item in native if item["source"].casefold() == "pyright"}
        if pyright_codes != {
            "reportAssignmentType", "reportOperatorIssue", "reportUndefinedVariable", "reportUnknownArgumentType",
        }:
            raise AssertionError(pyright_codes)
        ordered = sorted(native, key=lambda item: (
            item["row"], item["byteColumn"], item["endRow"], item["endByteColumn"],
            item["severity"], item["source"].casefold(), item["code"],
        ))
        if ordered[0]["code"] != "F401" or ordered[-1]["code"] != "F821":
            raise AssertionError(ordered)

        actions = [("d1-current", 0), *[("d1-next", i) for i in range(1, len(ordered))],
                   ("d1-next", 0), ("d1-previous", len(ordered) - 1), ("d1-clean", None)]
        self.diagnostic_audio = []
        self.audio_marker("begin")
        for number, (key, index) in enumerate(actions, start=1):
            item = ordered[index] if index is not None else None
            row, column = (item["row"], item["byteColumn"]) if item else (2, 0)
            if item:
                severity = "error" if item["severity"] == 1 else "warning"
                utterance = f'{item["source"]}, {severity}, {item["code"]}, {item["message"]}, {index + 1} of {len(ordered)}, line {row}'
                covering = [
                    candidate["severity"] for candidate in ordered
                    if (candidate["row"], candidate["byteColumn"]) <= (row, column)
                    < (candidate["endRow"], candidate["endByteColumn"])
                ]
                cue = "error" if min(covering) == 1 else "warning"
            else:
                utterance = "no diagnostic"
                cue = "none"
            self.audio_marker("action")
            offset = len(self.speech)
            self.press(key)
            expected_speech = " ".join(utterance.casefold().split())
            yield f"d1_action_{number}_cursor_and_complete_speech", lambda: (
                (editor := self.audio_editor_state()).get("row") == row
                and editor.get("byteColumn") == column
                and expected_speech in (" ".join(text.casefold().split()) for text in self.speech[offset:])
            )
            deadline = time.monotonic() + 1
            yield f"d1_action_{number}_render_window", lambda: time.monotonic() >= deadline
            count = sum(" ".join(text.casefold().split()) == expected_speech for text in self.speech[offset:])
            if count != 1:
                raise AssertionError((number, utterance, self.speech[offset:]))
            self.diagnostic_audio.append({"key": key, "code": item["code"] if item else None,
                                          "row": row, "byteColumn": column, "cue": cue})

        self.audio_marker("end")
        self.press("guided-exit")
        yield "d1_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if original.read_bytes() != original_content:
            raise AssertionError("The diagnostic fixture changed on disk")

    def guided_external_diagnostics_audio(self):
        root = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        case = os.environ["ACCESS_LINK_HUMAN_TEST_ID"].lower()
        if case == "d3":
            fixture = root / "diagnostics.c"
            reference_path = root / "expected-clang.json"
            provider, display_name, severity, cue = "clang-tidy", "Clang-Tidy", 1, "error"
            keys = (("d1-current", 0), ("d1-next", 1), ("d1-next", 0), ("d1-previous", 1))
            count = 2
        else:
            fixture = root / "diagnostics.md"
            reference_path = root / "expected-markdown.json"
            provider, display_name, severity, cue = "markdownlint", "markdownlint", 2, "warning"
            keys = (("d1-current", 0), ("d1-next", 0))
            count = 1
        contents = fixture.read_bytes()
        first_line = contents.decode("utf-8").splitlines()[0]
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        if len(reference) != count:
            raise AssertionError(reference)
        self.expected_window_title = "NAL Editor A"
        yield f"{case}_real_terminal_and_fixture", lambda: (
            self.terminal_focus() is not None and self.audio_editor_state().get("activeName") == fixture.name
        )
        self.expected_window_title = None
        self.press("guided-first-line")
        yield f"{case}_native_editor_on_first_fixture_line", lambda: (
            (state := self.audio_editor_state()).get("row") == 1 and state.get("line") == first_line
        )
        initial = self.audio_editor_state()
        self.press("toggle")
        yield f"{case}_inventory_ready", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.press("guided-claim")
        yield f"{case}_claimed_fixture", lambda: self.bound(first_line)
        if case == "d3":
            offset = len(self.speech)
            self.press("d3-task")
            yield "d3_f2_announces_actual_task", lambda: any(
                text.lstrip().startswith(("Test ID D3.", "Access Link human test: Test ID D3."))
                for text in self.speech[offset:]
            )
        offset = len(self.speech)
        self.press("d1-run")
        waiting = f"Waiting for {display_name} diagnostics."
        ready = f"Diagnostics ready: {count} from {display_name}."
        yield f"{case}_runs_real_linter_and_reports_ready_without_editing", lambda: (
            waiting in (heard := "\n".join(self.speech[offset:]))
            and heard.find(ready) > heard.find(waiting)
            and len((state := self.audio_editor_state()).get("diagnostics", ())) == count
            and state.get("changedtick") == initial["changedtick"] and state.get("modified") is False
        )
        findings = sorted(self.audio_editor_state()["diagnostics"], key=lambda item: (item["row"], item["byteColumn"]))
        if [{field: item[field] for field in expected} for item, expected in zip(findings, reference)] != reference:
            raise AssertionError((reference, findings))
        if any(item["severity"] != severity or item["source"] != provider for item in findings):
            raise AssertionError(findings)

        self.diagnostic_audio = []
        self.audio_marker("begin")
        for number, (key, i) in enumerate(keys, start=1):
            item = reference[i]
            row, column = item["row"], item["byteColumn"]
            code = item.get("code")
            position = f"{i + 1} of {count}" if count > 1 else None
            expected = ", ".join(
                part for part in (provider, cue, code, item["message"], position, f"line {row}")
                if part
            )
            self.audio_marker("action")
            offset = len(self.speech)
            self.press(key)
            yield f"{case}_action_{number}_native_cursor_and_complete_speech", lambda: (
                (state := self.audio_editor_state()).get("row") == row
                and state.get("byteColumn") == column
                and state.get("changedtick") == initial["changedtick"] and state.get("modified") is False
                and expected in (" ".join(text.split()) for text in self.speech[offset:])
            )
            deadline = time.monotonic() + 1
            yield f"{case}_action_{number}_render_window", lambda: time.monotonic() >= deadline
            utterances = self.speech[offset:]
            spoken = [text for text in utterances if " ".join(text.split()) == expected]
            if len(spoken) != 1:
                raise AssertionError((number, expected, utterances))
            observed = self.audio_editor_state()
            if (
                (observed.get("row"), observed.get("byteColumn")) != (row, column)
                or observed.get("changedtick") != initial["changedtick"]
                or observed.get("modified") is not False
            ):
                raise AssertionError((number, observed))
            self.diagnostic_audio.append({
                "key": key, "code": code, "message": item["message"], "cue": cue,
                "row": observed["row"], "byteColumn": observed["byteColumn"],
                "observedSpeech": spoken[0], "changedtick": observed["changedtick"],
            })
        self.audio_marker("end")
        self.press("guided-exit")
        yield f"{case}_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if fixture.read_bytes() != contents:
            raise AssertionError("The linter fixture changed on disk")

    def guided_d2(self):
        findings = yield from self.guided_diagnostic_fixture("d2")
        ruff = sorted((item for item in findings if item["row"] == 1), key=lambda item: item["byteColumn"])
        expected_messages = ("\x60os.path\x60 imported but unused", "\x60os.sep\x60 imported but unused")
        if [(item["source"].casefold(), item["code"], item["message"]) for item in ruff] != [
            ("ruff", "F401", message) for message in expected_messages
        ]:
            raise AssertionError(ruff)
        table = config.conf["braille"]["translationTable"]
        if table != "en-us-comp8-ext.utb":
            raise AssertionError(table)
        self.cells.clear()
        self.press("d1-current")
        yield "d2_current_diagnostic_and_original_braille", lambda: (
            any("F401" in sentence and "os.path" in sentence for sentence in self.speech)
            and bool(self.cells) and self.cells[-1][1].strip() == "from os import path, sep"
        )
        baseline = self.cells[-1]
        if len(baseline[0]) != 80 or not any(baseline[0]):
            raise AssertionError(baseline)
        def cursor_position():
            state = self.audio_editor_state()
            return {key: state.get(key) for key in ("row", "byteColumn", "cursorMoves")}

        def output_frame(frame, position):
            return {"cells": frame[0], "text": frame[1], "cursor": position}

        cursor = cursor_position()
        self.held_diagnostic_evidence = {"initial": output_frame(baseline, cursor), "held": []}
        for name, action, index in (
            ("held_path", "d2-begin", 0), ("next_sep", "d2-next", 1), ("previous_path", "d2-previous", 0),
        ):
            display = f"warning, diagnostic {index + 1} of 2: {expected_messages[index]} | Source: ruff F401"
            dots, *_ = louisHelper.translate([table, "braille-patterns.cti"], display)
            if len(dots) > 80:
                raise AssertionError("D2 reference text does not fit the selected cell width")
            expected_frame = (tuple(dots + [0] * (80 - len(dots))), display)
            self.cells.clear()
            self.press(action)

            def held_frame_matches():
                position = cursor_position()
                frame = next((item for item in self.cells if item[0] == expected_frame[0]
                              and item[1].strip() == display), None)
                if frame is None or position != cursor:
                    return False
                self.held_diagnostic_evidence["held"].append({"key": action, **output_frame(frame, position)})
                return True

            yield f"d2_{name}_renders_complete_dot_pattern", held_frame_matches
        self.cells.clear()
        self.press("d2-release")

        def restored_frame_matches():
            position = cursor_position()
            if not self.cells or self.cells[-1] != baseline or position != cursor:
                return False
            self.held_diagnostic_evidence["restored"] = output_frame(self.cells[-1], position)
            return True

        yield "d2_key_up_restores_identical_braille_cells", restored_frame_matches
        self.cells.clear()
        self.press("d2-next")

        def native_move_matches():
            position = cursor_position()
            if (position["row"] != cursor["row"] + 1 or position["cursorMoves"] <= cursor["cursorMoves"]
                    or not self.cells or self.cells[-1][1].strip()):
                return False
            self.held_diagnostic_evidence["nativeMove"] = output_frame(self.cells[-1], position)
            return True

        yield "d2_same_key_without_modifier_moves_editor", native_move_matches
        self.press("guided-exit")
        yield "d2_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0

    def guided_l3(self):
        fixture = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"]) / "lsp_features.py"
        omit_first_pan = fixture.with_name("l3-no-pan.txt").exists()
        original = fixture.read_bytes()
        source = "total = calculate_total(3.5, 2, 0.1)"
        table = config.conf["braille"]["translationTable"]
        if table != "en-us-comp8-ext.utb":
            raise AssertionError(table)
        for name, command in (("right", "braille_scrollForward"), ("left", "braille_scrollBack")):
            inputCore.manager.userGestureMap.add(f"br(nalAudit):{name}", "globalCommands", "GlobalCommands", command)
        self.expected_window_title = "NAL Editor A"
        yield "l3_foreground_terminal_and_native_pyright_ready", lambda: (
            self.terminal_focus() is not None and self.audio_editor_state().get("attached")
        )
        self.expected_window_title = None
        self.press("l3-position")
        yield "l3_independent_pyright_signature_help", lambda: (
            (state := self.audio_editor_state()).get("line") == source
            and state.get("byteColumn") == source.index("calculate_total")
            and state.get("signatureHelp", {}).get("activeSignature") == 0
        )
        reference = self.audio_editor_state()["signatureHelp"]["signatures"]
        if len(reference) != 2 or any(
            len(item["parameters"]) != 3 or not item.get("documentation", {}).get("value")
            for item in reference
        ):
            raise AssertionError(reference)
        self.signature_evidence = {"nativePyright": reference, "observed": []}
        self.press("toggle")
        yield "l3_inventory_ready", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.press("guided-claim")
        yield "l3_claimed_editor_and_source_braille", lambda: (
            self.bound(source) and bool(self.cells) and self.cells[-1][1].strip() == source
        )

        def cursor_matches(anchor):
            state = self.audio_editor_state()
            return all(state.get(key) == anchor[key] for key in ("row", "byteColumn", "cursorMoves"))

        def presentation(name, action, sig_index, anchor, param_index=None, page=False):
            item = reference[sig_index]
            label = item["label"]
            if param_index is None:
                doc = item["documentation"]["value"]
                spoken = f"Signature {sig_index + 1} of {len(reference)}: {label}. Documentation: {doc}"
                display = f"S {sig_index + 1} of {len(reference)}: {label}. D: {doc}"
            else:
                parameters = item["parameters"]
                start, end = parameters[param_index]["label"]
                detail = f"{param_index + 1} of {len(parameters)}: {label[start:end]}"
                spoken, display = f"Parameter {detail}", f"P {detail}"
            dots, *_ = louisHelper.translate([table, "braille-patterns.cti"], display)
            width = 40
            windows = [tuple((dots[index:index + width] + [0] * width)[:width])
                       for index in range(0, len(dots), width)]
            snd = len(self.speech)
            offset = len(self.cells)
            self.press(action)
            yield f"l3_{name}_speech_cells_and_fixed_cursor", lambda: (
                bool(self.cells[offset:]) and self.cells[-1][0] == windows[0]
                and any(" ".join(utterance.split()) == spoken for utterance in self.speech[snd:])
                and cursor_matches(anchor)
            )
            frames = [self.cells[-1][0]]
            self.signature_evidence["observed"].append({
                "action": name, "speech": next(s for s in self.speech[snd:] if " ".join(s.split()) == spoken),
                "cells": frames, "cursor": [anchor["row"], anchor["byteColumn"], anchor["cursorMoves"]],
            })
            if page:
                if len(windows) < 3 or any(a == b for a, b in zip(windows, windows[1:])):
                    raise AssertionError(windows)
                for direction, indices in (("right", range(1, len(windows))),
                                           ("left", range(len(windows) - 2, -1, -1))):
                    for index in indices:
                        offset = len(self.cells)
                        if not (omit_first_pan and name == "name" and direction == "right" and index == 1):
                            inputCore.manager.executeGesture(AuditPanGesture(direction))
                        yield f"l3_{name}_pan_{direction}_{index + 1}", lambda: (
                            bool(self.cells[offset:]) and self.cells[-1][0] == windows[index]
                            and cursor_matches(anchor)
                        )
                        frames.append(self.cells[-1][0])

        for location, column in (("name", source.index("calculate_total")),
                                 ("repeat", source.index("calculate_total")),
                                 ("open", source.index("(")), ("close", source.index(")"))):
            if location in {"open", "close"}:
                self.press("l3-cycle")
                yield f"l3_native_cursor_on_{location}", lambda: (
                    self.audio_editor_state().get("byteColumn") == column
                    and bool(self.cells) and self.cells[-1][1].strip() == source
                )
            anchor = self.audio_editor_state()
            baseline = self.cells[-1]
            if anchor.get("line") != source or anchor.get("byteColumn") != column or baseline[1].strip() != source:
                raise AssertionError((location, anchor, baseline))
            yield from presentation(location, "l3-begin", 0, anchor, page=location == "name")
            if location == "name":
                for name, action, sig_index, param_index in (
                    ("first_price", "l3-next-parameter", 0, 0),
                    ("first_quantity", "l3-next-parameter", 0, 1),
                    ("first_discount", "l3-next-parameter", 0, 2),
                    ("second_signature", "d2-next", 1, None),
                    ("second_price", "l3-next-parameter", 1, 0),
                    ("second_quantity", "l3-next-parameter", 1, 1),
                    ("back_to_first", "d2-previous", 0, None),
                    ("first_price_reset", "l3-next-parameter", 0, 0),
                    ("back_to_second", "d2-next", 1, None),
                    ("second_price_via_previous", "l3-previous-parameter", 1, 0),
                ):
                    yield from presentation(name, action, sig_index, anchor, param_index,
                                            page=name == "second_signature")
            offset = len(self.cells)
            self.press("d2-release")
            yield f"l3_{location}_key_up_restores_source_cells", lambda: (
                bool(self.cells[offset:]) and self.cells[-1] == baseline and cursor_matches(anchor)
            )

        self.press("d2-next")
        yield "l3_same_key_with_modifier_up_moves_editor", lambda: (
            (state := self.audio_editor_state()).get("row") == anchor["row"] + 1
            and state.get("cursorMoves", 0) > anchor["cursorMoves"]
        )
        self.press("guided-exit")
        yield "l3_editor_exited_cleanly", lambda: self.audio_editor_state().get("exitCode") == 0
        if fixture.read_bytes() != original:
            raise AssertionError("L3 fixture changed on disk")

    def native_powershell(self, title, marker, previous=None):
        obj = self.terminal_focus()
        title_matches = title in winUser.getWindowText(winUser.getForegroundWindow())
        self.last_native_probe = {"terminalFocused": obj is not None, "titleMatches": title_matches}
        if obj is None or not title_matches:
            return False
        self.last_native_probe["sameNvdaObject"] = obj == previous
        native_events = self.service.should_use_native_event(obj, "textChange")
        self.last_native_probe["nativeEvents"] = native_events
        try:
            content = obj.makeTextInfo(textInfos.POSITION_ALL).text
        except COMError as error:
            self.last_native_probe["textError"] = error.hresult
            return False
        found_marker = marker in content
        self.last_native_probe["markerFoundInTerminal"] = found_marker
        return native_events and found_marker

    def guided_s1(self):
        title = "NAL Editor A"
        native_title = "NAL Unclaimed PowerShell"
        source_marker = "from typing import overload"
        self.expected_window_title = title
        yield "s1_actual_terminal_foreground", lambda: (
            self.terminal_focus() is not None
            and title in winUser.getWindowText(winUser.getForegroundWindow())
        )
        self.expected_window_title = None
        first = self.terminal_focus()
        original_hwnd = winUser.getForegroundWindow()
        fixture = Path(os.environ["NAL_FOCUS_GUIDED_ROOT"])
        omitted_f10 = (fixture / "s1-no-f10.txt").exists()
        self.focus_evidence = {"originalWindow": original_hwnd, "omittedF10": omitted_f10}
        self.press("guided-first-line")
        self.press("toggle")
        yield "s1_real_nvda_discovery", lambda: (
            self.claims.inventory_ready and any("F12" in sequence for sequence in self.speech)
        )
        self.cells.clear()
        self.press("guided-claim")
        yield "s1_physical_f12_pairs_guided_editor", lambda: self.bound(source_marker)
        yield "s1_editor_reaches_digital_braille", lambda: any(
            source_marker in text and len(cells) == 40 and any(cells) for cells, text in self.cells
        )

        self.expected_window_title = native_title
        self.press("guided-native-tab")
        yield "s1_unclaimed_powershell_gets_focus", lambda: (
            winUser.getForegroundWindow() == original_hwnd
            and self.native_powershell(native_title, "PS ", previous=first)
        )
        self.expected_window_title = None
        self.speech.clear()
        self.cells.clear()
        self.press("guided-new-tab-edit")
        yield "s1_unclaimed_tab_edits_native_input_at_caret", lambda: self.native_powershell(
            native_title, "auxnativeba", previous=first,
        )
        yield "s1_unclaimed_tab_updates_native_digital_braille", lambda: any(
            "auxnativeba" in text and len(cells) == 40 and any(cells) for cells, text in self.cells
        )
        if any(source_marker in text for _, text in self.cells) or any(source_marker in text for text in self.speech):
            raise AssertionError("The Neovim source line reached the output after the unclaimed tab obtained focus")

        self.expected_window_title = title
        self.press("guided-first-tab")
        yield "s1_original_terminal_control_recovers_focus", lambda: (
            winUser.getForegroundWindow() == original_hwnd
            and title in winUser.getWindowText(original_hwnd)
            and self.terminal_focus() is not None
        )
        self.expected_window_title = None
        # A pointer-based focus recovery can move the editor cursor. The card
        # checks session ownership, not preservation of the original position.
        self.press("guided-first-line")
        yield "s1_return_restores_bound_tab", lambda: (
            winUser.getForegroundWindow() == original_hwnd and self.bound(source_marker)
        )
        if omitted_f10:
            deadline = time.monotonic() + 0.8
            yield "s1_control_keeps_bound_editor", lambda: (
                time.monotonic() >= deadline and winUser.getForegroundWindow() == original_hwnd
                and self.bound(source_marker)
            )
            self.focus_evidence["editorStillBound"] = True
        else:
            self.press("guided-exit")
        yield "s1_guided_f10_restores_original_powershell", lambda: (
            winUser.getForegroundWindow() == original_hwnd and self.native_powershell(title, "PS ")
        )
        self.speech.clear()
        self.cells.clear()
        self.press("guided-returned-edit")
        yield "s1_restored_tab_edits_native_input_at_caret", lambda: self.native_powershell(title, "auxreturnba")
        yield "s1_restored_tab_updates_native_digital_braille", lambda: any(
            "auxreturnba" in text and len(cells) == 40 and any(cells) for cells, text in self.cells
        )
        if any(source_marker in text for _, text in self.cells) or any(source_marker in text for text in self.speech):
            raise AssertionError("The Neovim source line reached the output after guided F10 restored PowerShell")

    def scenario(self):
        if os.environ.get("NAL_FOCUS_PRESTART") != "1":
            self.nvim(("new-tab", "--title", "NAL Editor A", "--suppressApplicationTitle"), "nal editor A")
        self.expected_window_title = "NAL Editor A"
        yield "native_fallback_with_real_foreground", self.native
        self.expected_window_title = None
        a = self.terminal_focus()
        primary = winUser.getForegroundWindow()

        self.press("toggle")
        yield "real_nvda_gesture_discovers_neovim", lambda: self.claims.inventory_ready and any("F12" in text for text in self.speech)
        self.press("claim-a")
        yield "physical_f12_pairs_first_editor", lambda: self.bound("nal editor A")
        self.cells.clear()
        self.press("edit-a")
        yield "physical_edit_updates_structured_state", lambda: self.bound("nal editor Az")
        yield "physical_edit_updates_digital_braille", lambda: any(
            "nal editor Az" in text and len(cells) == 40 and any(cells) for cells, text in self.cells
        )

        self.nvim(("split-pane", "-V", "--title", "NAL Editor B", "--suppressApplicationTitle"), "nal editor B")
        yield "unbound_split_pane_uses_native", lambda: self.native(different_from=a)
        b = self.terminal_focus()
        if winUser.getForegroundWindow() != primary:
            raise AssertionError('a.windowHandle == b.windowHandle')
        self.press("claim-b")
        yield "physical_f12_pairs_second_pane", lambda: self.bound("nal editor B")
        self.term("NalPrimary", "move-focus", "left")
        yield "switch_back_to_first_pane", lambda: self.bound("nal editor Az")
        self.term("NalPrimary", "move-focus", "right")
        yield "switch_to_second_pane", lambda: self.bound("nal editor B")

        self.term(
            "NalPrimary", "new-tab", "--title", "NAL Native Tab", "--suppressApplicationTitle",
            CMD, "/d", "/k", "echo Native tab",
        )
        self.expected_window_title = "NAL Native Tab"
        yield "unbound_tab_uses_native", lambda: (
            winUser.getForegroundWindow() == primary
            and "NAL Native Tab" in winUser.getWindowText(primary)
            and self.native(different_from=b)
        )
        self.expected_window_title = None
        self.term("NalPrimary", "focus-tab", "--target", "0")
        self.expected_window_title = "NAL Editor B"
        yield "switch_back_to_bound_tab", lambda: self.bound("nal editor B")
        self.expected_window_title = None

        self.term("NalSecondary", "new-tab", "--title", "NAL Other Window", CMD, "/d", "/k", "echo Other window")
        self.expected_window_title = "NAL Other Window"
        yield "unbound_second_window_uses_native", lambda: (
            winUser.getForegroundWindow() != primary
            and "NAL Other Window" in winUser.getWindowText(winUser.getForegroundWindow())
            and self.native()
        )
        self.expected_window_title = None
        self.press("return")
        self.expected_window_title = "NAL Editor B"
        yield "foreground_switch_restores_first_window", lambda: (
            winUser.getForegroundWindow() == primary and self.bound("nal editor B")
        )
        self.expected_window_title = None
        self.press("close-editor")
        yield "closing_bound_editor_restores_remaining_pane", lambda: self.bound("nal editor Az")
        if not (braille.handler.displaySize == 40):
            raise AssertionError('braille.handler.displaySize == 40')
        self.log("NAL_METRIC speech_sequences={} braille_frames={}".format(len(self.speech), len(self.cells)))
