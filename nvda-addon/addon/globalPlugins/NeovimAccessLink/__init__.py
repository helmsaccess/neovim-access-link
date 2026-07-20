"""NVDA 2026.1 global plugin for structured Neovim accessibility."""

import json
import os
import sys
import threading
import time
import unicodedata
import array

import addonHandler
import api
import braille as nvdaBraille
import buildVersion
import config
import globalPluginHandler
import globalVars
import queueHandler
import speech
import tones
import ui
from logHandler import log
from speech.priorities import SpeechPriority as NvdaSpeechPriority


_TERMINAL_LIFECYCLE_INTERVAL_MS = 5 * 60 * 1_000


def _windowIdentityExists(identity):
	"""Return True/False for a conclusive HWND check, or None on uncertainty."""
	from .nvda_windows import windowIdentityExists

	return windowIdentityExists(identity)


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

# Bundled modules are importable only after the vendor path is installed.
from .core.stdio_client import SshStdioClient  # noqa: E402
from .core.local_client import LocalTcpClient  # noqa: E402
from .core.clipboard import (  # noqa: E402
	MAX_CLIPBOARD_TEXT_BYTES,
	clipboard_result_state,
	valid_clipboard_text,
	valid_request_id,
)
from .core.terminal_control import terminal_control_result_state  # noqa: E402
from .core.braille import plan_braille, source_offset_for_expanded  # noqa: E402
from .core.diagnostics import DiagnosticBuffer  # noqa: E402
from .core.connection_profiles import (  # noqa: E402
	parse_profile,
	parse_profiles,
)
from .core.connection_coordinator import ConnectionCoordinator, PendingControlRequest  # noqa: E402
from .core.connection_targets import (  # noqa: E402
	LOCAL_WINDOWS_TCP,
	local_windows_target,
	remote_ssh_target,
)
from .core.frontend_policy import FrontendPolicy  # noqa: E402
from .core.gate import SessionGate, TerminalIdentity  # noqa: E402
from .core.speech import SpeechPlanner  # noqa: E402
from .core.ssh_sessions import SshSessionLister  # noqa: E402
from .core.local_sessions import LocalSessionLister  # noqa: E402
from .core.service_registrar import ServiceRegistrar  # noqa: E402
from .nvda_windows import processAlive  # noqa: E402
from .terminal_integration import (  # noqa: E402
	SessionClaimAuthorization as SessionClaimAuthorization,
	TerminalCommand as TerminalCommand,
	TerminalIntegrationService,
)
from .settings_service import SettingsService  # noqa: E402
from .managed_clients import ManagedClientFactory  # noqa: E402
from .session_claim import (  # noqa: E402
	ClaimTransitionKind,
	DiscoverySelectionKind,
	RememberedBindingActivationKind,
	RememberedStateRequestKind,
	SessionClaimService,
	TemporaryBindingOfferKind,
)
from .terminal_focus import (  # noqa: E402
	TerminalFocusDecision as TerminalFocusDecision,
	TerminalFocusService,
)

addonHandler.initTranslation()

# These modules contain translated class text and must follow translation setup.
from .nvda_ui import NvdaUiManager  # noqa: E402
from .nvda_presentation import NvdaPresentation  # noqa: E402


_CODE_ADDON = addonHandler.getCodeAddon()
_ADDON_MANIFEST = _CODE_ADDON.manifest
_ADDON_ID = _ADDON_MANIFEST["name"]
_PRODUCT_NAME = _ADDON_MANIFEST["summary"]
try:
	from .build_info import ARTIFACT_VERSION as _ADDON_VERSION
except ImportError:
	_ADDON_VERSION = _ADDON_MANIFEST["version"]

_serviceRegistrar = ServiceRegistrar()


def getTerminalIntegrationService():
	"""Return the narrow service published for application-specific adapters."""
	return _serviceRegistrar.current


def _localSessionLister():
	"""Create the neutral lister with NVDA's Windows process adapter."""
	return LocalSessionLister(process_alive=processAlive)


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
_MAX_PENDING_TERMINAL_CONTROL_REQUESTS = 16


def _frontendPolicy():
	fallback = {
		"format": 1,
		"frontends": [
			{
				"kind": "windowsTerminal",
				"status": "enabled",
				"appModule": "windowsterminal",
				"uiaClassNames": ["TermControl", "WPFTermControl"],
				"requiresRuntimeId": True,
			}
		],
	}
	try:
		path = os.path.join(_PACKAGE_DIR, "resources", "frontend-policy.json")
		with open(path, "r", encoding="utf-8") as stream:
			return FrontendPolicy.from_mapping(json.load(stream))
	except (OSError, ValueError, TypeError, json.JSONDecodeError):
		return FrontendPolicy.from_mapping(fallback)


_FRONTEND_POLICY = _frontendPolicy()


def _identityForObject(obj):
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
							candidate_process,
							candidate_window,
							"windowsTerminal",
							runtime_id,
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


def _identityElementForObject(obj, identity):
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


def _terminalIdentityFields(identity):
	return (
		None
		if identity is None
		else {
			"processId": identity.process_id,
			"windowHandle": identity.window_handle,
			"frontendKind": identity.frontend_kind,
			"runtimeId": list(identity.runtime_id),
		}
	)


