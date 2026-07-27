from __future__ import annotations

import unittest

from nvim_nvda_protocol import valid_braille_route_action_request


class BrailleRoutingActionValidationTests(unittest.TestCase):
	def setUp(self) -> None:
		self.payload = {
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"byteColumn": 4,
			"changedtick": 5,
			"modeRaw": "n",
			"action": "changeWord",
		}

	def test_accepts_only_fixed_word_and_line_actions(self) -> None:
		for action in ("changeWord", "deleteWord"):
			with self.subTest(action=action):
				self.assertTrue(
					valid_braille_route_action_request(
						{
							**self.payload,
							"action": action,
						}
					)
				)
		for action in ("changeLine", "deleteLine"):
			for line_start in ("routing", "indentation", "beginning"):
				with self.subTest(action=action, line_start=line_start):
					self.assertTrue(
						valid_braille_route_action_request(
							{
								**self.payload,
								"modeRaw": "i",
								"action": action,
								"lineStart": line_start,
							}
						)
					)

	def test_rejects_other_modes_actions_fields_and_unbounded_values(self) -> None:
		for changed in (
			{"modeRaw": "c"},
			{"modeRaw": "R"},
			{"modeRaw": "n" * 17},
			{"action": "dd"},
			{"line": 0},
			{"byteColumn": True},
			{"extra": "ignored"},
			{"action": "changeWord", "lineStart": "routing"},
			{"action": "changeLine"},
			{"action": "deleteLine", "lineStart": "cursor"},
		):
			with self.subTest(changed=changed):
				self.assertFalse(
					valid_braille_route_action_request(
						{
							**self.payload,
							**changed,
						}
					)
				)
