import unittest

from nvim_nvda_protocol.developer_context import (
    MAX_CONTEXT_TOTAL_TEXT_BYTES,
    developer_context_result_state,
    valid_callable_context_result,
    valid_context_request,
    valid_diagnostic_context_result,
)


class DeveloperContextProtocolTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "requestId": 7,
            "bufferId": 1,
            "windowId": 2,
            "tabpageId": 3,
            "changedtick": 4,
            "line": 5,
            "byteColumn": 6,
        }

    def test_exact_request_is_required(self):
        self.assertTrue(valid_context_request(self.request))
        self.assertFalse(valid_context_request({**self.request, "extra": True}))
        self.assertFalse(valid_context_request({**self.request, "line": 0}))
        self.assertFalse(valid_context_request({**self.request, "requestId": True}))
        for field in ("requestId", "bufferId", "windowId", "tabpageId", "line"):
            with self.subTest(field=field):
                self.assertFalse(valid_context_request({**self.request, field: 0}))
        for field in ("changedtick", "byteColumn"):
            with self.subTest(field=field):
                self.assertFalse(valid_context_request({**self.request, field: -1}))
        self.assertFalse(valid_context_request({**self.request, "byteColumn": 2**31}))

    def test_callable_result_is_bounded_and_strict(self):
        payload = {
            **self.request,
            "ok": True,
            "resultCode": "ok",
            "items": [{
                "signature": "calculate_total(price, quantity)",
                "parameters": ["price: float", "quantity: int"],
                "documentation": "Calculate a total.",
            }],
            "activeItem": 0,
            "activeParameter": 1,
        }
        self.assertTrue(valid_callable_context_result(payload))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "items": [{**payload["items"][0], "unexpected": ""}],
        }))
        without_buffer = dict(payload)
        del without_buffer["bufferId"]
        self.assertFalse(valid_callable_context_result(without_buffer))
        self.assertFalse(valid_callable_context_result({**payload, "activeItem": 1}))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "activeParameter": 2,
        }))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "items": [{
                "signature": "",
                "parameters": ["x" * 16_384] * (
                    MAX_CONTEXT_TOTAL_TEXT_BYTES // 16_384 + 1
                ),
                "documentation": "",
            }],
            "activeParameter": 0,
        }))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "items": [payload["items"][0]] * 101,
        }))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "items": [{
                "signature": "\ud800",
                "parameters": [],
                "documentation": "",
            }],
            "activeParameter": 0,
        }))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "ok": False,
            "resultCode": "noResult",
        }))

    def test_diagnostic_result_is_bounded_and_strict(self):
        item = {
            "message": "Undefined name",
            "severity": "error",
            "source": "ruff",
            "code": "F821",
            "line": 5,
            "byteColumn": 2,
            "endLine": 5,
            "endByteColumn": 6,
            "atCursor": True,
        }
        payload = {
            **self.request,
            "ok": True,
            "resultCode": "ok",
            "items": [item],
            "activeItem": 0,
            "activeParameter": 0,
        }
        self.assertTrue(valid_diagnostic_context_result(payload))
        self.assertTrue(valid_diagnostic_context_result({
            **payload,
            "items": [{**item, "code": None}],
        }))
        self.assertFalse(valid_diagnostic_context_result({
            **payload,
            "items": [{**item, "severity": "fatal"}],
        }))
        self.assertFalse(valid_diagnostic_context_result({
            **payload,
            "items": [{**item, "code": True}],
        }))
        self.assertFalse(valid_diagnostic_context_result({
            **payload,
            "items": [{**item, "endByteColumn": 1}],
        }))
        self.assertFalse(valid_diagnostic_context_result({
            **payload,
            "activeParameter": 1,
        }))
        self.assertFalse(valid_diagnostic_context_result({
            **payload,
            "items": [{**item, "code": 2**31}],
        }))
        self.assertFalse(valid_diagnostic_context_result({
            **payload,
            "items": [{**item, "source": "x" * (16 * 1024 + 1)}],
        }))
        self.assertTrue(valid_diagnostic_context_result({
            **payload,
            "items": [{
                **item,
                "endLine": item["line"] + 1,
                "endByteColumn": 0,
            }],
        }))

    def test_failure_and_result_state(self):
        payload = {
            **self.request,
            "ok": False,
            "resultCode": "noResult",
            "items": [],
            "activeItem": 0,
            "activeParameter": 0,
        }
        self.assertTrue(valid_callable_context_result(payload))
        state = developer_context_result_state(payload)
        self.assertEqual(self.request["bufferId"], state["bufferId"])
        self.assertNotIn("requestId", state)
        self.assertNotIn("items", state)
        for result_code in ("invalidOrStaleRequest", "requestFailed"):
            with self.subTest(result_code=result_code):
                self.assertTrue(valid_diagnostic_context_result({
                    **payload,
                    "resultCode": result_code,
                }))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "resultCode": "ok",
        }))
        self.assertFalse(valid_callable_context_result({
            **payload,
            "activeItem": 1,
        }))
        self.assertTrue(valid_callable_context_result({
            **payload,
            "mode": "normal",
            "cursor": {"line": 5, "byteColumn": 6},
        }))


if __name__ == "__main__":
    unittest.main()
