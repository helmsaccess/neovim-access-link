from __future__ import annotations

import unittest

from nvim_nvda_core.braille_routing_repeats import (
	BrailleRoutingActions,
	BrailleRoutingPressKind,
	BrailleRoutingRepeatController,
)


class BrailleRoutingRepeatTests(unittest.TestCase):
	def setUp(self) -> None:
		self.controller = BrailleRoutingRepeatController()
		self.actions = BrailleRoutingActions(
			word_action="changeWord",
			line_action="deleteLine",
			line_start="indentation",
		)

	def press(self, now: int, identity: object = ("buffer", 1, 4)):
		return self.controller.press(
			identity,
			now_ms=now,
			timeout_ms=500,
			actions=self.actions,
		)

	def test_first_routes_second_waits_and_third_replaces_word_with_line(self) -> None:
		self.assertIs(BrailleRoutingPressKind.ROUTE, self.press(0).kind)
		second = self.press(300)
		self.assertIs(BrailleRoutingPressKind.WAIT, second.kind)
		self.assertEqual(500, second.delay_ms)
		third = self.press(600)
		self.assertIs(BrailleRoutingPressKind.LINE, third.kind)
		self.assertEqual("deleteLine", third.action)
		self.assertEqual("indentation", third.line_start)
		self.assertIs(BrailleRoutingPressKind.NONE, self.controller.expire(second.token).kind)

	def test_double_press_expires_to_word_action(self) -> None:
		self.press(0)
		second = self.press(200)
		expired = self.controller.expire(second.token)
		self.assertIs(BrailleRoutingPressKind.WORD, expired.kind)
		self.assertEqual("changeWord", expired.action)
		self.assertIs(BrailleRoutingPressKind.NONE, self.controller.expire(second.token).kind)

	def test_changed_position_and_timeout_begin_a_new_single_route(self) -> None:
		self.press(0)
		self.assertIs(
			BrailleRoutingPressKind.ROUTE,
			self.press(100, ("buffer", 1, 5)).kind,
		)
		self.assertIs(
			BrailleRoutingPressKind.ROUTE,
			self.press(601, ("buffer", 1, 5)).kind,
		)

	def test_word_only_runs_immediately_on_second_press(self) -> None:
		actions = BrailleRoutingActions(word_action="deleteWord")
		first = self.controller.press("same", now_ms=0, timeout_ms=500, actions=actions)
		second = self.controller.press("same", now_ms=1, timeout_ms=500, actions=actions)
		self.assertIs(BrailleRoutingPressKind.ROUTE, first.kind)
		self.assertIs(BrailleRoutingPressKind.WORD, second.kind)
		self.assertEqual("deleteWord", second.action)

	def test_line_only_waits_for_third_and_double_expiry_does_nothing(self) -> None:
		actions = BrailleRoutingActions(line_action="changeLine", line_start="beginning")
		self.controller.press("same", now_ms=0, timeout_ms=500, actions=actions)
		second = self.controller.press("same", now_ms=1, timeout_ms=500, actions=actions)
		self.assertIs(BrailleRoutingPressKind.WAIT, second.kind)
		self.assertIs(BrailleRoutingPressKind.NONE, self.controller.expire(second.token).kind)

	def test_disabled_actions_preserve_every_single_route(self) -> None:
		for now in (0, 10, 20):
			self.assertIs(
				BrailleRoutingPressKind.ROUTE,
				self.controller.press(
					"same",
					now_ms=now,
					timeout_ms=500,
					actions=BrailleRoutingActions(),
				).kind,
			)

	def test_invalid_settings_and_times_are_rejected(self) -> None:
		for kwargs in (
			{"word_action": "cw"},
			{"line_action": "dd"},
			{"line_start": "cursor"},
		):
			with self.subTest(kwargs=kwargs):
				with self.assertRaises(ValueError):
					BrailleRoutingActions(**kwargs)
		with self.assertRaises(ValueError):
			self.controller.press("same", now_ms=-1, timeout_ms=500, actions=self.actions)
		with self.assertRaises(ValueError):
			self.controller.press("same", now_ms=0, timeout_ms=0, actions=self.actions)
