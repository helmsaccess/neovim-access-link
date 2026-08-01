from __future__ import annotations

import unittest

from nvim_nvda_core import (
	HeldContextController,
	HeldContextDirection,
	HeldContextKind,
	HeldContextLocation,
	TerminalIdentity,
)


class RequestIds:
	def __init__(self) -> None:
		self.value = 0

	def __call__(self) -> int:
		self.value += 1
		return self.value


def editor_state(**changes):
	value = {
		"bufferId": 1,
		"windowId": 2,
		"tabpageId": 3,
		"changedtick": 4,
		"cursor": {"line": 5, "byteColumn": 6},
	}
	value.update(changes)
	return value


class HeldContextControllerTests(unittest.TestCase):
	def setUp(self) -> None:
		self.controller = HeldContextController(RequestIds())
		self.location = HeldContextLocation.from_state(
			"connection-1",
			TerminalIdentity("windowsTerminal", 20, (1, 2, 3), 4),
			object(),
			object(),
			editor_state(),
		)
		assert self.location is not None

	def test_location_requires_complete_non_boolean_editor_identity(self):
		self.assertIsNone(
			HeldContextLocation.from_state(
				"",
				self.location.identity,
				self.location.adapter_token,
				self.location.service_generation,
				editor_state(),
			),
		)
		for field, value in (
			("bufferId", True),
			("windowId", 0),
			("tabpageId", -1),
			("changedtick", -1),
			("cursor", {"line": 0, "byteColumn": 0}),
		):
			with self.subTest(field=field):
				self.assertIsNone(
					HeldContextLocation.from_state(
						"connection-1",
						self.location.identity,
						self.location.adapter_token,
						self.location.service_generation,
						editor_state(**{field: value}),
					),
				)
		self.assertTrue(self.location.matches_state(editor_state()))
		self.assertFalse(
			self.location.matches_state(editor_state(cursor={"line": 5, "byteColumn": 7})),
		)

	def test_callable_request_and_navigation_are_correlated(self):
		request = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		self.assertEqual("callableContextRequest", request.control)
		self.assertEqual(1, request.payload["requestId"])
		event = {
			"type": "callableContextResult",
			"payload": {
				**editor_state(),
				"requestId": request.request_id,
				"ok": True,
				"resultCode": "ok",
				"items": [
					{
						"signature": "first(a, b)",
						"parameters": ["a", "b"],
						"documentation": "",
					},
					{
						"signature": "second(value)",
						"parameters": ["value"],
						"documentation": "",
					},
				],
				"activeItem": 0,
				"activeParameter": 1,
			},
		}
		presentation = self.controller.consume(HeldContextKind.CALLABLE, event)
		self.assertEqual("b", presentation.parameter)
		presentation = self.controller.navigate(HeldContextDirection.NEXT_PARAMETER)
		self.assertEqual("a", presentation.parameter)
		presentation = self.controller.navigate(HeldContextDirection.NEXT_ITEM)
		self.assertEqual("second(value)", presentation.item["signature"])
		self.assertEqual(
			"first(a, b)",
			self.controller.navigate(HeldContextDirection.NEXT_ITEM).item["signature"],
		)

	def test_diagnostic_items_wrap(self):
		request = self.controller.begin(HeldContextKind.DIAGNOSTIC, self.location)
		item = {
			"message": "problem",
			"severity": "warning",
			"source": "ruff",
			"code": "F001",
			"line": 5,
			"byteColumn": 6,
			"endLine": 5,
			"endByteColumn": 7,
			"atCursor": True,
		}
		event = {
			"type": "diagnosticContextResult",
			"payload": {
				**editor_state(),
				"requestId": request.request_id,
				"ok": True,
				"resultCode": "ok",
				"items": [item, {**item, "message": "second"}],
				"activeItem": 0,
				"activeParameter": 0,
			},
		}
		self.controller.consume(HeldContextKind.DIAGNOSTIC, event)
		self.assertEqual(
			"second",
			self.controller.navigate(HeldContextDirection.PREVIOUS_ITEM).item["message"],
		)

	def test_stale_response_and_other_adapter_release_are_rejected(self):
		request = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		stale = {
			"type": "callableContextResult",
			"payload": {
				**editor_state(changedtick=9),
				"requestId": request.request_id,
				"ok": False,
				"resultCode": "invalidOrStaleRequest",
				"items": [],
				"activeItem": 0,
				"activeParameter": 0,
			},
		}
		self.assertFalse(self.controller.accepts(HeldContextKind.CALLABLE, stale))
		self.assertIsNone(self.controller.consume(HeldContextKind.CALLABLE, stale))
		self.assertFalse(self.controller.cancel(object()))
		self.assertTrue(self.controller.cancel(self.location.adapter_token))

	def test_new_request_invalidates_previous_reply_and_malformed_items(self):
		first = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		second = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		self.assertNotEqual(first.request_id, second.request_id)
		old_event = {
			"type": "callableContextResult",
			"payload": {
				**editor_state(),
				"requestId": first.request_id,
				"ok": True,
				"resultCode": "ok",
				"items": [{
					"signature": "old(value)",
					"parameters": ["value"],
					"documentation": "",
				}],
				"activeItem": 0,
				"activeParameter": 0,
			},
		}
		self.assertFalse(self.controller.accepts(HeldContextKind.CALLABLE, old_event))
		malformed = {
			**old_event,
			"payload": {
				**old_event["payload"],
				"requestId": second.request_id,
				"items": ["not a mapping"] * 101,
			},
		}
		self.assertIsNone(self.controller.consume(HeldContextKind.CALLABLE, malformed))
		self.assertIsNone(self.controller.current())
		self.assertIsNone(self.controller.navigate(HeldContextDirection.NEXT_ITEM))

	def test_no_result_remains_releasable_without_retaining_items(self):
		request = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		event = {
			"type": "callableContextResult",
			"payload": {
				**editor_state(),
				"requestId": request.request_id,
				"ok": False,
				"resultCode": "noResult",
				"items": [],
				"activeItem": 0,
				"activeParameter": 0,
			},
		}
		self.assertIsNone(self.controller.consume(HeldContextKind.CALLABLE, event))
		self.assertEqual(self.location, self.controller.location)
		self.assertTrue(self.controller.cancel(self.location.adapter_token))

	def test_callable_can_be_requested_again_after_release(self):
		first = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		self.assertTrue(self.controller.cancel(self.location.adapter_token))
		second = self.controller.begin(HeldContextKind.CALLABLE, self.location)
		self.assertGreater(second.request_id, first.request_id)
		event = {
			"type": "callableContextResult",
			"payload": {
				**editor_state(),
				"requestId": second.request_id,
				"ok": True,
				"resultCode": "ok",
				"items": [{
					"signature": "calculate_total(price, quantity)",
					"parameters": ["price", "quantity"],
					"documentation": "",
				}],
				"activeItem": 0,
				"activeParameter": 0,
			},
		}
		presentation = self.controller.consume(HeldContextKind.CALLABLE, event)
		self.assertIsNotNone(presentation)
		self.assertEqual("price", presentation.parameter)


if __name__ == "__main__":
	unittest.main()
