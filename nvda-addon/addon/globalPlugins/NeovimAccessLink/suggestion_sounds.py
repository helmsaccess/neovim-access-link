"""Preload NVDA's own suggestion cues and play them without file I/O."""

from __future__ import annotations

import os
import wave

import config
import nvwave


class SuggestionSoundCache:
	_FILES = {"open": "suggestionsOpened.wav", "close": "suggestionsClosed.wav"}
	_PREFIX = "suggestionSound"

	def __init__(self, wave_directory: str, on_diagnostic=None, player_factory=None) -> None:
		self._diagnostic = on_diagnostic or (lambda _category, **_fields: None)
		self._players = {}
		self._frames = {}
		factory = player_factory or self._create_player
		for name, file_name in self._FILES.items():
			self._load(name, os.path.join(wave_directory, file_name), factory)

	def _load(self, name, path, factory) -> None:
		try:
			with wave.open(path, "rb") as source:
				channels = source.getnchannels()
				rate = source.getframerate()
				bits = source.getsampwidth() * 8
				frames = source.readframes(source.getnframes())
			self._players[name] = factory(channels, rate, bits)
			self._frames[name] = frames
			self._diagnostic(self._PREFIX + "Loaded", cue=name, bytes=len(frames))
		except Exception as error:
			self._diagnostic(
				self._PREFIX + "LoadError",
				cue=name,
				errorType=type(error).__name__,
				error=str(error),
			)

	@staticmethod
	def _create_player(channels, rate, bits):
		return nvwave.WavePlayer(
			channels=channels,
			samplesPerSec=rate,
			bitsPerSample=bits,
			outputDevice=config.conf["audio"]["outputDevice"],
			wantDucking=False,
			purpose=nvwave.AudioPurpose.SOUNDS,
		)

	def play(self, cue: str) -> bool:
		presentation = config.conf.get("presentation", {})
		if not bool(presentation.get("reportAutoSuggestionsWithSound", True)):
			self._diagnostic("suggestionSoundSuppressed", cue=cue, reason="nvdaSetting")
			return False
		player = self._players.get(cue)
		frames = self._frames.get(cue)
		if player is None or frames is None:
			self._diagnostic("suggestionSoundUnavailable", cue=cue)
			return False
		try:
			player.feed(frames)
			self._diagnostic("suggestionSoundPlayed", cue=cue, bytes=len(frames))
			return True
		except Exception as error:
			self._diagnostic(
				"suggestionSoundPlayError",
				cue=cue,
				errorType=type(error).__name__,
				error=str(error),
			)
			return False

	def close(self) -> None:
		for player in self._players.values():
			try:
				player.close()
			except Exception:
				pass
		self._players.clear()
		self._frames.clear()


class SpellingSoundCache(SuggestionSoundCache):
	"""Preload NVDA's textError.wav used by its spelling implementation."""

	_FILES = {"error": "textError.wav"}
	_PREFIX = "spellingSound"

	def play(self, cue: str = "error") -> bool:
		player = self._players.get(cue)
		frames = self._frames.get(cue)
		if player is None or frames is None:
			self._diagnostic("spellingSoundUnavailable", cue=cue)
			return False
		try:
			player.feed(frames)
			self._diagnostic("spellingSoundPlayed", bytes=len(frames))
			return True
		except Exception as error:
			self._diagnostic(
				"spellingSoundPlayError",
				errorType=type(error).__name__,
				error=str(error),
			)
			return False


class EditorSoundCache(SuggestionSoundCache):
	"""Preload NVDA-native and bundled CC0 editor earcons."""

	_PREFIX = "editorSound"
	_NVDA_FILES = {
		"insertMode": "focusMode.wav",
		"normalMode": "browseMode.wav",
		"matchingError": "error.wav",
	}
	_BUNDLED_FILES = {
		"delete": "delete.wav",
		"replace": "replace.wav",
		"lineStart": "lineStart.wav",
		"lineEnd": "lineEnd.wav",
		"fileStart": "fileStart.wav",
		"fileEnd": "fileEnd.wav",
		"lineCrossed": "lineCrossed.wav",
	}

	def __init__(self, nvda_wave_directory, bundled_directory, on_diagnostic=None, player_factory=None):
		self._diagnostic = on_diagnostic or (lambda _category, **_fields: None)
		self._players = {}
		self._frames = {}
		factory = player_factory or self._create_player
		for name, file_name in self._NVDA_FILES.items():
			self._load(name, os.path.join(nvda_wave_directory, file_name), factory)
		for name, file_name in self._BUNDLED_FILES.items():
			self._load(name, os.path.join(bundled_directory, file_name), factory)

	def play(self, cue: str) -> bool:
		player = self._players.get(cue)
		frames = self._frames.get(cue)
		if player is None or frames is None:
			self._diagnostic("editorSoundUnavailable", cue=cue)
			return False
		try:
			player.feed(frames)
			self._diagnostic("editorSoundPlayed", cue=cue, bytes=len(frames))
			return True
		except Exception as error:
			self._diagnostic(
				"editorSoundPlayError",
				cue=cue,
				errorType=type(error).__name__,
				error=str(error),
			)
			return False
