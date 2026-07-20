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
		focus_announcement_values: tuple[str, ...],
		focus_announcement_default: int,
		record_diagnostic: Callable[..., None],
		on_connections_changed: Callable[[], bool],
	):
		self._configRoot = config_root
		self._sectionName = section_name
		self._feedbackDefaults = dict(feedback_defaults)
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
		raw_connections = settings.get("connections")
		if not isinstance(raw_feedback, dict):
			self._recordDiagnostic("configError", error="feedback must be an object")
			raw_feedback = {}
		feedback = dict(self._feedbackDefaults)
		for key in feedback:
			value = raw_feedback.get(key, feedback[key])
			if isinstance(value, int) and 0 <= value <= 3:
				feedback[key] = value
			else:
				self._recordDiagnostic("configError", error="invalid feedback mode", option=key)
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
			if not hasattr(feedback_section, "items"):
				raise ValueError("feedback must be an object")
			settings = {
				"connections": json.loads(connections_value),
				"focusAnnouncement": section.get(
					"focusAnnouncement",
					self._focusAnnouncementDefault,
				),
				# NVDA exposes nested configuration through AggregatedSection.
				# Its public items() method has normal mapping semantics.
				"feedback": dict(feedback_section.items()),
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

	def _commit(self, values: dict) -> SettingsChange:
		previous = self._values
		feedback_changed = previous.get("feedback") != values.get("feedback")
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
			focus_announcement_changed=focus_changed,
			connections_changed=connections_changed,
			claim_inventory_started=inventory_started,
		)
