import unittest

from nvim_nvda_protocol.signature_help import valid_active_parameter_changed


def parameter_event():
    return {
        "pluginCapabilities": ["activeParameterHints"],
        "mode": "insert",
        "modeRaw": "i",
        "bufferId": 1,
        "windowId": 2,
        "changedtick": 3,
        "cursor": {"line": 7, "byteColumn": 18},
        "callName": "calculate_total",
        "callStartLine": 7,
        "callStartByteColumn": 15,
        "signature": "calculate_total(price: float, quantity: int) -> float",
        "signatureIndex": 1,
        "signatureCount": 2,
        "activeParameter": 1,
        "parameterCount": 2,
        "parameter": "price: float",
        "hintReason": "callEntered",
    }


class SignatureHelpProtocolTests(unittest.TestCase):
    def test_valid_transition_is_bounded_but_allows_snapshot_fields(self):
        payload = parameter_event()
        payload["lineText"] = "result = calculate_total("
        self.assertTrue(valid_active_parameter_changed(payload))

    def test_identity_counts_and_insert_context_are_strict(self):
        payload = parameter_event()
        for replacement in (
            {"mode": "normal"},
            {"modeRaw": "n"},
            {"activeParameter": 0},
            {"activeParameter": 3},
            {"parameterCount": True},
            {"signatureIndex": 3},
            {"hintReason": "cursorMoved"},
            {"pluginCapabilities": []},
        ):
            with self.subTest(replacement=replacement):
                self.assertFalse(valid_active_parameter_changed({**payload, **replacement}))
    def test_text_and_coordinates_are_bounded(self):
        payload = parameter_event()
        for replacement in (
            {"callName": ""},
            {"callName": "x" * 513},
            {"signature": "x" * 2049},
            {"parameter": "x" * 513},
            {"parameter": "\ud800"},
            {"callStartLine": 0},
            {"callStartByteColumn": -1},
            {"cursor": {"line": 0, "byteColumn": 0}},
        ):
            with self.subTest(replacement=replacement):
                self.assertFalse(valid_active_parameter_changed({**payload, **replacement}))
