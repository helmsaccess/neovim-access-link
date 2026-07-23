from __future__ import annotations

import unittest

from nvim_nvda_core import (
	ExplorationAction,
	ExplorationContext,
	ExplorationController,
	ExplorationRejection,
	ExplorationUnit,
	SpeechPlanner,
	TerminalIdentity,
)


def editor_state(**changes):
	value = {
		"bufferId": 1,
		"windowId": 2,
		"tabpageId": 3,
		"changedtick": 4,
		"modeRaw": "n",
		"lineText": "alpha beta",
		"character": "a",
		"word": "alpha",
		"cursor": {
			"line": 5,
			"byteColumn": 0,
			"characterColumn": 0,
			"virtualColumn": 0,
		},
	}
	value.update(changes)
	return value


class RequestIds:
	def __init__(self) -> None:
		self.value = 0

	def __call__(self) -> int:
		self.value += 1
		return self.value


class ExplorationControllerTests(unittest.TestCase):
	def setUp(self) -> None:
		self.ids = RequestIds()
		self.controller = ExplorationController(self.ids, max_pending_requests=2)
		self.identity = TerminalIdentity("windowsTerminal", 20, (1, 2, 3), 4)
		self.context = ExplorationContext("connection-1", self.identity, object(), object())

	@staticmethod
	def result_payload(plan, **changes):
		value = {
			**editor_state(),
			"requestId": plan.request_id,
			"explorationId": plan.exploration_id,
			"actionIndex": plan.action_index,
			"action": plan.payload["action"],
			"unit": {
				"characterLeft": "character",
				"characterRight": "character",
				"lineUp": "line",
				"lineDown": "line",
				"wordPrevious": "word",
				"wordNext": "word",
			}[plan.payload["action"]],
			"ok": True,
			"resultCode": "moved",
			"text": "value",
			"line": 5,
			"byteColumn": 1,
			"characterColumn": 1,
			"virtualColumn": 1,
			"atOrigin": False,
		}
		value.update(changes)
		return value

	def test_first_step_is_fixed_bounded_and_uses_canonical_origin(self) -> None:
		plan = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		self.assertTrue(plan.ready)
		self.assertEqual("exploreTextRequest", plan.control)
		self.assertEqual(
			{
				"requestId": 1,
				"explorationId": 1,
				"actionIndex": 1,
				"action": "characterRight",
				"count": 1,
				"bufferId": 1,
				"windowId": 2,
				"tabpageId": 3,
				"changedtick": 4,
				"modeRaw": "n",
				"cursorLine": 5,
				"cursorByteColumn": 0,
				"cursorVirtualColumn": 0,
			},
			dict(plan.payload),
		)
		with self.assertRaises(TypeError):
			plan.payload["action"] = "arbitrary"

	def test_capability_and_incomplete_state_fail_without_starting(self) -> None:
		missing = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.LINE_DOWN,
			capabilities=set(),
		)
		self.assertEqual(ExplorationRejection.CAPABILITY_MISSING, missing.rejection)
		self.assertFalse(self.controller.active)
		incomplete = self.controller.plan_step(
			self.context,
			editor_state(cursor={"line": 1}),
			ExplorationAction.LINE_DOWN,
			capabilities={"exploration"},
		)
		self.assertEqual(ExplorationRejection.INCOMPLETE_STATE, incomplete.rejection)
		self.assertFalse(self.controller.active)

	def test_context_or_real_cursor_change_invalidates_without_restart(self) -> None:
		self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		changed_cursor = editor_state(
			cursor={
				"line": 5,
				"byteColumn": 1,
				"characterColumn": 1,
				"virtualColumn": 1,
			}
		)
		rejected = self.controller.plan_step(
			self.context,
			changed_cursor,
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		self.assertEqual(ExplorationRejection.CONTEXT_CHANGED, rejected.rejection)
		self.assertFalse(self.controller.active)

	def test_pending_results_are_bounded_and_old_result_is_rejected(self) -> None:
		first = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		second = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		third = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		self.assertEqual((first.request_id,), third.discarded_request_ids)
		stale = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": self.result_payload(first, text="b"),
			},
		)
		self.assertEqual(ExplorationRejection.STALE_OR_UNBOUND, stale.rejection)
		accepted = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": self.result_payload(second, text="c"),
			},
		)
		self.assertTrue(accepted.accepted)
		self.assertEqual(
			("c", True, ExplorationUnit.CHARACTER),
			(
				accepted.speech_action.text,
				accepted.speech_action.spelling,
				accepted.unit,
			),
		)

	def test_mismatched_result_metadata_is_rejected(self) -> None:
		plan = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.WORD_NEXT,
			capabilities={"exploration"},
		)
		result = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": self.result_payload(
					plan,
					action="lineDown",
					unit="line",
					text="untrusted",
				),
			},
		)
		self.assertEqual(ExplorationRejection.INVALID_RESULT, result.rejection)
		self.assertFalse(self.controller.active)
		self.assertEqual(
			ExplorationRejection.INVALID_RESULT,
			self.controller.consume_result(self.context, None).rejection,
		)

	def test_result_with_changed_real_origin_is_rejected(self) -> None:
		plan = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		result = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": {
					**self.result_payload(plan, text="b"),
					"changedtick": 5,
				},
			},
		)
		self.assertEqual(ExplorationRejection.STALE_OR_UNBOUND, result.rejection)
		self.assertFalse(self.controller.active)

	def test_inconsistent_character_origin_marker_is_rejected(self) -> None:
		plan = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		result = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": self.result_payload(plan, text="b", atOrigin=True),
			},
		)
		self.assertEqual(ExplorationRejection.INVALID_RESULT, result.rejection)
		self.assertFalse(self.controller.active)

	def test_boundary_result_reuses_directional_sound(self) -> None:
		plan = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.LINE_UP,
			capabilities={"exploration"},
		)
		result = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": self.result_payload(
					plan,
					resultCode="boundary",
					text="",
					atOrigin=True,
				),
			},
		)
		self.assertTrue(result.accepted)
		self.assertEqual(
			("blank", "fileStart"),
			(
				result.speech_action.text,
				result.speech_action.sound,
			),
		)

	def test_each_unit_return_to_origin_plays_once_per_return(self) -> None:
		cases = (
			(
				ExplorationAction.CHARACTER_RIGHT,
				ExplorationAction.CHARACTER_LEFT,
				{"text": "b", "line": 5, "byteColumn": 1},
				{"text": "a", "line": 5, "byteColumn": 0},
				"lineStart",
			),
			(
				ExplorationAction.LINE_DOWN,
				ExplorationAction.LINE_UP,
				{"text": "next line", "line": 6, "byteColumn": 0},
				{"text": "alpha beta", "line": 5, "byteColumn": 0},
				"fileStart",
			),
			(
				ExplorationAction.WORD_NEXT,
				ExplorationAction.WORD_PREVIOUS,
				{"text": "beta", "line": 5, "byteColumn": 6},
				{"text": "alpha", "line": 5, "byteColumn": 0},
				"fileStart",
			),
		)
		for away_action, return_action, away_changes, return_changes, boundary_sound in cases:
			with self.subTest(unit=away_action):
				controller = ExplorationController(RequestIds(), max_pending_requests=2)
				away = controller.plan_step(
					self.context,
					editor_state(),
					away_action,
					capabilities={"exploration"},
				)
				away_result = controller.consume_result(
					self.context,
					{
						"type": "exploreTextResult",
						"payload": self.result_payload(
							away,
							**away_changes,
							characterColumn=away_changes["byteColumn"],
							virtualColumn=away_changes["byteColumn"],
							atOrigin=False,
						),
					},
				)
				self.assertIsNone(away_result.speech_action.sound)

				returned = controller.plan_step(
					self.context,
					editor_state(),
					return_action,
					capabilities={"exploration"},
				)
				returned_result = controller.consume_result(
					self.context,
					{
						"type": "exploreTextResult",
						"payload": self.result_payload(
							returned,
							**return_changes,
							characterColumn=return_changes["byteColumn"],
							virtualColumn=return_changes["byteColumn"],
							atOrigin=True,
						),
					},
				)
				self.assertEqual("explorationOrigin", returned_result.speech_action.sound)

				boundary = controller.plan_step(
					self.context,
					editor_state(),
					return_action,
					capabilities={"exploration"},
				)
				boundary_result = controller.consume_result(
					self.context,
					{
						"type": "exploreTextResult",
						"payload": self.result_payload(
							boundary,
							**return_changes,
							resultCode="boundary",
							characterColumn=return_changes["byteColumn"],
							virtualColumn=return_changes["byteColumn"],
							atOrigin=True,
						),
					},
				)
				self.assertEqual(boundary_sound, boundary_result.speech_action.sound)

	def test_release_uses_last_unit_at_real_cursor_and_drops_late_results(self) -> None:
		word = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.WORD_NEXT,
			capabilities={"exploration"},
		)
		release = self.controller.release(self.context, editor_state())
		self.assertTrue(release.ready)
		planner = SpeechPlanner()
		planner.plan({"type": "fullState", "payload": editor_state()})
		normal_word = planner.plan({"type": "wordMoved", "payload": editor_state()})[0]
		self.assertEqual(
			(
				normal_word.text,
				normal_word.character_suffix,
				normal_word.force_symbols,
			),
			(
				release.speech_action.text,
				release.speech_action.character_suffix,
				release.speech_action.force_symbols,
			),
		)
		self.assertEqual("endExplorationRequest", release.cleanup.control)
		self.assertEqual(word.exploration_id, release.cleanup.exploration_id)
		self.assertFalse(self.controller.active)
		late = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": {
					"requestId": word.request_id,
					"explorationId": word.exploration_id,
					"actionIndex": word.action_index,
					"action": "wordNext",
					"unit": "word",
					"ok": True,
					"resultCode": "moved",
					"text": "beta",
				},
			},
		)
		self.assertEqual(ExplorationRejection.STALE_OR_UNBOUND, late.rejection)

	def test_release_matches_normal_character_and_line_navigation_presentation(self) -> None:
		character_controller = ExplorationController(RequestIds())
		character_controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		character = character_controller.release(self.context, editor_state()).speech_action
		self.assertEqual(
			("a", True, None),
			(character.text, character.spelling, character.character_suffix),
		)

		line_controller = ExplorationController(RequestIds())
		line_state = editor_state(
			lineText="\talpha beta",
			character="a",
			cursor={
				"line": 5,
				"byteColumn": 1,
				"characterColumn": 1,
				"virtualColumn": 4,
			},
		)
		line_controller.plan_step(
			self.context,
			line_state,
			ExplorationAction.LINE_DOWN,
			capabilities={"exploration"},
		)
		line = line_controller.release(self.context, line_state).speech_action
		planner = SpeechPlanner()
		planner.plan({
			"type": "fullState",
			"payload": editor_state(
				lineText="old",
				cursor={
					"line": 4,
					"byteColumn": 1,
					"characterColumn": 1,
					"virtualColumn": 1,
				},
			),
		})
		normal_line = planner.plan({"type": "lineChanged", "payload": line_state})[0]
		self.assertEqual(
			(
				normal_line.text,
				normal_line.character_suffix,
				normal_line.indentation_tones,
			),
			(line.text, line.character_suffix, line.indentation_tones),
		)

	def test_release_word_character_is_configurable(self) -> None:
		for include_character in (False, True):
			with self.subTest(includeCharacter=include_character):
				controller = ExplorationController(RequestIds())
				state = editor_state(word="alpha", character="a")
				controller.plan_step(
					self.context,
					state,
					ExplorationAction.WORD_NEXT,
					capabilities={"exploration"},
				)
				action = controller.release(
					self.context,
					state,
					word_character=include_character,
				).speech_action
				self.assertEqual(
					"a" if include_character else None,
					action.character_suffix,
				)

	def test_release_line_supports_every_detail_combination(self) -> None:
		for line_word, line_character, expected in (
			(False, False, (None, None)),
			(True, False, ("beta", None)),
			(False, True, (None, "b")),
			(True, True, ("beta", "b")),
		):
			with self.subTest(
				lineWord=line_word,
				lineCharacter=line_character,
			):
				controller = ExplorationController(RequestIds())
				state = editor_state(
					lineText="alpha beta",
					word="beta",
					character="b",
				)
				controller.plan_step(
					self.context,
					state,
					ExplorationAction.LINE_DOWN,
					capabilities={"exploration"},
				)
				action = controller.release(
					self.context,
					state,
					line_word=line_word,
					line_character=line_character,
				).speech_action
				self.assertEqual(expected, (
					action.word_suffix,
					action.character_suffix,
				))

	def test_release_character_at_line_end_uses_sound_without_guessing_text(self) -> None:
		self.controller.plan_step(
			self.context,
			editor_state(character=""),
			ExplorationAction.CHARACTER_LEFT,
			capabilities={"exploration"},
		)
		release = self.controller.release(self.context, editor_state(character=""))
		self.assertEqual(
			("", "lineEnd", False),
			(
				release.speech_action.text,
				release.speech_action.sound,
				release.speech_action.spelling,
			),
		)

	def test_release_after_context_change_is_silent_and_clears_pending(self) -> None:
		self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.LINE_DOWN,
			capabilities={"exploration"},
		)
		release = self.controller.release(self.context, editor_state(changedtick=5))
		self.assertEqual(ExplorationRejection.CONTEXT_CHANGED, release.rejection)
		self.assertIsNone(release.speech_action)
		self.assertFalse(self.controller.active)

	def test_result_text_is_strictly_bounded(self) -> None:
		plan = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.LINE_DOWN,
			capabilities={"exploration"},
		)
		result = self.controller.consume_result(
			self.context,
			{
				"type": "exploreTextResult",
				"payload": self.result_payload(plan, text="x" * (16 * 1024 + 1)),
			},
		)
		self.assertEqual(ExplorationRejection.INVALID_RESULT, result.rejection)
		self.assertFalse(self.controller.active)

	def test_failed_dispatch_invalidates_only_its_active_exploration(self) -> None:
		first = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		self.assertTrue(self.controller.fail_request(first.request_id))
		self.assertFalse(self.controller.active)

		second = self.controller.plan_step(
			self.context,
			editor_state(),
			ExplorationAction.CHARACTER_RIGHT,
			capabilities={"exploration"},
		)
		self.assertFalse(self.controller.fail_request(first.request_id))
		self.assertTrue(self.controller.active)
		self.assertTrue(self.controller.fail_request(second.request_id))


if __name__ == "__main__":
	unittest.main()
