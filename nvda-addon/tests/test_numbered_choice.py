from __future__ import annotations

import unittest

from nvim_nvda_core import (
	NumberedChoiceContext,
	NumberedChoiceController,
	NumberedChoiceDirection,
	NumberedChoiceRejection,
	TerminalIdentity,
)


class NumberedChoiceControllerTests(unittest.TestCase):
	def setUp(self) -> None:
		self.controller = NumberedChoiceController()
		self.context = NumberedChoiceContext(
			"connection-1",
			TerminalIdentity("windowsTerminal", 20, (1, 2, 3), 4),
			object(),
			object(),
		)
		self.event = {
			"type": "numberedChoiceOpened",
			"payload": {
				"choiceKind": "spellSuggestions",
				"choiceId": 5,
				"items": ["first", "second", "third"],
				"bufferId": 1,
				"windowId": 2,
				"tabpageId": 3,
				"changedtick": 4,
			},
		}

	def test_navigation_wraps_and_exposes_only_the_item_label(self) -> None:
		self.assertTrue(self.controller.open(
			self.context,
			self.event,
			capabilities={"numberedChoices"},
		))
		self.assertEqual(
			"first",
			self.controller.navigate(self.context, NumberedChoiceDirection.NEXT).text,
		)
		self.assertEqual(
			"third",
			self.controller.navigate(self.context, NumberedChoiceDirection.PREVIOUS).text,
		)
		self.assertEqual("third", self.controller.display_text())
		self.assertNotIn("3", self.controller.display_text())

	def test_release_discards_only_local_selection_and_accept_keeps_native_index(self) -> None:
		self.controller.open(self.context, self.event, capabilities={"numberedChoices"})
		self.controller.navigate(self.context, NumberedChoiceDirection.NEXT)
		plan = self.controller.accept_plan(self.context, 9)
		self.assertTrue(plan.ready)
		self.assertEqual(0, plan.payload["itemIndex"])
		self.assertNotIn("first", plan.payload)
		self.assertTrue(self.controller.discard_selection(self.context))
		self.assertIsNone(self.controller.display_text())
		self.assertTrue(self.controller.available(self.context))
		self.assertEqual(
			NumberedChoiceRejection.NO_SELECTED_ITEM,
			self.controller.accept_plan(self.context, 10).rejection,
		)

	def test_invalid_or_stale_context_fails_closed_locally(self) -> None:
		self.assertFalse(self.controller.open(self.context, self.event, capabilities=set()))
		self.assertFalse(self.controller.available(self.context))
		self.controller.open(self.context, self.event, capabilities={"numberedChoices"})
		other = NumberedChoiceContext(
			"connection-2",
			self.context.identity,
			self.context.adapter_token,
			self.context.service_generation,
		)
		self.assertEqual(
			NumberedChoiceRejection.CONTEXT_CHANGED,
			self.controller.navigate(other, NumberedChoiceDirection.NEXT).rejection,
		)

	def test_close_must_match_the_exact_native_prompt_and_editor_state(self) -> None:
		self.controller.open(self.context, self.event, capabilities={"numberedChoices"})
		closed = {
			"type": "numberedChoiceClosed",
			"payload": {
				"choiceKind": "spellSuggestions",
				"choiceId": 5,
				"bufferId": 1,
				"windowId": 2,
				"tabpageId": 3,
				"changedtick": 4,
			},
		}
		self.assertFalse(self.controller.close(
			self.context,
			{"type": "numberedChoiceClosed", "payload": {**closed["payload"], "windowId": 9}},
		))
		self.assertTrue(self.controller.available(self.context))
		self.assertTrue(self.controller.close(self.context, closed))
		self.assertFalse(self.controller.available(self.context))


if __name__ == "__main__":
	unittest.main()
