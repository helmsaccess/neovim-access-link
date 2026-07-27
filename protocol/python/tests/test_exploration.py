from __future__ import annotations

import unittest

from nvim_nvda_protocol import (
	exploration_result_state,
	valid_end_exploration_request,
	valid_explore_text_request,
	valid_explore_text_result,
)


def request() -> dict:
	return {
		"requestId": 1,
		"explorationId": 2,
		"actionIndex": 3,
		"action": "wordNext",
		"count": 1,
		"bufferId": 4,
		"windowId": 5,
		"tabpageId": 6,
		"changedtick": 7,
		"modeRaw": "n",
		"cursorLine": 8,
		"cursorByteColumn": 9,
		"cursorVirtualColumn": 10,
	}


class ExplorationProtocolTests(unittest.TestCase):
	def test_step_request_is_exact_and_bounded(self) -> None:
		self.assertTrue(valid_explore_text_request(request()))
		for change in (
			{"action": "executeLua"},
			{"count": 65},
			{"cursorLine": 0},
			{"requestId": True},
			{"extra": "not allowed"},
		):
			with self.subTest(change=change):
				self.assertFalse(valid_explore_text_request({**request(), **change}))

	def test_end_request_accepts_only_two_positive_identifiers(self) -> None:
		self.assertTrue(valid_end_exploration_request({"requestId": 1, "explorationId": 2}))
		self.assertFalse(
			valid_end_exploration_request(
				{
					"requestId": 1,
					"explorationId": 2,
					"command": "arbitrary",
				}
			)
		)
		self.assertFalse(valid_end_exploration_request({"requestId": 1, "explorationId": 0}))

	def test_result_requires_bounded_correlated_semantics(self) -> None:
		result = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 3,
			"action": "wordNext",
			"unit": "word",
			"ok": True,
			"resultCode": "moved",
			"text": "beta",
			"explorationLineText": "alpha beta",
			"line": 8,
			"byteColumn": 9,
			"characterColumn": 9,
			"virtualColumn": 9,
			"atOrigin": False,
			"mode": "normal",
		}
		self.assertTrue(valid_explore_text_result(result))
		self.assertTrue(valid_explore_text_result({**result, "formatError": "spelling"}))
		self.assertFalse(valid_explore_text_result({**result, "formatError": "warning"}))
		self.assertFalse(
			valid_explore_text_result(
				{
					**result,
					"unit": "character",
					"action": "characterRight",
					"formatError": "spelling",
				}
			)
		)
		self.assertFalse(valid_explore_text_result({**result, "text": "x" * (16 * 1024 + 1)}))
		self.assertFalse(
			valid_explore_text_result(
				{
					**result,
					"explorationLineText": "x" * (16 * 1024 + 1),
				}
			)
		)
		self.assertFalse(valid_explore_text_result({**result, "explorationLineText": "x\0y"}))
		self.assertFalse(valid_explore_text_result({**result, "ok": 1}))
		self.assertFalse(valid_explore_text_result({**result, "atOrigin": 0}))
		self.assertTrue(
			valid_explore_text_result(
				{
					**result,
					"ok": False,
					"resultCode": "scanLimit",
				}
			)
		)
		state = exploration_result_state(result)
		self.assertEqual({"mode": "normal"}, state)
		self.assertNotIn("explorationLineText", state)
		self.assertEqual(
			{"mode": "normal"},
			exploration_result_state({**result, "formatError": "spelling"}),
		)


if __name__ == "__main__":
	unittest.main()
