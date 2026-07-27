from __future__ import annotations

import unittest

from nvim_nvda_protocol import (
	numbered_choice_state,
	valid_accept_numbered_choice_request,
	valid_numbered_choice_opened,
)


class NumberedChoiceProtocolTests(unittest.TestCase):
	def test_opened_choice_is_bounded_and_items_are_removed_from_cached_state(self) -> None:
		payload = {
			"choiceKind": "spellSuggestions",
			"choiceId": 7,
			"items": ["misspelled", "misapplied"],
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
			"lineText": "mispelled",
		}
		self.assertTrue(valid_numbered_choice_opened(payload))
		self.assertNotIn("items", numbered_choice_state(payload))
		self.assertFalse(valid_numbered_choice_opened({**payload, "items": []}))
		self.assertFalse(valid_numbered_choice_opened({**payload, "items": ["bad\0item"]}))
		self.assertFalse(valid_numbered_choice_opened({**payload, "choiceKind": "confirm"}))

	def test_accept_control_has_one_exact_zero_based_item(self) -> None:
		payload = {
			"requestId": 8,
			"choiceKind": "spellSuggestions",
			"choiceId": 7,
			"itemIndex": 1,
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
		}
		self.assertTrue(valid_accept_numbered_choice_request(payload))
		self.assertFalse(valid_accept_numbered_choice_request({**payload, "itemIndex": -1}))
		self.assertFalse(valid_accept_numbered_choice_request({**payload, "extra": True}))


if __name__ == "__main__":
	unittest.main()