_FEEDBACK_DEFAULTS = {
	"global": 3,
	"mode": 3,
	"delete": 3,
	"replace": 3,
	"lineBoundary": 2,
	"fileBoundary": 3,
	"lineCrossed": 2,
	"matchingError": 3,
	"clipboard": 3,
}
_FEEDBACK_FOR_SOUND = {
	"delete": "delete",
	"replace": "replace",
	"lineStart": "lineBoundary",
	"lineEnd": "lineBoundary",
	"fileStart": "fileBoundary",
	"fileEnd": "fileBoundary",
	"lineCrossed": "lineCrossed",
	"matchingError": "matchingError",
}
_FOCUS_ANNOUNCEMENT_VALUES = ("none", "line", "context")
_FOCUS_ANNOUNCEMENT_DEFAULT = 2
_NVDA_CONFIG_SECTION = "NeovimAccessLink"
_NVDA_CONFIG_SPEC = {
	"connections": 'string(default="[]")',
	"focusAnnouncement": f"integer(default={_FOCUS_ANNOUNCEMENT_DEFAULT}, min=0, max=2)",
	"feedback": {key: f"integer(default={value}, min=0, max=3)" for key, value in _FEEDBACK_DEFAULTS.items()},
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
		service = getTerminalIntegrationService()
		try:
			state = service.braille_state(self.obj) if service is not None else {}
		except Exception:
			state = {}
		self._state = state
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
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.should_suppress_braille(self.obj)
		except Exception:
			suppressed = False
		if not suppressed:
			return
		if not 0 <= braillePos < len(self.brailleToRawPos):
			service.record_braille_route_rejection("outOfRange", braillePos)
			return
		expanded_offset = self.brailleToRawPos[braillePos]
		if self._plan.routing_byte_columns is not None:
			if not 0 <= expanded_offset < len(self._plan.routing_byte_columns):
				service.record_braille_route_rejection("semanticOutOfRange", braillePos)
				return
			byte_column = self._plan.routing_byte_columns[expanded_offset]
			if byte_column is None:
				service.record_braille_route_rejection("semanticStatus", braillePos)
				return
		else:
			source_offset = source_offset_for_expanded(self._plan, expanded_offset)
			line = self._state.get("lineText", "")
			byte_column = len(line[:source_offset].encode("utf-8"))
		service.route_braille_cursor(self.obj, byte_column)


class StructuredTerminalBrailleOverlay:
	def _reportNewLines(self, lines):
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.suppress_terminal_live_text(self, len(lines))
		except Exception:
			suppressed = False
		if suppressed:
			return
		return super()._reportNewLines(lines)

	def getBrailleRegions(self, review=False):
		service = getTerminalIntegrationService()
		try:
			suppressed = service is not None and service.should_suppress_braille(self)
		except Exception:
			suppressed = False
		if review or not suppressed:
			raise NotImplementedError
		# Return a concrete iterable. A yield would turn this into a generator
		# and defer NotImplementedError until outside NVDA's fallback try block.
		return (StructuredLineRegion(self),)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		self._serviceRegistrationToken = None
		self._diagnostics = DiagnosticBuffer()
		_registerNvdaConfigSpec()
		self._settingsService = SettingsService(
			config.conf,
			section_name=_NVDA_CONFIG_SECTION,
			feedback_defaults=_FEEDBACK_DEFAULTS,
			focus_announcement_values=_FOCUS_ANNOUNCEMENT_VALUES,
			focus_announcement_default=_FOCUS_ANNOUNCEMENT_DEFAULT,
			record_diagnostic=self._diagnostics.record,
			on_connections_changed=self._onSettingsConnectionsChanged,
		)
		self._presentation = NvdaPresentation(
			os.path.join(globalVars.appDir, "waves"),
			os.path.join(_PACKAGE_DIR, "resources", "sounds"),
			self._settingsService.snapshot,
			_FEEDBACK_DEFAULTS,
			_FEEDBACK_FOR_SOUND,
			self._diagnostics.record,
		)
		self._connectionCoordinator = ConnectionCoordinator(
			gate=SessionGate(_FRONTEND_POLICY.enabled_kinds),
			planner=SpeechPlanner(translate=_),
		)
		self._sessionPasswords = {}
		self._pendingMainThreadCalls = set()
		managed_client_factory = ManagedClientFactory(
			local_client_constructor=lambda *args, **kwargs: LocalTcpClient(*args, **kwargs),
			ssh_client_constructor=lambda *args, **kwargs: SshStdioClient(*args, **kwargs),
			on_event=self._onManagedEvent,
			on_state=self._onManagedState,
			record_network_diagnostic=self._recordNetworkDiagnostic,
		)
		self._sessionClaimService = SessionClaimService(
			self._connectionCoordinator,
			record_diagnostic=self._diagnostics.record,
			identity_fields=_terminalIdentityFields,
			list_local_sessions=self._listLocalClaimSessions,
			list_remote_sessions=self._listRemoteClaimSessions,
			queue_main_thread=self._queueClaimResult,
			start_worker=self._startClaimWorker,
			monotonic=time.monotonic,
			sleep=time.sleep,
			local_claim_wait_seconds=_LOCAL_CLAIM_WAIT_SECONDS,
			local_claim_poll_seconds=_LOCAL_CLAIM_POLL_SECONDS,
			new_instance_runtime=self._newInstanceRuntime,
			stop_client_async=lambda instance_id, client: self._stopManagedClientAsync(
				instance_id,
				client,
			),
			client_factory=managed_client_factory,
		)
		self._terminalFocusService = TerminalFocusService(
			self._connectionCoordinator,
			identity_for_object=_identityForObject,
			identity_element=_identityElementForObject,
			identity_fields=_terminalIdentityFields,
			record_diagnostic=self._diagnostics.record,
			discard_transient_context=self._discardTransientFocusContext,
			activate_remembered_binding=self._activateRememberedBinding,
			consume_temporary_binding_reactivation=(
				self._sessionClaimService.consume_temporary_binding_reactivation
			),
			handle_pending_full_state=self._handleManagedEvent,
			reset_typed_echo=self._resetTypedEcho,
			cancel_speech=speech.cancelSpeech,
			schedule_main_thread_call=self._scheduleMainThreadCall,
			identity_exists=_terminalIdentityExists,
			monotonic=time.monotonic,
			lifecycle_interval_ms=_TERMINAL_LIFECYCLE_INTERVAL_MS,
			new_instance_runtime=self._newInstanceRuntime,
			stop_client_async=self._stopManagedClientAsync,
			log_lifecycle_failure=self._logTerminalLifecycleFailure,
		)
		self._nvdaUi = NvdaUiManager(
			self._settingsService,
			record_diagnostic=self._diagnostics.record,
			password_for_profile=self._passwordForProfile,
			askpass_path=self._askpassPath,
			product_name=_PRODUCT_NAME,
			package_dir=_PACKAGE_DIR,
			feedback_defaults=_FEEDBACK_DEFAULTS,
			focus_announcement_default=_FOCUS_ANNOUNCEMENT_DEFAULT,
		)
		config.post_configProfileSwitch.register(self._settingsService.handle_profile_switch)
		settings = self._settingsService.snapshot()
		self._diagnostics.record(
			"addonStart",
			nvdaVersion=getattr(buildVersion, "version", "unknown"),
			configured=bool(settings.get("connections")),
		)
		log.info("%s %s initialized", _ADDON_ID, _ADDON_VERSION)
		self._nvdaUi.register()
		self._terminalIntegrationService = TerminalIntegrationService(
			self,
			self._terminalFocusService,
			self._sessionClaimService,
		)
		self._serviceRegistrationToken = _serviceRegistrar.publish(self._terminalIntegrationService)

	@property
	def _instanceManager(self):
		"""Compatibility view while connection behavior moves into its coordinator."""
		return self._connectionCoordinator.instances

	@property
	def _pendingClaimTargets(self):
		return self._sessionClaimService.pending_targets

	@_pendingClaimTargets.setter
	def _pendingClaimTargets(self, value):
		self._sessionClaimService.pending_targets = value

	@property
	def _pendingObservedClaim(self):
		return self._sessionClaimService.pending_observed

	@_pendingObservedClaim.setter
	def _pendingObservedClaim(self, value):
		self._sessionClaimService.pending_observed = value

	@property
	def _claimInventoryGeneration(self):
		return self._sessionClaimService.inventory_generation

	@_claimInventoryGeneration.setter
	def _claimInventoryGeneration(self, value):
		self._sessionClaimService.inventory_generation = value

	@property
	def _claimInventoryReady(self):
		return self._sessionClaimService.inventory_ready

	@_claimInventoryReady.setter
	def _claimInventoryReady(self, value):
		self._sessionClaimService.inventory_ready = value

	@property
	def _claimBaselines(self):
		return self._sessionClaimService.baselines

	@_claimBaselines.setter
	def _claimBaselines(self, value):
		self._sessionClaimService.baselines = value

	@property
	def _claimEligibleTargets(self):
		return self._sessionClaimService.eligible_targets

	@_claimEligibleTargets.setter
	def _claimEligibleTargets(self, value):
		self._sessionClaimService.eligible_targets = value

	@property
	def _claimInventoryErrors(self):
		return self._sessionClaimService.inventory_errors

	@_claimInventoryErrors.setter
	def _claimInventoryErrors(self, value):
		self._sessionClaimService.inventory_errors = value

	@property
	def _sessionDiscoveryGeneration(self):
		return self._sessionClaimService.discovery_generation

	@_sessionDiscoveryGeneration.setter
	def _sessionDiscoveryGeneration(self, value):
		self._sessionClaimService.discovery_generation = value

	@property
	def _gate(self):
		return self._connectionCoordinator.gate

	@property
	def _suggestionSounds(self):
		return self._presentation.suggestion_sounds

	@property
	def _spellingSound(self):
		return self._presentation.spelling_sound

	@property
	def _editorSounds(self):
		return self._presentation.editor_sounds

	@property
	def _planner(self):
		return self._connectionCoordinator.planner

	@_planner.setter
	def _planner(self, value):
		self._connectionCoordinator.planner = value

	@property
	def _currentState(self):
		return self._connectionCoordinator.current_state

	@_currentState.setter
	def _currentState(self, value):
		self._connectionCoordinator.current_state = value

	@property
	def _lastMode(self):
		return self._connectionCoordinator.last_mode

	@_lastMode.setter
	def _lastMode(self, value):
		self._connectionCoordinator.last_mode = value

	@property
	def _typedWord(self):
		return self._connectionCoordinator.typed_word

	@_typedWord.setter
	def _typedWord(self, value):
		self._connectionCoordinator.typed_word = value

	@property
	def _typedPosition(self):
		return self._connectionCoordinator.typed_position

	@_typedPosition.setter
	def _typedPosition(self, value):
		self._connectionCoordinator.typed_position = value

	@property
	def _menuDocumentation(self):
		return self._connectionCoordinator.menu_documentation

	@_menuDocumentation.setter
	def _menuDocumentation(self, value):
		self._connectionCoordinator.menu_documentation = value

	@property
	def _client(self):
		return self._connectionCoordinator.active_client

	@_client.setter
	def _client(self, value):
		self._connectionCoordinator.active_client = value

	@property
	def _lastConnectionState(self):
		return self._connectionCoordinator.last_connection_state

	@_lastConnectionState.setter
	def _lastConnectionState(self, value):
		self._connectionCoordinator.last_connection_state = value

	@property
	def _connected(self):
		return self._connectionCoordinator.connected

	@_connected.setter
	def _connected(self, value):
		self._connectionCoordinator.connected = value

	@property
	def _rememberedTerminalBindings(self):
		return self._connectionCoordinator.remembered_terminal_bindings

	@property
	def _rememberOfferInstances(self):
		return self._connectionCoordinator.remember_offer_instances

	@property
	def _authenticatedInstances(self):
		return self._connectionCoordinator.authenticated_instances

	@property
	def _instanceTerminalPassthrough(self):
		return self._connectionCoordinator.terminal_passthrough

	@property
	def _activeInstanceId(self):
		return self._connectionCoordinator.active_instance_id

	@_activeInstanceId.setter
	def _activeInstanceId(self, value):
		self._connectionCoordinator.active_instance_id = value

	@property
	def _instanceRuntimeStates(self):
		return self._connectionCoordinator.runtime_states

	@property
	def _pendingInstanceFullStates(self):
		return self._connectionCoordinator.pending_full_states

	@property
	def _pendingFocusContexts(self):
		return self._connectionCoordinator.pending_focus_contexts

	@property
	def _pendingClipboardRequests(self):
		return self._connectionCoordinator.pending_clipboard_requests

	@property
	def _pendingTerminalControlRequests(self):
		return self._connectionCoordinator.pending_terminal_control_requests

	@property
	def _transportCapabilities(self):
		return self._connectionCoordinator.transport_capabilities

	@_transportCapabilities.setter
	def _transportCapabilities(self, value):
		self._connectionCoordinator.transport_capabilities = value

	@property
	def _focusedTerminalObject(self):
		return self._terminalFocusService.focused_terminal_object

	@_focusedTerminalObject.setter
	def _focusedTerminalObject(self, value):
		self._terminalFocusService.focused_terminal_object = value

	@property
	def _focusedAppModule(self):
		return self._terminalFocusService.focused_app_module

	@property
	def _focusedAdapterToken(self):
		return self._terminalFocusService.focused_adapter_token

	def terminate(self):
		_serviceRegistrar.unpublish(self._terminalIntegrationService, self._serviceRegistrationToken)
		self._serviceRegistrationToken = None
		for pending in tuple(self._pendingMainThreadCalls):
			try:
				pending.Stop()
			except Exception:
				pass
		self._pendingMainThreadCalls.clear()
		self._gate.disable()
		config.post_configProfileSwitch.unregister(self._settingsService.handle_profile_switch)
		self._clearSessionPasswords()
		self._stopClient()
		try:
			self._instanceManager.stop_all()
		except Exception as error:
			self._diagnostics.record("connectionInstancesStopError", error=str(error))
		self._connectionCoordinator.clear_runtime_tracking()
		self._terminalFocusService.clear()
		self._connectionCoordinator.discard_focus_context()
		self._discardClipboardRequests()
		self._discardTerminalControlRequests()
		self._sessionClaimService.cancel_pending_authorization()
		self._nvdaUi.unregister()
		self._presentation.close()
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
				"delayedActionStarted",
				action=getattr(callback, "__name__", "unknown"),
			)
			callback(*args)

		pending = wx.CallLater(delay_ms, invoke)
		holder[0] = pending
		if pending is not None:
			self._pendingMainThreadCalls.add(pending)
		self._diagnostics.record(
			"delayedActionScheduled",
			action=getattr(callback, "__name__", "unknown"),
			delayMs=delay_ms,
		)
		return pending

	def _ensureTerminalLifecycleSweep(self):
		self._terminalFocusService.ensure_lifecycle_sweep()

	def _runTerminalLifecycleSweep(self):
		self._terminalFocusService.run_lifecycle_sweep()

	@property
	def _terminalLifecycleScheduledAt(self):
		return self._terminalFocusService.lifecycle_scheduled_at

	@_terminalLifecycleScheduledAt.setter
	def _terminalLifecycleScheduledAt(self, value):
		self._terminalFocusService.lifecycle_scheduled_at = value

	def action_toggleNeovimMode(self, gesture):
		try:
			self._toggleNeovimMode()
		except Exception as error:
			self._gate.disable()
			self._stopClient()
			self._diagnostics.record("toggleError", errorType=type(error).__name__, error=str(error))
			log.exception("NeovimAccessLink activation failed")
			ui.message(_("Neovim accessibility failed; normal terminal output restored"))

	def _toggleNeovimMode(self):
		identity = self._gate.focused
		if self._gate.manual_enabled:
			self._sessionClaimService.cancel_pending_authorization()
			self._gate.disable()
			self._planner.reset()
			self._resetTypedEcho()
			self._clearSessionPasswords()
			self._stopClient()
			ui.message(_("Neovim accessibility off"))
			self._queueBrailleRefresh(rebuild=True)
			self._diagnostics.record("manualMode", enabled=False)
			log.info("NeovimAccessLink manual mode disabled")
			return
		if identity is None:
			ui.message(_("Neovim accessibility unavailable in this window"))
			return
		self._gate.manual_enabled = True
		self._planner.reset()
		self._resetTypedEcho()
		self._diagnostics.record("manualMode", enabled=True, terminal=self._identityFields(identity))
		log.info("NeovimAccessLink manual mode requested")
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

	def _promptForSessionClaim(self, profile, identity):
		self._diagnostics.record(
			"sessionClaimRequested",
			profileId=profile.identifier,
			terminal=self._identityFields(identity),
			key=_SESSION_CLAIM_KEY_NAME,
		)
		ui.message(
			_(
				"Neovim accessibility ready for {name}. Focus the desired Neovim session and press {key}"
			).format(name=profile.name, key=_SESSION_CLAIM_KEY_NAME)
		)

	def _automaticClaimProfiles(self):
		"""Return profiles that can be inspected without opening a password dialog."""
		try:
			profiles = parse_profiles(self._settingsService.snapshot().get("connections", []))
		except ValueError as error:
			self._diagnostics.record("claimInventoryConfigError", error=str(error))
			return []
		result = []
		seen = set()
		for profile in profiles:
			if profile.authentication == "password" and profile.identifier not in self._sessionPasswords:
				continue
			key = (
				profile.ssh_target,
				profile.port,
				profile.identity_file,
				profile.authentication,
			)
			if key in seen:
				continue
			seen.add(key)
			result.append(profile)
		return result

	def _beginClaimInventory(self):
		profiles = self._automaticClaimProfiles()
		passwords = {
			profile.identifier: self._sessionPasswords.get(profile.identifier, "") for profile in profiles
		}
		self._sessionClaimService.start_inventory(
			profiles,
			passwords,
			self._finishClaimInventory,
		)

	def _beginAutomaticClaimResolution(self, identity, local_claim_not_before_ns=0):
		profiles = [
			profile
			for profile in self._automaticClaimProfiles()
			if self._sessionClaimService.is_target_eligible("remoteSsh", profile.identifier)
		]
		passwords = {
			profile.identifier: self._sessionPasswords.get(profile.identifier, "") for profile in profiles
		}
		baseline = self._sessionClaimService.baseline_snapshot()
		self._sessionClaimService.start_resolution(
			profiles,
			passwords,
			identity,
			baseline,
			local_claim_not_before_ns,
			self._finishAutomaticClaimResolution,
		)

	@staticmethod
	def _startClaimWorker(name, target, args):
		threading.Thread(target=target, args=args, name=name, daemon=True).start()

	@staticmethod
	def _queueClaimResult(callback, *args):
		queueHandler.queueFunction(queueHandler.eventQueue, callback, *args)

	@staticmethod
	def _listLocalClaimSessions():
		return _localSessionLister().list()

	def _listRemoteClaimSessions(self, profile, password):
		return SshSessionLister().list(
			profile.ssh_target,
			profile.port,
			profile.identity_file,
			password=password,
			askpass_path=self._askpassPath(),
		)

	def _finishClaimInventory(self, generation, results, _identity=None):
		summary = self._sessionClaimService.finish_inventory(generation, results)
		if summary is None:
			return
		configured = len(self._settingsService.snapshot().get("connections", []))
		self._diagnostics.record(
			"claimInventoryReady",
			eligibleTargets=summary.eligible_targets,
			errors=summary.errors,
			eligibleSessions=summary.eligible_sessions,
			localSessions=summary.local_sessions,
			remoteSessions=summary.remote_sessions,
			automaticSshProfiles=summary.automatic_ssh_profiles,
			scannedSshProfiles=summary.scanned_ssh_profiles,
			configuredSshProfiles=configured,
		)
		if summary.errors and configured > summary.scanned_ssh_profiles:
			ui.message(
				_(
					"Neovim connections ready. Some saved connections could not be checked, "
					"and password connections require manual selection. Focus Neovim and press {key}"
				).format(key=_SESSION_CLAIM_KEY_NAME)
			)
		elif summary.errors:
			ui.message(
				_(
					"Neovim connections ready. Some saved connections could not be checked. "
					"Focus Neovim and press {key}, or choose a connection manually"
				).format(key=_SESSION_CLAIM_KEY_NAME)
			)
		elif configured > summary.scanned_ssh_profiles:
			ui.message(
				_(
					"Neovim connections ready. Password connections require manual selection. "
					"Focus Neovim and press {key}"
				).format(key=_SESSION_CLAIM_KEY_NAME)
			)
		else:
			ui.message(
				_("Neovim connections ready. Focus Neovim and press {key}").format(
					key=_SESSION_CLAIM_KEY_NAME
				)
			)

	def _finishAutomaticClaimResolution(
		self,
		generation,
		results,
		identity,
		local_claim_not_before_ns=0,
	):
		resolution = self._sessionClaimService.finish_resolution(
			generation,
			results,
			identity,
			local_claim_not_before_ns,
		)
		if resolution is None:
			return
		for target_error in resolution.errors:
			self._diagnostics.record(
				"automaticClaimTargetError",
				targetKind=target_error.target_kind,
				targetId=target_error.target_id,
				errorType=target_error.error_type,
				error=target_error.error,
			)
		candidates = resolution.candidates
		self._diagnostics.record(
			"automaticClaimResolutionCompleted",
			candidates=len(candidates),
			targets=resolution.targets,
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
			labels.append(
				_("{target}: {session}").format(
					target=target,
					session=self._remoteSessionLabel(session),
				)
			)
		dialog = wx.SingleChoiceDialog(
			gui.mainFrame,
			_("More than one Neovim session confirmed F12. Select the intended session."),
			_("Select Neovim session"),
			labels,
		)
		ui.message(_("Multiple Neovim sessions confirmed F12; opening session selection"))

		def finish(result):
			if result != wx.ID_OK or not self._sessionClaimService.is_current(generation, identity):
				return
			selection = dialog.GetSelection()
			if 0 <= selection < len(candidates):
				self._connectAutomaticClaim(identity, candidates[selection])

		gui.runScriptModalDialog(dialog, finish)

	def action_copyDiagnosticReport(self, gesture):
		report = self._diagnostics.report(
			{
				"addonVersion": _ADDON_VERSION,
				"nvdaVersion": getattr(buildVersion, "version", "unknown"),
				"manualEnabled": self._gate.manual_enabled,
				"suppressionActive": self._gate.suppression_active,
				"connected": self._connected,
			},
			product_name=_PRODUCT_NAME,
		)
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
			state.get("buftype", "") != ""
			or state.get("modifiable") is not True
			or state.get("readonly") is True
			or state.get("fileManager")
		):
			self._clipboardFailure(_("The current Neovim buffer cannot be edited by this command"))
			return
		text = self._readWindowsClipboardText()
		if text is None:
			return
		request_id = self._nextClipboardRequestId()
		payload = {**expected, "requestId": request_id, "text": text}
		self._rememberClipboardRequest(
			request_id,
			(
				instance_id,
				identity,
				"pasteTextRequest",
			),
		)
		accepted = client.send_control("pasteTextRequest", payload)
		if not accepted:
			self._connectionCoordinator.take_pending_request("clipboard", request_id)
			self._clipboardFailure(_("Could not send text to the active Neovim session"))
		self._diagnostics.record(
			"clipboardPasteRequested",
			requestId=request_id,
			accepted=accepted,
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
		self._rememberClipboardRequest(
			request_id,
			(
				instance_id,
				identity,
				"setRegisterRequest",
			),
		)
		accepted = client.send_control("setRegisterRequest", payload)
		if not accepted:
			self._connectionCoordinator.take_pending_request("clipboard", request_id)
			self._clipboardFailure(_("Could not send text to the active Neovim session"))
		self._diagnostics.record(
			"clipboardRegisterRequested",
			requestId=request_id,
			accepted=accepted,
			bytes=len(text.encode("utf-8")),
		)

	def action_leaveDirectTerminalInput(self, gesture):
		identity = self._gate.focused
		selected = self._instanceManager.selected_for(identity) if identity else None
		if (
			identity is None
			or selected is None
			or self._client is None
			or selected.identifier != self._activeInstanceId
			or not self._gate.manual_enabled
			or not self._gate.authenticated
			or not self._gate.nvim_active
			or self._gate.bound_terminal != identity
		):
			ui.message(_("No active Neovim session is bound to this terminal"))
			return
		if "terminalControl" not in self._transportCapabilities:
			ui.message(_("The connected Neovim components do not support terminal control"))
			return
		state = self._currentState
		if (
			state.get("buftype") != "terminal"
			or state.get("mode") != "terminal"
			or state.get("modeRaw") != "t"
			or state.get("modeBlocking") is True
		):
			ui.message(_("Neovim is not in direct terminal input"))
			return
		expected = {
			"bufferId": state.get("bufferId"),
			"windowId": state.get("windowId"),
			"tabpageId": state.get("tabpageId"),
			"modeRaw": state.get("modeRaw"),
		}
		if any(
			not isinstance(expected[name], int) or isinstance(expected[name], bool)
			for name in ("bufferId", "windowId", "tabpageId")
		):
			ui.message(_("The active Neovim state is incomplete; try again"))
			return
		request_id = self._connectionCoordinator.next_request_id("terminalControl")
		discarded_request_ids = self._connectionCoordinator.remember_pending_request(
			"terminalControl",
			request_id,
			PendingControlRequest(
				selected.identifier,
				identity,
				"leaveTerminalInputRequest",
			),
			_MAX_PENDING_TERMINAL_CONTROL_REQUESTS,
		)
		for discarded_id in discarded_request_ids:
			self._diagnostics.record(
				"terminalControlRequestDiscarded",
				requestId=discarded_id,
				reason="queueLimit",
			)
		accepted = self._client.send_control(
			"leaveTerminalInputRequest",
			{**expected, "requestId": request_id},
		)
		if not accepted:
			self._connectionCoordinator.take_pending_request(
				"terminalControl",
				request_id,
			)
			ui.message(_("Could not ask Neovim to leave direct terminal input"))
		self._diagnostics.record(
			"leaveTerminalInputRequested",
			requestId=request_id,
			accepted=accepted,
			instanceId=selected.identifier,
		)

	def _readWindowsClipboardText(self):
		try:
			text = api.getClipData()
		except Exception as error:
			self._diagnostics.record(
				"clipboardReadFailed",
				errorType=type(error).__name__,
			)
			self._clipboardFailure(_("Could not read text from the Windows clipboard"))
			return None
		if not valid_clipboard_text(text):
			reason = (
				"tooLarge"
				if isinstance(text, str) and len(text.encode("utf-8", "ignore")) > MAX_CLIPBOARD_TEXT_BYTES
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
		self._rememberClipboardRequest(
			request_id,
			(
				instance_id,
				identity,
				"copyTextRequest",
			),
		)
		accepted = client.send_control("copyTextRequest", payload)
		if not accepted:
			self._connectionCoordinator.take_pending_request("clipboard", request_id)
			self._clipboardFailure(_("Could not request text from the active Neovim session"))
		self._diagnostics.record(
			"clipboardCopyRequested",
			requestId=request_id,
			source=source,
			accepted=accepted,
		)

	def _clipboardControlContext(self):
		identity = self._gate.focused
		selected = self._instanceManager.selected_for(identity) if identity else None
		if (
			identity is None
			or selected is None
			or self._client is None
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
		if any(
			not isinstance(expected[name], int) or isinstance(expected[name], bool)
			for name in ("bufferId", "windowId", "tabpageId", "changedtick")
		) or not isinstance(expected["modeRaw"], str):
			self._clipboardFailure(_("The active Neovim state is incomplete; try again"))
			return None
		return identity, selected.identifier, self._client, state, expected

	def _nextClipboardRequestId(self):
		return self._connectionCoordinator.next_request_id("clipboard")

	def _rememberClipboardRequest(self, request_id, request):
		discarded_request_ids = self._connectionCoordinator.remember_pending_request(
			"clipboard",
			request_id,
			PendingControlRequest(*request),
			_MAX_PENDING_CLIPBOARD_REQUESTS,
		)
		for discarded_id in discarded_request_ids:
			self._diagnostics.record(
				"clipboardRequestDiscarded",
				requestId=discarded_id,
				reason="queueLimit",
			)

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
		profiles = self._settingsService.snapshot().get("connections", [])
		choices = [_("This computer - local Neovim")]
		choices.extend(profile.get("name", "") for profile in profiles)
		profile_dialog = wx.SingleChoiceDialog(
			gui.mainFrame,
			_("Select where the Neovim session is running."),
			_("Connect terminal to Neovim"),
			choices,
		)
		self._diagnostics.record(
			"connectionProfileDialogScheduled",
			terminal=self._identityFields(identity),
			profileCount=len(profiles),
			localTarget=True,
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
				self._sessionClaimService.set_pending_target(identity, LOCAL_WINDOWS_TCP, "")
				self._diagnostics.record(
					"connectionTargetDialogClosed",
					accepted=True,
					targetKind=LOCAL_WINDOWS_TCP,
					terminal=self._identityFields(identity),
				)
				ui.message(
					_("Local Neovim selected. Focus the desired Neovim session and press {key}").format(
						key=_SESSION_CLAIM_KEY_NAME
					)
				)
				return
			try:
				parsed_profile = parse_profile(profiles[selection - 1])
			except ValueError:
				ui.message(_("The selected connection profile is unavailable"))
				return
			self._diagnostics.record(
				"connectionProfileDialogClosed",
				accepted=True,
				profileId=parsed_profile.identifier,
			)
			if parsed_profile.authentication == "password":
				password = self._passwordForProfile(parsed_profile)
				if password is None:
					return
			self._sessionClaimService.set_pending_target(
				identity,
				"remoteSsh",
				parsed_profile.identifier,
			)
			self._promptForSessionClaim(parsed_profile, identity)

		# NVDA's helper schedules the modal dialog for a fresh GUI-loop turn and
		# manages popup focus. A direct ShowModal call can remain behind Windows
		# Terminal or interfere with NVDA event processing.
		gui.runScriptModalDialog(profile_dialog, finish_profile_selection)

	def action_claimFocusedNeovimSession(
		self,
		gesture,
		forward_gesture=True,
		expected_identity=None,
		claim_generation=None,
	):
		"""Observe F12 reaching Neovim, then select only that fresh claim."""
		identity = self._gate.focused
		if expected_identity is None:
			expected_identity = identity
		if claim_generation is None:
			claim_generation = self._sessionClaimService.authorize(expected_identity)
		if claim_generation is None or not self._sessionClaimService.accept(
			expected_identity,
			claim_generation,
		):
			self._diagnostics.record("sessionClaimIgnored", reason="notAuthorizedOrFocusChanged")
			if forward_gesture and gesture is not None:
				gesture.send()
			return
		transition = self._sessionClaimService.consume_transition(expected_identity)
		identity = transition.identity
		if transition.kind == ClaimTransitionKind.PASS_THROUGH:
			if forward_gesture and gesture is not None:
				gesture.send()
			return
		if transition.kind == ClaimTransitionKind.INVENTORY_PENDING:
			ui.message(
				_(
					"Neovim connections are still being checked. Press {key} again after the ready message"
				).format(key=_SESSION_CLAIM_KEY_NAME)
			)
			return
		local_claim_not_before_ns = time.monotonic_ns()
		if forward_gesture and gesture is not None:
			gesture.send()
		if not self._gate.manual_enabled:
			self._gate.manual_enabled = True
			self._planner.reset()
			self._resetTypedEcho()
			self._gate.focused = identity
			self._diagnostics.record(
				"manualMode",
				enabled=True,
				terminal=self._identityFields(identity),
			)
		if transition.kind == ClaimTransitionKind.LOCAL:
			ui.message(_("Connecting the focused local Neovim session"))
			self._scheduleMainThreadCall(
				250,
				self._beginLocalSessionSelection,
				identity,
				True,
				True,
				True,
				None,
				local_claim_not_before_ns,
			)
			return
		if transition.kind == ClaimTransitionKind.AUTOMATIC:
			ui.message(_("Connecting the focused Neovim session"))
			self._scheduleMainThreadCall(
				250,
				self._beginAutomaticClaimResolution,
				identity,
				local_claim_not_before_ns,
			)
			return
		profile = self._connectionProfileById(transition.target_id)
		if profile is None:
			if transition.explicit_target:
				ui.message(_("The selected connection profile is unavailable"))
			else:
				ui.message(
					_("Configure a Neovim connection before using {key} pairing").format(
						key=_SESSION_CLAIM_KEY_NAME,
					)
				)
			return
		ui.message(_("Connecting the focused Neovim session"))
		self._scheduleMainThreadCall(
			250,
			self._beginSessionSelection,
			profile,
			identity,
			True,
			True,
			True,
		)

	def _beginLocalSessionSelection(
		self,
		identity,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		fallback_profile=None,
		claim_not_before_ns=0,
	):
		if not require_recent_claim:
			ui.message(_("Looking for local Neovim sessions"))
		self._sessionClaimService.start_local_discovery(
			identity,
			replace_existing,
			offer_remember,
			require_recent_claim,
			fallback_profile,
			claim_not_before_ns,
			self._finishLocalSessionDiscovery,
		)

	def _finishLocalSessionDiscovery(
		self,
		generation,
		identity,
		sessions,
		error,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		fallback_profile=None,
		claim_not_before_ns=0,
	):
		selection = self._sessionClaimService.resolve_local_discovery(
			generation,
			identity,
			sessions,
			error,
			require_recent_claim=require_recent_claim,
			has_fallback=fallback_profile is not None,
			claim_not_before_ns=claim_not_before_ns,
		)
		if selection.kind == DiscoverySelectionKind.STALE:
			self._diagnostics.record("localSessionDiscoveryIgnored")
			return
		if selection.kind == DiscoverySelectionKind.ERROR:
			self._diagnostics.record(
				"localSessionDiscoveryError",
				errorType=selection.error_type,
				error=selection.error,
			)
			ui.message(_("Could not list local Neovim sessions"))
			return
		if selection.kind == DiscoverySelectionKind.FALLBACK:
			self._beginSessionSelection(
				fallback_profile,
				identity,
				replace_existing,
				offer_remember,
				require_recent_claim,
			)
			return
		if selection.kind == DiscoverySelectionKind.EMPTY:
			ui.message(
				_(
					"No local Neovim accessibility session was found. Install the local components "
					"and restart Neovim"
				)
			)
			return
		if selection.kind == DiscoverySelectionKind.CLAIM_MISSING:
			ui.message(_("The focused local Neovim did not confirm F12 pairing; try again"))
			return
		if selection.kind == DiscoverySelectionKind.CHOOSE:
			self._showLocalSessionChoice(
				generation,
				identity,
				selection.sessions,
				replace_existing,
				offer_remember,
			)
			return
		session = selection.session
		if require_recent_claim:
			if self._reuseLocalSession(identity, session, offer_remember):
				return
		self._startLocalSession(
			identity,
			session,
			replace_existing=replace_existing,
			offer_remember=offer_remember,
		)

	def _reuseLocalSession(self, identity, session, offer_remember=False):
		plan = self._sessionClaimService.plan_local_connection(
			identity,
			session,
			allow_reuse=True,
			replace_existing=False,
		)
		instance = self._applyConnectionReuse(identity, plan, offer_remember)
		if instance is None:
			return False
		self._activateRememberedBinding(identity, instance.identifier)
		ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
		return True

	def _applyConnectionReuse(self, identity, plan, offer_remember=False):
		result = self._sessionClaimService.apply_connection_reuse(identity, plan)
		if result is None:
			return None
		for terminal in result.displaced_identities:
			self._terminalFocusService.forget_identity(terminal)
		self._ensureTerminalLifecycleSweep()
		if offer_remember and not self._sessionClaimService.is_temporary_binding_remembered(identity):
			self._sessionClaimService.request_temporary_binding_offer(result.instance.identifier)
		return result.instance

	def _startLocalSession(
		self,
		identity,
		session,
		replace_existing=False,
		offer_remember=False,
	):
		plan = self._sessionClaimService.plan_local_connection(
			identity,
			session,
			allow_reuse=False,
			replace_existing=replace_existing,
		)
		self._startLocalManagedInstance(
			session,
			identity,
			self._remoteSessionLabel(session),
			plan.replace_instance_id,
			offer_remember,
		)

	def _showLocalSessionChoice(
		self,
		generation,
		identity,
		sessions,
		replace_existing,
		offer_remember,
	):
		import gui
		import wx

		labels = [self._remoteSessionLabel(session) for session in sessions]
		dialog = wx.SingleChoiceDialog(
			gui.mainFrame,
			_("Select the local Neovim session for the focused terminal."),
			_("Local Neovim session"),
			labels,
		)
		ui.message(_("Multiple local Neovim sessions found; opening session selection"))

		def finish(result):
			if not self._sessionClaimService.is_discovery_current(generation, identity):
				return
			if result != wx.ID_OK:
				return
			selection = dialog.GetSelection()
			if not 0 <= selection < len(sessions):
				ui.message(_("The selected local Neovim session is no longer available"))
				return
			self._startLocalSession(
				identity,
				sessions[selection],
				replace_existing,
				offer_remember,
			)

		gui.runScriptModalDialog(dialog, finish)

	def _startLocalManagedInstance(
		self,
		session,
		identity,
		session_label="",
		replace_instance_id="",
		offer_remember=False,
	):
		if identity is None:
			ui.message(_("Starting a connection instance requires a focused terminal"))
			return
		if not self._instanceManager.list() and self._client is not None:
			self._stopClient()
		target = local_windows_target(_("This computer - local Neovim"))
		label = _("Local Neovim, {session}").format(
			session=session_label or _("Neovim session"),
		)
		result = self._sessionClaimService.start_local_connection(
			identity,
			session,
			target,
			label,
			context_label=_("local"),
			replace_instance_id=replace_instance_id,
		)
		self._completeManagedConnectionStart(
			result,
			offer_remember=offer_remember,
			diagnostic_fields={"targetKind": LOCAL_WINDOWS_TCP},
			failure_message=_("Could not start the local Neovim connection"),
		)

	def _completeManagedConnectionStart(
		self,
		result,
		*,
		offer_remember=False,
		diagnostic_fields=None,
		failure_message="",
	):
		if result.instance is None:
			self._reportConnectionStartError(
				RuntimeError(result.error),
				diagnostic_fields,
				failure_message,
				error_type=result.error_type,
			)
			return None
		self._ensureTerminalLifecycleSweep()
		if offer_remember:
			self._sessionClaimService.request_temporary_binding_offer(result.instance.identifier)
		if result.replacement_error_type:
			self._diagnostics.record(
				"replacedConnectionStopError",
				instanceId=result.replaced_instance_id,
				errorType=result.replacement_error_type,
				error=result.replacement_error,
			)
		ui.message(_("Neovim connection started: {name}").format(name=result.instance.label))
		return result.instance

	def _reportConnectionStartError(
		self,
		error,
		diagnostic_fields,
		failure_message,
		*,
		error_type="",
	):
		self._diagnostics.record(
			"connectionInstanceStartError",
			**(diagnostic_fields or {}),
			errorType=error_type or type(error).__name__,
			error=str(error),
		)
		ui.message(failure_message)

	def action_disconnectConnectionInstance(self, gesture):
		identity = self._gate.focused
		if identity is None:
			return
		result = self._sessionClaimService.disconnect_connection(identity)
		if result.instance is None:
			if result.error_type:
				self._diagnostics.record(
					"connectionInstanceDisconnectError",
					errorType=result.error_type,
					error=result.error,
				)
			ui.message(_("No Neovim connection instance is selected for this terminal"))
			return
		self._terminalFocusService.forget_identity(identity)
		if result.error_type:
			self._diagnostics.record(
				"connectionInstanceDisconnectError",
				instanceId=result.instance.identifier,
				errorType=result.error_type,
				error=result.error,
			)
		ui.message(_("Neovim connection disconnected: {name}").format(name=result.instance.label))

	def action_forgetTemporaryTerminalBinding(self, gesture):
		identity = self._gate.focused
		if identity is None:
			return
		if not self._sessionClaimService.forget_temporary_binding(identity):
			ui.message(_("No temporary Neovim connection is remembered for this terminal"))
			return
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
			instance.session_id
			for instance in self._instanceManager.list()
			if instance.target_id == profile.identifier
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
					label=label,
					position=positions[base],
					total=totals[base],
				)
			if include_connection_status and session.identifier in connected:
				label = _("{label}, already connected").format(label=label)
			labels.append(label)
		return labels

	def _beginSessionSelection(
		self,
		profile,
		identity,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		preserve_dialog_identity=False,
	):
		if not preserve_dialog_identity and self._gate.focused != identity:
			return
		password = self._passwordForProfile(profile)
		if profile.authentication == "password" and password is None:
			return
		self._diagnostics.record(
			"remoteSessionDiscoveryStarted",
			profileId=profile.identifier,
			terminal=self._identityFields(identity),
			preserveDialogIdentity=preserve_dialog_identity,
		)
		if not require_recent_claim:
			ui.message(_("Looking for Neovim sessions on {name}").format(name=profile.name))
		self._sessionClaimService.start_remote_discovery(
			profile,
			identity,
			password or "",
			replace_existing,
			offer_remember,
			require_recent_claim,
			preserve_dialog_identity,
			self._finishSessionDiscovery,
		)

	def _finishSessionDiscovery(
		self,
		generation,
		profile,
		identity,
		sessions,
		error,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		preserve_dialog_identity=False,
	):
		selection = self._sessionClaimService.resolve_remote_discovery(
			generation,
			identity,
			sessions,
			error,
			require_recent_claim=require_recent_claim,
			preserve_dialog_identity=preserve_dialog_identity,
		)
		if selection.kind == DiscoverySelectionKind.STALE:
			self._diagnostics.record("sessionDiscoveryIgnored", profileId=profile.identifier)
			return
		if selection.kind == DiscoverySelectionKind.ERROR:
			self._diagnostics.record(
				"sessionDiscoveryError",
				profileId=profile.identifier,
				errorType=selection.error_type,
				error=selection.error,
			)
			ui.message(_("Could not list Neovim sessions on {name}").format(name=profile.name))
			return
		if selection.kind == DiscoverySelectionKind.EMPTY:
			ui.message(_("No active Neovim session was found on {name}").format(name=profile.name))
			return
		if selection.kind == DiscoverySelectionKind.CLAIM_MISSING:
			self._diagnostics.record(
				"freshSessionClaimMissing",
				profileId=profile.identifier,
				sessionCount=len(sessions),
			)
			ui.message(_("The focused Neovim did not confirm F12 pairing; try again"))
			return
		if selection.kind == DiscoverySelectionKind.CHOOSE:
			self._showRemoteSessionChoice(
				generation,
				profile,
				identity,
				selection.sessions,
				replace_existing,
				offer_remember,
				preserve_dialog_identity,
			)
			return
		session = selection.session
		if require_recent_claim:
			self._diagnostics.record(
				"freshSessionClaimSelected",
				profileId=profile.identifier,
				sessionId=session.identifier,
				claimAgeMs=session.claim_age_ms,
			)
			if self._reuseClaimedSession(
				profile,
				identity,
				session,
				offer_remember=offer_remember,
			):
				return
			self._startDiscoveredSession(
				profile,
				identity,
				session,
				replace_existing,
				offer_remember,
			)
			return
		self._startDiscoveredSession(
			profile,
			identity,
			session,
			replace_existing,
			offer_remember,
		)

	def _reuseClaimedSession(self, profile, identity, session, offer_remember=False):
		"""Move or refresh an existing transport instead of duplicating it."""
		plan = self._sessionClaimService.plan_remote_connection(
			identity,
			profile.identifier,
			session,
			allow_reuse=True,
			replace_existing=False,
		)
		instance = self._applyConnectionReuse(identity, plan, offer_remember)
		if instance is None:
			return False
		client = self._instanceManager.client_for(instance.identifier)
		already_active = (
			self._gate.bound_terminal == identity
			and self._client is client
			and self._gate.authenticated
			and self._gate.nvim_active
			and self._activeInstanceId == instance.identifier
		)
		self._activateRememberedBinding(identity, instance.identifier)
		if already_active and self._sessionClaimService.has_temporary_binding_offer(instance.identifier):
			client.send_control("requestFullState", {})
		self._diagnostics.record(
			"claimedSessionTransportReused",
			instanceId=instance.identifier,
			profileId=profile.identifier,
			sessionId=session.identifier,
			terminal=self._identityFields(identity),
		)
		ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
		return True

	def _startDiscoveredSession(
		self,
		profile,
		identity,
		session,
		replace_existing=False,
		offer_remember=False,
		session_label="",
	):
		plan = self._sessionClaimService.plan_remote_connection(
			identity,
			profile.identifier,
			session,
			allow_reuse=False,
			replace_existing=replace_existing,
		)
		self._startManagedInstance(
			profile.identifier,
			session.identifier,
			identity=identity,
			session_label=session_label or self._remoteSessionLabel(session),
			replace_instance_id=plan.replace_instance_id,
			offer_remember=offer_remember,
		)

	def _showRemoteSessionChoice(
		self,
		generation,
		profile,
		identity,
		sessions,
		replace_existing,
		offer_remember,
		preserve_dialog_identity=False,
	):
		import gui
		import wx

		dialog = wx.SingleChoiceDialog(
			gui.mainFrame,
			_("Select the Neovim session for the focused terminal."),
			_("Neovim session"),
			self._remoteSessionLabels(profile, sessions),
		)
		self._diagnostics.record(
			"remoteSessionDialogScheduled",
			profileId=profile.identifier,
			sessionCount=len(sessions),
			terminal=self._identityFields(identity),
		)
		ui.message(
			_("Multiple Neovim sessions found on {name}; opening session selection").format(
				name=profile.name,
			)
		)

		def finish_session_selection(result):
			if not self._sessionClaimService.is_discovery_current(
				generation,
				identity,
				preserve_dialog_identity=preserve_dialog_identity,
			):
				self._diagnostics.record(
					"remoteSessionDialogIgnored",
					profileId=profile.identifier,
					reason="stale",
				)
				return
			if result != wx.ID_OK:
				self._diagnostics.record(
					"remoteSessionDialogClosed",
					profileId=profile.identifier,
					accepted=False,
				)
				return
			selection = dialog.GetSelection()
			if not 0 <= selection < len(sessions):
				ui.message(_("The selected Neovim session is no longer available"))
				return
			session = sessions[selection]
			self._diagnostics.record(
				"remoteSessionDialogClosed",
				profileId=profile.identifier,
				accepted=True,
			)
			labels = self._remoteSessionLabels(
				profile,
				sessions,
				include_connection_status=False,
			)
			self._startDiscoveredSession(
				profile,
				identity,
				session,
				replace_existing,
				offer_remember,
				labels[selection],
			)

		# Session discovery completes on NVDA's event queue. Schedule the modal
		# chooser through NVDA's GUI helper rather than nesting ShowModal here.
		gui.runScriptModalDialog(dialog, finish_session_selection)

	def _startManagedInstance(
		self,
		profile_id,
		session_id,
		identity=None,
		session_label="",
		replace_instance_id="",
		offer_remember=False,
	):
		try:
			profile = next(
				item
				for item in parse_profiles(self._settingsService.snapshot().get("connections", []))
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
		result = self._sessionClaimService.start_remote_connection(
			identity,
			profile,
			session_id,
			remote_ssh_target(profile.identifier, profile.name),
			f"{profile.name}, {session_label}" if session_label else profile.name,
			password=password or "",
			askpass_path=self._askpassPath(),
			context_label=profile.name,
			replace_instance_id=replace_instance_id,
		)
		self._completeManagedConnectionStart(
			result,
			offer_remember=offer_remember,
			diagnostic_fields={"profileId": profile.identifier},
			failure_message=_("Could not start the Neovim connection"),
		)

	def _bindManagedInstance(self, instance_id):
		identity = self._gate.focused
		if identity is None:
			ui.message(_("Connection selection requires a focused terminal"))
			return
		result = self._sessionClaimService.select_connection(identity, instance_id)
		if result.instance is None or result.client is None:
			self._diagnostics.record(
				"connectionInstanceBindError",
				errorType=result.error_type,
				error=result.error,
			)
			ui.message(_("The selected Neovim connection no longer exists"))
			return
		self._ensureTerminalLifecycleSweep()
		self._gate.bound_terminal = identity
		result.client.send_control("requestFullState", {})
		ui.message(_("Neovim connection selected: {name}").format(name=result.instance.label))

	def _offerTemporaryTerminalBinding(self, identity, instance_id):
		offer = self._sessionClaimService.arm_temporary_binding_reactivation(identity, instance_id)
		if offer.kind == TemporaryBindingOfferKind.FOCUS_CHANGED:
			self._diagnostics.record(
				"temporaryTerminalBindingOfferIgnored",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if offer.kind == TemporaryBindingOfferKind.UNAVAILABLE:
			self._diagnostics.record(
				"temporaryTerminalBindingUnavailable",
				terminal=self._identityFields(identity),
			)
			return
		if offer.kind != TemporaryBindingOfferKind.OFFER or offer.instance is None:
			return
		import gui
		import wx

		answer = wx.MessageBox(
			_(
				"Remember this connection for this Windows Terminal tab until NVDA or "
				"Windows Terminal closes?\n\n{connection}"
			).format(connection=offer.instance.label),
			_("Remember temporary terminal connection"),
			wx.YES_NO | wx.ICON_QUESTION,
			gui.mainFrame,
		)
		focused = self._gate.focused
		if focused is not None:
			selected = self._instanceManager.selected_for(focused)
			self._sessionClaimService.consume_temporary_binding_reactivation(
				focused,
				selected.identifier if selected is not None else None,
			)
		if answer != wx.YES:
			self._diagnostics.record(
				"temporaryTerminalBindingDeclined",
				instanceId=instance_id,
				terminal=self._identityFields(identity),
			)
			return
		remembered = self._sessionClaimService.remember_temporary_binding(identity, instance_id)
		if remembered.kind != TemporaryBindingOfferKind.OFFER or remembered.instance is None:
			self._diagnostics.record(
				"temporaryTerminalBindingOfferIgnored",
				instanceId=instance_id,
				reason=remembered.kind.value,
			)
			return
		self._diagnostics.record(
			"temporaryTerminalBindingRemembered",
			instanceId=instance_id,
			transportKind=remembered.instance.transport_kind,
			terminal=self._identityFields(identity),
		)
		ui.message(_("Connection remembered for this terminal tab until NVDA exits"))

	@staticmethod
	def _newInstanceRuntime():
		return {
			"planner": SpeechPlanner(translate=_),
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
		self._connectionCoordinator.switch_runtime(
			instance_id,
			self._newInstanceRuntime,
		)

	def _dropInstanceRuntime(self, instance_id):
		self._connectionCoordinator.drop_runtime(
			instance_id,
			self._newInstanceRuntime,
		)

	def _activateRememberedBinding(self, identity, instance_id, focus_regained=False):
		activation = self._sessionClaimService.activate_remembered_binding(
			identity,
			instance_id,
			focus_regained=focus_regained,
		)
		if activation.kind != RememberedBindingActivationKind.ACTIVATE:
			return
		# Focus events for Windows Terminal tabs can be followed by transient
		# child-focus events. Let focus settle before accepting a new fullState.
		self._scheduleMainThreadCall(
			100,
			self._requestRememberedBindingState,
			identity,
			instance_id,
		)
		self._diagnostics.record(
			"temporaryTerminalBindingActivated",
			instanceId=instance_id,
			terminal=self._identityFields(identity),
			suppressionImmediate=False,
		)

	def _requestRememberedBindingState(self, identity, instance_id):
		request = self._sessionClaimService.plan_remembered_state_request(identity, instance_id)
		if request.kind == RememberedStateRequestKind.SKIP:
			self._diagnostics.record(
				"temporaryTerminalBindingStateSkipped",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if request.kind == RememberedStateRequestKind.STALE or request.client is None:
			return
		if request.kind == RememberedStateRequestKind.FOCUS_CONTEXT:
			sent = request.client.send_control(
				"requestFocusContext",
				{"requestId": request.request_id},
			)
			if not sent:
				self._connectionCoordinator.discard_focus_context(instance_id)
			self._diagnostics.record(
				"temporaryTerminalFocusContextRequested",
				instanceId=instance_id,
				requestId=request.request_id,
				sent=sent,
			)
			return
		request.client.send_control("requestFullState", {})
		self._diagnostics.record(
			"temporaryTerminalBindingStateRequested",
			instanceId=instance_id,
		)

	def _onManagedEvent(self, instance_id, event):
		queueHandler.queueFunction(queueHandler.eventQueue, self._handleManagedEvent, instance_id, event)

	def _handleManagedEvent(self, instance_id, event):
		identity = self._gate.focused
		selected = self._instanceManager.selected_for(identity) if identity else None
		if event.get("type") == "focusContext":
			payload = event.get("payload")
			request_id = payload.get("_focusRequestId") if isinstance(payload, dict) else None
			if (
				not self._connectionCoordinator.matches_focus_context(
					instance_id,
					request_id,
					identity,
				)
				or selected is None
				or selected.identifier != instance_id
				or instance_id not in self._authenticatedInstances
			):
				self._diagnostics.record(
					"focusContextIgnored",
					instanceId=instance_id,
					reason="staleOrUnbound",
				)
				return
			self._connectionCoordinator.discard_focus_context(instance_id)
			self._connectionCoordinator.confirm_foreground_instance(
				instance_id,
				identity,
				self._newInstanceRuntime,
			)
			self._diagnostics.record(
				"temporaryTerminalForegroundConfirmed",
				instanceId=instance_id,
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
					"instanceFullStateDeferred",
					instanceId=instance_id,
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
				"instanceEventIgnored",
				instanceId=instance_id,
				reason="foregroundUnconfirmed",
			)
			return
		self._connectionCoordinator.select_instance(
			instance_id,
			identity,
			self._newInstanceRuntime,
		)
		if event.get("type") in {"copyTextResult", "pasteTextResult", "setRegisterResult"}:
			event = self._handleClipboardResult(instance_id, identity, event)
			if event is None:
				return
		elif event.get("type") == "leaveTerminalInputResult":
			event = self._handleTerminalControlResult(instance_id, identity, event)
			if event is None:
				return
		payload = event.get("payload")
		if event.get("type") == "fullState":
			self._authenticatedInstances.add(instance_id)
		if isinstance(payload, dict):
			if event.get("type") in {"focusContext", "contextChanged"}:
				payload = dict(payload)
				payload["_connectionLabel"] = selected.context_label
				event = {**event, "payload": payload}
			self._instanceTerminalPassthrough[instance_id] = (
				payload.get("buftype") == "terminal" and payload.get("mode") == "terminal"
			)
		self._handleEvent(event)
		if event.get("type") == "fullState" and self._sessionClaimService.consume_temporary_binding_offer(
			instance_id
		):
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
				"clipboardResultIgnored",
				instanceId=instance_id,
				reason="invalidRequestId",
			)
			return None
		pending = self._connectionCoordinator.take_pending_request(
			"clipboard",
			request_id,
		)
		expected_control = {
			"copyTextResult": "copyTextRequest",
			"pasteTextResult": "pasteTextRequest",
			"setRegisterResult": "setRegisterRequest",
		}.get(event_type)
		if pending != PendingControlRequest(instance_id, identity, expected_control):
			self._diagnostics.record(
				"clipboardResultIgnored",
				instanceId=instance_id,
				requestId=request_id,
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
						"clipboardWriteFailed",
						errorType=type(error).__name__,
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
			"clipboardResult",
			instanceId=instance_id,
			requestId=request_id,
			type=event_type,
			ok=ok,
			resultCode=result_code,
			copiedCharacterCount=safe_payload.get("copiedCharacterCount"),
			copiedLineCount=safe_payload.get("copiedLineCount"),
			insertedBytes=safe_payload.get("insertedBytes"),
			insertedLines=safe_payload.get("insertedLines"),
			storedBytes=safe_payload.get("storedBytes"),
			storedLineCount=safe_payload.get("storedLineCount"),
		)
		return {**event, "payload": clipboard_result_state(safe_payload)}

	def _discardClipboardRequests(self, *, instance_id=None):
		self._connectionCoordinator.discard_pending_requests(
			"clipboard",
			instance_id,
		)

	def _handleTerminalControlResult(self, instance_id, identity, event):
		payload = event.get("payload")
		request_id = payload.get("requestId") if isinstance(payload, dict) else None
		if not valid_request_id(request_id):
			self._diagnostics.record(
				"terminalControlResultIgnored",
				instanceId=instance_id,
				reason="invalidRequestId",
			)
			return None
		pending = self._connectionCoordinator.take_pending_request(
			"terminalControl",
			request_id,
		)
		if pending != PendingControlRequest(
			instance_id,
			identity,
			"leaveTerminalInputRequest",
		):
			self._diagnostics.record(
				"terminalControlResultIgnored",
				instanceId=instance_id,
				requestId=request_id,
				reason="staleOrUnbound",
			)
			return None
		ok = payload.get("ok") is True
		result_code = payload.get("resultCode")
		if not isinstance(result_code, str) or len(result_code) > 64:
			ok = False
			result_code = "invalidResult"
		if not ok:
			if result_code == "staleState":
				message = _("Neovim changed before terminal input could be left; try again")
			else:
				message = _("Neovim could not leave direct terminal input")
			ui.message(message)
		self._diagnostics.record(
			"terminalControlResult",
			instanceId=instance_id,
			requestId=request_id,
			ok=ok,
			resultCode=result_code,
		)
		return {**event, "payload": terminal_control_result_state(payload)}

	def _discardTerminalControlRequests(self, *, instance_id=None):
		self._connectionCoordinator.discard_pending_requests(
			"terminalControl",
			instance_id,
		)

	def _discardTransientFocusContext(self):
		self._connectionCoordinator.discard_focus_context()
		self._discardClipboardRequests()
		self._discardTerminalControlRequests()

	def _onManagedState(self, instance_id, state):
		queueHandler.queueFunction(queueHandler.eventQueue, self._handleManagedState, instance_id, state)

	def _handleManagedState(self, instance_id, state):
		if state == "disconnected":
			self._authenticatedInstances.discard(instance_id)
			self._instanceTerminalPassthrough.pop(instance_id, None)
			self._pendingInstanceFullStates.pop(instance_id, None)
			self._connectionCoordinator.discard_focus_context(instance_id)
			self._discardClipboardRequests(instance_id=instance_id)
			self._discardTerminalControlRequests(instance_id=instance_id)
		identity = self._gate.focused
		selected = self._instanceManager.selected_for(identity) if identity else None
		if selected is not None and selected.identifier == instance_id:
			self._switchInstanceRuntime(instance_id)
			self._handleConnectionState(state)

	def _prepareTerminalFocus(self, obj, adapter_token, app_module=None):
		return self._terminalFocusService.prepare_focus(obj, adapter_token, app_module)

	def _finishTerminalFocus(self, decision):
		self._terminalFocusService.finish_focus(decision)

	def _failOpenTerminalEvent(self, event_name, error):
		"""Drop suppression after a frontend event failure."""
		self._gate.disconnect()
		self._client = None
		self._diagnostics.record(
			"terminalEventFailedOpen",
			event=event_name,
			errorType=type(error).__name__,
		)

	def _refreshFocusedTerminalForAction(
		self,
		obj,
		app_module=None,
		adapter_token=None,
	):
		return self._terminalFocusService.refresh_for_action(obj, app_module, adapter_token)

	def _pruneClosedTerminalBindings(self):
		return self._terminalFocusService.prune_closed_bindings()

	def _stopManagedClientAsync(self, instance_id, client):
		threading.Thread(
			target=self._stopManagedClient,
			args=(instance_id, client),
			name="nvim-nvda-managed-client-stop",
			daemon=True,
		).start()

	@staticmethod
	def _logTerminalLifecycleFailure():
		log.exception("terminal lifecycle sweep failed open")

	def _stopManagedClient(self, instance_id, client):
		try:
			client.stop()
		except Exception as error:
			self._diagnostics.record(
				"managedClientStopError",
				instanceId=instance_id,
				errorType=type(error).__name__,
				error=str(error),
			)

	def _terminalApplicationLostFocus(self, adapter_token):
		self._terminalFocusService.lose_focus(adapter_token)

	def _shouldUseNativeTerminalEvent(self, obj):
		"""Return whether the AppModule must continue native event handling."""
		return not self._shouldSuppress(obj)

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
				"eventIgnored",
				type=event.get("type"),
				reason="frontendNotFocused",
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
		log.debug("NeovimAccessLink %s %r", category, fields)

	def _handleConnectionState(self, state):
		previous = self._lastConnectionState
		self._lastConnectionState = state
		self._diagnostics.record("connectionState", previous=previous, state=state)
		if state == "disconnected" and previous == "connected" and self._gate.focused is not None:
			self._planner.reset()
			self._resetTypedEcho()
			ui.message(_("Neovim connection lost; normal terminal output restored"))
			self._refreshBraille(rebuild=True)

	def _handleEvent(self, event):
		activated = False
		payload = event.get("payload")
		previous_state = self._currentState
		keyObserverDiagnostics = (
			payload.get("keyObserverDiagnostics", {}) if isinstance(payload, dict) else {}
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
			modeBlocking=(payload.get("modeBlocking") if isinstance(payload, dict) else None),
			bufferId=payload.get("bufferId") if isinstance(payload, dict) else None,
			windowId=payload.get("windowId") if isinstance(payload, dict) else None,
			changedtick=payload.get("changedtick") if isinstance(payload, dict) else None,
			cursor=payload.get("cursor") if isinstance(payload, dict) else None,
			lineText=payload.get("lineText") if isinstance(payload, dict) else None,
			transport=payload.get("_transport") if isinstance(payload, dict) else None,
			preConnectErrorCode=(payload.get("preConnectErrorCode") if isinstance(payload, dict) else None),
			preConnectErrorKind=(payload.get("preConnectErrorKind") if isinstance(payload, dict) else None),
			currentErrorCode=(payload.get("currentErrorCode") if isinstance(payload, dict) else None),
			currentErrorKind=(payload.get("currentErrorKind") if isinstance(payload, dict) else None),
			keyObserverErrorCount=keyObserverDiagnostics.get("observerErrorCount"),
			keyObserverErrorKind=keyObserverDiagnostics.get("observerErrorKind"),
			keyClaimErrorKind=keyObserverDiagnostics.get("claimErrorKind"),
			keyClaimSkippedMode=keyObserverDiagnostics.get("claimSkippedMode"),
			keyClaimConsumed=keyObserverDiagnostics.get("claimKeyConsumed"),
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
		previous_buffer_id = previous_state.get("bufferId") if isinstance(previous_state, dict) else None
		buffer_id = payload.get("bufferId") if isinstance(payload, dict) else None
		if event.get("type") == "menuSelectionChanged" and isinstance(payload, dict):
			item = payload.get("item", {})
			documentation = item.get("documentation", "") if isinstance(item, dict) else ""
			self._menuDocumentation = documentation if isinstance(documentation, str) else ""
		elif event.get("type") == "menuClosed":
			self._menuDocumentation = ""
		event_type = event.get("type")
		terminal_passthrough = (
			isinstance(payload, dict)
			and payload.get("buftype") == "terminal"
			and payload.get("mode") == "terminal"
		)
		if terminal_passthrough != self._gate.terminal_passthrough:
			# Direct terminal input must fail open before any optional sound or
			# speech is produced for the mode transition.
			self._gate.terminal_passthrough = terminal_passthrough
			self._diagnostics.record(
				"terminalPassthrough",
				enabled=terminal_passthrough,
				bufferId=payload.get("bufferId") if isinstance(payload, dict) else None,
			)
		mode_sound = self._modeSoundKind(mode)
		previous_mode_sound = self._modeSoundKind(previous_mode)
		if event_type == "focusContext" and self._gate.manual_enabled and mode_sound is not None:
			self._playModeSound(mode, focus_context=True)
		elif (
			event_type == "messageReceived"
			and isinstance(payload, dict)
			and payload.get("commandLineReturn") is True
			and mode_sound is not None
		):
			# A message-producing Ex command has already returned to its
			# previous editor mode. Play that mode cue immediately before the
			# structured command result and configured return presentation.
			self._playModeSound(mode)
		elif (
			event_type in {"commandLineChanged", "modeChanged"}
			and mode_sound == "commandLine"
			and previous_mode != "commandLine"
		):
			self._playModeSound(mode)
		elif (
			event_type in {"modeChanged", "contextChanged"}
			and mode_sound == "insert"
			and previous_mode_sound != "insert"
		):
			self._playModeSound(mode)
		elif (
			event_type in {"modeChanged", "contextChanged"}
			and mode_sound == "normal"
			and (
				previous_mode_sound == "insert"
				or (
					previous_mode == "commandLine"
					and isinstance(previous_state, dict)
					and previous_state.get("buftype") == "terminal"
				)
			)
		):
			self._playModeSound(mode)
		elif (
			event_type in {"modeChanged", "contextChanged"}
			and mode == "terminalNormal"
			and (previous_mode != "terminalNormal" or previous_buffer_id != buffer_id)
		):
			# :terminal enters raw mode "nt" before direct terminal input.
			# Announce that distinct state once, while duplicate TermOpen /
			# context events for the same buffer remain silent.
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
		if not self._gate.manual_enabled:
			return
		self._presentation.deliver_actions(
			self._planner.plan(
				event,
				focus_announcement=self._focusAnnouncement(),
			),
			event_type=event.get("type"),
			mode=mode,
			previous_mode=previous_mode,
			payload=payload,
			speak_structured_typing=self._speakStructuredTyping,
		)
		if self._gate.suppression_active:
			self._refreshBraille(rebuild=activated)

	def _reportIndentation(self, quarterTones, level):
		self._presentation.report_indentation(quarterTones, level)

	def _speakStructuredTyping(self, text, state=None, *, command_line=False):
		keyboard = config.conf["keyboard"]
		speak_characters = int(keyboard["speakTypedCharacters"]) != 0
		speak_words = int(keyboard["speakTypedWords"]) != 0
		cursor = state.get("cursor", {}) if isinstance(state, dict) else {}
		line = cursor.get("line") if isinstance(cursor, dict) else None
		byte_column = (
			state.get("commandLinePosition")
			if command_line and isinstance(state, dict)
			else cursor.get("byteColumn")
			if isinstance(cursor, dict)
			else None
		)
		buffer_id = state.get("bufferId") if isinstance(state, dict) else None
		byte_length = len(text.encode("utf-8")) if "\n" not in text else None
		start = (
			byte_column - byte_length if isinstance(byte_column, int) and byte_length is not None else None
		)
		identity = ("commandLine", buffer_id) if command_line else (buffer_id, line)
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
			log.exception("NeovimAccessLink braille failure")

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
		# Compatibility for existing callers; focus runtime uses the injected
		# identity function owned by TerminalFocusService.
		return _identityForObject(obj)

	def _identityFields(self, identity):
		return self._terminalFocusService.identity_fields(identity)

	def _feedbackMode(self, key):
		return self._presentation.feedback_mode(key)

	def _focusAnnouncement(self):
		return self._settingsService.focus_announcement()

	@staticmethod
	def _modeSoundKind(mode):
		return NvdaPresentation.mode_sound_kind(mode)

	def _playModeSound(self, mode, *, focus_context=False):
		self._presentation.play_mode_sound(mode, focus_context=focus_context)

	def _actionSpeechAllowed(self, event_type, feedback_key):
		return self._presentation.action_speech_allowed(event_type, feedback_key)

	def _onSettingsConnectionsChanged(self):
		"""Refresh claim discovery only while manual support is active."""
		if not self._gate.manual_enabled:
			return False
		self._beginClaimInventory()
		return True

	def _connectionProfileById(self, identifier):
		return self._settingsService.connection_profile_by_id(identifier)

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
		self._sessionClaimService.invalidate_connection_state()
		self._connectionCoordinator.discard_focus_context()
		self._discardClipboardRequests()
		self._discardTerminalControlRequests()
		if hasattr(self, "_instanceManager") and self._instanceManager.list():
			try:
				self._instanceManager.stop_all()
			finally:
				self._connectionCoordinator.clear_runtime_tracking()
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
			log.exception("NeovimAccessLink client shutdown failed")
		self._connected = False
		self._diagnostics.record("clientStopped")
