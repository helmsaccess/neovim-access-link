"""Static NVDA runtime configuration and Windows Terminal identity adapters."""

import array
import json
import os
import sys

import addonHandler
import config

PACKAGE_DIR = os.path.dirname(__file__)
VENDOR_DIR = os.path.join(PACKAGE_DIR, "vendor")
if VENDOR_DIR not in sys.path:
	sys.path.insert(0, VENDOR_DIR)

from .core.frontend_policy import FrontendPolicy  # noqa: E402
from .core.gate import TerminalIdentity  # noqa: E402
from .core.local_sessions import LocalSessionLister  # noqa: E402
from .nvda_windows import processAlive  # noqa: E402
from .settings_service import (  # noqa: E402
	AUTOMATIC_PARAMETER_HINTS_DEFAULT,
	BRAILLE_DEVELOPER_START_DEFAULT,
	BRAILLE_DEVELOPER_START_MAXIMUM,
	BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
	BRAILLE_ROUTING_DEFAULTS,
	BRAILLE_SUGGESTION_START_DEFAULT,
	BRAILLE_SUGGESTION_START_MAXIMUM,
)

addonHandler.initTranslation()

TERMINAL_LIFECYCLE_INTERVAL_MS = 5 * 60 * 1_000


def window_identity_exists(identity):
	"""Return True/False for a conclusive HWND check, or None on uncertainty."""
	from .nvda_windows import windowIdentityExists

	return windowIdentityExists(identity)


def terminal_identity_exists(identity, known_element=None):
	"""Validate the exact WT tab; uncertainty is deliberately non-destructive."""
	window_exists = window_identity_exists(identity)
	if window_exists is False:
		return False
	if window_exists is None or not identity.runtime_id:
		return True
	if known_element is not None:
		try:
			known_runtime_id = tuple(int(value) for value in known_element.getRuntimeId())
			if known_runtime_id == identity.runtime_id:
				return True
			# The focus service only stores an alias element under this canonical
			# identity after comparing both live UIA elements. Preserve that proof
			# when the provider later exposes only the alias runtime ID.
			if _terminal_identity_alias_shape(identity, known_runtime_id):
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


CODE_ADDON = addonHandler.getCodeAddon()
ADDON_MANIFEST = CODE_ADDON.manifest
ADDON_ID = ADDON_MANIFEST["name"]
PRODUCT_NAME = ADDON_MANIFEST["summary"]
try:
	from .build_info import ARTIFACT_VERSION as ADDON_VERSION
except ImportError:
	ADDON_VERSION = ADDON_MANIFEST["version"]


def local_session_lister():
	"""Create the neutral lister with NVDA's Windows process adapter."""
	return LocalSessionLister(process_alive=processAlive)


def _linuxComponentConfig():
	fallback = {
		"format": 1,
		"sessionClaim": {"neovimKey": "<F12>", "nvdaGesture": "kb:f12"},
	}
	try:
		path = os.path.join(PACKAGE_DIR, "resources", "linux-components.json")
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
SESSION_CLAIM_GESTURE = _LINUX_COMPONENT_CONFIG["sessionClaim"]["nvdaGesture"]
SESSION_CLAIM_KEY_NAME = _LINUX_COMPONENT_CONFIG["sessionClaim"]["neovimKey"].strip("<>")
LOCAL_CLAIM_WAIT_SECONDS = 1.5
LOCAL_CLAIM_POLL_SECONDS = 0.05
MAX_PENDING_CLIPBOARD_REQUESTS = 32
MAX_PENDING_OUTBOUND_CONTROLS = 64
MAX_PENDING_TERMINAL_CONTROL_REQUESTS = 16


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
		path = os.path.join(PACKAGE_DIR, "resources", "frontend-policy.json")
		with open(path, "r", encoding="utf-8") as stream:
			return FrontendPolicy.from_mapping(json.load(stream))
	except (OSError, ValueError, TypeError, json.JSONDecodeError):
		return FrontendPolicy.from_mapping(fallback)


FRONTEND_POLICY = _frontendPolicy()


def _terminal_identity_alias_shape(identity, other_runtime_id):
	return bool(
		identity is not None
		and identity.frontend_kind == "windowsTerminal"
		and len(identity.runtime_id) >= 2
		and len(other_runtime_id) >= 2
		and identity.runtime_id[-2:] == other_runtime_id[-2:]
	)


