from __future__ import annotations

import unittest

from nvim_nvda_protocol import valid_leave_terminal_input_request


class TerminalControlValidationTests(unittest.TestCase):
    def test_requires_exact_terminal_mode_identity_without_changedtick(self) -> None:
        payload = {
            "requestId": 1, "bufferId": 2, "windowId": 3,
            "tabpageId": 4, "modeRaw": "t",
        }
        self.assertTrue(valid_leave_terminal_input_request(payload))
        self.assertTrue(valid_leave_terminal_input_request({
            **payload, "changedtick": 999,
        }))
        for field, value in (
            ("requestId", True), ("bufferId", -1), ("windowId", None),
            ("tabpageId", "4"), ("modeRaw", "nt"),
        ):
            with self.subTest(field=field):
                self.assertFalse(valid_leave_terminal_input_request({
                    **payload, field: value,
                }))


if __name__ == "__main__":
    unittest.main()
