"""NVDA speech, Braille-message, tone, and sound delivery service."""

from __future__ import annotations

import addonHandler
import braille as nvdaBraille
import config
import speech
import tones
from logHandler import log
from speech.priorities import SpeechPriority as NvdaSpeechPriority

from .core.speech import Priority
from .editor_session import mode_sound_kind as editor_mode_sound_kind
from .suggestion_sounds import EditorSoundCache, SpellingSoundCache, SuggestionSoundCache

addonHandler.initTranslation()


class NvdaPresentation:
	"""Own optional editor cues and deliver already planned NVDA feedback."""

	def __init__(
		self,
		nvda_wave_directory,
		bundled_sound_directory,
		settings_provider,
		feedback_defaults,
		feedback_for_sound,
		on_diagnostic,
	):
		self._settings_provider = settings_provider
		self._feedback_defaults = dict(feedback_defaults)
		self._feedback_for_sound = dict(feedback_for_sound)
		self._diagnostic = on_diagnostic
		self.suggestion_sounds = SuggestionSoundCache(
			nvda_wave_directory,
			on_diagnostic=on_diagnostic,
		)
		self.spelling_sound = SpellingSoundCache(
			nvda_wave_directory,
			on_diagnostic=on_diagnostic,
		)
		self.editor_sounds = EditorSoundCache(
			nvda_wave_directory,
			bundled_sound_directory,
			on_diagnostic=on_diagnostic,
		)

	def close(self):
		self.suggestion_sounds.close()
		self.spelling_sound.close()
		self.editor_sounds.close()

	def feedback_mode(self, key):
		settings = self._settings_provider()
		feedback = settings.get("feedback", {})
		global_mode = feedback.get("global", self._feedback_defaults["global"])
		local_mode = feedback.get(key, self._feedback_defaults.get(key, 3)) if key else 3
		return int(global_mode) & int(local_mode)

	@staticmethod
	def mode_sound_kind(mode):
		return editor_mode_sound_kind(mode)

	def play_mode_sound(self, mode, *, focus_context=False):
		sound_kind = self.mode_sound_kind(mode)
		if sound_kind == "insert":
			if self.feedback_mode("mode") & 2 and not self.editor_sounds.play("insertMode"):
				tones.beep(880, 45)
			self._diagnostic(
				"insertModeSound",
				cue="focusMode.wav",
				focusContext=focus_context,
				mode=mode,
			)
		elif sound_kind == "normal":
			if not focus_context:
				speech.cancelSpeech()
			if self.feedback_mode("mode") & 2 and not self.editor_sounds.play("normalMode"):
				tones.beep(330, 28)
			self._diagnostic(
				"normalModeSound",
				cue="browseMode.wav",
				focusContext=focus_context,
				mode=mode,
			)
		elif sound_kind == "commandLine":
			if self.feedback_mode("mode") & 2:
				tones.beep(600, 30)
			self._diagnostic(
				"commandLineModeSound",
				cue="tone-600hz-30ms",
				focusContext=focus_context,
				mode=mode,
			)

	def action_speech_allowed(self, event_type, feedback_key):
		if feedback_key in {"delete", "replace"} and event_type in {
			"textChanged",
			"textDeleted",
			"textReplaced",
			"replacementPerformed",
		}:
			return bool(self.feedback_mode(feedback_key) & 1)
		if feedback_key in {"fileBoundary", "matchingError"}:
			return bool(self.feedback_mode(feedback_key) & 1)
		return True

	def deliver_actions(
		self,
		actions,
		*,
		event_type,
		mode,
		previous_mode,
		payload,
		speak_structured_typing,
	):
		for action in actions:
			indentation = getattr(action, "indentation_tones", None)
			if indentation is not None:
				self.report_indentation(
					indentation,
					getattr(action, "indentation_level", None),
				)
			sound = getattr(action, "sound", None)
			feedback_key = self._feedback_for_sound.get(sound)
			feedback_mode = self.feedback_mode(feedback_key) if feedback_key else 3
			self._play_action_sound(sound, mode, bool(feedback_mode & 2))
			if action.interrupt and action.priority < Priority.CRITICAL:
				speech.cancelSpeech()
			priority = {
				Priority.NAVIGATION: NvdaSpeechPriority.NORMAL,
				Priority.STATUS: NvdaSpeechPriority.NEXT,
				Priority.CRITICAL: NvdaSpeechPriority.NOW,
			}[action.priority]
			try:
				speech_allowed = self.action_speech_allowed(event_type, feedback_key)
				if event_type == "modeChanged" and {previous_mode, mode} <= {"normal", "insert"}:
					speech_allowed = bool(self.feedback_mode("mode") & 1)
				if (
					speech_allowed
					and feedback_key == "lineBoundary"
					and feedback_mode & 1
					and not action.text
				):
					speech.speakText(
						_("line start") if sound == "lineStart" else _("line end"),
						priority=priority,
					)
				elif speech_allowed and feedback_key == "lineCrossed" and feedback_mode & 1:
					speech.speakText(_("new line"), priority=priority)
				format_error = getattr(action, "format_error", None)
				if format_error and speech_allowed:
					self._present_format_error(action, format_error, priority)
				elif getattr(action, "typed", False) and speech_allowed:
					speak_structured_typing(
						action.text,
						payload,
						command_line=event_type == "commandLineChanged",
					)
				elif getattr(action, "spelling", False) and speech_allowed:
					speech.speakSpelling(action.text, priority=priority)
				elif action.text and speech_allowed:
					kwargs = {"priority": priority}
					if getattr(action, "force_symbols", False):
						kwargs["symbolLevel"] = 300
					speech.speakText(action.text, **kwargs)
				if speech_allowed and getattr(action, "character_suffix", None):
					speech.speakSpelling(action.character_suffix, priority=priority)
				if getattr(action, "braille_message", None):
					nvdaBraille.handler.message(action.braille_message)
			except Exception as error:
				self._diagnostic(
					"speechError",
					errorType=type(error).__name__,
					error=str(error),
				)
				log.exception("NeovimAccessLink speech failure")

	def _play_action_sound(self, sound, mode, enabled):
		if sound == "delete":
			if enabled and not self.editor_sounds.play("delete"):
				tones.beep(180, 24)
		elif sound == "replace":
			if enabled and not self.editor_sounds.play("replace"):
				tones.beep(440, 18)
				tones.beep(620, 22)
		elif sound == "lineStart" and mode == "normal":
			if enabled and not self.editor_sounds.play("lineStart"):
				tones.beep(720, 12)
		elif sound == "lineEnd" and mode == "normal":
			if enabled and not self.editor_sounds.play("lineEnd"):
				tones.beep(360, 18)
		elif sound == "explorationOrigin":
			if enabled:
				tones.beep(660, 12)
				tones.beep(880, 12)
		elif sound == "fileStart":
			if enabled and not self.editor_sounds.play("fileStart"):
				tones.beep(520, 35)
		elif sound == "fileEnd":
			if enabled and not self.editor_sounds.play("fileEnd"):
				tones.beep(260, 45)
		elif sound == "lineCrossed":
			if enabled and not self.editor_sounds.play("lineCrossed"):
				tones.beep(610, 16)
		elif sound == "matchingError":
			if enabled and not self.editor_sounds.play("matchingError"):
				tones.beep(190, 35)
		elif sound == "suggestionsOpen":
			self.suggestion_sounds.play("open")
		elif sound == "suggestionsClose":
			self.suggestion_sounds.play("close")

	def _present_format_error(self, action, format_error, priority):
		formatting = config.conf.get("documentFormatting", {})
		report_mode = int(formatting.get("reportSpellingErrors2", 0))
		if getattr(action, "typed_format_error", False):
			keyboard = config.conf.get("keyboard", {})
			speech_state = speech.getState() if hasattr(speech, "getState") else None
			speech_mode = str(getattr(speech_state, "speechMode", "on")).lower()
			speech_active = not (speech_mode.endswith("off") or "ondemand" in speech_mode)
			if report_mode and bool(keyboard.get("alertForSpellingErrors", True)) and speech_active:
				self.spelling_sound.play()
			return
		leaving = format_error.startswith("out:")
		kind = format_error[4:] if leaving else format_error
		if not leaving and report_mode & 2:
			self.spelling_sound.play()
		if (report_mode & 1) or (leaving and report_mode & 3):
			label = "grammar error" if kind == "grammar" else "spelling error"
			speech.speakText(("out of " if leaving else "") + label, priority=priority)

	def report_indentation(self, quarter_tones, level):
		formatting = config.conf.get("documentFormatting", {})
		report_mode = int(formatting.get("reportLineIndentation", 0))
		if report_mode == 0 or not isinstance(quarter_tones, int) or quarter_tones < 0:
			return
		if report_mode in (2, 3) and quarter_tones <= 72:
			duration = int(formatting.get("indentToneDuration", 40))
			frequency = round(220 * (2 ** (quarter_tones / 24.0)))
			tones.beep(frequency, duration)
			self._diagnostic(
				"indentationTone",
				quarterTones=quarter_tones,
				frequency=frequency,
				durationMs=duration,
			)
		if report_mode in (1, 3) or quarter_tones > 72:
			speech.speakText(
				"no indent" if quarter_tones == 0 else f"indentation level {level}",
			)
