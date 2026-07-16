"""NVDA 2026.1 global plugin for structured Neovim accessibility."""

import json
import os
import sys
import threading
import time
import unicodedata
import array
from concurrent.futures import ThreadPoolExecutor, as_completed

import addonHandler
import api
import braille as nvdaBraille
import buildVersion
import controlTypes
import config
import globalPluginHandler
import globalVars
import queueHandler
import scriptHandler
import speech
import tones
import ui
from logHandler import log
from speech.priorities import SpeechPriority as NvdaSpeechPriority


_TERMINAL_LIFECYCLE_INTERVAL_MS = 5 * 60 * 1_000


def _windowIdentityExists(identity):
    """Return True/False for a conclusive HWND check, or None on uncertainty."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindow.argtypes = (wintypes.HWND,)
        user32.IsWindow.restype = wintypes.BOOL
        user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        if not user32.IsWindow(identity.window_handle):
            return False
        process_id = wintypes.DWORD()
        if not user32.GetWindowThreadProcessId(identity.window_handle, ctypes.byref(process_id)):
            return False
        return process_id.value == identity.process_id
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _terminalIdentityExists(identity, known_element=None):
    """Validate the exact WT tab; uncertainty is deliberately non-destructive."""
    window_exists = _windowIdentityExists(identity)
    if window_exists is False:
        return False
    if window_exists is None or not identity.runtime_id:
        return True
    if known_element is not None:
        try:
            if tuple(int(value) for value in known_element.getRuntimeId()) == identity.runtime_id:
                return True
        except Exception:
            pass
    try:
        import UIAHandler
        client = UIAHandler.handler.clientObject
        root = client.elementFromHandle(identity.window_handle)
        condition = client.createPropertyCondition(
            UIAHandler.UIA_RuntimeIdPropertyId,
            array.array("l", identity.runtime_id),
        )
        return bool(root.findFirst(UIAHandler.TreeScope_Subtree, condition))
    except Exception:
        # COM failure, unavailable handler, or a transient provider failure is
        # not proof that a tab was closed.
        return True

_PACKAGE_DIR = os.path.dirname(__file__)
_VENDOR_DIR = os.path.join(_PACKAGE_DIR, "vendor")
if _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

from .core.stdio_client import SshStdioClient
from .core.local_client import LocalTcpClient
from .core.clipboard import (
    MAX_CLIPBOARD_TEXT_BYTES, clipboard_result_state,
    valid_clipboard_text, valid_request_id,
)
from .core.braille import plan_braille, source_offset_for_expanded
from .core.diagnostics import DiagnosticBuffer
from .core.connection_profiles import (
    parse_profile, parse_profiles, remove_profile, save_profile, unique_profile_id,
)
from .core.connection_instances import ConnectionInstanceManager
from .core.connection_targets import ConnectionTarget, LOCAL_WINDOWS_TCP, local_windows_target
from .core.frontend_policy import FrontendPolicy
from .core.gate import SessionGate, TerminalIdentity
from .core.speech import Priority, SpeechPlanner
from .core.ssh_install import InstallResult, SshUserInstaller
from .core.ssh_sessions import SshSessionLister
from .core.local_install import LocalPluginInstaller
from .core.local_sessions import LocalSessionLister
from .suggestion_sounds import EditorSoundCache, SpellingSoundCache, SuggestionSoundCache

addonHandler.initTranslation()

_CODE_ADDON = addonHandler.getCodeAddon()
_ADDON_MANIFEST = _CODE_ADDON.manifest
_ADDON_ID = _ADDON_MANIFEST["name"]
_PRODUCT_NAME = _ADDON_MANIFEST["summary"]
try:
    from .build_info import ARTIFACT_VERSION as _ADDON_VERSION
except ImportError:
    _ADDON_VERSION = _ADDON_MANIFEST["version"]

_activePlugin = None


def getActivePlugin():
    """Return the add-on service instance for application-specific adapters."""
    return _activePlugin


def _linuxComponentConfig():
    fallback = {
        "format": 1,
        "sessionClaim": {"neovimKey": "<F12>", "nvdaGesture": "kb:f12"},
    }
    try:
        path = os.path.join(_PACKAGE_DIR, "resources", "linux-components.json")
        with open(path, "r", encoding="utf-8") as stream:
            value = json.load(stream)
        if not isinstance(value, dict):
            raise TypeError("component configuration must be an object")
        claim = value.get("sessionClaim", {})
        if not isinstance(claim, dict):
            raise TypeError("session claim configuration must be an object")
        neovim_key = claim.get("neovimKey", "")
        gesture = claim.get("nvdaGesture", "")
        if not (neovim_key.startswith("<F") and neovim_key.endswith(">")):
            raise ValueError("session claim key must be a function key")
        number = int(neovim_key[2:-1])
        if value.get("format") != 1 or not 1 <= number <= 24 or gesture != f"kb:f{number}":
            raise ValueError("inconsistent session claim gestures")
        return value
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return fallback


_LINUX_COMPONENT_CONFIG = _linuxComponentConfig()
_SESSION_CLAIM_GESTURE = _LINUX_COMPONENT_CONFIG["sessionClaim"]["nvdaGesture"]
_SESSION_CLAIM_KEY_NAME = _LINUX_COMPONENT_CONFIG["sessionClaim"]["neovimKey"].strip("<>")
_LOCAL_CLAIM_WAIT_SECONDS = 1.5
_LOCAL_CLAIM_POLL_SECONDS = 0.05
_MAX_PENDING_CLIPBOARD_REQUESTS = 32


def _frontendPolicy():
    fallback = {
        "format": 1,
        "frontends": [{
            "kind": "windowsTerminal", "status": "enabled",
            "appModule": "windowsterminal",
            "uiaClassNames": ["TermControl", "WPFTermControl"],
            "requiresRuntimeId": True,
        }],
    }
    try:
        path = os.path.join(_PACKAGE_DIR, "resources", "frontend-policy.json")
        with open(path, "r", encoding="utf-8") as stream:
            return FrontendPolicy.from_mapping(json.load(stream))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return FrontendPolicy.from_mapping(fallback)


_FRONTEND_POLICY = _frontendPolicy()

_FEEDBACK_DEFAULTS = {
    "global": 3, "mode": 3, "delete": 3, "replace": 3,
    "lineBoundary": 2, "fileBoundary": 3, "lineCrossed": 2, "matchingError": 3,
    "clipboard": 3,
}
_FEEDBACK_FOR_SOUND = {
    "delete": "delete", "replace": "replace",
    "lineStart": "lineBoundary", "lineEnd": "lineBoundary",
    "fileStart": "fileBoundary", "fileEnd": "fileBoundary",
    "lineCrossed": "lineCrossed", "matchingError": "matchingError",
}
_FOCUS_ANNOUNCEMENT_VALUES = ("none", "line", "context")
_FOCUS_ANNOUNCEMENT_DEFAULT = 2
_NVDA_CONFIG_SECTION = "nvimNvdaAccess"
_NATIVE_CONFIG_SCHEMA_VERSION = 5
_NVDA_CONFIG_SCHEMA_VERSION = 7
_NVDA_CONFIG_SPEC = {
    "schemaVersion": "integer(default=0, min=0)",
    "connections": 'string(default="[]")',
    "focusAnnouncement": f"integer(default={_FOCUS_ANNOUNCEMENT_DEFAULT}, min=0, max=2)",
    "feedback": {
        key: f"integer(default={value}, min=0, max=3)"
        for key, value in _FEEDBACK_DEFAULTS.items()
    },
}


def _registerNvdaConfigSpec():
    """Expose add-on settings to NVDA's native configuration-profile stack."""
    if _NVDA_CONFIG_SECTION not in config.conf.spec:
        config.conf.spec[_NVDA_CONFIG_SECTION] = _NVDA_CONFIG_SPEC


class StructuredLineRegion(nvdaBraille.Region):
    """Let NVDA translate and decorate one structured Neovim line."""

    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        self.focusToHardLeft = True

    def update(self):
        plugin = _activePlugin
        state = dict(plugin._currentState) if plugin is not None else {}
        formatting = config.conf.get("documentFormatting", {})
        state["reportSpellingBraille"] = bool(int(formatting.get("reportSpellingErrors2", 0)) & 4)
        plan = plan_braille(state)
        self._plan = plan
        self.rawText = plan.text
        self.cursorPos = plan.cursor
        self.selectionStart = plan.selection_start
        self.selectionEnd = plan.selection_end
        self.brailleSelectionStart = None
        self.brailleSelectionEnd = None
        super().update()

    def routeTo(self, braillePos):
        plugin = _activePlugin
        if plugin is None or not plugin._shouldSuppress(self.obj):
            return
        if not 0 <= braillePos < len(self.brailleToRawPos):
            plugin._diagnostics.record("brailleRouteRejected", reason="outOfRange", braillePos=braillePos)
            return
        expanded_offset = self.brailleToRawPos[braillePos]
        source_offset = source_offset_for_expanded(self._plan, expanded_offset)
        line = plugin._currentState.get("lineText", "")
        byte_column = len(line[:source_offset].encode("utf-8"))
        plugin._routeBrailleCursor(byte_column)


