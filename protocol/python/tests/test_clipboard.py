from __future__ import annotations

import unittest

from nvim_nvda_protocol import (
    MAX_CLIPBOARD_TEXT_BYTES,
    valid_clipboard_text,
    valid_copy_text_request,
    valid_paste_text_request,
    valid_set_register_request,
)


def expected_state() -> dict:
    return {
        "bufferId": 1, "windowId": 2, "tabpageId": 3,
        "changedtick": 4, "modeRaw": "n",
    }


class ClipboardValidationTests(unittest.TestCase):
    def test_copy_control_accepts_only_fixed_sources_and_exact_state(self) -> None:
        for source in ("visualSelection", "yankRegister"):
            self.assertTrue(valid_copy_text_request({
                **expected_state(), "requestId": 7, "source": source,
            }))
        self.assertFalse(valid_copy_text_request({
            **expected_state(), "requestId": 7, "source": 'vim.fn.getreg("+")',
        }))
        self.assertFalse(valid_copy_text_request({
            **expected_state(), "requestId": True, "source": "yankRegister",
        }))

    def test_paste_text_is_utf8_bounded_and_rejects_nul(self) -> None:
        self.assertTrue(valid_paste_text_request({
            **expected_state(), "requestId": 8, "text": "alpha\n😀",
        }))
        self.assertFalse(valid_paste_text_request({
            **expected_state(), "requestId": 8, "text": "alpha\0beta",
        }))
        self.assertTrue(valid_clipboard_text("x" * MAX_CLIPBOARD_TEXT_BYTES))
        self.assertFalse(valid_clipboard_text("x" * (MAX_CLIPBOARD_TEXT_BYTES + 1)))
        self.assertFalse(valid_clipboard_text("😀" * (MAX_CLIPBOARD_TEXT_BYTES // 4 + 1)))

    def test_set_register_uses_the_same_bounded_text_contract(self) -> None:
        self.assertTrue(valid_set_register_request({
            **expected_state(), "requestId": 9, "text": "from Windows\r\nsecond line",
        }))
        self.assertFalse(valid_set_register_request({
            **expected_state(), "requestId": 9, "text": "bad\0register",
        }))


if __name__ == "__main__":
    unittest.main()
