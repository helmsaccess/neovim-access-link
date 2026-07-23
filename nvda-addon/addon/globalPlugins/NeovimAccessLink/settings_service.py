"""Transactional access to the add-on's NVDA configuration section."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .core.connection_profiles import parse_profiles


@dataclass(frozen=True)
class SettingsChange:
	"""Describe one committed settings transition."""

	feedback_changed: bool
	navigation_details_changed: bool
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
		if not isinstance(raw_feedback, dict):
			self._recordDiagnostic("configError", error="feedback must be an object")
			raw_feedback = {}
		if not isinstance(raw_navigation_details, dict):
			self._recordDiagnostic("configError", error="navigationDetails must be an object")
			raw_navigation_details = {}
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
			if not hasattr(feedback_section, "items"):
				raise ValueError("feedback must be an object")
			if not hasattr(navigation_details_section, "items"):
				raise ValueError("navigationDetails must be an object")
			settings = {
				"connections": json.loads(connections_value),
				"focusAnnouncement": section.get(
					"focusAnnouncement",
					self._focusAnnouncementDefault,
				),
				# NVDA exposes nested configuration through AggregatedSection.
				# Its public items() method has normal mapping semantics.
				"feedback": dict(feedback_section.items()),
				"navigationDetails": dict(navigation_details_section.items()),
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

	def _commit(self, values: dict) -> SettingsChange:
		previous = self._values
		feedback_changed = previous.get("feedback") != values.get("feedback")
		navigation_details_changed = previous.get("navigationDetails") != values.get(
			"navigationDetails"
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
			focus_announcement_changed=focus_changed,
			connections_changed=connections_changed,
			claim_inventory_started=inventory_started,
		)
