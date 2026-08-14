"""Transactional access to the add-on's NVDA configuration section."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .core.braille_routing_repeats import BrailleRoutingActions
from .core.connection_profiles import parse_profiles


BRAILLE_SUGGESTION_START_DEFAULT = 1
BRAILLE_SUGGESTION_START_MAXIMUM = 1000
BRAILLE_DEVELOPER_START_DEFAULT = BRAILLE_SUGGESTION_START_DEFAULT
BRAILLE_DEVELOPER_START_MAXIMUM = BRAILLE_SUGGESTION_START_MAXIMUM
BRAILLE_ROUTING_WORD_ACTIONS = ("none", "changeWord", "deleteWord")
BRAILLE_ROUTING_LINE_ACTIONS = ("none", "changeLine", "deleteLine")
BRAILLE_ROUTING_LINE_STARTS = ("routing", "indentation", "beginning")
BRAILLE_ROUTING_DEFAULTS = {
	"wordAction": 0,
	"lineAction": 0,
	"lineStart": 0,
}
BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT = True
AUTOMATIC_PARAMETER_HINTS_DEFAULT = True


@dataclass(frozen=True)
class SettingsChange:
	"""Describe one committed settings transition."""

	feedback_changed: bool
	navigation_details_changed: bool
	braille_suggestion_start_changed: bool
	braille_developer_start_changed: bool
	braille_routing_changed: bool
	braille_follow_speech_exploration_changed: bool
	automatic_parameter_hints_changed: bool
	focus_announcement_changed: bool
	connections_changed: bool
	claim_inventory_started: bool


class SettingsService:
	"""Own normalized settings, NVDA persistence, and profile-switch reloads."""

	def __init__(
		self,
		config_root: Any,
		*,
		section_name: str,
		feedback_defaults: dict[str, int],
		navigation_details_defaults: dict[str, int],
		focus_announcement_values: tuple[str, ...],
		focus_announcement_default: int,
		record_diagnostic: Callable[..., None],
		on_connections_changed: Callable[[], bool],
	):
		self._configRoot = config_root
		self._sectionName = section_name
		self._feedbackDefaults = dict(feedback_defaults)
		self._navigationDetailsDefaults = dict(navigation_details_defaults)
		self._focusAnnouncementValues = tuple(focus_announcement_values)
		self._focusAnnouncementDefault = focus_announcement_default
		self._recordDiagnostic = record_diagnostic
		self._onConnectionsChanged = on_connections_changed
		self._values = self._load()

	def snapshot(self) -> dict:
		"""Return a detached settings value safe for dialogs and presentation."""
		return deepcopy(self._values)

	def normalize(self, settings: object) -> dict:
		"""Return the current schema with invalid values replaced by defaults."""
		if not isinstance(settings, dict):
			self._recordDiagnostic("configError", error="settings must be an object")
			settings = {}
		raw_feedback = settings.get("feedback", {})
		raw_navigation_details = settings.get("navigationDetails", {})
		raw_connections = settings.get("connections")
		raw_braille_routing = settings.get("brailleRouting", {})
		braille_follow_speech_exploration = settings.get(
			"brailleFollowSpeechExploration",
			BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
		)
		automatic_parameter_hints = settings.get(
			"automaticParameterHints",
			AUTOMATIC_PARAMETER_HINTS_DEFAULT,
		)
		if not isinstance(raw_feedback, dict):
			self._recordDiagnostic("configError", error="feedback must be an object")
			raw_feedback = {}
		if not isinstance(raw_navigation_details, dict):
			self._recordDiagnostic("configError", error="navigationDetails must be an object")
			raw_navigation_details = {}
		if not isinstance(raw_braille_routing, dict):
			self._recordDiagnostic("configError", error="brailleRouting must be an object")
			raw_braille_routing = {}
		if not isinstance(braille_follow_speech_exploration, bool):
			self._recordDiagnostic(
				"configError",
				error="invalid Braille speech exploration follow setting",
				option="brailleFollowSpeechExploration",
			)
			braille_follow_speech_exploration = BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT
		if not isinstance(automatic_parameter_hints, bool):
			self._recordDiagnostic(
				"configError",
				error="invalid automatic parameter hints setting",
				option="automaticParameterHints",
			)
			automatic_parameter_hints = AUTOMATIC_PARAMETER_HINTS_DEFAULT
		feedback = dict(self._feedbackDefaults)
		for key in feedback:
			value = raw_feedback.get(key, feedback[key])
			if isinstance(value, int) and 0 <= value <= 3:
				feedback[key] = value
			else:
				self._recordDiagnostic("configError", error="invalid feedback mode", option=key)
		navigation_details = dict(self._navigationDetailsDefaults)
		for key, default in navigation_details.items():
			value = raw_navigation_details.get(key, default)
			maximum = 1 if key.endswith("Word") else 3
			if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum:
				navigation_details[key] = value
			else:
				self._recordDiagnostic(
					"configError",
					error="invalid navigation details",
					option=key,
				)
		braille_suggestion_start = settings.get(
			"brailleSuggestionStart",
			BRAILLE_SUGGESTION_START_DEFAULT,
		)
		if not (
			isinstance(braille_suggestion_start, int)
			and not isinstance(braille_suggestion_start, bool)
			and BRAILLE_SUGGESTION_START_DEFAULT
			<= braille_suggestion_start
			<= BRAILLE_SUGGESTION_START_MAXIMUM
		):
			self._recordDiagnostic(
				"configError",
				error="invalid Braille suggestion start",
				option="brailleSuggestionStart",
			)
			braille_suggestion_start = BRAILLE_SUGGESTION_START_DEFAULT
		braille_developer_start = settings.get(
			"brailleDeveloperStart",
			braille_suggestion_start,
		)
		if not (
			isinstance(braille_developer_start, int)
			and not isinstance(braille_developer_start, bool)
			and BRAILLE_DEVELOPER_START_DEFAULT <= braille_developer_start <= BRAILLE_DEVELOPER_START_MAXIMUM
		):
			self._recordDiagnostic(
				"configError",
				error="invalid Braille developer information start",
				option="brailleDeveloperStart",
			)
			braille_developer_start = braille_suggestion_start
		braille_routing = dict(BRAILLE_ROUTING_DEFAULTS)
		for key, maximum in (
			("wordAction", len(BRAILLE_ROUTING_WORD_ACTIONS) - 1),
			("lineAction", len(BRAILLE_ROUTING_LINE_ACTIONS) - 1),
			("lineStart", len(BRAILLE_ROUTING_LINE_STARTS) - 1),
		):
			value = raw_braille_routing.get(key, braille_routing[key])
			if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum:
				braille_routing[key] = value
			else:
				self._recordDiagnostic(
					"configError",
					error="invalid repeated Braille routing setting",
					option=key,
				)
		try:
			connections = parse_profiles(raw_connections)
		except ValueError as error:
			self._recordDiagnostic("configError", error=str(error), option="connections")
			connections = []
		focus_announcement = settings.get(
			"focusAnnouncement",
			self._focusAnnouncementDefault,
		)
		if not (
			isinstance(focus_announcement, int)
			and 0 <= focus_announcement < len(self._focusAnnouncementValues)
		):
			self._recordDiagnostic(
				"configError",
				error="invalid focus announcement",
				option="focusAnnouncement",
			)
			focus_announcement = self._focusAnnouncementDefault
		return {
			"feedback": feedback,
			"navigationDetails": navigation_details,
			"brailleSuggestionStart": braille_suggestion_start,
			"brailleDeveloperStart": braille_developer_start,
			"brailleRouting": braille_routing,
			"brailleFollowSpeechExploration": braille_follow_speech_exploration,
			"automaticParameterHints": automatic_parameter_hints,
			"focusAnnouncement": focus_announcement,
			"connections": [profile.as_dict() for profile in connections],
		}

	def update(self, settings: object) -> SettingsChange:
		"""Validate and persist one complete settings transaction."""
		values = self.normalize(settings)
		self._write(values)
		return self._commit(values)

	def save(self) -> None:
		"""Persist the already normalized current snapshot."""
		self._write(self._values)

	def reload(self) -> SettingsChange:
		"""Reload the active NVDA configuration profile without saving it."""
		change = self._commit(self._load())
		self._recordDiagnostic(
			"nvdaConfigProfileSettingsReloaded",
			feedbackChanged=change.feedback_changed,
			navigationDetailsChanged=change.navigation_details_changed,
			brailleSuggestionStartChanged=change.braille_suggestion_start_changed,
			brailleDeveloperStartChanged=change.braille_developer_start_changed,
			brailleRoutingChanged=change.braille_routing_changed,
			brailleFollowSpeechExplorationChanged=(change.braille_follow_speech_exploration_changed),
			automaticParameterHintsChanged=change.automatic_parameter_hints_changed,
			focusAnnouncementChanged=change.focus_announcement_changed,
			connectionsChanged=change.connections_changed,
		)
		return change

	def handle_profile_switch(self, **_kwargs: object) -> None:
		"""NVDA profile-switch callback registered by the composition root."""
		self.reload()

	def focus_announcement(self) -> str:
		index = self._values.get("focusAnnouncement", self._focusAnnouncementDefault)
		if isinstance(index, int) and 0 <= index < len(self._focusAnnouncementValues):
			return self._focusAnnouncementValues[index]
		return self._focusAnnouncementValues[self._focusAnnouncementDefault]

	def navigation_details(self, *, exploration: bool) -> tuple[bool, bool, bool]:
		"""Return word-character, line-word, and line-character choices."""
		values = self._values.get("navigationDetails", self._navigationDetailsDefaults)
		prefix = "exploration" if exploration else "navigation"
		word = values.get(f"{prefix}Word", self._navigationDetailsDefaults[f"{prefix}Word"])
		line = values.get(f"{prefix}Line", self._navigationDetailsDefaults[f"{prefix}Line"])
		return bool(word & 1), bool(line & 1), bool(line & 2)

	def braille_suggestion_start(self) -> int:
		"""Return the one-based Braille cell for transient spelling suggestions."""
		value = self._values.get("brailleSuggestionStart", BRAILLE_SUGGESTION_START_DEFAULT)
		if (
			isinstance(value, int)
			and not isinstance(value, bool)
			and BRAILLE_SUGGESTION_START_DEFAULT <= value <= BRAILLE_SUGGESTION_START_MAXIMUM
		):
			return value
		return BRAILLE_SUGGESTION_START_DEFAULT

	def braille_developer_start(self) -> int:
		"""Return the one-based Braille cell for held developer information."""
		value = self._values.get("brailleDeveloperStart", self.braille_suggestion_start())
		if (
			isinstance(value, int)
			and not isinstance(value, bool)
			and BRAILLE_DEVELOPER_START_DEFAULT <= value <= BRAILLE_DEVELOPER_START_MAXIMUM
		):
			return value
		return self.braille_suggestion_start()

	def braille_routing_actions(self) -> BrailleRoutingActions:
		"""Return fixed repeated-routing actions selected for the active profile."""
		values = self._values.get("brailleRouting", BRAILLE_ROUTING_DEFAULTS)
		try:
			return BrailleRoutingActions(
				word_action=BRAILLE_ROUTING_WORD_ACTIONS[int(values.get("wordAction", 0))],
				line_action=BRAILLE_ROUTING_LINE_ACTIONS[int(values.get("lineAction", 0))],
				line_start=BRAILLE_ROUTING_LINE_STARTS[int(values.get("lineStart", 0))],
			)
		except (IndexError, TypeError, ValueError):
			return BrailleRoutingActions()

	def braille_follows_speech_exploration(self) -> bool:
		"""Return whether contextual speech exploration also owns the Braille line."""
		value = self._values.get(
			"brailleFollowSpeechExploration",
			BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
		)
		return value if isinstance(value, bool) else BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT

	def automatic_parameter_hints(self) -> bool:
		"""Return whether active Insert-mode parameters are spoken automatically."""
		value = self._values.get("automaticParameterHints", AUTOMATIC_PARAMETER_HINTS_DEFAULT)
		return value if isinstance(value, bool) else AUTOMATIC_PARAMETER_HINTS_DEFAULT

	def connection_profile_by_id(self, identifier: str):
		try:
			return next(
				profile
				for profile in parse_profiles(self._values.get("connections", []))
				if profile.identifier == identifier
			)
		except (StopIteration, ValueError):
			return None

	def _load(self) -> dict:
		try:
			section = self._configRoot[self._sectionName]
			connections_value = section.get("connections", "[]")
			if not isinstance(connections_value, str):
				raise ValueError("connections must be a JSON string")
			feedback_section = section.get("feedback", {})
			navigation_details_section = section.get("navigationDetails", {})
			braille_routing_section = section.get("brailleRouting", {})
			if not hasattr(feedback_section, "items"):
				raise ValueError("feedback must be an object")
			if not hasattr(navigation_details_section, "items"):
				raise ValueError("navigationDetails must be an object")
			if not hasattr(braille_routing_section, "items"):
				raise ValueError("brailleRouting must be an object")
			settings = {
				"connections": json.loads(connections_value),
				"focusAnnouncement": section.get(
					"focusAnnouncement",
					self._focusAnnouncementDefault,
				),
				"brailleSuggestionStart": section.get(
					"brailleSuggestionStart",
					BRAILLE_SUGGESTION_START_DEFAULT,
				),
				"brailleDeveloperStart": section.get(
					"brailleDeveloperStart",
					section.get("brailleSuggestionStart", BRAILLE_SUGGESTION_START_DEFAULT),
				),
				"brailleFollowSpeechExploration": section.get(
					"brailleFollowSpeechExploration",
					BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
				),
				"automaticParameterHints": section.get(
					"automaticParameterHints",
					AUTOMATIC_PARAMETER_HINTS_DEFAULT,
				),
				# NVDA exposes nested configuration through AggregatedSection.
				# Its public items() method has normal mapping semantics.
				"feedback": dict(feedback_section.items()),
				"navigationDetails": dict(navigation_details_section.items()),
				"brailleRouting": dict(braille_routing_section.items()),
			}
		except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
			self._recordDiagnostic(
				"configError",
				errorType=type(error).__name__,
				error=str(error),
				source="nvdaConfig",
			)
			settings = {}
		return self.normalize(settings)

	def _write(self, settings: dict) -> None:
		section = self._configRoot[self._sectionName]
		section["focusAnnouncement"] = int(settings.get("focusAnnouncement", self._focusAnnouncementDefault))
		section["brailleSuggestionStart"] = int(
			settings.get("brailleSuggestionStart", BRAILLE_SUGGESTION_START_DEFAULT)
		)
		section["brailleDeveloperStart"] = int(
			settings.get("brailleDeveloperStart", settings["brailleSuggestionStart"])
		)
		section["brailleFollowSpeechExploration"] = bool(
			settings.get(
				"brailleFollowSpeechExploration",
				BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
			)
		)
		section["automaticParameterHints"] = bool(
			settings.get("automaticParameterHints", AUTOMATIC_PARAMETER_HINTS_DEFAULT)
		)
		section["connections"] = json.dumps(
			settings.get("connections", []),
			ensure_ascii=False,
			separators=(",", ":"),
		)
		feedback = section["feedback"]
		values = settings.get("feedback", {})
		for key, default in self._feedbackDefaults.items():
			feedback[key] = int(values.get(key, default))
		navigation_details = section["navigationDetails"]
		values = settings.get("navigationDetails", {})
		for key, default in self._navigationDetailsDefaults.items():
			navigation_details[key] = int(values.get(key, default))
		braille_routing = section["brailleRouting"]
		values = settings.get("brailleRouting", {})
		for key, default in BRAILLE_ROUTING_DEFAULTS.items():
			braille_routing[key] = int(values.get(key, default))

	def _commit(self, values: dict) -> SettingsChange:
		previous = self._values
		feedback_changed = previous.get("feedback") != values.get("feedback")
		navigation_details_changed = previous.get("navigationDetails") != values.get("navigationDetails")
		braille_suggestion_start_changed = previous.get("brailleSuggestionStart") != values.get(
			"brailleSuggestionStart"
		)
		braille_developer_start_changed = previous.get("brailleDeveloperStart") != values.get(
			"brailleDeveloperStart"
		)
		braille_routing_changed = previous.get("brailleRouting") != values.get("brailleRouting")
		braille_follow_speech_exploration_changed = previous.get(
			"brailleFollowSpeechExploration"
		) != values.get("brailleFollowSpeechExploration")
		automatic_parameter_hints_changed = previous.get("automaticParameterHints") != values.get(
			"automaticParameterHints"
		)
		focus_changed = previous.get("focusAnnouncement") != values.get("focusAnnouncement")
		connections_changed = previous.get("connections") != values.get("connections")
		self._values = values
		inventory_started = False
		if connections_changed:
			try:
				inventory_started = bool(self._onConnectionsChanged())
			except Exception as error:
				self._recordDiagnostic(
					"settingsConnectionsChangedError",
					errorType=type(error).__name__,
					error=str(error),
				)
		return SettingsChange(
			feedback_changed=feedback_changed,
			navigation_details_changed=navigation_details_changed,
			braille_suggestion_start_changed=braille_suggestion_start_changed,
			braille_developer_start_changed=braille_developer_start_changed,
			braille_routing_changed=braille_routing_changed,
			braille_follow_speech_exploration_changed=(braille_follow_speech_exploration_changed),
			automatic_parameter_hints_changed=automatic_parameter_hints_changed,
			focus_announcement_changed=focus_changed,
			connections_changed=connections_changed,
			claim_inventory_started=inventory_started,
		)
