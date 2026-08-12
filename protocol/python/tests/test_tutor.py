from __future__ import annotations

import unittest

from nvim_nvda_protocol import tutor_public_state


class TutorPublicStateTests(unittest.TestCase):
	def test_accepts_only_fixed_status_on_exact_tutor_filetype(self) -> None:
		for status in ("correct", "incorrect"):
			with self.subTest(status=status):
				state = tutor_public_state({
					"filetype": "tutor",
					"buftype": "nowrite",
					"tutorExerciseStatus": status,
				})
				self.assertEqual(status, state["tutorExerciseStatus"])

	def test_removes_spoofed_or_invalid_status(self) -> None:
		for payload in (
			{"filetype": "lua", "tutorExerciseStatus": "correct"},
			{"filetype": "tutor", "tutorExerciseStatus": "unknown"},
			{"filetype": "tutor", "tutorExerciseStatus": True},
		):
			with self.subTest(payload=payload):
				self.assertNotIn("tutorExerciseStatus", tutor_public_state(payload))


if __name__ == "__main__":
	unittest.main()
