from __future__ import annotations

import unittest

from nvim_nvda_protocol import valid_move_braille_line_request


class BrailleLineNavigationValidationTests(unittest.TestCase):
	def setUp(self) -> None:
		self.payload = {
			"bufferId": 1,
			"windowId": 2,
			"line": 3,
			"changedtick": 4,
			"modeRaw": "i",
			"direction": "next",
			"targetColumn": "preferred",
			"preferredVirtualColumn": 79,
		}

	def test_accepts_complete_editor_line_navigation(self) -> None:
		self.assertTrue(valid_move_braille_line_request(self.payload))
		self.assertTrue(
			valid_move_braille_line_request({
				**self.payload,
				"modeRaw": "n",
				"direction": "previous",
			})
		)

	def test_rejects_command_terminal_unbounded_and_extra_state(self) -> None:
		for changed in (
			{"modeRaw": "c"},
			{"modeRaw": "t"},
			{"direction": "left"},
			{"targetColumn": "middle"},
			{"preferredVirtualColumn": True},
			{"preferredVirtualColumn": 2_147_483_648},
			{"line": 0},
			{"extra": "ignored"},
		):
			with self.subTest(changed=changed):
				self.assertFalse(valid_move_braille_line_request({**self.payload, **changed}))