def terminal_identities_equivalent(first, first_element, second, second_element):
	"""Confirm two provider-specific runtime IDs for one live WT control."""
	if first == second:
		return True
	if (
		first is None
		or second is None
		or first_element is None
		or second_element is None
		or first.process_id != second.process_id
		or first.window_handle != second.window_handle
		or first.frontend_kind != "windowsTerminal"
		or second.frontend_kind != "windowsTerminal"
		or not _terminal_identity_alias_shape(first, second.runtime_id)
	):
		return False
	descriptor = FRONTEND_POLICY.descriptor("windowsTerminal")
	if descriptor is None or not descriptor.enabled:
		return False
	try:
		if (
			str(first_element.cachedClassName or "") not in descriptor.uia_class_names
			or str(second_element.cachedClassName or "") not in descriptor.uia_class_names
		):
			return False
		import UIAHandler

		# CompareElements alone can be overly permissive with some providers.
		# The process, HWND, WT class, and stable pane tail above are mandatory.
		return bool(UIAHandler.handler.clientObject.compareElements(first_element, second_element))
	except Exception:
		# A provider disagreement or COM failure must keep the controls separate.
		return False


def identity_for_object(obj):
	process_id = getattr(obj, "processID", None)
	window_handle = getattr(obj, "windowHandle", None)
	if not isinstance(process_id, int) or not isinstance(window_handle, int) or not window_handle:
		return None
	descriptor = FRONTEND_POLICY.descriptor("windowsTerminal")
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


def identity_element_for_object(obj, identity):
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


def terminal_identity_fields(identity):
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


FEEDBACK_DEFAULTS = {
	"global": 3,
	"mode": 3,
	"delete": 3,
	"replace": 3,
	"lineBoundary": 2,
	"fileBoundary": 3,
	"lineCrossed": 2,
	"matchingError": 3,
	"diagnosticLine": 2,
	"diagnosticPosition": 2,
	"clipboard": 3,
}
FEEDBACK_FOR_SOUND = {
	"delete": "delete",
	"replace": "replace",
	"lineStart": "lineBoundary",
	"lineEnd": "lineBoundary",
	"explorationOrigin": "lineBoundary",
	"fileStart": "fileBoundary",
	"fileEnd": "fileBoundary",
	"lineCrossed": "lineCrossed",
	"matchingError": "matchingError",
	"diagnosticNone": "diagnosticPosition",
}
FOCUS_ANNOUNCEMENT_VALUES = ("none", "line", "context")
FOCUS_ANNOUNCEMENT_DEFAULT = 2
NAVIGATION_DETAILS_DEFAULTS = {
	"navigationWord": 1,
	"navigationLine": 2,
	"explorationWord": 1,
	"explorationLine": 2,
}
NVDA_CONFIG_SECTION = "NeovimAccessLink"
NVDA_CONFIG_SPEC = {
	"connections": 'string(default="[]")',
	"focusAnnouncement": f"integer(default={FOCUS_ANNOUNCEMENT_DEFAULT}, min=0, max=2)",
	"brailleSuggestionStart": (
		f"integer(default={BRAILLE_SUGGESTION_START_DEFAULT}, "
		f"min={BRAILLE_SUGGESTION_START_DEFAULT}, max={BRAILLE_SUGGESTION_START_MAXIMUM})"
	),
	"brailleDeveloperStart": (
		f"integer(default={BRAILLE_DEVELOPER_START_DEFAULT}, "
		f"min={BRAILLE_DEVELOPER_START_DEFAULT}, max={BRAILLE_DEVELOPER_START_MAXIMUM})"
	),
	"brailleFollowSpeechExploration": (
		f"boolean(default={str(BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT).lower()})"
	),
	"automaticParameterHints": (f"boolean(default={str(AUTOMATIC_PARAMETER_HINTS_DEFAULT).lower()})"),
	"brailleRouting": {
		"wordAction": f"integer(default={BRAILLE_ROUTING_DEFAULTS['wordAction']}, min=0, max=2)",
		"lineAction": f"integer(default={BRAILLE_ROUTING_DEFAULTS['lineAction']}, min=0, max=2)",
		"lineStart": f"integer(default={BRAILLE_ROUTING_DEFAULTS['lineStart']}, min=0, max=2)",
	},
	"feedback": {key: f"integer(default={value}, min=0, max=3)" for key, value in FEEDBACK_DEFAULTS.items()},
	"navigationDetails": {
		key: f"integer(default={value}, min=0, max={1 if key.endswith('Word') else 3})"
		for key, value in NAVIGATION_DETAILS_DEFAULTS.items()
	},
}


def register_nvda_config_spec():
	"""Expose add-on settings to NVDA's native configuration-profile stack."""
	if NVDA_CONFIG_SECTION not in config.conf.spec:
		config.conf.spec[NVDA_CONFIG_SECTION] = NVDA_CONFIG_SPEC
