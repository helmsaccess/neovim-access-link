"""Check that QEMU calibration matching requires real waveform segments."""

from io import BytesIO
import unittest
import wave

import numpy as np

from prepare_audio_calibration import marker
from verify_audio_capture import RATE, find_matches, find_qemu_c1_markers


NAME = "before-selection"
OFFSETS = [milliseconds * RATE // 1000 for milliseconds in (30, 105, 180, 255, 330)]
SEGMENT = 36 * RATE // 1000


def reference(frequency):
    with wave.open(BytesIO(marker(frequency, 1)), "rb") as stream:
        return np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")[::2].astype(float)


def capture(template, shifts, *, record_at=1000):
    waveform = np.zeros(RATE)
    for offset, shift in zip(OFFSETS, shifts):
        start = record_at + offset + shift
        waveform[start:start + SEGMENT] = template[offset:offset + SEGMENT]
    return waveform


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.template = reference(2960)
        self.jitter = (0, -16, 193, 193, 193)

    def test_recovers_a_marker_from_five_real_segments(self):
        waveform = capture(self.template, self.jitter)
        self.assertEqual(find_matches(waveform, self.template, NAME), [])
        matched, = find_qemu_c1_markers(waveform, self.template, NAME)
        self.assertEqual(matched.calibration_segments, 5)
        self.assertEqual(matched.drift_samples, 209)

    def test_rejects_noise_and_a_different_real_marker(self):
        noise = np.random.default_rng(79).normal(0, 5000, RATE)
        self.assertEqual(find_qemu_c1_markers(noise, self.template, NAME), [])
        different = np.pad(reference(1130), (1000, 1000))
        self.assertEqual(find_qemu_c1_markers(different, self.template, NAME), [])

    def test_rejects_too_few_segments_and_incompatible_shifts(self):
        for shifts in (self.jitter[:3], (0, 1440, 2880, 4320, 5760)):
            with self.subTest(shifts=shifts):
                waveform = capture(self.template, shifts)
                self.assertEqual(find_qemu_c1_markers(waveform, self.template, NAME), [])

    def test_distinguishes_a_clean_and_a_jittered_copy(self):
        jittered = capture(self.template, self.jitter)
        mixed = np.concatenate((jittered, np.zeros(1000), self.template, np.zeros(1000)))
        self.assertEqual(len(find_qemu_c1_markers(mixed, self.template, NAME)), 2)


if __name__ == "__main__":
    unittest.main()
