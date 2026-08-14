from __future__ import annotations

import struct
import unittest

import msgpack

from nvim_nvda_protocol import (
    ExponentialBackoff,
    FrameDecoder,
    InvalidByteColumn,
    MessageFactory,
    ProtocolError,
    SessionTracker,
    cursor_text,
    encode_frame,
    utf16_column,
)


def message(sequence: int = 0, kind: str = "fullState", session: str = "session-a") -> dict:
    return {
        "protocolVersion": 2,
        "sessionId": session,
        "sequence": sequence,
        "timestampMonotonic": 123456,
        "type": kind,
        "payload": {},
    }


class CodecTests(unittest.TestCase):
    def test_every_byte_boundary_and_concatenated_frames(self) -> None:
        data = encode_frame(message()) + encode_frame(message(1, "modeChanged"))
        decoder = FrameDecoder()
        decoded = []
        for byte in data:
            decoded.extend(decoder.feed(bytes((byte,))))
        self.assertEqual([message(), message(1, "modeChanged")], decoded)

    def test_oversized_declared_frame_is_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            FrameDecoder(max_frame_bytes=8).feed(struct.pack(">I", 9))

    def test_exact_frame_size_limit_is_accepted(self) -> None:
        unbounded_frame = encode_frame(message())
        payload_size = len(unbounded_frame) - 4
        self.assertEqual(unbounded_frame, encode_frame(message(), max_frame_bytes=payload_size))
        self.assertEqual(
            [message()],
            FrameDecoder(max_frame_bytes=payload_size).feed(unbounded_frame),
        )

    def test_missing_field_is_rejected(self) -> None:
        invalid = message()
        del invalid["payload"]
        with self.assertRaises(ProtocolError):
            encode_frame(invalid)

    def test_boolean_and_negative_integer_fields_are_rejected(self) -> None:
        for field, value in (
            ("sequence", True),
            ("sequence", -1),
            ("timestampMonotonic", False),
            ("timestampMonotonic", -1),
        ):
            with self.subTest(field=field, value=value):
                invalid = message()
                invalid[field] = value
                with self.assertRaises(ProtocolError):
                    encode_frame(invalid)

    def test_invalid_decoded_values_are_protocol_errors(self) -> None:
        for decoded in ([], "message", None):
            with self.subTest(decoded=decoded):
                raw = msgpack.packb(decoded, use_bin_type=True)
                frame = struct.pack(">I", len(raw)) + raw
                with self.assertRaisesRegex(ProtocolError, "top-level value must be a map"):
                    FrameDecoder().feed(frame)

        raw = b"\xc1"
        with self.assertRaisesRegex(ProtocolError, "invalid MessagePack payload"):
            FrameDecoder().feed(struct.pack(">I", len(raw)) + raw)

    def test_protocol_v1_is_rejected_without_compatibility_fallback(self) -> None:
        obsolete = message()
        obsolete["protocolVersion"] = 1
        with self.assertRaisesRegex(ProtocolError, "unsupported protocol version"):
            encode_frame(obsolete)


class SessionTests(unittest.TestCase):
    def test_sequence_gap_requests_resync(self) -> None:
        tracker = SessionTracker()
        self.assertEqual("accept", tracker.observe(message()))
        self.assertEqual("resyncRequired", tracker.observe(message(2, "cursorMoved")))
        self.assertEqual("resyncRequired", tracker.observe(message(2, "cursorMoved")))
        self.assertEqual("duplicate", tracker.observe(message(0, "fullState")))
        self.assertEqual("accept", tracker.observe(message(3, "fullState")))

    def test_new_session_requires_full_state(self) -> None:
        tracker = SessionTracker()
        tracker.observe(message())
        self.assertEqual("staleSession", tracker.observe(message(0, "cursorMoved", "session-b")))
        self.assertEqual("staleSession", tracker.observe(message(4, "fullState", "session-b")))
        self.assertEqual("accept", tracker.observe(message(0, "fullState", "session-b")))

    def test_first_message_must_be_full_state_sequence_zero(self) -> None:
        tracker = SessionTracker()
        self.assertEqual("resyncRequired", tracker.observe(message(1, "cursorMoved")))
        self.assertEqual("resyncRequired", tracker.observe(message(2, "modeChanged")))
        self.assertEqual("resyncRequired", tracker.observe(message(3, "fullState")))
        self.assertIsNone(tracker.session_id)
        self.assertEqual("accept", tracker.observe(message()))


class TextTests(unittest.TestCase):
    def test_byte_column_maps_wide_combining_and_emoji(self) -> None:
        line = "a\te\u0301界🙂z"
        self.assertEqual((2, "e"), (cursor_text(line, 2).character_column, cursor_text(line, 2).character))
        self.assertEqual((4, "界"), (cursor_text(line, 5).character_column, cursor_text(line, 5).character))
        self.assertEqual((5, "🙂"), (cursor_text(line, 8).character_column, cursor_text(line, 8).character))
        self.assertEqual((6, "z"), (cursor_text(line, 12).character_column, cursor_text(line, 12).character))

    def test_invalid_utf8_byte_columns_are_rejected(self) -> None:
        for byte_column in (-1, 1, 2, 4):
            with self.subTest(byte_column=byte_column):
                with self.assertRaises(InvalidByteColumn):
                    cursor_text("界", byte_column)

    def test_end_of_line_has_empty_character(self) -> None:
        self.assertEqual("", cursor_text("🙂", 4).character)

    def test_utf16_counts_astral_character_and_rejects_out_of_range_columns(self) -> None:
        self.assertEqual(3, utf16_column("a🙂z", 2))
        for character_column in (-1, 4):
            with self.subTest(character_column=character_column):
                with self.assertRaises(ValueError):
                    utf16_column("a🙂z", character_column)


class ReconnectTests(unittest.TestCase):
    def test_backoff_is_bounded_and_resets(self) -> None:
        backoff = ExponentialBackoff(initial_seconds=0.25, maximum_seconds=1.0)
        self.assertEqual([0.25, 0.5, 1.0, 1.0], [backoff.next_delay() for _ in range(4)])
        backoff.reset()
        self.assertEqual(0.25, backoff.next_delay())

    def test_message_factory_starts_new_transport_session(self) -> None:
        first = MessageFactory(session_id="transport-a")
        self.assertEqual(0, first.create("fullState")["sequence"])
        self.assertEqual(1, first.create("heartbeat")["sequence"])
        second = MessageFactory(session_id="transport-b")
        self.assertNotEqual(first.session_id, second.session_id)


if __name__ == "__main__":
    unittest.main()
