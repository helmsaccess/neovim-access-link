from __future__ import annotations

import unittest

from nvim_nvda_core import (
	BrailleExplorationController,
	BrailleExplorationRejection,
)


def editor_state(**changes):
	value = {
		"bufferId": 1,
		"windowId": 2,
		"tabpageId": 3,
		"changedtick": 4,
		"mode": "normal",
		"modeRaw": "n",
		"lineText": "origin",
		"lineCount": 6,
		"tabstop": 8,
		"selection": {"currentLine": {"startByteColumn": 0, "endByteColumn": 2}},
		"spellingErrors": [{"startByteColumn": 0, "endByteColumn": 2}],
		"fileManager": {"name": "Oil"},
		"cursor": {
			"line": 3,
			"byteColumn": 2,
			"characterColumn": 2,
			"virtualColumn": 2,
			"preferredVirtualColumn": 79,
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


class BrailleExplorationControllerTests(unittest.TestCase):
	def setUp(self) -> None:
		self.ids = RequestIds()
		self.controller = BrailleExplorationController(self.ids, max_pending_requests=2)
		self.state = editor_state()

	def enable(self):
		plan = self.controller.toggle(
			self.state,
			capabilities={"brailleExploration"},
		)
		self.assertTrue(plan.changed)
		self.assertTrue(plan.enabled)
		return plan

	@staticmethod
	def result(plan, state, **changes):
		action = plan.payload["action"]
		line = state["cursor"]["line"] + (1 if action == "lineDown" else -1)
		value = {
			**state,
			"requestId": plan.request_id,
			"explorationId": plan.payload["explorationId"],
			"actionIndex": plan.payload["actionIndex"],
			"action": action,
			"ok": True,
			"resultCode": "moved",
			"unit": "line",
			"text": "target",
			"line": line,
			"byteColumn": 6,
			"characterColumn": 6,
			"virtualColumn": 6,
			"atOrigin": False,
		}
		value.update(changes)
		return {"type": "brailleExploreLineResult", "payload": value}

	def test_toggle_is_independent_capability_gated_and_cleanup_is_correlated(self) -> None:
		missing = self.controller.toggle(self.state, capabilities={"exploration"})
		self.assertEqual(BrailleExplorationRejection.CAPABILITY_MISSING, missing.rejection)
		self.assertFalse(self.controller.enabled)

		self.enable()
		request = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(request.ready)
		disabled = self.controller.toggle(
			self.state,
			capabilities={"brailleExploration"},
		)
		self.assertTrue(disabled.changed)
		self.assertFalse(disabled.enabled)
		self.assertEqual("endBrailleExplorationRequest", disabled.cleanup_control)
		self.assertEqual(
			{"requestId": 2, "explorationId": 1},
			dict(disabled.cleanup_payload),
		)
		self.assertFalse(self.controller.enabled)

	def test_request_uses_real_origin_but_preserves_neovim_preferred_column(self) -> None:
		self.enable()
		plan = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(plan.ready)
		self.assertEqual("brailleExploreLineRequest", plan.control)
		self.assertEqual(
			{
				"requestId": 1,
				"explorationId": 1,
				"actionIndex": 1,
				"action": "lineDown",
				"count": 1,
				"bufferId": 1,
				"windowId": 2,
				"tabpageId": 3,
				"changedtick": 4,
				"modeRaw": "n",
				"cursorLine": 3,
				"cursorByteColumn": 2,
				"cursorVirtualColumn": 2,
				"desiredVirtualColumn": 79,
				"targetColumn": "preferred",
			},
			dict(plan.payload),
		)
		self.assertEqual(3, self.state["cursor"]["line"])

	def test_horizontal_wrap_targets_replace_the_virtual_preferred_column(self) -> None:
		self.enable()
		end = self.controller.plan_step(
			self.state,
			"previous",
			capabilities={"brailleExploration"},
			target_column="end",
		)
		self.assertTrue(end.ready)
		self.assertEqual("end", end.payload["targetColumn"])
		accepted = self.controller.consume_result(
			self.state,
			self.result(
				end,
				self.state,
				text="0123456789",
				line=2,
				byteColumn=10,
				characterColumn=10,
				virtualColumn=10,
			),
		)
		self.assertTrue(accepted.accepted)

		preferred = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertEqual(10, preferred.payload["desiredVirtualColumn"])
		self.assertEqual("preferred", preferred.payload["targetColumn"])
		self.assertEqual(
			BrailleExplorationRejection.INCOMPLETE_STATE,
			self.controller.plan_step(
				self.state,
				"next",
				capabilities={"brailleExploration"},
				target_column="middle",
			).rejection,
		)

	def test_result_replaces_only_braille_line_and_never_the_real_state(self) -> None:
		self.enable()
		plan = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		result = self.controller.consume_result(
			self.state,
			self.result(plan, self.state),
		)
		self.assertTrue(result.accepted)
		display = self.controller.display_state(self.state)
		self.assertEqual("target", display["lineText"])
		self.assertEqual(
			{
				"line": 4,
				"byteColumn": 6,
				"characterColumn": 6,
				"virtualColumn": 6,
				"preferredVirtualColumn": 79,
			},
			display["cursor"],
		)
		self.assertIsNone(display["selection"])
		self.assertEqual([], display["spellingErrors"])
		self.assertNotIn("fileManager", display)
		self.assertEqual("origin", self.state["lineText"])
		self.assertEqual(3, self.state["cursor"]["line"])

	def test_real_cursor_motion_does_not_move_or_reanchor_virtual_braille(self) -> None:
		self.enable()
		first = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(
			self.controller.consume_result(
				self.state,
				self.result(first, self.state),
			).accepted,
		)
		moved_cursor_state = editor_state(
			mode="insert",
			modeRaw="i",
			lineText="real cursor line",
			cursor={
				"line": 1,
				"byteColumn": 0,
				"characterColumn": 0,
				"virtualColumn": 0,
				"preferredVirtualColumn": 0,
			},
		)
		display = self.controller.display_state(moved_cursor_state)
		self.assertEqual("target", display["lineText"])
		self.assertEqual(4, display["cursor"]["line"])

		second = self.controller.plan_step(
			moved_cursor_state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(second.ready)
		self.assertEqual(3, second.payload["cursorLine"])
		self.assertEqual(2, second.payload["cursorByteColumn"])
		self.assertTrue(
			self.controller.consume_result(
				moved_cursor_state,
				self.result(second, moved_cursor_state, line=5, text="next virtual line"),
			).accepted,
		)
		self.assertEqual(
			"next virtual line",
			self.controller.display_state(moved_cursor_state)["lineText"],
		)
		command_line_state = editor_state(
			mode="commandLine",
			modeRaw="c",
			lineText="real command-line context",
		)
		self.assertEqual(
			"next virtual line",
			self.controller.display_state(command_line_state)["lineText"],
		)
		self.assertEqual(
			BrailleExplorationRejection.MODE_UNAVAILABLE,
			self.controller.plan_step(
				command_line_state,
				"next",
				capabilities={"brailleExploration"},
			).rejection,
		)

	def test_text_input_advances_snapshot_without_moving_virtual_braille(self) -> None:
		self.enable()
		first = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(
			self.controller.consume_result(
				self.state,
				self.result(first, self.state),
			).accepted,
		)
		typed_state = editor_state(
			changedtick=5,
			mode="insert",
			modeRaw="i",
			lineText="typed at the real cursor",
			cursor={
				"line": 3,
				"byteColumn": 24,
				"characterColumn": 24,
				"virtualColumn": 24,
				"preferredVirtualColumn": 24,
			},
		)

		display = self.controller.display_state(typed_state)
		self.assertEqual("target", display["lineText"])
		self.assertEqual(4, display["cursor"]["line"])
		self.assertEqual(4, display["changedtick"])

		second = self.controller.plan_step(
			typed_state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(second.ready)
		self.assertEqual(5, second.payload["changedtick"])
		self.assertEqual("n", second.payload["modeRaw"])
		self.assertEqual(3, second.payload["cursorLine"])
		self.assertTrue(
			self.controller.consume_result(
				typed_state,
				self.result(
					second,
					typed_state,
					line=5,
					text="next after typing",
				),
			).accepted,
		)
		self.assertEqual(
			"next after typing",
			self.controller.display_state(typed_state)["lineText"],
		)

	def test_change_on_explored_line_refreshes_text_without_reanchoring(self) -> None:
		self.enable()
		first = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(
			self.controller.consume_result(
				self.state,
				self.result(first, self.state),
			).accepted,
		)
		replaced_state = editor_state(
			changedtick=5,
			lineText="tXrget",
			cursor={
				"line": 4,
				"byteColumn": 1,
				"characterColumn": 1,
				"virtualColumn": 1,
				"preferredVirtualColumn": 1,
			},
			selection=None,
			spellingErrors=[],
			fileManager=None,
		)

		display = self.controller.display_state(replaced_state)
		self.assertEqual("tXrget", display["lineText"])
		self.assertEqual(5, display["changedtick"])
		self.assertEqual(4, display["cursor"]["line"])
		self.assertEqual(6, display["cursor"]["byteColumn"])

		continued = self.controller.plan_step(
			replaced_state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(continued.ready)
		self.assertEqual(5, continued.payload["changedtick"])
		self.assertEqual(4, self.controller.display_state(replaced_state)["cursor"]["line"])

	def test_displayed_line_stays_current_across_edit_and_mode_return(self) -> None:
		self.enable()
		first = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(
			self.controller.consume_result(
				self.state,
				self.result(first, self.state),
			).accepted,
		)
		insert_state = editor_state(
			changedtick=5,
			mode="insert",
			modeRaw="i",
			lineText="target changed completely",
			tabstop=4,
			shiftwidth=2,
			selection=None,
			spellingErrors=[{"startByteColumn": 7, "endByteColumn": 14}],
			spellingError={"startByteColumn": 7, "endByteColumn": 14},
			diagnostic={"message": "example"},
			cursor={
				"line": 4,
				"byteColumn": 10,
				"characterColumn": 10,
				"virtualColumn": 10,
				"preferredVirtualColumn": 10,
			},
		)

		insert_display = self.controller.display_state(insert_state)
		self.assertEqual("target changed completely", insert_display["lineText"])
		self.assertEqual("i", insert_display["modeRaw"])
		self.assertEqual(5, insert_display["changedtick"])
		self.assertEqual(4, insert_display["cursor"]["line"])
		self.assertEqual(6, insert_display["cursor"]["byteColumn"])
		self.assertEqual(79, insert_display["cursor"]["preferredVirtualColumn"])
		self.assertEqual(insert_state["spellingErrors"], insert_display["spellingErrors"])
		self.assertEqual(insert_state["diagnostic"], insert_display["diagnostic"])

		normal_state = editor_state(
			**{
				**insert_state,
				"mode": "normal",
				"modeRaw": "n",
			},
		)
		normal_display = self.controller.display_state(normal_state)
		self.assertEqual("target changed completely", normal_display["lineText"])
		self.assertEqual("n", normal_display["modeRaw"])
		self.assertEqual(5, normal_display["changedtick"])
		self.assertEqual(4, normal_display["cursor"]["line"])
		self.assertEqual(79, normal_display["cursor"]["preferredVirtualColumn"])

		routing_state = self.controller.routing_state(normal_state)
		self.assertIsNotNone(routing_state)
		self.assertEqual("n", routing_state["modeRaw"])
		self.assertEqual(5, routing_state["changedtick"])
		self.assertEqual(4, routing_state["cursor"]["line"])
		self.assertEqual("target changed completely", routing_state["lineText"])

	def test_routing_rejects_stale_virtual_content_without_moving_display(self) -> None:
		self.enable()
		first = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(
			self.controller.consume_result(
				self.state,
				self.result(first, self.state),
			).accepted,
		)
		changed_elsewhere = editor_state(
			changedtick=5,
			mode="insert",
			modeRaw="i",
			lineText="changed at real cursor",
			lineCount=7,
			tabstop=4,
			shiftwidth=2,
			cursor={
				"line": 3,
				"byteColumn": 22,
				"characterColumn": 22,
				"virtualColumn": 22,
				"preferredVirtualColumn": 22,
			},
		)

		self.assertIsNone(self.controller.routing_state(changed_elsewhere))
		display = self.controller.display_state(changed_elsewhere)
		self.assertEqual("target", display["lineText"])
		self.assertEqual(4, display["changedtick"])
		self.assertEqual(4, display["cursor"]["line"])
		self.assertEqual(79, display["cursor"]["preferredVirtualColumn"])
		self.assertEqual(7, display["lineCount"])
		self.assertEqual(4, display["tabstop"])
		self.assertEqual(2, display["shiftwidth"])

	def test_multiple_queued_steps_are_ordered_and_bounded(self) -> None:
		self.enable()
		first = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		second = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		third = self.controller.plan_step(
			self.state,
			"previous",
			capabilities={"brailleExploration"},
		)
		self.assertEqual((first.request_id,), third.discarded_request_ids)
		self.assertEqual((4, 5, 4), (
			first.payload["cursorLine"] + 1,
			second.payload["cursorLine"] + 2,
			third.payload["cursorLine"] + 1,
		))
		self.assertFalse(
			self.controller.consume_result(
				self.state,
				self.result(first, self.state),
			).accepted,
		)

	def test_context_change_invalidates_position_but_keeps_selected_mode(self) -> None:
		self.enable()
		plan = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		stale_state = editor_state(windowId=5)
		result = self.controller.consume_result(
			stale_state,
			self.result(plan, self.state),
		)
		self.assertEqual(BrailleExplorationRejection.STALE_OR_UNBOUND, result.rejection)
		self.assertTrue(self.controller.enabled)
		self.assertEqual(stale_state, self.controller.display_state(stale_state))

	def test_command_line_terminal_and_boundaries_never_dispatch(self) -> None:
		for mode_raw in ("c", "t"):
			with self.subTest(mode_raw=mode_raw):
				controller = BrailleExplorationController(RequestIds())
				plan = controller.toggle(
					editor_state(modeRaw=mode_raw),
					capabilities={"brailleExploration"},
				)
				self.assertEqual(BrailleExplorationRejection.MODE_UNAVAILABLE, plan.rejection)
		self.state = editor_state(cursor={
			**self.state["cursor"],
			"line": 6,
		})
		self.enable()
		plan = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertEqual(BrailleExplorationRejection.BOUNDARY, plan.rejection)

	def test_invalid_utf8_position_and_dispatch_failure_fail_safely(self) -> None:
		self.enable()
		plan = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		result = self.controller.consume_result(
			self.state,
			self.result(
				plan,
				self.state,
				text="ä",
				byteColumn=1,
				characterColumn=1,
			),
		)
		self.assertEqual(BrailleExplorationRejection.INVALID_RESULT, result.rejection)
		self.assertTrue(self.controller.enabled)
		reanchored = self.controller.plan_step(
			self.state,
			"next",
			capabilities={"brailleExploration"},
		)
		self.assertTrue(reanchored.ready)
		self.assertTrue(self.controller.fail_request(reanchored.request_id))
		self.assertTrue(self.controller.enabled)


if __name__ == "__main__":
	unittest.main()
