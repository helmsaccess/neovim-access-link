from __future__ import annotations

import unittest

from nvim_nvda_protocol import (
	valid_braille_explore_line_request,
	valid_braille_explore_line_result,
	valid_end_braille_exploration_request,
)


class BrailleExplorationValidationTests(unittest.TestCase):
	def setUp(self) -> None:
		self.request = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 3,
			"action": "lineDown",
			"count": 1,
			"bufferId": 4,
			"windowId": 5,
			"tabpageId": 6,
			"changedtick": 7,
			"modeRaw": "i",
			"cursorLine": 8,
			"cursorByteColumn": 9,
			"cursorVirtualColumn": 9,
			"desiredVirtualColumn": 79,
			"targetColumn": "preferred",
		}
		self.result = {
			**self.request,
			"ok": True,
			"resultCode": "moved",
			"unit": "line",
			"text": "target",
			"line": 9,
			"byteColumn": 6,
			"characterColumn": 6,
			"virtualColumn": 6,
			"atOrigin": False,
		}

	def test_accepts_only_line_actions_with_a_bounded_desired_column(self) -> None:
		self.assertTrue(valid_braille_explore_line_request(self.request))
		self.assertTrue(valid_braille_explore_line_request({
			**self.request,
			"action": "lineUp",
			"desiredVirtualColumn": 2_147_483_647,
		}))
		for changes in (
			{"action": "characterRight"},
			{"desiredVirtualColumn": True},
			{"desiredVirtualColumn": -1},
			{"desiredVirtualColumn": 2_147_483_648},
			{"targetColumn": "middle"},
			{"count": 65},
			{"modeRaw": ""},
			{"extra": "ignored"},
		):
			with self.subTest(changes=changes):
				self.assertFalse(valid_braille_explore_line_request({
					**self.request,
					**changes,
				}))

	def test_accepts_only_correlated_line_results(self) -> None:
		self.assertTrue(valid_braille_explore_line_result(self.result))
		self.assertTrue(valid_braille_explore_line_result({
			**self.result,
			"ok": False,
			"resultCode": "invalidOrStaleRequest",
		}))
		for changes in (
			{"unit": "character"},
			{"action": "wordNext"},
			{"text": "\0"},
			{"requestId": 0},
		):
			with self.subTest(changes=changes):
				self.assertFalse(valid_braille_explore_line_result({
					**self.result,
					**changes,
				}))

	def test_cleanup_is_exact_and_positive(self) -> None:
		self.assertTrue(valid_end_braille_exploration_request({
			"requestId": 1,
			"explorationId": 2,
		}))
		self.assertFalse(valid_end_braille_exploration_request({
			"requestId": 0,
			"explorationId": 2,
		}))
		self.assertFalse(valid_end_braille_exploration_request({
			"requestId": 1,
			"explorationId": 2,
			"extra": True,
		}))


if __name__ == "__main__":
	unittest.main()