class StructuredTerminalBrailleOverlay:
    def _reportNewLines(self, lines):
        plugin = _activePlugin
        if plugin is not None and plugin._shouldSuppress(self):
            plugin._diagnostics.record("terminalLiveTextSuppressed", lineCount=len(lines))
            return
        return super()._reportNewLines(lines)

    def getBrailleRegions(self, review=False):
        plugin = _activePlugin
        if review or plugin is None or not plugin._shouldSuppress(self):
            raise NotImplementedError
        # Return a concrete iterable. A yield would turn this into a generator
        # and defer NotImplementedError until outside NVDA's fallback try block.
        return (StructuredLineRegion(self),)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _PRODUCT_NAME

    def __init__(self):
        global _activePlugin
        super().__init__()
        self._gate = SessionGate(_FRONTEND_POLICY.enabled_kinds)
        self._planner = SpeechPlanner()
        self._diagnostics = DiagnosticBuffer()
        self._suggestionSounds = SuggestionSoundCache(
            os.path.join(globalVars.appDir, "waves"),
            on_diagnostic=self._diagnostics.record,
        )
        self._spellingSound = SpellingSoundCache(
            os.path.join(globalVars.appDir, "waves"), on_diagnostic=self._diagnostics.record,
        )
        self._editorSounds = EditorSoundCache(
            os.path.join(globalVars.appDir, "waves"),
            os.path.join(_PACKAGE_DIR, "resources", "sounds"),
            on_diagnostic=self._diagnostics.record,
        )
        self._client = None
        self._lastConnectionState = None
        self._connected = False
        self._currentState = {}
        self._lastMode = None
        self._typedWord = []
        self._typedPosition = None
        self._menuDocumentation = ""
        self._menuItems = []
        self._settingsPanelClass = None
        self._sessionPasswords = {}
        self._sessionDiscoveryGeneration = 0
        self._instanceManager = ConnectionInstanceManager()
        self._rememberedTerminalBindings = set()
        self._rememberOfferInstances = set()
        self._authenticatedInstances = set()
        self._instanceTerminalPassthrough = {}
        self._activeInstanceId = None
        self._instanceRuntimeStates = {}
        self._pendingInstanceFullStates = {}
        self._focusContextRequestId = 0
        self._pendingFocusContexts = {}
        self._clipboardRequestId = 0
        self._pendingClipboardRequests = {}
        self._transportCapabilities = frozenset()
        self._pendingClaimTargets = {}
        self._claimGestureGeneration = 0
        self._pendingObservedClaim = None
        self._claimInventoryGeneration = 0
        self._claimInventoryReady = False
        self._claimBaselines = {}
        self._claimEligibleTargets = set()
        self._claimInventoryErrors = {}
        self._pendingMainThreadCalls = set()
        self._terminalLifecycleCall = None
        self._terminalLifecycleScheduledAt = 0.0
        self._terminalLifecycleMisses = {}
        self._focusedTerminalObject = None
        self._terminalIdentityElements = {}
        self._focusedAppModule = None
        _activePlugin = self
        _registerNvdaConfigSpec()
        settings = self._loadSettings()
        self._settings = settings
        config.post_configProfileSwitch.register(self._onNvdaConfigProfileSwitch)
        self._diagnostics.record(
            "addonStart",
            nvdaVersion=getattr(buildVersion, "version", "unknown"),
            configured=bool(settings.get("connections")),
        )
        log.info("%s %s initialized", _ADDON_ID, _ADDON_VERSION)
        self._installMenus()
        self._registerSettingsPanel()

    def _dispatchConfiguredTerminalScript(self, gesture, action_name):
        """Run a configurable command only for an exact Windows Terminal control.

        These scripts are global solely so NVDA can always expose them in the
        Input Gestures dialog.  They must not consume a user-assigned gesture
        in another application or mutate terminal focus state there.
        """
        try:
            obj = api.getFocusObject()
            app_module = getattr(obj, "appModule", None)
            descriptor = _FRONTEND_POLICY.descriptor("windowsTerminal")
            if (
                descriptor is None
                or getattr(app_module, "appName", None) != descriptor.app_module
            ):
                identity = None
            else:
                identity = self._identity(obj)
        except Exception as error:
            obj = None
            identity = None
            self._diagnostics.record(
                "configuredGestureFocusFailed",
                action=action_name,
                errorType=type(error).__name__,
            )
        if identity is None:
            self._diagnostics.record(
                "configuredGesturePassedThrough", action=action_name,
            )
            if gesture is not None:
                gesture.send()
            return
        self._refreshFocusedTerminalForAction(
            obj, app_module,
        )
        getattr(self, action_name)(gesture)

    @scriptHandler.script(
        description=_("Turn Neovim accessibility on or off and discover configured connections"),
        category=scriptCategory,
    )
    def script_toggleNeovimMode(self, gesture):
        self._dispatchConfiguredTerminalScript(gesture, "action_toggleNeovimMode")

    @scriptHandler.script(
        description=_("Read documentation for the selected Neovim completion item"),
        category=scriptCategory,
    )
    def script_readCompletionDocumentation(self, gesture):
        self._dispatchConfiguredTerminalScript(
            gesture, "action_readCompletionDocumentation",
        )

    @scriptHandler.script(
        description=_("Copy the active Neovim Visual selection to the Windows clipboard"),
        category=scriptCategory,
    )
    def script_copyNeovimSelection(self, gesture):
        self._dispatchConfiguredTerminalScript(gesture, "action_copyNeovimSelection")

    @scriptHandler.script(
        description=_("Copy Neovim's last yank to the Windows clipboard"),
        category=scriptCategory,
    )
    def script_copyLastNeovimYank(self, gesture):
        self._dispatchConfiguredTerminalScript(gesture, "action_copyLastNeovimYank")

    @scriptHandler.script(
        description=_("Paste Windows clipboard text into the active Neovim buffer"),
        category=scriptCategory,
    )
    def script_pasteWindowsClipboard(self, gesture):
        self._dispatchConfiguredTerminalScript(gesture, "action_pasteWindowsClipboard")

    @scriptHandler.script(
        description=_("Store Windows clipboard text in Neovim's unnamed register"),
        category=scriptCategory,
    )
    def script_setNeovimRegisterFromWindowsClipboard(self, gesture):
        self._dispatchConfiguredTerminalScript(
            gesture, "action_setNeovimRegisterFromWindowsClipboard",
        )

    @scriptHandler.script(
        description=_("Choose a server and connect this terminal to a new Neovim session"),
        category=scriptCategory,
    )
    def script_startConnectionInstance(self, gesture):
        self._dispatchConfiguredTerminalScript(gesture, "action_startConnectionInstance")

    @scriptHandler.script(
        description=_("Disconnect the selected Neovim connection instance"),
        category=scriptCategory,
    )
    def script_disconnectConnectionInstance(self, gesture):
        self._dispatchConfiguredTerminalScript(
            gesture, "action_disconnectConnectionInstance",
        )

    @scriptHandler.script(
        description=_("Forget the temporary Neovim connection for the focused terminal"),
        category=scriptCategory,
    )
    def script_forgetTemporaryTerminalBinding(self, gesture):
        self._dispatchConfiguredTerminalScript(
            gesture, "action_forgetTemporaryTerminalBinding",
        )

    def terminate(self):
        global _activePlugin
        for pending in tuple(self._pendingMainThreadCalls):
            try:
                pending.Stop()
            except Exception:
                pass
        self._pendingMainThreadCalls.clear()
        self._terminalLifecycleCall = None
        self._terminalLifecycleMisses.clear()
        self._gate.disable()
        config.post_configProfileSwitch.unregister(self._onNvdaConfigProfileSwitch)
        self._clearSessionPasswords()
        self._stopClient()
        try:
            self._instanceManager.stop_all()
        except Exception as error:
            self._diagnostics.record("connectionInstancesStopError", error=str(error))
        self._rememberedTerminalBindings.clear()
        self._terminalIdentityElements.clear()
        self._rememberOfferInstances.clear()
        self._authenticatedInstances.clear()
        self._instanceTerminalPassthrough.clear()
        self._instanceRuntimeStates.clear()
        self._pendingInstanceFullStates.clear()
        self._pendingFocusContexts.clear()
        self._pendingClipboardRequests.clear()
        self._pendingObservedClaim = None
        self._focusedTerminalObject = None
        self._focusedAppModule = None
        self._activeInstanceId = None
        self._removeMenus()
        self._unregisterSettingsPanel()
        self._suggestionSounds.close()
        self._spellingSound.close()
        self._editorSounds.close()
        _activePlugin = None
        self._diagnostics.record("addonStop")
        log.info("%s %s terminated", _ADDON_ID, _ADDON_VERSION)
        super().terminate()

    def _scheduleMainThreadCall(self, delay_ms, callback, *args):
        """Keep wx.CallLater alive until it runs or the add-on terminates."""
        import wx
        holder = [None]

        def invoke():
            pending = holder[0]
            if pending is not None:
                self._pendingMainThreadCalls.discard(pending)
            self._diagnostics.record(
                "delayedActionStarted", action=getattr(callback, "__name__", "unknown"),
            )
            callback(*args)

        pending = wx.CallLater(delay_ms, invoke)
        holder[0] = pending
        if pending is not None:
            self._pendingMainThreadCalls.add(pending)
        self._diagnostics.record(
            "delayedActionScheduled", action=getattr(callback, "__name__", "unknown"),
            delayMs=delay_ms,
        )
        return pending

    def _ensureTerminalLifecycleSweep(self):
        """Periodically notice closed WT tabs even when Neovim is otherwise idle."""
        if self._terminalLifecycleCall is not None or not self._instanceManager.list():
            return
        self._terminalLifecycleScheduledAt = time.monotonic()
        self._terminalLifecycleCall = self._scheduleMainThreadCall(
            _TERMINAL_LIFECYCLE_INTERVAL_MS, self._runTerminalLifecycleSweep,
        )

    def _runTerminalLifecycleSweep(self):
        self._terminalLifecycleCall = None
        # Some unit-test wx shims execute CallLater synchronously. Avoid a
        # recursive reschedule while retaining the real delayed behavior.
        elapsed_ms = (time.monotonic() - self._terminalLifecycleScheduledAt) * 1_000
        try:
            self._pruneClosedTerminalBindings()
        except Exception as error:
            # This maintenance task must never retain suppression or become a
            # repeating source of failures on NVDA's main thread.
            self._gate.disconnect()
            self._client = None
            self._diagnostics.record(
                "terminalLifecycleFailedOpen", errorType=type(error).__name__,
            )
            log.exception("terminal lifecycle sweep failed open")
            return
        if elapsed_ms >= _TERMINAL_LIFECYCLE_INTERVAL_MS / 2:
            self._ensureTerminalLifecycleSweep()

    def _chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if (
            getattr(obj, "role", None) == controlTypes.Role.TERMINAL
            and self._identity(obj) is not None
        ):
            clsList.insert(0, StructuredTerminalBrailleOverlay)

    def action_toggleNeovimMode(self, gesture):
        try:
            self._toggleNeovimMode()
        except Exception as error:
            self._gate.disable()
            self._stopClient()
            self._diagnostics.record("toggleError", errorType=type(error).__name__, error=str(error))
            log.exception("nvimNvdaAccess activation failed")
            ui.message(_("Neovim accessibility failed; normal terminal output restored"))

    def _toggleNeovimMode(self):
        identity = self._gate.focused
        if self._gate.manual_enabled:
            self._sessionDiscoveryGeneration += 1
            self._pendingObservedClaim = None
            self._gate.disable()
            self._planner.reset()
            self._resetTypedEcho()
            self._clearSessionPasswords()
            self._stopClient()
            ui.message(_("Neovim accessibility off"))
            self._queueBrailleRefresh(rebuild=True)
            self._diagnostics.record("manualMode", enabled=False)
            log.info("nvimNvdaAccess manual mode disabled")
            return
        if identity is None:
            ui.message(_("Neovim accessibility unavailable in this window"))
            return
        self._gate.manual_enabled = True
        self._planner.reset()
        self._resetTypedEcho()
        self._diagnostics.record("manualMode", enabled=True, terminal=self._identityFields(identity))
        log.info("nvimNvdaAccess manual mode requested")
        self._gate.focused = identity
        self._beginClaimInventory()
        if self._connected:
            self._gate.authenticated = True
            self._gate.nvim_active = True
            self._gate.bound_terminal = identity
            ui.message(_("Neovim accessibility on"))
            self._queueBrailleRefresh(rebuild=True)
        else:
            ui.message(_("Checking local and saved Neovim connections"))

    def _captureObservedSessionClaim(self, identity):
        """Authorize this physical F12 for exactly the focused WT control."""
        if (
            not self._gate.manual_enabled
            or identity is None
            or identity.frontend_kind != "windowsTerminal"
            or (
                not self._claimInventoryReady
                and identity not in self._pendingClaimTargets
                and self._instanceManager.selected_for(identity) is None
            )
        ):
            return None
        self._claimGestureGeneration += 1
        generation = self._claimGestureGeneration
        self._pendingObservedClaim = (identity, generation)
        self._diagnostics.record(
            "sessionClaimAuthorized", generation=generation,
            terminal=self._identityFields(identity),
        )
        return generation

    def _acceptObservedSessionClaim(self, identity, generation):
        if self._pendingObservedClaim != (identity, generation):
            return False
        self._pendingObservedClaim = None
        return self._gate.manual_enabled and self._gate.focused == identity

    def _promptForSessionClaim(self, profile, identity):
        self._diagnostics.record(
            "sessionClaimRequested", profileId=profile.identifier,
            terminal=self._identityFields(identity), key=_SESSION_CLAIM_KEY_NAME,
        )
        ui.message(_(
            "Neovim accessibility ready for {name}. Focus the desired Neovim session "
            "and press {key}"
        ).format(name=profile.name, key=_SESSION_CLAIM_KEY_NAME))

    def _automaticClaimProfiles(self):
        """Return profiles that can be inspected without opening a password dialog."""
        try:
            profiles = parse_profiles(self._settings.get("connections", []))
        except ValueError as error:
            self._diagnostics.record("claimInventoryConfigError", error=str(error))
            return []
        result = []
        seen = set()
        for profile in profiles:
            if (
                profile.authentication == "password"
                and profile.identifier not in self._sessionPasswords
            ):
                continue
            key = (
                profile.ssh_target, profile.port, profile.identity_file,
                profile.authentication,
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(profile)
        return result

    def _beginClaimInventory(self):
        self._claimInventoryGeneration += 1
        generation = self._claimInventoryGeneration
        self._claimInventoryReady = False
        profiles = self._automaticClaimProfiles()
        passwords = {
            profile.identifier: self._sessionPasswords.get(profile.identifier, "")
            for profile in profiles
        }
        threading.Thread(
            target=self._scanClaimTargets,
            args=(generation, profiles, passwords, True, None),
            name="nvim-nvda-claim-inventory", daemon=True,
        ).start()

    def _beginAutomaticClaimResolution(self, identity, local_claim_not_before_ns=0):
        self._claimInventoryGeneration += 1
        generation = self._claimInventoryGeneration
        profiles = [
            profile for profile in self._automaticClaimProfiles()
            if ("remoteSsh", profile.identifier) in self._claimEligibleTargets
        ]
        passwords = {
            profile.identifier: self._sessionPasswords.get(profile.identifier, "")
            for profile in profiles
        }
        baseline = dict(self._claimBaselines)
        threading.Thread(
            target=self._scanAutomaticClaimTargets,
            args=(
                generation, profiles, passwords, identity, baseline,
                local_claim_not_before_ns,
            ),
            name="nvim-nvda-claim-resolution", daemon=True,
        ).start()

    def _scanAutomaticClaimTargets(
        self, generation, profiles, passwords, identity, baseline,
        local_claim_not_before_ns=0,
    ):
        """Resolve a local claim without waiting for unrelated SSH probes.

        F12 reaches only the focused terminal.  Therefore a newly incremented
        local claim is already conclusive; scanning remote hosts afterwards
        would add latency and can make a second key press invalidate the first
        scan generation.  When no local claim changed, retain the existing
        parallel SSH resolution path.
        """
        def changed(sessions):
            return any(
                self._claimSequence(session) > baseline.get(
                    ("localWindowsTcp", "local-windows", session.identifier), 0,
                )
                or (
                    local_claim_not_before_ns > 0
                    and 0 <= session.claim_age_ms <= 15_000
                    and session.claimed_monotonic_ns >= local_claim_not_before_ns
                )
                for session in sessions
            )

        local_sessions, local_error, local_attempts = self._pollLocalSessions(changed)
        local_changed = local_error is None and changed(local_sessions)
        self._diagnostics.record(
            "automaticLocalClaimChecked", attempts=local_attempts,
            sessions=len(local_sessions), changed=local_changed,
            errorType=type(local_error).__name__ if local_error is not None else "",
        )
        local_result = (
            "localWindowsTcp", "local-windows", None, local_sessions, local_error,
        )
        if local_changed:
            queueHandler.queueFunction(
                queueHandler.eventQueue, self._finishAutomaticClaimResolution,
                generation, [local_result], identity, local_claim_not_before_ns,
            )
            return

        jobs = [("remoteSsh", profile.identifier, profile) for profile in profiles]

        def scan(profile):
            return SshSessionLister().list(
                profile.ssh_target, profile.port, profile.identity_file,
                password=passwords.get(profile.identifier, ""),
                askpass_path=self._askpassPath(),
            )

        results = [local_result]
        if jobs:
            workers = max(1, min(4, len(jobs)))
            with ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="nvim-nvda-claim-remote",
            ) as pool:
                futures = {
                    pool.submit(scan, profile): (kind, target_id, profile)
                    for kind, target_id, profile in jobs
                }
                for future in as_completed(futures):
                    kind, target_id, profile = futures[future]
                    try:
                        results.append((kind, target_id, profile, future.result(), None))
                    except Exception as error:
                        results.append((kind, target_id, profile, [], error))
        queueHandler.queueFunction(
            queueHandler.eventQueue, self._finishAutomaticClaimResolution,
            generation, results, identity,
        )

    @staticmethod
    def _pollLocalSessions(predicate):
        """Wait briefly for Neovim's atomic registry update on a worker thread."""
        deadline = time.monotonic() + _LOCAL_CLAIM_WAIT_SECONDS
        attempts = 0
        sessions = []
        while True:
            attempts += 1
            try:
                sessions = LocalSessionLister().list()
            except Exception as error:
                return [], error, attempts
            if predicate(sessions) or time.monotonic() >= deadline:
                return sessions, None, attempts
            time.sleep(_LOCAL_CLAIM_POLL_SECONDS)

    def _scanClaimTargets(self, generation, profiles, passwords, inventory, identity):
        jobs = [("localWindowsTcp", "local-windows", None)]
        jobs.extend(("remoteSsh", profile.identifier, profile) for profile in profiles)

        def scan(kind, _target_id, profile):
            if kind == "localWindowsTcp":
                return LocalSessionLister().list()
            return SshSessionLister().list(
                profile.ssh_target, profile.port, profile.identity_file,
                password=passwords.get(profile.identifier, ""),
                askpass_path=self._askpassPath(),
            )

        results = []
        workers = max(1, min(4, len(jobs)))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="nvim-nvda-scan") as pool:
            futures = {
                pool.submit(scan, kind, target_id, profile): (kind, target_id, profile)
                for kind, target_id, profile in jobs
            }
            for future in as_completed(futures):
                kind, target_id, profile = futures[future]
                try:
                    results.append((kind, target_id, profile, future.result(), None))
                except Exception as error:
                    results.append((kind, target_id, profile, [], error))
        queueHandler.queueFunction(
            queueHandler.eventQueue,
            self._finishClaimInventory if inventory else self._finishAutomaticClaimResolution,
            generation, results, identity,
        )

    @staticmethod
    def _claimSequence(session):
        value = getattr(session, "claim_sequence", 0)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    def _finishClaimInventory(self, generation, results, _identity=None):
        if generation != self._claimInventoryGeneration or not self._gate.manual_enabled:
            self._diagnostics.record("claimInventoryIgnored")
            return
        baselines = {}
        eligible = set()
        errors = {}
        for kind, target_id, _profile, sessions, error in results:
            target = (kind, target_id)
            if error is not None:
                errors[target] = str(error)
                continue
            eligible.add(target)
            for session in sessions:
                baselines[(kind, target_id, session.identifier)] = self._claimSequence(session)
        self._claimBaselines = baselines
        self._claimEligibleTargets = eligible
        self._claimInventoryErrors = errors
        self._claimInventoryReady = True
        configured = len(self._settings.get("connections", []))
        scanned_remote = len([item for item in results if item[0] == "remoteSsh"])
        automatic = len([target for target in eligible if target[0] == "remoteSsh"])
        local_sessions = sum(
            len(sessions) for kind, _target_id, _profile, sessions, error in results
            if kind == "localWindowsTcp" and error is None
        )
        remote_sessions = sum(
            len(sessions) for kind, _target_id, _profile, sessions, error in results
            if kind == "remoteSsh" and error is None
        )
        self._diagnostics.record(
            "claimInventoryReady", eligibleTargets=len(eligible), errors=len(errors),
            eligibleSessions=len(baselines),
            localSessions=local_sessions, remoteSessions=remote_sessions,
            automaticSshProfiles=automatic, scannedSshProfiles=scanned_remote,
            configuredSshProfiles=configured,
        )
        if errors and configured > scanned_remote:
            ui.message(_(
                "Neovim connections ready. Some saved connections could not be checked, "
                "and password connections require manual selection. Focus Neovim and press {key}"
            ).format(key=_SESSION_CLAIM_KEY_NAME))
        elif errors:
            ui.message(_(
                "Neovim connections ready. Some saved connections could not be checked. "
                "Focus Neovim and press {key}, or choose a connection manually"
            ).format(key=_SESSION_CLAIM_KEY_NAME))
        elif configured > scanned_remote:
            ui.message(_(
                "Neovim connections ready. Password connections require manual selection. "
                "Focus Neovim and press {key}"
            ).format(key=_SESSION_CLAIM_KEY_NAME))
        else:
            ui.message(_(
                "Neovim connections ready. Focus Neovim and press {key}"
            ).format(key=_SESSION_CLAIM_KEY_NAME))

    def _finishAutomaticClaimResolution(
        self, generation, results, identity, local_claim_not_before_ns=0,
    ):
        if (
            generation != self._claimInventoryGeneration
            or not self._gate.manual_enabled or self._gate.focused != identity
        ):
            self._diagnostics.record("automaticClaimResolutionIgnored")
            return
        candidates = []
        new_baselines = dict(self._claimBaselines)
        for kind, target_id, profile, sessions, error in results:
            if error is not None:
                self._diagnostics.record(
                    "automaticClaimTargetError", targetKind=kind, targetId=target_id,
                    errorType=type(error).__name__, error=str(error),
                )
                continue
            current_keys = set()
            for session in sessions:
                key = (kind, target_id, session.identifier)
                current_keys.add(key)
                sequence = self._claimSequence(session)
                previous = self._claimBaselines.get(key, 0)
                fresh_local_claim = (
                    kind == "localWindowsTcp"
                    and local_claim_not_before_ns > 0
                    and 0 <= session.claim_age_ms <= 15_000
                    and session.claimed_monotonic_ns >= local_claim_not_before_ns
                )
                if sequence > previous or fresh_local_claim:
                    candidates.append((kind, profile, session))
                new_baselines[key] = sequence
            for key in list(new_baselines):
                if key[:2] == (kind, target_id) and key not in current_keys:
                    del new_baselines[key]
        self._claimBaselines = new_baselines
        self._diagnostics.record(
            "automaticClaimResolutionCompleted", candidates=len(candidates),
            targets=len(results),
        )
        if not candidates:
            return
        if len(candidates) == 1:
            self._connectAutomaticClaim(identity, candidates[0])
            return
        self._showAutomaticClaimChoice(generation, identity, candidates)

    def _connectAutomaticClaim(self, identity, candidate):
        kind, profile, session = candidate
        if kind == "localWindowsTcp":
            if not self._reuseLocalSession(identity, session, offer_remember=True):
                self._startLocalSession(identity, session, replace_existing=True, offer_remember=True)
            return
        if self._reuseClaimedSession(profile, identity, session, offer_remember=True):
            return
        self._startDiscoveredSession(profile, identity, session, True, True)

    def _showAutomaticClaimChoice(self, generation, identity, candidates):
        import gui
        import wx
        labels = []
        for kind, profile, session in candidates:
            target = _("This computer") if kind == "localWindowsTcp" else profile.name
            labels.append(_("{target}: {session}").format(
                target=target, session=self._remoteSessionLabel(session),
            ))
        dialog = wx.SingleChoiceDialog(
            gui.mainFrame,
            _("More than one Neovim session confirmed F12. Select the intended session."),
            _("Select Neovim session"), labels,
        )
        ui.message(_("Multiple Neovim sessions confirmed F12; opening session selection"))

        def finish(result):
            if (
                result != wx.ID_OK or generation != self._claimInventoryGeneration
                or not self._gate.manual_enabled or self._gate.focused != identity
            ):
                return
            selection = dialog.GetSelection()
            if 0 <= selection < len(candidates):
                self._connectAutomaticClaim(identity, candidates[selection])

        gui.runScriptModalDialog(dialog, finish)

    def action_copyDiagnosticReport(self, gesture):
        report = self._diagnostics.report({
            "addonVersion": _ADDON_VERSION,
            "nvdaVersion": getattr(buildVersion, "version", "unknown"),
            "manualEnabled": self._gate.manual_enabled,
            "suppressionActive": self._gate.suppression_active,
            "connected": self._connected,
        }, product_name=_PRODUCT_NAME)
        if api.copyToClip(report):
            ui.message(_("Neovim diagnostic report copied"))
        else:
            ui.message(_("Could not copy Neovim diagnostic report"))

    def action_copyNeovimSelection(self, gesture):
        self._requestNeovimCopy("visualSelection")

    def action_copyLastNeovimYank(self, gesture):
        self._requestNeovimCopy("yankRegister")

    def action_pasteWindowsClipboard(self, gesture):
        context = self._clipboardControlContext()
        if context is None:
            return
        identity, instance_id, client, state, expected = context
        if state.get("mode") not in {"normal", "insert"} or state.get("modeBlocking") is True:
            self._clipboardFailure(_("Paste is available only in Normal or Insert mode"))
            return
        if (
            state.get("buftype", "") != "" or state.get("modifiable") is not True
            or state.get("readonly") is True or state.get("fileManager")
        ):
            self._clipboardFailure(_("The current Neovim buffer cannot be edited by this command"))
            return
        text = self._readWindowsClipboardText()
        if text is None:
            return
        request_id = self._nextClipboardRequestId()
        payload = {**expected, "requestId": request_id, "text": text}
        self._rememberClipboardRequest(request_id, (
            instance_id, identity, "pasteTextRequest",
        ))
        accepted = client.send_control("pasteTextRequest", payload)
        if not accepted:
            self._pendingClipboardRequests.pop(request_id, None)
            self._clipboardFailure(_("Could not send text to the active Neovim session"))
        self._diagnostics.record(
            "clipboardPasteRequested", requestId=request_id, accepted=accepted,
            bytes=len(text.encode("utf-8")),
        )

    def action_setNeovimRegisterFromWindowsClipboard(self, gesture):
        context = self._clipboardControlContext()
        if context is None:
            return
        identity, instance_id, client, _state, expected = context
        text = self._readWindowsClipboardText()
        if text is None:
            return
        request_id = self._nextClipboardRequestId()
        payload = {**expected, "requestId": request_id, "text": text}
        self._rememberClipboardRequest(request_id, (
            instance_id, identity, "setRegisterRequest",
        ))
        accepted = client.send_control("setRegisterRequest", payload)
        if not accepted:
            self._pendingClipboardRequests.pop(request_id, None)
            self._clipboardFailure(_("Could not send text to the active Neovim session"))
        self._diagnostics.record(
            "clipboardRegisterRequested", requestId=request_id, accepted=accepted,
            bytes=len(text.encode("utf-8")),
        )

    def _readWindowsClipboardText(self):
        try:
            text = api.getClipData()
        except Exception as error:
            self._diagnostics.record(
                "clipboardReadFailed", errorType=type(error).__name__,
            )
            self._clipboardFailure(_("Could not read text from the Windows clipboard"))
            return None
        if not valid_clipboard_text(text):
            reason = (
                "tooLarge"
                if isinstance(text, str)
                and len(text.encode("utf-8", "ignore")) > MAX_CLIPBOARD_TEXT_BYTES
                else "emptyOrInvalid"
            )
            self._diagnostics.record("clipboardTextRejected", reason=reason)
            self._clipboardFailure(_("The Windows clipboard does not contain supported text"))
            return None
        return text

    def _requestNeovimCopy(self, source):
        context = self._clipboardControlContext()
        if context is None:
            return
        identity, instance_id, client, state, expected = context
        if source == "visualSelection" and state.get("modeRaw") not in {"v", "V", "\x16"}:
            self._clipboardFailure(_("Select text in Neovim Visual mode before copying"))
            return
        request_id = self._nextClipboardRequestId()
        payload = {**expected, "requestId": request_id, "source": source}
        self._rememberClipboardRequest(request_id, (
            instance_id, identity, "copyTextRequest",
        ))
        accepted = client.send_control("copyTextRequest", payload)
        if not accepted:
            self._pendingClipboardRequests.pop(request_id, None)
            self._clipboardFailure(_("Could not request text from the active Neovim session"))
        self._diagnostics.record(
            "clipboardCopyRequested", requestId=request_id, source=source, accepted=accepted,
        )

    def _clipboardControlContext(self):
        identity = self._gate.focused
        selected = self._instanceManager.selected_for(identity) if identity else None
        if (
            identity is None or selected is None or self._client is None
            or selected.identifier != self._activeInstanceId
            or not self._gate.suppression_active
        ):
            self._clipboardFailure(_("No active Neovim session is bound to this terminal"))
            return None
        if "clipboardTransfer" not in self._transportCapabilities:
            self._clipboardFailure(_("The connected Neovim components do not support copy and paste"))
            return None
        state = self._currentState
        expected = {
            "bufferId": state.get("bufferId"),
            "windowId": state.get("windowId"),
            "tabpageId": state.get("tabpageId"),
            "changedtick": state.get("changedtick"),
            "modeRaw": state.get("modeRaw"),
        }
        if (
            any(
                not isinstance(expected[name], int) or isinstance(expected[name], bool)
                for name in ("bufferId", "windowId", "tabpageId", "changedtick")
            )
            or not isinstance(expected["modeRaw"], str)
        ):
            self._clipboardFailure(_("The active Neovim state is incomplete; try again"))
            return None
        return identity, selected.identifier, self._client, state, expected

    def _nextClipboardRequestId(self):
        self._clipboardRequestId = (self._clipboardRequestId + 1) % 2_147_483_648
        return self._clipboardRequestId

    def _rememberClipboardRequest(self, request_id, request):
        while len(self._pendingClipboardRequests) >= _MAX_PENDING_CLIPBOARD_REQUESTS:
            discarded_id = next(iter(self._pendingClipboardRequests))
            self._pendingClipboardRequests.pop(discarded_id, None)
            self._diagnostics.record(
                "clipboardRequestDiscarded", requestId=discarded_id, reason="queueLimit",
            )
        self._pendingClipboardRequests[request_id] = request

    def _clipboardSuccess(self, message):
        mode = self._feedbackMode("clipboard")
        if mode & 2:
            tones.beep(660, 25)
        if mode & 1:
            speech.speakText(message, priority=NvdaSpeechPriority.NEXT)

    def _clipboardFailure(self, message):
        if self._feedbackMode("clipboard") & 2:
            tones.beep(220, 35)
        # Failures remain audible even if optional action feedback is off.
        ui.message(message)

    def action_readCompletionDocumentation(self, gesture):
        if self._menuDocumentation:
            speech.speakText(self._menuDocumentation, priority=NvdaSpeechPriority.NOW)
        else:
            ui.message(_("No completion documentation available"))

    def action_startConnectionInstance(self, gesture):
        identity = self._gate.focused
        if identity is None:
            return
        import gui
        import wx
        if not self._gate.manual_enabled:
            ui.message(_("Activate Neovim accessibility before connecting a terminal"))
            return
        profiles = self._settings.get("connections", [])
        choices = [_("This computer - local Neovim")]
        choices.extend(profile.get("name", "") for profile in profiles)
        profile_dialog = wx.SingleChoiceDialog(
            gui.mainFrame,
            _("Select where the Neovim session is running."),
            _("Connect terminal to Neovim"),
            choices,
        )
        self._diagnostics.record(
            "connectionProfileDialogScheduled", terminal=self._identityFields(identity),
            profileCount=len(profiles), localTarget=True,
        )
        ui.message(_("Opening the Neovim server selection"))

        def finish_profile_selection(result):
            if result != wx.ID_OK:
                self._diagnostics.record("connectionProfileDialogClosed", accepted=False)
                return
            selection = profile_dialog.GetSelection()
            if not 0 <= selection < len(choices):
                ui.message(_("The selected connection profile is unavailable"))
                return
            if selection == 0:
                self._pendingClaimTargets[identity] = (LOCAL_WINDOWS_TCP, "")
                self._diagnostics.record(
                    "connectionTargetDialogClosed", accepted=True,
                    targetKind=LOCAL_WINDOWS_TCP, terminal=self._identityFields(identity),
                )
                ui.message(_(
                    "Local Neovim selected. Focus the desired Neovim session and press {key}"
                ).format(key=_SESSION_CLAIM_KEY_NAME))
                return
            try:
                parsed_profile = parse_profile(profiles[selection - 1])
            except ValueError:
                ui.message(_("The selected connection profile is unavailable"))
                return
            self._diagnostics.record(
                "connectionProfileDialogClosed", accepted=True,
                profileId=parsed_profile.identifier,
            )
            if parsed_profile.authentication == "password":
                password = self._passwordForProfile(parsed_profile)
                if password is None:
                    return
            self._pendingClaimTargets[identity] = ("remoteSsh", parsed_profile.identifier)
            self._promptForSessionClaim(parsed_profile, identity)

        # NVDA's helper schedules the modal dialog for a fresh GUI-loop turn and
        # manages popup focus. A direct ShowModal call can remain behind Windows
        # Terminal or interfere with NVDA event processing.
        gui.runScriptModalDialog(profile_dialog, finish_profile_selection)

    def action_claimFocusedNeovimSession(
        self, gesture, forward_gesture=True, expected_identity=None, claim_generation=None,
    ):
        """Observe F12 reaching Neovim, then select only that fresh claim."""
        identity = self._gate.focused
        if expected_identity is None:
            expected_identity = identity
        if claim_generation is None:
            claim_generation = self._captureObservedSessionClaim(expected_identity)
        if claim_generation is None or not self._acceptObservedSessionClaim(
            expected_identity, claim_generation,
        ):
            self._diagnostics.record("sessionClaimIgnored", reason="notAuthorizedOrFocusChanged")
            if forward_gesture and gesture is not None:
                gesture.send()
            return
        identity = expected_identity
        selected = self._instanceManager.selected_for(identity) if identity is not None else None
        self._diagnostics.record(
            "sessionClaimGestureReceived",
            terminal=self._identityFields(identity),
            inventoryReady=self._claimInventoryReady,
            selected=selected is not None,
        )
        profile = (
            self._connectionProfileById(selected.target_id)
            if selected is not None and selected.transport_kind == "remoteSsh"
            else None
        )
        pending_target = self._pendingClaimTargets.pop(identity, None) if identity is not None else None
        if not pending_target and selected is not None and selected.transport_kind == LOCAL_WINDOWS_TCP:
            pending_target = (LOCAL_WINDOWS_TCP, "")
        if identity is None or identity.frontend_kind != "windowsTerminal":
            if forward_gesture and gesture is not None:
                gesture.send()
            return
        if selected is None and not pending_target and not self._claimInventoryReady:
            ui.message(_(
                "Neovim connections are still being checked. Press {key} again after the ready message"
            ).format(key=_SESSION_CLAIM_KEY_NAME))
            return
        local_claim_not_before_ns = time.monotonic_ns()
        if forward_gesture and gesture is not None:
            gesture.send()
        if pending_target and pending_target[0] == LOCAL_WINDOWS_TCP:
            if not self._gate.manual_enabled:
                self._gate.manual_enabled = True
                self._planner.reset()
                self._resetTypedEcho()
                self._gate.focused = identity
                self._diagnostics.record(
                    "manualMode", enabled=True, terminal=self._identityFields(identity),
                )
            ui.message(_("Connecting the focused local Neovim session"))
            self._scheduleMainThreadCall(
                250, self._beginLocalSessionSelection, identity, True, True, True,
                None, local_claim_not_before_ns,
            )
            return
        if pending_target:
            pending_profile = self._connectionProfileById(pending_target[1])
            if pending_profile is None:
                ui.message(_("The selected connection profile is unavailable"))
                return
            ui.message(_("Connecting the focused Neovim session"))
            self._scheduleMainThreadCall(
                250, self._beginSessionSelection, pending_profile, identity,
                True, True, True,
            )
            return
        if selected is None:
            if not self._gate.manual_enabled:
                self._gate.manual_enabled = True
                self._planner.reset()
                self._resetTypedEcho()
                self._gate.focused = identity
                self._diagnostics.record(
                    "manualMode", enabled=True, terminal=self._identityFields(identity),
                )
            ui.message(_("Connecting the focused Neovim session"))
            self._scheduleMainThreadCall(
                250, self._beginAutomaticClaimResolution, identity,
                local_claim_not_before_ns,
            )
            return
        if profile is None:
            ui.message(_("Configure a Neovim connection before using {key} pairing").format(
                key=_SESSION_CLAIM_KEY_NAME,
            ))
            return
        if not self._gate.manual_enabled:
            self._gate.manual_enabled = True
            self._planner.reset()
            self._resetTypedEcho()
            self._gate.focused = identity
            self._diagnostics.record(
                "manualMode", enabled=True, terminal=self._identityFields(identity),
            )
        ui.message(_("Connecting the focused Neovim session"))
        self._scheduleMainThreadCall(
            250, self._beginSessionSelection, profile, identity, True, True, True,
        )

    def _beginLocalSessionSelection(
        self, identity, replace_existing=False, offer_remember=False,
        require_recent_claim=False, fallback_profile=None, claim_not_before_ns=0,
    ):
        self._sessionDiscoveryGeneration += 1
        generation = self._sessionDiscoveryGeneration
        if not require_recent_claim:
            ui.message(_("Looking for local Neovim sessions"))
        threading.Thread(
            target=self._discoverLocalSessions,
            args=(
                generation, identity, replace_existing, offer_remember,
                require_recent_claim, fallback_profile, claim_not_before_ns,
            ),
            name="nvim-nvda-local-session-list", daemon=True,
        ).start()

    def _discoverLocalSessions(
        self, generation, identity, replace_existing, offer_remember,
        require_recent_claim, fallback_profile, claim_not_before_ns,
    ):
        if require_recent_claim:
            def fresh(sessions):
                return any(
                    0 <= session.claim_age_ms <= 15_000
                    and (
                        not claim_not_before_ns
                        or session.claimed_monotonic_ns >= claim_not_before_ns
                    )
                    for session in sessions
                )

            sessions, error, attempts = self._pollLocalSessions(fresh)
            self._diagnostics.record(
                "localClaimWaitCompleted", attempts=attempts, sessions=len(sessions),
                matched=error is None and fresh(sessions),
                errorType=type(error).__name__ if error is not None else "",
            )
        else:
            attempts = 1
            try:
                sessions, error = LocalSessionLister().list(), None
            except Exception as caught:
                sessions, error = [], caught
        queueHandler.queueFunction(
            queueHandler.eventQueue, self._finishLocalSessionDiscovery,
            generation, identity, sessions, error, replace_existing,
            offer_remember, require_recent_claim, fallback_profile, claim_not_before_ns,
        )

    def _finishLocalSessionDiscovery(
        self, generation, identity, sessions, error, replace_existing=False,
        offer_remember=False, require_recent_claim=False, fallback_profile=None,
        claim_not_before_ns=0,
    ):
        if (
            generation != self._sessionDiscoveryGeneration
            or not self._gate.manual_enabled or self._gate.focused != identity
        ):
            self._diagnostics.record("localSessionDiscoveryIgnored")
            return
        if error is not None:
            self._diagnostics.record(
                "localSessionDiscoveryError", errorType=type(error).__name__, error=str(error),
            )
            if fallback_profile is not None:
                self._beginSessionSelection(
                    fallback_profile, identity, replace_existing,
                    offer_remember, require_recent_claim,
                )
                return
            ui.message(_("Could not list local Neovim sessions"))
            return
        if not sessions:
            if fallback_profile is not None:
                self._beginSessionSelection(
                    fallback_profile, identity, replace_existing,
                    offer_remember, require_recent_claim,
                )
                return
            ui.message(_(
                "No local Neovim accessibility session was found. Install the local components "
                "and restart Neovim"
            ))
            return
        if require_recent_claim:
            claimed = [
                session for session in sessions
                if 0 <= session.claim_age_ms <= 15_000
                and (
                    not claim_not_before_ns
                    or session.claimed_monotonic_ns >= claim_not_before_ns
                )
            ]
            if not claimed:
                if fallback_profile is not None:
                    self._beginSessionSelection(
                        fallback_profile, identity, replace_existing,
                        offer_remember, require_recent_claim,
                    )
                    return
                ui.message(_("The focused local Neovim did not confirm F12 pairing; try again"))
                return
            session = min(claimed, key=lambda item: item.claim_age_ms)
            if self._reuseLocalSession(identity, session, offer_remember):
                return
            self._startLocalSession(
                identity, session, replace_existing=replace_existing,
                offer_remember=offer_remember,
            )
            return
        if len(sessions) > 1:
            self._showLocalSessionChoice(
                generation, identity, sessions, replace_existing, offer_remember,
            )
            return
        self._startLocalSession(
            identity, sessions[0], replace_existing=replace_existing,
            offer_remember=offer_remember,
        )

    def _reuseLocalSession(self, identity, session, offer_remember=False):
        matches = [
            instance for instance in self._instanceManager.list()
            if instance.transport_kind == LOCAL_WINDOWS_TCP
            and instance.session_id == session.identifier
        ]
        if not matches:
            return False
        instance = matches[0]
        for terminal in self._instanceManager.bound_terminals_for(instance.identifier):
            if terminal != identity:
                self._instanceManager.unbind(terminal)
                self._rememberedTerminalBindings.discard(terminal)
                self._terminalIdentityElements.pop(terminal, None)
        self._instanceManager.bind(identity, instance.identifier)
        self._ensureTerminalLifecycleSweep()
        if offer_remember and identity not in self._rememberedTerminalBindings:
            self._rememberOfferInstances.add(instance.identifier)
        self._activateRememberedBinding(identity, instance.identifier)
        ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
        return True

    def _startLocalSession(
        self, identity, session, replace_existing=False, offer_remember=False,
    ):
        existing = self._instanceManager.selected_for(identity) if replace_existing else None
        self._startLocalManagedInstance(
            session, identity, self._remoteSessionLabel(session),
            existing.identifier if existing is not None else "", offer_remember,
        )

    def _showLocalSessionChoice(
        self, generation, identity, sessions, replace_existing, offer_remember,
    ):
        import gui
        import wx
        labels = [self._remoteSessionLabel(session) for session in sessions]
        dialog = wx.SingleChoiceDialog(
            gui.mainFrame, _("Select the local Neovim session for the focused terminal."),
            _("Local Neovim session"), labels,
        )
        ui.message(_("Multiple local Neovim sessions found; opening session selection"))

        def finish(result):
            if (
                generation != self._sessionDiscoveryGeneration
                or not self._gate.manual_enabled or self._gate.focused != identity
            ):
                return
            if result != wx.ID_OK:
                return
            selection = dialog.GetSelection()
            if not 0 <= selection < len(sessions):
                ui.message(_("The selected local Neovim session is no longer available"))
                return
            self._startLocalSession(
                identity, sessions[selection], replace_existing, offer_remember,
            )

        gui.runScriptModalDialog(dialog, finish)

    def _startLocalManagedInstance(
        self, session, identity, session_label="", replace_instance_id="",
        offer_remember=False,
    ):
        if identity is None:
            ui.message(_("Starting a connection instance requires a focused terminal"))
            return
        if not self._instanceManager.list() and self._client is not None:
            self._stopClient()
        client = LocalTcpClient(
            session.host, session.port,
            lambda event: self._onManagedEvent(
                getattr(client, "nvim_nvda_instance_id", None), event,
            ),
            lambda state: self._onManagedState(
                getattr(client, "nvim_nvda_instance_id", None), state,
            ),
            on_diagnostic=lambda category, fields: self._recordNetworkDiagnostic(
                category, {**fields, "instanceId": getattr(client, "nvim_nvda_instance_id", None)},
            ),
            session_nonce=session.session_nonce,
        )
        try:
            target = local_windows_target(_("This computer - local Neovim"))
            label = _("Local Neovim, {session}").format(
                session=session_label or _("Neovim session"),
            )
            instance = self._instanceManager.add_target(
                target, session.identifier, label, client, context_label=_("local"),
            )
            self._instanceManager.bind(identity, instance.identifier)
            self._ensureTerminalLifecycleSweep()
            self._switchInstanceRuntime(instance.identifier)
            if offer_remember:
                self._rememberOfferInstances.add(instance.identifier)
            if replace_instance_id and replace_instance_id != instance.identifier:
                self._removeReplacedInstance(replace_instance_id)
            self._client = client
            self._gate.focused = identity
            ui.message(_("Neovim connection started: {name}").format(name=instance.label))
        except Exception as error:
            self._diagnostics.record(
                "connectionInstanceStartError", targetKind=LOCAL_WINDOWS_TCP,
                errorType=type(error).__name__, error=str(error),
            )
            ui.message(_("Could not start the local Neovim connection"))

    def _removeReplacedInstance(self, instance_id):
        try:
            self._instanceManager.remove(instance_id)
            self._authenticatedInstances.discard(instance_id)
            self._instanceTerminalPassthrough.pop(instance_id, None)
            self._pendingInstanceFullStates.pop(instance_id, None)
            self._dropInstanceRuntime(instance_id)
        except Exception as error:
            self._diagnostics.record(
                "replacedConnectionStopError", instanceId=instance_id,
                errorType=type(error).__name__, error=str(error),
            )

    def action_disconnectConnectionInstance(self, gesture):
        identity = self._gate.focused
        if identity is None:
            return
        instance = self._instanceManager.selected_for(identity) if identity else None
        if instance is None:
            ui.message(_("No Neovim connection instance is selected for this terminal"))
            return
        self._rememberedTerminalBindings.discard(identity)
        self._terminalIdentityElements.pop(identity, None)
        self._rememberOfferInstances.discard(instance.identifier)
        self._instanceManager.remove(instance.identifier)
        self._authenticatedInstances.discard(instance.identifier)
        self._instanceTerminalPassthrough.pop(instance.identifier, None)
        self._pendingInstanceFullStates.pop(instance.identifier, None)
        self._dropInstanceRuntime(instance.identifier)
        if self._client is not None:
            self._client = None
        self._gate.disconnect()
        ui.message(_("Neovim connection disconnected: {name}").format(name=instance.label))

    def action_forgetTemporaryTerminalBinding(self, gesture):
        identity = self._gate.focused
        if identity is None:
            return
        if identity not in self._rememberedTerminalBindings:
            ui.message(_("No temporary Neovim connection is remembered for this terminal"))
            return
        self._rememberedTerminalBindings.discard(identity)
        self._diagnostics.record("temporaryTerminalBindingForgotten", terminal=self._identityFields(identity))
        ui.message(_("Temporary Neovim connection forgotten"))

    @staticmethod
    def _remoteSessionLabel(session):
        if session.name and session.cwd and session.cwd != session.name:
            return _("{name}, working directory {cwd}").format(name=session.name, cwd=session.cwd)
        return session.name or session.cwd or _("Neovim session")

    def _remoteSessionLabels(self, profile, sessions, include_connection_status=True):
        bases = [self._remoteSessionLabel(session) for session in sessions]
        totals = {base: bases.count(base) for base in set(bases)}
        positions = {}
        connected = {
            instance.session_id for instance in self._instanceManager.list()
            if instance.profile_id == profile.identifier
        }
        labels = []
        for session, base in zip(sessions, bases):
            label = base
            if totals[base] > 1:
                positions[base] = positions.get(base, 0) + 1
                if session.started_unix:
                    started = time.strftime("%H:%M", time.localtime(session.started_unix))
                    label = _("{label}, started {started}").format(label=label, started=started)
                label = _("{label}, session {position} of {total}").format(
                    label=label, position=positions[base], total=totals[base],
                )
            if include_connection_status and session.identifier in connected:
                label = _("{label}, already connected").format(label=label)
            labels.append(label)
        return labels

    def _beginSessionSelection(
        self, profile, identity, replace_existing=False, offer_remember=False,
        require_recent_claim=False, preserve_dialog_identity=False,
    ):
        if not preserve_dialog_identity and self._gate.focused != identity:
            return
        password = self._passwordForProfile(profile)
        if profile.authentication == "password" and password is None:
            return
        self._sessionDiscoveryGeneration += 1
        generation = self._sessionDiscoveryGeneration
        self._diagnostics.record(
            "remoteSessionDiscoveryStarted", profileId=profile.identifier,
            terminal=self._identityFields(identity),
            preserveDialogIdentity=preserve_dialog_identity,
        )
        if not require_recent_claim:
            ui.message(_("Looking for Neovim sessions on {name}").format(name=profile.name))
        threading.Thread(
            target=self._discoverRemoteSessions,
            args=(
                generation, profile, identity, password or "", replace_existing,
                offer_remember, require_recent_claim, preserve_dialog_identity,
            ),
            name="nvim-nvda-session-list",
            daemon=True,
        ).start()

    def _discoverRemoteSessions(
        self, generation, profile, identity, password, replace_existing, offer_remember,
        require_recent_claim, preserve_dialog_identity,
    ):
        try:
            sessions = SshSessionLister().list(
                profile.ssh_target, profile.port, profile.identity_file,
                password=password, askpass_path=self._askpassPath(),
            )
            error = None
        except Exception as caught:
            sessions, error = [], caught
        queueHandler.queueFunction(
            queueHandler.eventQueue, self._finishSessionDiscovery,
            generation, profile, identity, sessions, error, replace_existing, offer_remember,
            require_recent_claim, preserve_dialog_identity,
        )

    def _finishSessionDiscovery(
        self, generation, profile, identity, sessions, error, replace_existing=False,
        offer_remember=False, require_recent_claim=False, preserve_dialog_identity=False,
    ):
        if (
            generation != self._sessionDiscoveryGeneration
            or not self._gate.manual_enabled
            or (not preserve_dialog_identity and self._gate.focused != identity)
        ):
            self._diagnostics.record("sessionDiscoveryIgnored", profileId=profile.identifier)
            return
        if error is not None:
            self._diagnostics.record(
                "sessionDiscoveryError", profileId=profile.identifier,
                errorType=type(error).__name__, error=str(error),
            )
            ui.message(_("Could not list Neovim sessions on {name}").format(name=profile.name))
            return
        if not sessions:
            ui.message(_("No active Neovim session was found on {name}").format(name=profile.name))
            return
        if require_recent_claim:
            claimed = [session for session in sessions if 0 <= session.claim_age_ms <= 15_000]
            if not claimed:
                self._diagnostics.record(
                    "freshSessionClaimMissing", profileId=profile.identifier,
                    sessionCount=len(sessions),
                )
                ui.message(_("The focused Neovim did not confirm F12 pairing; try again"))
                return
            session = min(claimed, key=lambda item: item.claim_age_ms)
            self._diagnostics.record(
                "freshSessionClaimSelected", profileId=profile.identifier,
                sessionId=session.identifier, claimAgeMs=session.claim_age_ms,
            )
            if self._reuseClaimedSession(
                profile, identity, session, offer_remember=offer_remember,
            ):
                return
            self._startDiscoveredSession(
                profile, identity, session, replace_existing, offer_remember,
            )
            return
        if len(sessions) > 1:
            self._showRemoteSessionChoice(
                generation, profile, identity, sessions, replace_existing, offer_remember,
                preserve_dialog_identity,
            )
            return
        self._startDiscoveredSession(
            profile, identity, sessions[0], replace_existing, offer_remember,
        )

    def _reuseClaimedSession(self, profile, identity, session, offer_remember=False):
        """Move or refresh an existing transport instead of duplicating it."""
        matches = [
            instance for instance in self._instanceManager.list()
            if instance.profile_id == profile.identifier
            and instance.session_id == session.identifier
        ]
        if not matches:
            return False
        selected = self._instanceManager.selected_for(identity)
        instance = next(
            (item for item in matches if selected and item.identifier == selected.identifier),
            matches[0],
        )
        for terminal in self._instanceManager.bound_terminals_for(instance.identifier):
            if terminal != identity:
                self._instanceManager.unbind(terminal)
                self._rememberedTerminalBindings.discard(terminal)
                self._terminalIdentityElements.pop(terminal, None)
        self._instanceManager.bind(identity, instance.identifier)
        self._ensureTerminalLifecycleSweep()
        if offer_remember and identity not in self._rememberedTerminalBindings:
            self._rememberOfferInstances.add(instance.identifier)
        client = self._instanceManager.client_for(instance.identifier)
        already_active = (
            self._gate.bound_terminal == identity and self._client is client
            and self._gate.authenticated and self._gate.nvim_active
            and self._activeInstanceId == instance.identifier
        )
        self._activateRememberedBinding(identity, instance.identifier)
        if already_active and instance.identifier in self._rememberOfferInstances:
            client.send_control("requestFullState", {})
        self._diagnostics.record(
            "claimedSessionTransportReused", instanceId=instance.identifier,
            profileId=profile.identifier, sessionId=session.identifier,
            terminal=self._identityFields(identity),
        )
        ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
        return True

    def _startDiscoveredSession(
        self, profile, identity, session, replace_existing=False, offer_remember=False,
    ):
        existing = self._instanceManager.selected_for(identity) if replace_existing else None
        self._startManagedInstance(
            profile.identifier, session.identifier, identity=identity,
            session_label=self._remoteSessionLabel(session),
            replace_instance_id=existing.identifier if existing is not None else "",
            offer_remember=offer_remember,
        )

    def _showRemoteSessionChoice(
        self, generation, profile, identity, sessions, replace_existing, offer_remember,
        preserve_dialog_identity=False,
    ):
        import gui
        import wx
        dialog = wx.SingleChoiceDialog(
            gui.mainFrame, _("Select the Neovim session for the focused terminal."),
            _("Neovim session"), self._remoteSessionLabels(profile, sessions),
        )
        self._diagnostics.record(
            "remoteSessionDialogScheduled", profileId=profile.identifier,
            sessionCount=len(sessions), terminal=self._identityFields(identity),
        )
        ui.message(
            _("Multiple Neovim sessions found on {name}; opening session selection").format(
                name=profile.name,
            )
        )

        def finish_session_selection(result):
            if (
                generation != self._sessionDiscoveryGeneration
                or not self._gate.manual_enabled
                or (not preserve_dialog_identity and self._gate.focused != identity)
            ):
                self._diagnostics.record(
                    "remoteSessionDialogIgnored", profileId=profile.identifier,
                    reason="stale",
                )
                return
            if result != wx.ID_OK:
                self._diagnostics.record(
                    "remoteSessionDialogClosed", profileId=profile.identifier, accepted=False,
                )
                return
            selection = dialog.GetSelection()
            if not 0 <= selection < len(sessions):
                ui.message(_("The selected Neovim session is no longer available"))
                return
            session = sessions[selection]
            self._diagnostics.record(
                "remoteSessionDialogClosed", profileId=profile.identifier, accepted=True,
            )
            labels = self._remoteSessionLabels(
                profile, sessions, include_connection_status=False,
            )
            existing = self._instanceManager.selected_for(identity) if replace_existing else None
            self._startManagedInstance(
                profile.identifier, session.identifier, identity=identity,
                session_label=labels[selection],
                replace_instance_id=existing.identifier if existing is not None else "",
                offer_remember=offer_remember,
            )

        # Session discovery completes on NVDA's event queue. Schedule the modal
        # chooser through NVDA's GUI helper rather than nesting ShowModal here.
        gui.runScriptModalDialog(dialog, finish_session_selection)

    def _startManagedInstance(
        self, profile_id, session_id, identity=None, session_label="", replace_instance_id="",
        offer_remember=False,
    ):
        try:
            profile = next(
                item for item in parse_profiles(self._settings.get("connections", []))
                if item.identifier == profile_id
            )
        except (StopIteration, ValueError) as error:
            self._diagnostics.record("connectionInstanceStartError", error=str(error), profileId=profile_id)
            ui.message(_("The selected connection profile is unavailable"))
            return
        identity = identity or self._gate.focused
        if identity is None:
            ui.message(_("Starting a connection instance requires a focused terminal"))
            return
        password = self._passwordForProfile(profile)
        if profile.authentication == "password" and password is None:
            return
        if not self._instanceManager.list() and self._client is not None:
            self._stopClient()
        client = SshStdioClient(
            profile.ssh_target,
            lambda event: self._onManagedEvent(getattr(client, "nvim_nvda_instance_id", None), event),
            lambda state: self._onManagedState(getattr(client, "nvim_nvda_instance_id", None), state),
            on_diagnostic=lambda category, fields: self._recordNetworkDiagnostic(
                category, {**fields, "instanceId": getattr(client, "nvim_nvda_instance_id", None)},
            ),
            ssh_port=profile.port, identity_file=profile.identity_file,
            session_id=session_id, password=password or "", askpass_path=self._askpassPath(),
        )
        try:
            instance = self._instanceManager.add(
                profile.identifier, session_id,
                f"{profile.name}, {session_label}" if session_label else profile.name,
                client, context_label=profile.name,
            )
            self._instanceManager.bind(identity, instance.identifier)
            self._ensureTerminalLifecycleSweep()
            self._switchInstanceRuntime(instance.identifier)
            if offer_remember:
                self._rememberOfferInstances.add(instance.identifier)
            if replace_instance_id and replace_instance_id != instance.identifier:
                try:
                    self._instanceManager.remove(replace_instance_id)
                    self._authenticatedInstances.discard(replace_instance_id)
                    self._instanceTerminalPassthrough.pop(replace_instance_id, None)
                    self._pendingInstanceFullStates.pop(replace_instance_id, None)
                    self._dropInstanceRuntime(replace_instance_id)
                except Exception as error:
                    self._diagnostics.record(
                        "replacedConnectionStopError", instanceId=replace_instance_id,
                        errorType=type(error).__name__, error=str(error),
                    )
            self._client = client
            self._gate.focused = identity
            ui.message(_("Neovim connection started: {name}").format(name=instance.label))
        except Exception as error:
            self._diagnostics.record(
                "connectionInstanceStartError", profileId=profile.identifier,
                errorType=type(error).__name__, error=str(error),
            )
            ui.message(_("Could not start the Neovim connection"))

    def _bindManagedInstance(self, instance_id):
        identity = self._gate.focused
        if identity is None:
            ui.message(_("Connection selection requires a focused terminal"))
            return
        try:
            instance = self._instanceManager.bind(identity, instance_id)
            self._ensureTerminalLifecycleSweep()
            self._switchInstanceRuntime(instance_id)
            self._client = self._instanceManager.client_for(instance_id)
            self._gate.focused = identity
            self._gate.bound_terminal = identity
            self._client.send_control("requestFullState", {})
            ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
        except ValueError as error:
            self._diagnostics.record("connectionInstanceBindError", error=str(error))
            ui.message(_("The selected Neovim connection no longer exists"))

    def _offerTemporaryTerminalBinding(self, identity, instance_id):
        focused = self._gate.focused
        selected = self._instanceManager.selected_for(focused) if focused else None
        if focused != identity or selected is None or selected.identifier != instance_id:
            self._diagnostics.record(
                "temporaryTerminalBindingOfferIgnored", instanceId=instance_id,
                reason="focusChanged",
            )
            return
        if identity.frontend_kind != "windowsTerminal" or not identity.runtime_id:
            self._diagnostics.record(
                "temporaryTerminalBindingUnavailable", terminal=self._identityFields(identity),
            )
            return
        try:
            instance = next(
                item for item in self._instanceManager.list() if item.identifier == instance_id
            )
        except StopIteration:
            return
        import gui
        import wx
        answer = wx.MessageBox(
            _(
                "Remember this connection for this Windows Terminal tab until NVDA or "
                "Windows Terminal closes?\n\n{connection}"
            ).format(connection=instance.label),
            _("Remember temporary terminal connection"),
            wx.YES_NO | wx.ICON_QUESTION,
            gui.mainFrame,
        )
        if answer != wx.YES:
            self._diagnostics.record(
                "temporaryTerminalBindingDeclined", instanceId=instance_id,
                terminal=self._identityFields(identity),
            )
            return
        self._rememberedTerminalBindings.add(identity)
        self._diagnostics.record(
            "temporaryTerminalBindingRemembered", instanceId=instance_id,
            transportKind=instance.transport_kind, terminal=self._identityFields(identity),
        )
        ui.message(_("Connection remembered for this terminal tab until NVDA exits"))

    def _captureInstanceRuntime(self):
        return {
            "planner": self._planner,
            "currentState": self._currentState,
            "lastMode": self._lastMode,
            "typedWord": self._typedWord,
            "typedPosition": self._typedPosition,
            "menuDocumentation": self._menuDocumentation,
            "connected": self._connected,
            "lastConnectionState": self._lastConnectionState,
            "transportCapabilities": self._transportCapabilities,
        }

    @staticmethod
    def _newInstanceRuntime():
        return {
            "planner": SpeechPlanner(),
            "currentState": {},
            "lastMode": None,
            "typedWord": [],
            "typedPosition": None,
            "menuDocumentation": "",
            "connected": False,
            "lastConnectionState": None,
            "transportCapabilities": frozenset(),
        }

    def _switchInstanceRuntime(self, instance_id):
        if instance_id == self._activeInstanceId:
            return
        if self._activeInstanceId is not None:
            self._instanceRuntimeStates[self._activeInstanceId] = self._captureInstanceRuntime()
        runtime = self._instanceRuntimeStates.pop(instance_id, None) or self._newInstanceRuntime()
        self._planner = runtime["planner"]
        self._currentState = runtime["currentState"]
        self._lastMode = runtime["lastMode"]
        self._typedWord = runtime["typedWord"]
        self._typedPosition = runtime["typedPosition"]
        self._menuDocumentation = runtime["menuDocumentation"]
        self._connected = runtime["connected"]
        self._lastConnectionState = runtime["lastConnectionState"]
        self._transportCapabilities = runtime["transportCapabilities"]
        self._activeInstanceId = instance_id

    def _dropInstanceRuntime(self, instance_id):
        self._instanceRuntimeStates.pop(instance_id, None)
        if self._activeInstanceId == instance_id:
            runtime = self._newInstanceRuntime()
            self._planner = runtime["planner"]
            self._currentState = runtime["currentState"]
            self._lastMode = runtime["lastMode"]
            self._typedWord = runtime["typedWord"]
            self._typedPosition = runtime["typedPosition"]
            self._menuDocumentation = runtime["menuDocumentation"]
            self._connected = runtime["connected"]
            self._lastConnectionState = runtime["lastConnectionState"]
            self._transportCapabilities = runtime["transportCapabilities"]
            self._activeInstanceId = None

    def _activateRememberedBinding(self, identity, instance_id, focus_regained=False):
        try:
            client = self._instanceManager.client_for(instance_id)
            if (
                self._gate.bound_terminal == identity and self._client is client
                and self._gate.authenticated and self._gate.nvim_active
                and self._activeInstanceId == instance_id
                and not focus_regained
            ):
                return
            self._switchInstanceRuntime(instance_id)
            self._client = client
            trusted = instance_id in self._authenticatedInstances
            if trusted:
                # A live authenticated client proves session identity, not that
                # Neovim is still visible in this WT control. Keep the transport
                # selected but fail open until the focus-correlated context reply.
                self._connected = True
                self._gate.focused = identity
                self._gate.disconnect()
                self._gate.focused = identity
            else:
                self._connected = False
                self._gate.disconnect()
                self._gate.focused = identity
            # Focus events for Windows Terminal tabs can be followed by transient
            # child-focus events. Let focus settle before accepting a new fullState.
            self._scheduleMainThreadCall(
                100, self._requestRememberedBindingState, identity, instance_id,
            )
            self._diagnostics.record(
                "temporaryTerminalBindingActivated", instanceId=instance_id,
                terminal=self._identityFields(identity), suppressionImmediate=False,
            )
        except ValueError:
            self._rememberedTerminalBindings.discard(identity)

    def _requestRememberedBindingState(self, identity, instance_id):
        focused = self._gate.focused
        selected = self._instanceManager.selected_for(identity)
        if focused != identity or selected is None or selected.identifier != instance_id:
            self._diagnostics.record(
                "temporaryTerminalBindingStateSkipped", instanceId=instance_id,
                reason="focusChanged",
            )
            return
        try:
            client = self._instanceManager.client_for(instance_id)
            if instance_id in self._authenticatedInstances:
                self._focusContextRequestId = (self._focusContextRequestId + 1) % 2_147_483_648
                request_id = self._focusContextRequestId
                self._pendingFocusContexts[instance_id] = (request_id, identity)
                sent = client.send_control("requestFocusContext", {"requestId": request_id})
                if not sent:
                    self._pendingFocusContexts.pop(instance_id, None)
                self._diagnostics.record(
                    "temporaryTerminalFocusContextRequested", instanceId=instance_id,
                    requestId=request_id, sent=sent,
                )
                return
            client.send_control("requestFullState", {})
            self._diagnostics.record(
                "temporaryTerminalBindingStateRequested", instanceId=instance_id,
            )
        except ValueError:
            self._rememberedTerminalBindings.discard(identity)

    def _onManagedEvent(self, instance_id, event):
        queueHandler.queueFunction(queueHandler.eventQueue, self._handleManagedEvent, instance_id, event)

    def _handleManagedEvent(self, instance_id, event):
        identity = self._gate.focused
        selected = self._instanceManager.selected_for(identity) if identity else None
        if event.get("type") == "focusContext":
            payload = event.get("payload")
            pending = self._pendingFocusContexts.get(instance_id)
            request_id = payload.get("_focusRequestId") if isinstance(payload, dict) else None
            if (
                pending is None or pending != (request_id, identity)
                or selected is None or selected.identifier != instance_id
                or instance_id not in self._authenticatedInstances
            ):
                self._diagnostics.record(
                    "focusContextIgnored", instanceId=instance_id, reason="staleOrUnbound",
                )
                return
            self._pendingFocusContexts.pop(instance_id, None)
            self._switchInstanceRuntime(instance_id)
            self._client = self._instanceManager.client_for(instance_id)
            self._connected = True
            self._gate.focused = identity
            self._gate.bound_terminal = identity
            self._gate.authenticated = True
            self._gate.nvim_active = True
            self._gate.terminal_passthrough = self._instanceTerminalPassthrough.get(
                instance_id, False
            )
            self._diagnostics.record(
                "temporaryTerminalForegroundConfirmed", instanceId=instance_id,
                terminal=self._identityFields(identity),
            )
        if selected is None or selected.identifier != instance_id:
            if event.get("type") == "fullState":
                # A modal profile/session chooser can still own NVDA focus when
                # the newly started client delivers its first fullState.  The
                # instance was explicitly bound before it started; defer this
                # authoritative state until its terminal regains focus.
                try:
                    self._instanceManager.client_for(instance_id)
                except ValueError:
                    return
                self._pendingInstanceFullStates[instance_id] = event
                self._diagnostics.record(
                    "instanceFullStateDeferred", instanceId=instance_id,
                    reason="terminalNotFocused",
                )
                return
            self._diagnostics.record("instanceEventIgnored", instanceId=instance_id, reason="notSelected")
            return
        if (
            instance_id in self._authenticatedInstances
            and event.get("type") != "focusContext"
            and not (
                self._gate.authenticated
                and self._gate.nvim_active
                and self._gate.bound_terminal == identity
                and self._activeInstanceId == instance_id
            )
        ):
            self._diagnostics.record(
                "instanceEventIgnored", instanceId=instance_id,
                reason="foregroundUnconfirmed",
            )
            return
        self._switchInstanceRuntime(instance_id)
        self._client = self._instanceManager.client_for(instance_id)
        if event.get("type") in {"copyTextResult", "pasteTextResult", "setRegisterResult"}:
            event = self._handleClipboardResult(instance_id, identity, event)
            if event is None:
                return
        payload = event.get("payload")
        if event.get("type") == "fullState":
            self._authenticatedInstances.add(instance_id)
        if isinstance(payload, dict):
            if event.get("type") == "focusContext":
                payload = dict(payload)
                payload["_connectionLabel"] = selected.context_label
                event = {**event, "payload": payload}
            self._instanceTerminalPassthrough[instance_id] = (
                payload.get("buftype") == "terminal" and payload.get("mode") == "terminal"
            )
        self._handleEvent(event)
        if event.get("type") == "fullState" and instance_id in self._rememberOfferInstances:
            self._rememberOfferInstances.discard(instance_id)
            # Activate the authenticated state immediately. Only the optional
            # remember question is deferred out of NVDA's event queue; its answer
            # must never control whether native terminal output is suppressed.
            import wx
            wx.CallAfter(self._offerTemporaryTerminalBinding, identity, instance_id)
            return

    def _handleClipboardResult(self, instance_id, identity, event):
        payload = event.get("payload")
        event_type = event.get("type")
        request_id = payload.get("requestId") if isinstance(payload, dict) else None
        if not valid_request_id(request_id):
            self._diagnostics.record(
                "clipboardResultIgnored", instanceId=instance_id, reason="invalidRequestId",
            )
            return None
        pending = self._pendingClipboardRequests.pop(request_id, None)
        expected_control = {
            "copyTextResult": "copyTextRequest",
            "pasteTextResult": "pasteTextRequest",
            "setRegisterResult": "setRegisterRequest",
        }.get(event_type)
        if pending != (instance_id, identity, expected_control):
            self._diagnostics.record(
                "clipboardResultIgnored", instanceId=instance_id, requestId=request_id,
                reason="staleOrUnbound",
            )
            return None
        safe_payload = dict(payload)
        text = safe_payload.pop("clipboardText", None)
        safe_payload.pop("text", None)
        ok = payload.get("ok") is True
        result_code = payload.get("resultCode")
        if not isinstance(result_code, str) or len(result_code) > 64:
            ok = False
            result_code = "invalidResult"
        if event_type == "copyTextResult" and ok:
            if not valid_clipboard_text(text):
                ok = False
                result_code = "invalidText"
            else:
                try:
                    copied = bool(api.copyToClip(text))
                except Exception as error:
                    copied = False
                    self._diagnostics.record(
                        "clipboardWriteFailed", errorType=type(error).__name__,
                    )
                if copied:
                    self._clipboardSuccess(_("Copied from Neovim"))
                else:
                    ok = False
                    result_code = "clipboardWriteFailed"
        elif event_type == "pasteTextResult" and ok:
            self._clipboardSuccess(_("Pasted into Neovim"))
        elif event_type == "setRegisterResult" and ok:
            self._clipboardSuccess(_("Stored the Windows clipboard in Neovim's unnamed register"))
        if not ok:
            if result_code == "staleState":
                message = _("Neovim changed before the copy or paste completed; try again")
            elif result_code in {"visualSelectionRequired", "selectionUnavailable"}:
                message = _("The Neovim Visual selection is no longer available")
            elif result_code in {"bufferNotEditable", "unsupportedContext", "unsupportedMode"}:
                message = _("The current Neovim context does not accept this paste")
            elif result_code == "textTooLarge":
                message = _("The selected Neovim text is too large to copy")
            elif result_code == "emptyText":
                message = _("There is no Neovim text to copy")
            elif result_code == "clipboardWriteFailed":
                message = _("Could not write text to the Windows clipboard")
            elif result_code == "registerRejected":
                message = _("Neovim could not replace its unnamed register")
            else:
                message = _("Neovim could not complete the copy or paste command")
            self._clipboardFailure(message)
        self._diagnostics.record(
            "clipboardResult", instanceId=instance_id, requestId=request_id,
            type=event_type, ok=ok, resultCode=result_code,
            copiedCharacterCount=safe_payload.get("copiedCharacterCount"),
            copiedLineCount=safe_payload.get("copiedLineCount"),
            insertedBytes=safe_payload.get("insertedBytes"),
            insertedLines=safe_payload.get("insertedLines"),
            storedBytes=safe_payload.get("storedBytes"),
            storedLineCount=safe_payload.get("storedLineCount"),
        )
        return {**event, "payload": clipboard_result_state(safe_payload)}

    def _discardClipboardRequests(self, *, instance_id=None):
        if instance_id is None:
            self._pendingClipboardRequests.clear()
            return
        for request_id, pending in tuple(self._pendingClipboardRequests.items()):
            if pending[0] == instance_id:
                self._pendingClipboardRequests.pop(request_id, None)

    def _onManagedState(self, instance_id, state):
        queueHandler.queueFunction(queueHandler.eventQueue, self._handleManagedState, instance_id, state)

    def _handleManagedState(self, instance_id, state):
        if state == "disconnected":
            self._authenticatedInstances.discard(instance_id)
            self._instanceTerminalPassthrough.pop(instance_id, None)
            self._pendingInstanceFullStates.pop(instance_id, None)
            self._pendingFocusContexts.pop(instance_id, None)
            self._discardClipboardRequests(instance_id=instance_id)
        identity = self._gate.focused
        selected = self._instanceManager.selected_for(identity) if identity else None
        if selected is not None and selected.identifier == instance_id:
            self._switchInstanceRuntime(instance_id)
            self._handleConnectionState(state)

    def _event_gainFocus(self, obj, nextHandler, app_module=None):
        previous = self._gate.focused
        identity = self._identity(obj)
        if previous != identity:
            self._pendingFocusContexts.clear()
            self._pendingClipboardRequests.clear()
            self._gate.disconnect()
            self._diagnostics.record(
                "terminalFocusIdentityChanged",
                previous=self._identityFields(previous),
                current=self._identityFields(identity),
            )
        self._gate.focused = identity
        if identity is not None:
            element = self._identityElement(obj, identity)
            if element is not None:
                self._terminalIdentityElements[identity] = element
        self._focusedTerminalObject = obj if identity is not None else None
        self._focusedAppModule = app_module
        instance = self._instanceManager.selected_for(identity) if identity else None
        pending_full_state = (
            self._pendingInstanceFullStates.pop(instance.identifier, None)
            if instance is not None else None
        )
        if identity in self._rememberedTerminalBindings:
            if instance is None:
                self._rememberedTerminalBindings.discard(identity)
            else:
                self._activateRememberedBinding(
                    identity, instance.identifier, focus_regained=previous != identity,
                )
        suppress_focus_speech = self._shouldSuppress(obj) or pending_full_state is not None
        nextHandler()
        if suppress_focus_speech:
            # Terminal.event_gainFocus must run: it starts LiveText monitoring
            # and initializes editable-text selection tracking.  Cancelling the
            # synchronous native focus report afterwards keeps that machinery
            # intact while structured fullState remains authoritative.
            speech.cancelSpeech()
            self._diagnostics.record(
                "terminalFocusAnnouncementSuppressed",
                terminal=self._identityFields(identity),
            )
        if pending_full_state is not None:
            self._diagnostics.record(
                "instanceFullStateResumed", instanceId=instance.identifier,
            )
            self._handleManagedEvent(instance.identifier, pending_full_state)

    def _failOpenTerminalEvent(self, event_name, error):
        """Drop suppression after a frontend event failure."""
        self._gate.disconnect()
        self._client = None
        self._diagnostics.record(
            "terminalEventFailedOpen",
            event=event_name,
            errorType=type(error).__name__,
        )

    def _refreshFocusedTerminalForAction(self, obj, app_module=None):
        """Refresh focus when an action does not receive a new gainFocus event."""
        identity = self._identity(obj)
        previous = self._gate.focused
        self._gate.focused = identity
        if identity is not None:
            element = self._identityElement(obj, identity)
            if element is not None:
                self._terminalIdentityElements[identity] = element
        self._focusedTerminalObject = obj if identity is not None else None
        self._focusedAppModule = app_module if identity is not None else None
        self._diagnostics.record(
            "terminalActionFocusRefreshed",
            previous=self._identityFields(previous),
            current=self._identityFields(identity),
        )
        return identity

    def _pruneClosedTerminalBindings(self):
        removed = set()
        for instance in list(self._instanceManager.list()):
            try:
                terminals = self._instanceManager.bound_terminals_for(instance.identifier)
            except ValueError:
                continue
            invalid = []
            for terminal in terminals:
                # A focused terminal is direct positive evidence of life. UIA
                # tree searches can transiently miss an otherwise active WT
                # tab while focus or accessibility objects are being rebuilt.
                if terminal == self._gate.focused:
                    self._terminalLifecycleMisses.pop(terminal, None)
                    continue
                exists = _terminalIdentityExists(
                    terminal, self._terminalIdentityElements.get(terminal),
                )
                if exists:
                    self._terminalLifecycleMisses.pop(terminal, None)
                    continue
                misses = self._terminalLifecycleMisses.get(terminal, 0) + 1
                self._terminalLifecycleMisses[terminal] = misses
                # Never destroy a binding on one negative UIA observation.
                if misses >= 2:
                    invalid.append(terminal)
            if not invalid:
                continue
            for terminal in invalid:
                self._instanceManager.unbind(terminal)
                self._rememberedTerminalBindings.discard(terminal)
                self._terminalIdentityElements.pop(terminal, None)
                self._terminalLifecycleMisses.pop(terminal, None)
                if self._gate.focused == terminal:
                    self._gate.focused = None
                    self._gate.disconnect()
                    self._client = None
            if self._instanceManager.bound_terminals_for(instance.identifier):
                continue
            try:
                _detached, client = self._instanceManager.detach(instance.identifier)
            except ValueError:
                continue
            removed.add(instance.identifier)
            self._authenticatedInstances.discard(instance.identifier)
            self._instanceTerminalPassthrough.pop(instance.identifier, None)
            self._pendingInstanceFullStates.pop(instance.identifier, None)
            self._rememberOfferInstances.discard(instance.identifier)
            self._dropInstanceRuntime(instance.identifier)
            threading.Thread(
                target=self._stopPrunedClient, args=(instance.identifier, client),
                name="nvim-nvda-closed-terminal-stop", daemon=True,
            ).start()
            self._diagnostics.record(
                "closedTerminalBindingPruned", instanceId=instance.identifier,
                terminals=[self._identityFields(terminal) for terminal in invalid],
            )
        return removed

    def _stopPrunedClient(self, instance_id, client):
        try:
            client.stop()
        except Exception as error:
            self._diagnostics.record(
                "closedTerminalClientStopError", instanceId=instance_id,
                errorType=type(error).__name__, error=str(error),
            )

    def _event_appModule_loseFocus(self, app_module=None):
        if (
            app_module is not None
            and self._focusedAppModule is not None
            and app_module is not self._focusedAppModule
        ):
            self._diagnostics.record("staleAppModuleLoseFocusIgnored")
            return
        previous = self._gate.focused
        self._gate.disconnect()
        self._gate.focused = None
        self._pendingFocusContexts.clear()
        self._pendingClipboardRequests.clear()
        self._focusedTerminalObject = None
        self._focusedAppModule = None
        self._resetTypedEcho()
        if previous is not None:
            self._diagnostics.record(
                "terminalApplicationLostFocus",
                previous=self._identityFields(previous),
            )

    def _event_textChange(self, obj, nextHandler):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _event_typedCharacter(self, obj, nextHandler, ch):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _event_UIA_notification(self, obj, nextHandler, **kwargs):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _event_liveRegionChange(self, obj, nextHandler):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _event_valueChange(self, obj, nextHandler):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _event_nameChange(self, obj, nextHandler):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _event_descriptionChange(self, obj, nextHandler):
        if not self._shouldSuppress(obj):
            nextHandler()

    def _onNetworkEvent(self, event):
        queueHandler.queueFunction(
            queueHandler.eventQueue,
            self._handleScopedNetworkEvent,
            event,
            _immediate=event.get("type") == "modeChanged",
        )

    def _handleScopedNetworkEvent(self, event):
        if self._gate.focused is None:
            self._diagnostics.record(
                "eventIgnored", type=event.get("type"), reason="frontendNotFocused",
            )
            return
        self._handleEvent(event)

    def _onNetworkState(self, state):
        # Fail open immediately in the network thread. Speech/UI stays on main.
        if state == "disconnected":
            self._gate.disconnect()
            self._connected = False
        queueHandler.queueFunction(queueHandler.eventQueue, self._handleConnectionState, state)

    def _recordNetworkDiagnostic(self, category, fields):
        self._diagnostics.record(category, **fields)
        log.debug("nvimNvdaAccess %s %r", category, fields)

    def _handleConnectionState(self, state):
        previous = self._lastConnectionState
        self._lastConnectionState = state
        self._diagnostics.record("connectionState", previous=previous, state=state)
        if (
            state == "disconnected" and previous == "connected"
            and self._gate.focused is not None
        ):
            self._planner.reset()
            self._resetTypedEcho()
            ui.message(_("Neovim connection lost; normal terminal output restored"))
            self._refreshBraille(rebuild=True)

    def _handleEvent(self, event):
        activated = False
        payload = event.get("payload")
        keyObserverDiagnostics = (
            payload.get("keyObserverDiagnostics", {})
            if isinstance(payload, dict) else {}
        )
        if not isinstance(keyObserverDiagnostics, dict):
            keyObserverDiagnostics = {}
        if isinstance(payload, dict):
            self._currentState = payload
            transport = payload.get("_transport")
            if isinstance(transport, dict) and isinstance(transport.get("capabilities"), list):
                self._transportCapabilities = frozenset(
                    value for value in transport["capabilities"] if isinstance(value, str)
                )
        self._diagnostics.record(
            "eventDispatch",
            type=event.get("type"),
            sessionId=event.get("sessionId"),
            sequence=event.get("sequence"),
            mode=payload.get("mode") if isinstance(payload, dict) else None,
            modeRaw=payload.get("modeRaw") if isinstance(payload, dict) else None,
            modeBlocking=(
                payload.get("modeBlocking") if isinstance(payload, dict) else None
            ),
            bufferId=payload.get("bufferId") if isinstance(payload, dict) else None,
            windowId=payload.get("windowId") if isinstance(payload, dict) else None,
            changedtick=payload.get("changedtick") if isinstance(payload, dict) else None,
            cursor=payload.get("cursor") if isinstance(payload, dict) else None,
            lineText=payload.get("lineText") if isinstance(payload, dict) else None,
            transport=payload.get("_transport") if isinstance(payload, dict) else None,
            preConnectErrorCode=(
                payload.get("preConnectErrorCode") if isinstance(payload, dict) else None
            ),
            preConnectErrorKind=(
                payload.get("preConnectErrorKind") if isinstance(payload, dict) else None
            ),
            currentErrorCode=(
                payload.get("currentErrorCode") if isinstance(payload, dict) else None
            ),
            currentErrorKind=(
                payload.get("currentErrorKind") if isinstance(payload, dict) else None
            ),
            keyObserverErrorCount=keyObserverDiagnostics.get("observerErrorCount"),
            keyObserverErrorKind=keyObserverDiagnostics.get("observerErrorKind"),
            keyClaimErrorKind=keyObserverDiagnostics.get("claimErrorKind"),
            keyClaimSkippedMode=keyObserverDiagnostics.get("claimSkippedMode"),
            keyModeAfterClaim=keyObserverDiagnostics.get("modeAfterClaim"),
            keyTranslated=keyObserverDiagnostics.get("translatedKey"),
            keyTypedTranslated=keyObserverDiagnostics.get("translatedTyped"),
            keyByteLength=keyObserverDiagnostics.get("keyByteLength"),
            keyTypedByteLength=keyObserverDiagnostics.get("typedByteLength"),
            keyPromptActive=keyObserverDiagnostics.get("promptActive"),
            keyPromptKind=keyObserverDiagnostics.get("promptKind"),
            keyPromptClass=keyObserverDiagnostics.get("promptClass"),
            keyPromptLength=keyObserverDiagnostics.get("promptLength"),
        )
        mode = payload.get("mode") if isinstance(payload, dict) else None
        previous_mode = self._lastMode
        if event.get("type") == "menuSelectionChanged" and isinstance(payload, dict):
            item = payload.get("item", {})
            documentation = item.get("documentation", "") if isinstance(item, dict) else ""
            self._menuDocumentation = documentation if isinstance(documentation, str) else ""
        elif event.get("type") == "menuClosed":
            self._menuDocumentation = ""
        event_type = event.get("type")
        if (
            event_type == "focusContext" and self._gate.manual_enabled
            and mode in {"insert", "normal"}
        ):
            self._playModeSound(mode, focus_context=True)
        elif event_type == "modeChanged" and mode == "insert" and self._lastMode != "insert":
            self._playModeSound(mode)
        elif event_type == "modeChanged" and mode == "normal" and self._lastMode == "insert":
            self._playModeSound(mode)
        if event.get("type") == "fullState" or (
            event.get("type") == "modeChanged" and mode != self._lastMode
        ):
            self._resetTypedEcho()
        if mode is not None:
            self._lastMode = mode
        if event.get("type") == "fullState":
            self._connected = True
            self._lastConnectionState = "connected"
            if self._gate.manual_enabled and self._gate.focused is not None:
                self._gate.authenticated = True
                self._gate.nvim_active = True
                self._gate.bound_terminal = self._gate.focused
                activated = True
        terminal_passthrough = (
            isinstance(payload, dict)
            and payload.get("buftype") == "terminal"
            and payload.get("mode") == "terminal"
        )
        if terminal_passthrough != self._gate.terminal_passthrough:
            self._gate.terminal_passthrough = terminal_passthrough
            self._diagnostics.record(
                "terminalPassthrough", enabled=terminal_passthrough,
                bufferId=payload.get("bufferId") if isinstance(payload, dict) else None,
            )
        if not self._gate.manual_enabled:
            return
        for action in self._planner.plan(
            event, focus_announcement=self._focusAnnouncement(),
        ):
            indentation = getattr(action, "indentation_tones", None)
            if indentation is not None:
                self._reportIndentation(indentation, getattr(action, "indentation_level", None))
            sound = getattr(action, "sound", None)
            feedback_key = _FEEDBACK_FOR_SOUND.get(sound)
            feedback_mode = self._feedbackMode(feedback_key) if feedback_key else 3
            play_action_sound = bool(feedback_mode & 2)
            if sound == "delete":
                if play_action_sound and not self._editorSounds.play("delete"):
                    tones.beep(180, 24)
            elif sound == "replace":
                if play_action_sound and not self._editorSounds.play("replace"):
                    tones.beep(440, 18)
                    tones.beep(620, 22)
            elif sound == "lineStart" and mode == "normal":
                if play_action_sound and not self._editorSounds.play("lineStart"):
                    tones.beep(720, 12)
            elif sound == "lineEnd" and mode == "normal":
                if play_action_sound and not self._editorSounds.play("lineEnd"):
                    tones.beep(360, 18)
            elif sound == "fileStart":
                if play_action_sound and not self._editorSounds.play("fileStart"):
                    tones.beep(520, 35)
            elif sound == "fileEnd":
                if play_action_sound and not self._editorSounds.play("fileEnd"):
                    tones.beep(260, 45)
            elif sound == "lineCrossed":
                if play_action_sound and not self._editorSounds.play("lineCrossed"):
                    tones.beep(610, 16)
            elif sound == "matchingError":
                if play_action_sound and not self._editorSounds.play("matchingError"):
                    tones.beep(190, 35)
            elif sound == "suggestionsOpen":
                self._suggestionSounds.play("open")
            elif sound == "suggestionsClose":
                self._suggestionSounds.play("close")
            if action.interrupt and action.priority < Priority.CRITICAL:
                speech.cancelSpeech()
            priority = {
                Priority.NAVIGATION: NvdaSpeechPriority.NORMAL,
                Priority.STATUS: NvdaSpeechPriority.NEXT,
                Priority.CRITICAL: NvdaSpeechPriority.NOW,
            }[action.priority]
            try:
                event_type = event.get("type")
                speech_allowed = self._actionSpeechAllowed(event_type, feedback_key)
                if event_type == "modeChanged" and {previous_mode, mode} <= {"normal", "insert"}:
                    speech_allowed = bool(self._feedbackMode("mode") & 1)
                if speech_allowed and feedback_key == "lineBoundary" and feedback_mode & 1 and not action.text:
                    speech.speakText(
                        _("line start") if sound == "lineStart" else _("line end"), priority=priority,
                    )
                elif speech_allowed and feedback_key == "lineCrossed" and feedback_mode & 1:
                    speech.speakText(_("new line"), priority=priority)
                format_error = getattr(action, "format_error", None)
                if format_error and speech_allowed:
                    formatting = config.conf.get("documentFormatting", {})
                    report_mode = int(formatting.get("reportSpellingErrors2", 0))
                    if getattr(action, "typed_format_error", False):
                        keyboard = config.conf.get("keyboard", {})
                        speech_state = speech.getState() if hasattr(speech, "getState") else None
                        speech_mode = str(getattr(speech_state, "speechMode", "on")).lower()
                        speech_active = not (speech_mode.endswith("off") or "ondemand" in speech_mode)
                        if report_mode and bool(keyboard.get("alertForSpellingErrors", True)) and speech_active:
                            self._spellingSound.play()
                    else:
                        leaving = format_error.startswith("out:")
                        kind = format_error[4:] if leaving else format_error
                        if not leaving and report_mode & 2:
                            self._spellingSound.play()
                        if (report_mode & 1) or (leaving and report_mode & 3):
                            label = "grammar error" if kind == "grammar" else "spelling error"
                            speech.speakText(("out of " if leaving else "") + label, priority=priority)
                elif getattr(action, "typed", False) and speech_allowed:
                    self._speakStructuredTyping(action.text, payload)
                elif getattr(action, "spelling", False) and speech_allowed:
                    speech.speakSpelling(action.text, priority=priority)
                elif action.text and speech_allowed:
                    kwargs = {"priority": priority}
                    if getattr(action, "force_symbols", False):
                        kwargs["symbolLevel"] = 300  # characterProcessing.SymbolLevel.ALL
                    speech.speakText(action.text, **kwargs)
                if speech_allowed and getattr(action, "character_suffix", None):
                    speech.speakSpelling(action.character_suffix, priority=priority)
                if getattr(action, "braille_message", None):
                    nvdaBraille.handler.message(action.braille_message)
            except Exception as error:
                self._diagnostics.record("speechError", errorType=type(error).__name__, error=str(error))
                log.exception("nvimNvdaAccess speech failure")
        if self._gate.suppression_active:
            self._refreshBraille(rebuild=activated)

    def _reportIndentation(self, quarterTones, level):
        formatting = config.conf.get("documentFormatting", {})
        # NVDA ReportLineIndentation: 0 off, 1 speech, 2 tones, 3 both.
        report_mode = int(formatting.get("reportLineIndentation", 0))
        if report_mode == 0:
            return
        if not isinstance(quarterTones, int) or quarterTones < 0:
            return
        if report_mode in (2, 3) and quarterTones <= 72:
            duration = int(formatting.get("indentToneDuration", 40))
            frequency = round(220 * (2 ** (quarterTones / 24.0)))
            tones.beep(frequency, duration)
            self._diagnostics.record(
                "indentationTone", quarterTones=quarterTones,
                frequency=frequency, durationMs=duration,
            )
        if report_mode in (1, 3) or quarterTones > 72:
            speech.speakText("no indent" if quarterTones == 0 else f"indentation level {level}")

    def _speakStructuredTyping(self, text, state=None):
        keyboard = config.conf["keyboard"]
        speak_characters = int(keyboard["speakTypedCharacters"]) != 0
        speak_words = int(keyboard["speakTypedWords"]) != 0
        cursor = state.get("cursor", {}) if isinstance(state, dict) else {}
        line = cursor.get("line") if isinstance(cursor, dict) else None
        byte_column = cursor.get("byteColumn") if isinstance(cursor, dict) else None
        buffer_id = state.get("bufferId") if isinstance(state, dict) else None
        byte_length = len(text.encode("utf-8")) if "\n" not in text else None
        start = byte_column - byte_length if isinstance(byte_column, int) and byte_length is not None else None
        identity = (buffer_id, line)
        if self._typedPosition is not None and isinstance(start, int) and isinstance(byte_column, int):
            previous_identity, previous_end = self._typedPosition
            if previous_identity == identity and start < previous_end <= byte_column:
                overlap = previous_end - start
                encoded = text.encode("utf-8")
                try:
                    text = encoded[overlap:].decode("utf-8")
                    start = previous_end
                except UnicodeDecodeError:
                    # A malformed overlap must never cause older text to be guessed.
                    self._typedWord = []
        if self._typedPosition is not None:
            previous_identity, previous_end = self._typedPosition
            if identity != previous_identity or start != previous_end:
                self._typedWord = []
        for character in text:
            if unicodedata.category(character)[:1] in {"L", "M", "N"}:
                self._typedWord.append(character)
            else:
                if self._typedWord and speak_words:
                    speech.speakText("".join(self._typedWord))
                self._typedWord = []
            if speak_characters:
                speech.speakSpelling(character)
        self._typedPosition = (identity, byte_column) if isinstance(byte_column, int) else None

    def _resetTypedEcho(self):
        self._typedWord = []
        self._typedPosition = None
        speech.clearTypedWordBuffer()

    def _refreshBraille(self, rebuild):
        try:
            focus = self._focusedTerminalObject
            if focus is None:
                return
            if rebuild:
                nvdaBraille.handler.handleGainFocus(focus, shouldAutoTether=False)
            else:
                nvdaBraille.handler.handleUpdate(focus)
        except Exception as error:
            self._diagnostics.record("brailleError", errorType=type(error).__name__, error=str(error))
            log.exception("nvimNvdaAccess braille failure")

    def _queueBrailleRefresh(self, rebuild):
        queueHandler.queueFunction(queueHandler.eventQueue, self._refreshBraille, rebuild)

    def _shouldSuppress(self, obj):
        identity = self._identity(obj)
        return identity is not None and self._gate.should_suppress(identity)

    def _routeBrailleCursor(self, byte_column):
        state = self._currentState
        capabilities = state.get("_transport", {}).get("capabilities", [])
        if "cursorRouting" not in capabilities:
            self._diagnostics.record("brailleRouteRejected", reason="capabilityMissing")
            return
        cursor = state.get("cursor", {})
        payload = {
            "bufferId": state.get("bufferId"),
            "windowId": state.get("windowId"),
            "line": cursor.get("line"),
            "byteColumn": byte_column,
            "changedtick": state.get("changedtick"),
        }
        if self._client is None or not all(isinstance(value, int) for value in payload.values()):
            self._diagnostics.record("brailleRouteRejected", reason="incompleteState", byteColumn=byte_column)
            return
        accepted = self._client.send_control("routeCursor", payload)
        self._diagnostics.record("brailleRoute", accepted=accepted, **payload)

    @staticmethod
    def _identity(obj):
        process_id = getattr(obj, "processID", None)
        window_handle = getattr(obj, "windowHandle", None)
        if not isinstance(process_id, int) or not isinstance(window_handle, int) or not window_handle:
            return None
        descriptor = _FRONTEND_POLICY.descriptor("windowsTerminal")
        if descriptor is None or not descriptor.enabled:
            return None
        candidate = obj
        for _depth in range(8):
            element = getattr(candidate, "UIAElement", None)
            if element is not None:
                try:
                    class_name = str(element.cachedClassName or "")
                    if class_name in descriptor.uia_class_names:
                        runtime_id = tuple(int(value) for value in element.getRuntimeId())
                        if runtime_id or not descriptor.requires_runtime_id:
                            candidate_process = getattr(candidate, "processID", process_id)
                            candidate_window = getattr(candidate, "windowHandle", window_handle)
                            if not isinstance(candidate_process, int) or not isinstance(candidate_window, int):
                                break
                            return TerminalIdentity(
                                candidate_process, candidate_window, "windowsTerminal", runtime_id,
                            )
                except Exception:
                    pass
            try:
                candidate = candidate.parent
            except Exception:
                break
            if candidate is None:
                break
        return None

    @staticmethod
    def _identityElement(obj, identity):
        candidate = obj
        for _depth in range(8):
            element = getattr(candidate, "UIAElement", None)
            if element is not None:
                try:
                    runtime_id = tuple(int(value) for value in element.getRuntimeId())
                    if runtime_id == identity.runtime_id:
                        return element
                except Exception:
                    pass
            try:
                candidate = candidate.parent
            except Exception:
                break
            if candidate is None:
                break
        return None

    @staticmethod
    def _identityFields(identity):
        return None if identity is None else {
            "processId": identity.process_id,
            "windowHandle": identity.window_handle,
            "frontendKind": identity.frontend_kind,
            "runtimeId": list(identity.runtime_id),
        }

    def _feedbackMode(self, key):
        feedback = self._settings.get("feedback", {})
        global_mode = feedback.get("global", _FEEDBACK_DEFAULTS["global"])
        local_mode = feedback.get(key, _FEEDBACK_DEFAULTS.get(key, 3)) if key else 3
        return int(global_mode) & int(local_mode)

    def _focusAnnouncement(self):
        value = self._settings.get("focusAnnouncement", _FOCUS_ANNOUNCEMENT_DEFAULT)
        if isinstance(value, int) and 0 <= value < len(_FOCUS_ANNOUNCEMENT_VALUES):
            return _FOCUS_ANNOUNCEMENT_VALUES[value]
        return _FOCUS_ANNOUNCEMENT_VALUES[_FOCUS_ANNOUNCEMENT_DEFAULT]

    def _playModeSound(self, mode, *, focus_context=False):
        if mode == "insert":
            if self._feedbackMode("mode") & 2 and not self._editorSounds.play("insertMode"):
                tones.beep(880, 45)
            self._diagnostics.record(
                "insertModeSound", cue="focusMode.wav", focusContext=focus_context,
            )
        elif mode == "normal":
            if not focus_context:
                speech.cancelSpeech()
            if self._feedbackMode("mode") & 2 and not self._editorSounds.play("normalMode"):
                tones.beep(330, 28)
            self._diagnostics.record(
                "normalModeSound", cue="browseMode.wav", focusContext=focus_context,
            )

    def _actionSpeechAllowed(self, event_type, feedback_key):
        if feedback_key in {"delete", "replace"} and event_type in {
            "textChanged", "textDeleted", "textReplaced", "replacementPerformed",
        }:
            return bool(self._feedbackMode(feedback_key) & 1)
        if feedback_key in {"fileBoundary", "matchingError"}:
            return bool(self._feedbackMode(feedback_key) & 1)
        return True

    def _loadSettings(self):
        try:
            section = config.conf[_NVDA_CONFIG_SECTION]
            connections_value = section.get("connections", "[]")
            if not isinstance(connections_value, str):
                raise ValueError("connections must be a JSON string")
            feedback_section = section.get("feedback", {})
            if not hasattr(feedback_section, "items"):
                raise ValueError("feedback must be an object")
            settings = {
                "schemaVersion": section.get("schemaVersion", 0),
                "connections": json.loads(connections_value),
                "focusAnnouncement": section.get(
                    "focusAnnouncement", _FOCUS_ANNOUNCEMENT_DEFAULT,
                ),
                # NVDA exposes nested configuration through AggregatedSection.
                # Iterating that object does not have normal mapping semantics,
                # while its public items() method does.
                "feedback": dict(feedback_section.items()),
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._diagnostics.record(
                "configError", errorType=type(error).__name__, error=str(error),
                source="nvdaConfig",
            )
            settings = {}
        try:
            schema_version = int(settings.get("schemaVersion", 0) or 0)
        except (TypeError, ValueError):
            schema_version = 0
            self._diagnostics.record("configError", error="invalid schemaVersion")
        if schema_version < _NATIVE_CONFIG_SCHEMA_VERSION:
            legacy = self._loadLegacySettings()
            if legacy is not None:
                normalized = self._normalizeSettings(legacy)
                try:
                    self._writeSettingsToNvda(normalized)
                    config.conf.save()
                    self._diagnostics.record(
                        "legacyConfigMigrated", schemaVersion=_NVDA_CONFIG_SCHEMA_VERSION,
                    )
                except Exception as error:
                    self._diagnostics.record(
                        "legacyConfigMigrationError",
                        errorType=type(error).__name__, error=str(error),
                    )
                return normalized
        return self._normalizeSettings(settings)

    def _loadLegacySettings(self):
        path = self._legacySettingsPath()
        try:
            # utf-8-sig accepts both normal UTF-8 and files written with the BOM
            # used by Windows PowerShell 5.1.
            with open(path, encoding="utf-8-sig") as settings_file:
                settings = json.load(settings_file)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as error:
            self._diagnostics.record("configError", errorType=type(error).__name__, error=str(error), path=path)
            return None
        if not isinstance(settings, dict):
            self._diagnostics.record("configError", error="top level must be an object", path=path)
            return None
        return settings

    def _normalizeSettings(self, settings):
        raw_feedback = settings.get("feedback", {})
        raw_connections = settings.get("connections")
        if not isinstance(raw_feedback, dict):
            self._diagnostics.record("configError", error="feedback must be an object")
            raw_feedback = {}
        feedback = dict(_FEEDBACK_DEFAULTS)
        for key in feedback:
            value = raw_feedback.get(key, feedback[key])
            if isinstance(value, int) and 0 <= value <= 3:
                feedback[key] = value
            else:
                self._diagnostics.record("configError", error="invalid feedback mode", option=key)
        try:
            connections = parse_profiles(raw_connections)
        except ValueError as error:
            self._diagnostics.record("configError", error=str(error), option="connections")
            connections = []
        focus_announcement = settings.get(
            "focusAnnouncement", _FOCUS_ANNOUNCEMENT_DEFAULT,
        )
        if not (
            isinstance(focus_announcement, int)
            and 0 <= focus_announcement < len(_FOCUS_ANNOUNCEMENT_VALUES)
        ):
            self._diagnostics.record(
                "configError", error="invalid focus announcement", option="focusAnnouncement",
            )
            focus_announcement = _FOCUS_ANNOUNCEMENT_DEFAULT
        return {
            "feedback": feedback,
            "focusAnnouncement": focus_announcement,
            "schemaVersion": _NVDA_CONFIG_SCHEMA_VERSION,
            "connections": [profile.as_dict() for profile in connections],
        }

    def _onNvdaConfigProfileSwitch(self, **_kwargs):
        previous = self._settings
        self._settings = self._loadSettings()
        connections_changed = previous.get("connections") != self._settings.get("connections")
        self._diagnostics.record(
            "nvdaConfigProfileSettingsReloaded",
            feedbackChanged=previous.get("feedback") != self._settings.get("feedback"),
            focusAnnouncementChanged=(
                previous.get("focusAnnouncement") != self._settings.get("focusAnnouncement")
            ),
            connectionsChanged=connections_changed,
        )
        if connections_changed and self._gate.manual_enabled:
            self._beginClaimInventory()

    def _connectionProfileById(self, identifier):
        try:
            return next(
                profile for profile in parse_profiles(self._settings.get("connections", []))
                if profile.identifier == identifier
            )
        except (StopIteration, ValueError):
            return None

    def _passwordForProfile(self, profile):
        if profile is None or profile.authentication != "password":
            return ""
        if profile.identifier in self._sessionPasswords:
            return self._sessionPasswords[profile.identifier]
        password = self._promptPassword(profile.name)
        if password is None:
            self._diagnostics.record("sshPasswordCancelled", profileId=profile.identifier)
            return None
        self._sessionPasswords[profile.identifier] = password
        return password

    @staticmethod
    def _promptPassword(profile_name):
        import gui
        import wx
        dialog = wx.PasswordEntryDialog(
            gui.mainFrame,
            _("Enter the SSH password for {profile}. It will not be saved.").format(profile=profile_name),
            _("Neovim SSH password"),
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return dialog.GetValue()
        finally:
            dialog.Destroy()

    @staticmethod
    def _askpassPath():
        return os.path.join(_PACKAGE_DIR, "resources", "ssh-askpass.cmd")

    def _clearSessionPasswords(self):
        self._sessionPasswords.clear()

    def _stopClient(self):
        self._pendingClaimTargets.clear()
        self._pendingObservedClaim = None
        self._claimInventoryGeneration += 1
        self._claimInventoryReady = False
        self._claimBaselines.clear()
        self._claimEligibleTargets.clear()
        self._claimInventoryErrors.clear()
        self._pendingFocusContexts.clear()
        self._pendingClipboardRequests.clear()
        if hasattr(self, "_instanceManager") and self._instanceManager.list():
            try:
                self._instanceManager.stop_all()
            finally:
                self._client = None
                self._connected = False
                self._rememberedTerminalBindings.clear()
                self._rememberOfferInstances.clear()
                self._authenticatedInstances.clear()
                self._instanceTerminalPassthrough.clear()
                self._instanceRuntimeStates.clear()
                self._pendingInstanceFullStates.clear()
                self._activeInstanceId = None
            self._diagnostics.record("clientInstancesStopped")
            return
        client = self._client
        self._client = None
        if client is None:
            return
        try:
            client.stop()
        except Exception as error:
            self._diagnostics.record("clientStopError", errorType=type(error).__name__, error=str(error))
            log.exception("nvimNvdaAccess client shutdown failed")
        self._connected = False
        self._diagnostics.record("clientStopped")

    @staticmethod
    def _legacySettingsPath():
        return os.path.join(globalVars.appArgs.configPath, "nvimNvdaAccess.json")

    @staticmethod
    def _writeSettingsToNvda(settings):
        section = config.conf[_NVDA_CONFIG_SECTION]
        section["schemaVersion"] = _NVDA_CONFIG_SCHEMA_VERSION
        section["focusAnnouncement"] = int(settings.get(
            "focusAnnouncement", _FOCUS_ANNOUNCEMENT_DEFAULT,
        ))
        section["connections"] = json.dumps(
            settings.get("connections", []), ensure_ascii=False, separators=(",", ":"),
        )
        feedback = section["feedback"]
        values = settings.get("feedback", {})
        for key, default in _FEEDBACK_DEFAULTS.items():
            feedback[key] = int(values.get(key, default))

    def _saveSettings(self):
        self._writeSettingsToNvda(self._settings)

    def _promptConnectionProfile(self, existing, profiles):
        values = dict(existing or {})
        while True:
            result = self._showConnectionProfileDialog(values)
            if result is None:
                return None
            values.update(result)
            try:
                port = int(result["port"])
            except ValueError:
                ui.message(_("SSH port must be a number between 1 and 65535"))
                continue
            identifier = values.get("id", "") or unique_profile_id(
                result["name"], {profile.get("id", "") for profile in profiles},
            )
            candidate = {
                "id": identifier, "name": result["name"].strip(), "host": result["host"].strip(),
                "user": result["user"].strip(), "port": port,
                "identityFile": result["identityFile"],
                "authentication": result["authentication"],
            }
            if candidate["authentication"] == "password":
                candidate["identityFile"] = ""
            try:
                return parse_profile(candidate).as_dict()
            except ValueError as error:
                self._diagnostics.record("connectionProfileValidationError", error=str(error))
                ui.message(_("The connection settings are invalid: {error}").format(error=str(error)))

    @staticmethod
    def _authenticationChoices():
        return (
            _("Use OpenSSH setup (recommended: keys, ssh-agent or SSH config)"),
            _("Ask for the SSH password when connecting (password is not saved)"),
        )

    @staticmethod
    def _authenticationDescription(authentication):
        if authentication == "password":
            return _(
                "NVDA asks for the Linux account password when it connects. "
                "The password stays in memory only and the Linux SSH server must allow password login."
            )
        return _(
            "OpenSSH uses the normal Windows SSH configuration, a selected private key, "
            "or ssh-agent. Choose this when ssh from Windows already works without a password prompt."
        )

    def _showConnectionProfileDialog(self, values):
        import gui
        import wx
        dialog = wx.Dialog(
            gui.mainFrame,
            title=_("Add Linux connection") if not values.get("id") else _("Edit Linux connection"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        try:
            outer = wx.BoxSizer(wx.VERTICAL)
            introduction = wx.StaticText(
                dialog,
                label=_(
                    "Save the Linux account used for Neovim. The same connection is used to "
                    "install the Linux components and to exchange accessibility data."
                ),
            )
            introduction.Wrap(560)
            outer.Add(introduction, 0, wx.EXPAND | wx.ALL, 10)
            grid = wx.FlexGridSizer(rows=0, cols=2, vgap=8, hgap=10)
            grid.AddGrowableCol(1, 1)

            def add_text(label, value, name):
                grid.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
                control = wx.TextCtrl(dialog, value=value, name=name)
                grid.Add(control, 1, wx.EXPAND)
                return control

            name = add_text(_("Connection name:"), values.get("name", ""), "connectionName")
            host = add_text(
                _("Server name, address or SSH alias:"), values.get("host", ""), "connectionHost",
            )
            user = add_text(
                _("Linux username (optional when defined by SSH config):"),
                values.get("user", ""), "connectionUser",
            )
            port = add_text(_("SSH port:"), str(values.get("port", 22)), "connectionPort")
            identity = add_text(
                _("Private key file (optional):"), values.get("identityFile", ""), "connectionIdentity",
            )
            grid.Add(wx.StaticText(dialog, label=_("Sign-in method:")), 0, wx.ALIGN_CENTER_VERTICAL)
            authentication = wx.Choice(dialog, choices=list(self._authenticationChoices()))
            authentication.SetSelection(1 if values.get("authentication") == "password" else 0)
            grid.Add(authentication, 1, wx.EXPAND)
            outer.Add(grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
            authentication_help = wx.StaticText(dialog)
            authentication_help.Wrap(560)
            outer.Add(authentication_help, 0, wx.EXPAND | wx.ALL, 10)

            def update_authentication(_event=None):
                method = "password" if authentication.GetSelection() == 1 else "openSsh"
                authentication_help.SetLabel(self._authenticationDescription(method))
                authentication_help.Wrap(560)
                identity.Enable(method == "openSsh")
                dialog.Layout()

            authentication.Bind(wx.EVT_CHOICE, update_authentication)
            update_authentication()
            buttons = dialog.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
            if buttons is not None:
                outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
            dialog.SetSizerAndFit(outer)
            dialog.SetMinSize((640, -1))
            dialog.CentreOnParent()
            name.SetFocus()
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return {
                "name": name.GetValue(), "host": host.GetValue(), "user": user.GetValue(),
                "port": port.GetValue(), "identityFile": identity.GetValue(),
                "authentication": "password" if authentication.GetSelection() == 1 else "openSsh",
            }
        finally:
            dialog.Destroy()

    @staticmethod
    def _profileChoiceLabel(value):
        try:
            profile = parse_profile(value)
            port = f":{profile.port}" if profile.port != 22 else ""
            return f"{profile.name} — {profile.ssh_target}{port}"
        except ValueError:
            return str(value.get("name", _("Invalid connection"))) if isinstance(value, dict) else _("Invalid connection")

    def _registerSettingsPanel(self):
        try:
            import wx
            from gui import guiHelper
            from gui.settingsDialogs import NVDASettingsDialog, SettingsPanel
            plugin = self
            labels = (
                ("global", _("&Global action feedback:")),
                ("mode", _("Insert and normal &mode changes:")),
                ("delete", _("&Deleting text:")),
                ("replace", _("&Replacing text:")),
                ("lineBoundary", _("Line &boundaries:")),
                ("fileBoundary", _("&File boundaries:")),
                ("lineCrossed", _("Crossing into another &line:")),
                ("matchingError", _("Missing matching &bracket:")),
                ("clipboard", _("Copy and &paste:")),
            )

            class NeovimNvdaSettingsPanel(SettingsPanel):
                title = _PRODUCT_NAME

                def makeSettings(self, sizer):
                    helper = guiHelper.BoxSizerHelper(self, sizer=sizer)
                    self.settingsNotebook = wx.Notebook(self)
                    helper.addItem(self.settingsNotebook)
                    general_page = wx.Panel(self.settingsNotebook)
                    feedback_page = wx.Panel(self.settingsNotebook)
                    connections_page = wx.Panel(self.settingsNotebook)
                    general_sizer = wx.BoxSizer(wx.VERTICAL)
                    feedback_sizer = wx.BoxSizer(wx.VERTICAL)
                    connections_sizer = wx.BoxSizer(wx.VERTICAL)
                    general_page.SetSizer(general_sizer)
                    feedback_page.SetSizer(feedback_sizer)
                    connections_page.SetSizer(connections_sizer)
                    self.settingsNotebook.AddPage(general_page, _("General"))
                    self.settingsNotebook.AddPage(feedback_page, _("Feedback"))
                    self.settingsNotebook.AddPage(connections_page, _("Connections"))
                    self.settingsTabLabels = (_("General"), _("Feedback"), _("Connections"))
                    general_helper = guiHelper.BoxSizerHelper(general_page, sizer=general_sizer)
                    feedback_helper = guiHelper.BoxSizerHelper(feedback_page, sizer=feedback_sizer)
                    connections_helper = guiHelper.BoxSizerHelper(connections_page, sizer=connections_sizer)

                    global_sizer = wx.StaticBoxSizer(wx.VERTICAL, general_page, label=_("Global action feedback"))
                    general_helper.addItem(global_sizer)
                    global_group = guiHelper.BoxSizerHelper(general_page, sizer=global_sizer)
                    choices = [_('Off'), _('Speech'), _('Tones'), _('Both Speech and Tones')]
                    self.feedbackControls = {}
                    feedback = plugin._settings.get("feedback", _FEEDBACK_DEFAULTS)
                    key, label = labels[0]
                    control = global_group.addLabeledControl(label, wx.Choice, choices=choices)
                    control.SetSelection(int(feedback.get(key, _FEEDBACK_DEFAULTS[key])))
                    self.feedbackControls[key] = control

                    focus_sizer = wx.StaticBoxSizer(
                        wx.VERTICAL, general_page, label=_("Session focus"),
                    )
                    general_helper.addItem(focus_sizer)
                    focus_group = guiHelper.BoxSizerHelper(general_page, sizer=focus_sizer)
                    self.focusAnnouncement = focus_group.addLabeledControl(
                        _("When focusing a Neovim session:"), wx.Choice,
                        choices=[
                            _("No announcement"),
                            _("Current line"),
                            _("Current context, mode and connection name"),
                        ],
                    )
                    self.focusAnnouncement.SetSelection(int(plugin._settings.get(
                        "focusAnnouncement", _FOCUS_ANNOUNCEMENT_DEFAULT,
                    )))

                    actions_sizer = wx.StaticBoxSizer(wx.VERTICAL, feedback_page, label=_("Individual actions"))
                    feedback_helper.addItem(actions_sizer)
                    actions_group = guiHelper.BoxSizerHelper(feedback_page, sizer=actions_sizer)
                    for key, label in labels[1:]:
                        control = actions_group.addLabeledControl(label, wx.Choice, choices=choices)
                        control.SetSelection(int(feedback.get(key, _FEEDBACK_DEFAULTS[key])))
                        self.feedbackControls[key] = control
                    note = wx.StaticText(
                        feedback_page,
                        label=_(
                            "Typing echo, indentation, suggestions, spelling and grammar continue to use NVDA settings."
                        ),
                    )
                    actions_group.addItem(note)

                    connection_sizer = wx.StaticBoxSizer(wx.VERTICAL, connections_page, label=_("Saved SSH connections"))
                    connections_helper.addItem(connection_sizer)
                    connection_group = guiHelper.BoxSizerHelper(connections_page, sizer=connection_sizer)
                    self.connectionProfiles = list(plugin._settings.get("connections", []))
                    self.connectionChoice = connection_group.addLabeledControl(
                        _("Saved &connections:"), wx.Choice,
                        choices=[
                            plugin._profileChoiceLabel(profile) for profile in self.connectionProfiles
                        ],
                    )
                    self.connectionChoice.SetSelection(0 if self.connectionProfiles else -1)
                    self.connectionChoice.Bind(wx.EVT_CHOICE, self._onConnectionSelection)
                    connection_buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
                    self.addConnectionButton = connection_buttons.addButton(connections_page, label=_("&Add connection..."))
                    self.editConnectionButton = connection_buttons.addButton(connections_page, label=_("&Edit connection..."))
                    self.removeConnectionButton = connection_buttons.addButton(connections_page, label=_("&Remove connection"))
                    self.addConnectionButton.Bind(wx.EVT_BUTTON, self._onAddConnection)
                    self.editConnectionButton.Bind(wx.EVT_BUTTON, self._onEditConnection)
                    self.removeConnectionButton.Bind(wx.EVT_BUTTON, self._onRemoveConnection)
                    connection_group.addItem(connection_buttons)
                    connection_group.addItem(wx.StaticText(
                        connections_page,
                        label=_(
                            "To install or update components, use the add-on command "
                            "in NVDA's Tools menu and select this computer or saved Linux connections."
                        ),
                    ))
                    self._updateConnectionButtons()

                def _onConnectionSelection(self, _event):
                    self._updateConnectionButtons()

                def _updateConnectionButtons(self):
                    selected = 0 <= self.connectionChoice.GetSelection() < len(self.connectionProfiles)
                    self.editConnectionButton.Enable(selected)
                    self.removeConnectionButton.Enable(selected)

                def _refreshConnections(self, selected_id=""):
                    self.connectionChoice.SetItems([
                        plugin._profileChoiceLabel(profile) for profile in self.connectionProfiles
                    ])
                    index = next((
                        position for position, profile in enumerate(self.connectionProfiles)
                        if profile.get("id") == selected_id
                    ), 0 if self.connectionProfiles else -1)
                    self.connectionChoice.SetSelection(index)
                    self._updateConnectionButtons()

                def _onAddConnection(self, _event):
                    profile = plugin._promptConnectionProfile(None, self.connectionProfiles)
                    if profile is None:
                        return
                    profiles = save_profile(self.connectionProfiles, profile)
                    self.connectionProfiles = [item.as_dict() for item in profiles]
                    self._refreshConnections(profile["id"])

                def _onEditConnection(self, _event):
                    index = self.connectionChoice.GetSelection()
                    if not 0 <= index < len(self.connectionProfiles):
                        return
                    original = self.connectionProfiles[index]
                    profile = plugin._promptConnectionProfile(original, self.connectionProfiles)
                    if profile is None:
                        return
                    profiles = save_profile(self.connectionProfiles, profile, original["id"])
                    self.connectionProfiles = [item.as_dict() for item in profiles]
                    self._refreshConnections(profile["id"])

                def _onRemoveConnection(self, _event):
                    index = self.connectionChoice.GetSelection()
                    if not 0 <= index < len(self.connectionProfiles):
                        return
                    identifier = self.connectionProfiles[index].get("id", "")
                    profiles = remove_profile(self.connectionProfiles, identifier)
                    self.connectionProfiles = [item.as_dict() for item in profiles]
                    self._refreshConnections()

                def onSave(self):
                    previous_connections = plugin._settings.get("connections", [])
                    plugin._settings["focusAnnouncement"] = self.focusAnnouncement.GetSelection()
                    plugin._settings["feedback"] = {
                        key: control.GetSelection() for key, control in self.feedbackControls.items()
                    }
                    plugin._settings["connections"] = list(self.connectionProfiles)
                    plugin._saveSettings()
                    connection_changed = previous_connections != plugin._settings["connections"]
                    if connection_changed and plugin._gate.manual_enabled:
                        plugin._beginClaimInventory()
                        ui.message(_("Saved connections changed; checking Neovim connections again"))

            NVDASettingsDialog.categoryClasses.append(NeovimNvdaSettingsPanel)
            self._settingsPanelClass = NeovimNvdaSettingsPanel
        except Exception as error:
            self._diagnostics.record("settingsPanelUnavailable", errorType=type(error).__name__, error=str(error))

    def _unregisterSettingsPanel(self):
        panel = self._settingsPanelClass
        self._settingsPanelClass = None
        if panel is None:
            return
        try:
            from gui.settingsDialogs import NVDASettingsDialog
            if panel in NVDASettingsDialog.categoryClasses:
                NVDASettingsDialog.categoryClasses.remove(panel)
        except Exception as error:
            self._diagnostics.record("settingsPanelRemoveError", errorType=type(error).__name__, error=str(error))

    def _installMenus(self):
        try:
            import gui
            import wx
            tray = gui.mainFrame.sysTrayIcon
            menu = tray.toolsMenu
            install_handler = self._onInstallServer
            install_item = menu.Append(
                wx.ID_ANY,
                _PRODUCT_NAME + _(': Install or update components...'),
            )
            tray.Bind(wx.EVT_MENU, install_handler, install_item)
            self._menuItems.append((tray, menu, install_item, install_handler, wx))
            remove_handler = self._onRemoveComponents
            remove_item = menu.Append(
                wx.ID_ANY,
                _PRODUCT_NAME + _(': Remove components...'),
            )
            tray.Bind(wx.EVT_MENU, remove_handler, remove_item)
            self._menuItems.append((tray, menu, remove_item, remove_handler, wx))
        except Exception as error:
            self._diagnostics.record("menuUnavailable", errorType=type(error).__name__, error=str(error))

    def _removeMenus(self):
        for tray, menu, item, handler, wx in self._menuItems:
            try:
                tray.Unbind(wx.EVT_MENU, item)
            except Exception:
                pass
            try:
                menu.Remove(item.GetId())
            except Exception:
                pass
        self._menuItems = []

    @staticmethod
    def _installProfileLabel(profile):
        method = _("OpenSSH keys or configuration") if profile.authentication == "openSsh" else _("password prompt")
        return _("{name}: {target}, port {port}, {method}").format(
            name=profile.name, target=profile.ssh_target, port=profile.port, method=method,
        )

    @staticmethod
    def _installTargetLabel(target):
        if isinstance(target, ConnectionTarget) and target.kind == LOCAL_WINDOWS_TCP:
            return _("This computer: local Windows Neovim plugin")
        return GlobalPlugin._installProfileLabel(target)

    @staticmethod
    def _installTargetSummary(target):
        if isinstance(target, ConnectionTarget) and target.kind == LOCAL_WINDOWS_TCP:
            return target.name, _("this computer")
        return target.name, target.ssh_target

    def _chooseComponentTargets(self, remove=False):
        import gui
        import wx
        from gui.nvdaControls import CustomCheckListBox
        try:
            profiles = parse_profiles(self._settings.get("connections", []))
        except ValueError as error:
            self._diagnostics.record("installProfileListError", error=str(error))
            ui.message(_("The saved Linux connections are invalid; correct them in settings first"))
            return None
        targets = [local_windows_target(_("This computer - local Neovim")), *profiles]
        dialog = wx.Dialog(
            gui.mainFrame,
            title=_("Remove Neovim components") if remove else _("Install or update Neovim components"),
        )
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(
            dialog,
            label=_(
                "Close Neovim on the selected targets, then choose where to remove the components. "
                "Other Neovim plugins and configuration are preserved."
            ) if remove else _(
                "Select one or more targets. Administrator rights are not required."
            ),
        )
        instructions.Wrap(620)
        outer_sizer.Add(instructions, 0, wx.ALL | wx.EXPAND, 12)
        select_all = wx.CheckBox(dialog, label=_("Select all connections"))
        outer_sizer.Add(select_all, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        list_label = wx.StaticText(
            dialog, label=_("Connections to remove components from:") if remove else _("Connections to update:"),
        )
        outer_sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT, 12)
        connection_list = CustomCheckListBox(
            dialog, choices=[self._installTargetLabel(target) for target in targets],
        )
        connection_list.SetName(
            _("Connections to remove components from") if remove else _("Connections to update")
        )
        outer_sizer.Add(connection_list, 1, wx.ALL | wx.EXPAND, 12)

        def on_select_all(_event):
            checked = select_all.IsChecked()
            for index in range(len(targets)):
                connection_list.Check(index, checked)

        def on_connection_checked(event):
            event.Skip()
            select_all.SetValue(all(connection_list.IsChecked(index) for index in range(len(targets))))

        select_all.Bind(wx.EVT_CHECKBOX, on_select_all)
        connection_list.Bind(wx.EVT_CHECKLISTBOX, on_connection_checked)
        outer_sizer.Add(dialog.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL | wx.ALIGN_RIGHT, 12)
        dialog.SetSizerAndFit(outer_sizer)
        dialog.SetMinSize((680, 360))
        select_all.SetFocus()
        try:
            while dialog.ShowModal() == wx.ID_OK:
                selected = [targets[index] for index in connection_list.GetCheckedItems()]
                if selected:
                    return selected
                wx.MessageBox(
                    _("Select at least one target to remove components from.") if remove else _(
                        "Select at least one target to update."
                    ),
                    _("No target selected"), wx.OK | wx.ICON_WARNING, dialog,
                )
                select_all.SetFocus()
            return None
        finally:
            dialog.Destroy()

    def _chooseInstallProfiles(self):
        return self._chooseComponentTargets(remove=False)

    def _chooseUninstallProfiles(self):
        return self._chooseComponentTargets(remove=True)

    def _onInstallServer(self, _event):
        targets = self._chooseInstallProfiles()
        if targets is None:
            return
        jobs = []
        immediate_results = []
        for profile in targets:
            if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
                jobs.append((profile, ""))
                continue
            password = self._passwordForProfile(profile)
            if profile.authentication == "password" and password is None:
                immediate_results.append((profile, InstallResult(False, _("SSH password entry cancelled"))))
                continue
            jobs.append((profile, password or ""))
        if not jobs:
            self._finishServerInstalls(immediate_results)
            return
        ui.message(
            _("Updating Neovim components on {count} targets").format(count=len(jobs))
        )
        package = os.path.join(_PACKAGE_DIR, "resources", "server-user.tar.gz")
        local_plugin = os.path.join(_PACKAGE_DIR, "resources", "neovim-plugin")
        threading.Thread(
            target=self._runServerInstalls,
            args=(jobs, package, immediate_results, local_plugin),
            daemon=True,
        ).start()

    def _runServerInstalls(self, jobs, package, initial_results=None, local_plugin=""):
        results = list(initial_results or [])
        installer = SshUserInstaller()
        local_installer = LocalPluginInstaller()
        package_path = __import__("pathlib").Path(package)
        total = len(jobs) + len(results)
        completed = len(results)
        for profile, password in jobs:
            try:
                if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
                    result = local_installer.install(__import__("pathlib").Path(local_plugin))
                else:
                    result = installer.install(
                        profile.ssh_target, package_path, profile.port, profile.identity_file,
                        password, self._askpassPath(),
                    )
            except Exception as error:
                result = InstallResult(
                    False, _("Unexpected installation error"),
                    "{kind}: {message}".format(kind=type(error).__name__, message=error),
                )
            results.append((profile, result))
            self._diagnostics.record(
                "componentInstall", targetId=profile.identifier,
                targetKind=(profile.kind if isinstance(profile, ConnectionTarget) else "remoteSsh"),
                success=result.success, message=result.message, diagnostics=result.diagnostics,
            )
            completed += 1
            queueHandler.queueFunction(
                queueHandler.eventQueue, self._reportServerInstallProgress,
                profile, result, completed, total,
            )
        queueHandler.queueFunction(queueHandler.eventQueue, self._finishServerInstalls, results)

    def _reportServerInstallProgress(self, profile, result, completed, total):
        name = self._installTargetSummary(profile)[0]
        if result.success:
            ui.message(_("{name} updated, {completed} of {total}").format(
                name=name, completed=completed, total=total,
            ))
        else:
            ui.message(_("{name} failed, {completed} of {total}").format(
                name=name, completed=completed, total=total,
            ))

    @staticmethod
    def _installResultSummary(results):
        successful = [(profile, result) for profile, result in results if result.success]
        failed = [(profile, result) for profile, result in results if not result.success]
        lines = [_('Neovim component update completed.')]
        lines.extend(("", _("Successful: {count}").format(count=len(successful))))
        lines.extend(_("- {name} ({target})").format(
            name=GlobalPlugin._installTargetSummary(profile)[0],
            target=GlobalPlugin._installTargetSummary(profile)[1],
        ) for profile, _result in successful)
        lines.extend(("", _("Failed: {count}").format(count=len(failed))))
        lines.extend(_("- {name} ({target}): {reason}").format(
            name=GlobalPlugin._installTargetSummary(profile)[0],
            target=GlobalPlugin._installTargetSummary(profile)[1], reason=result.message,
        ) for profile, result in failed)
        if successful:
            lines.extend(("", _("Restart Neovim once on successfully updated targets.")))
        return "\n".join(lines)

    def _finishServerInstalls(self, results):
        import gui
        successful = len([result for _profile, result in results if result.success])
        failed = len(results) - successful
        if successful:
            self._saveSettings()
        ui.message(_(
            "Neovim component update completed: {successful} successful, {failed} failed"
        ).format(successful=successful, failed=failed))
        message = self._installResultSummary(results)
        dialog = gui.MessageDialog(
            gui.mainFrame, message, _("Neovim component update results"),
        )
        dialog.Show()

    def _onRemoveComponents(self, _event):
        targets = self._chooseUninstallProfiles()
        if targets is None:
            return
        jobs = []
        immediate_results = []
        for profile in targets:
            if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
                jobs.append((profile, ""))
                continue
            password = self._passwordForProfile(profile)
            if profile.authentication == "password" and password is None:
                immediate_results.append((profile, InstallResult(False, _("SSH password entry cancelled"))))
                continue
            jobs.append((profile, password or ""))
        if not jobs:
            self._finishComponentRemovals(immediate_results)
            return
        ui.message(
            _("Removing Neovim components from {count} targets").format(count=len(jobs))
        )
        threading.Thread(
            target=self._runComponentRemovals,
            args=(jobs, immediate_results),
            daemon=True,
        ).start()

    def _runComponentRemovals(self, jobs, initial_results=None):
        results = list(initial_results or [])
        installer = SshUserInstaller()
        local_installer = LocalPluginInstaller()
        total = len(jobs) + len(results)
        completed = len(results)
        for profile, password in jobs:
            try:
                if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
                    result = local_installer.uninstall()
                else:
                    result = installer.uninstall(
                        profile.ssh_target, profile.port, profile.identity_file,
                        password, self._askpassPath(),
                    )
            except Exception as error:
                result = InstallResult(
                    False, _("Unexpected removal error"),
                    "{kind}: {message}".format(kind=type(error).__name__, message=error),
                )
            results.append((profile, result))
            self._diagnostics.record(
                "componentRemoval", targetId=profile.identifier,
                targetKind=(profile.kind if isinstance(profile, ConnectionTarget) else "remoteSsh"),
                success=result.success, message=result.message, diagnostics=result.diagnostics,
            )
            completed += 1
            queueHandler.queueFunction(
                queueHandler.eventQueue, self._reportComponentRemovalProgress,
                profile, result, completed, total,
            )
        queueHandler.queueFunction(queueHandler.eventQueue, self._finishComponentRemovals, results)

    def _reportComponentRemovalProgress(self, profile, result, completed, total):
        name = self._installTargetSummary(profile)[0]
        if result.success:
            ui.message(_("{name} removed, {completed} of {total}").format(
                name=name, completed=completed, total=total,
            ))
        else:
            ui.message(_("{name} failed, {completed} of {total}").format(
                name=name, completed=completed, total=total,
            ))

    @staticmethod
    def _componentRemovalResultSummary(results):
        successful = [(profile, result) for profile, result in results if result.success]
        failed = [(profile, result) for profile, result in results if not result.success]
        lines = [_('Neovim component removal completed.')]
        lines.extend(("", _("Successful: {count}").format(count=len(successful))))
        lines.extend(_("- {name} ({target})").format(
            name=GlobalPlugin._installTargetSummary(profile)[0],
            target=GlobalPlugin._installTargetSummary(profile)[1],
        ) for profile, _result in successful)
        lines.extend(("", _("Failed: {count}").format(count=len(failed))))
        lines.extend(_("- {name} ({target}): {reason}").format(
            name=GlobalPlugin._installTargetSummary(profile)[0],
            target=GlobalPlugin._installTargetSummary(profile)[1], reason=result.message,
        ) for profile, result in failed)
        lines.extend(("", _("Saved connection settings were preserved.")))
        return "\n".join(lines)

    def _finishComponentRemovals(self, results):
        import gui
        successful = len([result for _profile, result in results if result.success])
        failed = len(results) - successful
        ui.message(_(
            "Neovim component removal completed: {successful} successful, {failed} failed"
        ).format(successful=successful, failed=failed))
        dialog = gui.MessageDialog(
            gui.mainFrame, self._componentRemovalResultSummary(results),
            _("Neovim component removal results"),
        )
        dialog.Show()
