from __future__ import annotations

import unittest

from nvim_nvda_protocol import tutor_public_state, valid_tutor_exercise_changed


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

	def test_ordinary_payload_is_not_copied_for_tutor_support(self) -> None:
		payload = {"filetype": "lua", "lineText": "local value = 1"}
		self.assertIs(payload, tutor_public_state(payload))

	def test_removes_spoofed_or_invalid_status(self) -> None:
		for payload in (
			{"filetype": "lua", "tutorExerciseStatus": "correct"},
			{"filetype": "tutor", "tutorExerciseStatus": "unknown"},
			{"filetype": "tutor", "tutorExerciseStatus": True},
			{"filetype": "tutor", "tutorExerciseStatus": None},
		):
			with self.subTest(payload=payload):
				self.assertNotIn("tutorExerciseStatus", tutor_public_state(payload))

	def test_transition_requires_exact_tutor_context_and_status(self) -> None:
		self.assertTrue(valid_tutor_exercise_changed({
			"filetype": "tutor", "tutorExerciseStatus": "correct",
		}))
		for payload in (
			{"filetype": "tutor"},
			{"filetype": "lua", "tutorExerciseStatus": "correct"},
			{"filetype": "tutor", "tutorExerciseStatus": "unknown"},
		):
			with self.subTest(payload=payload):
				self.assertFalse(valid_tutor_exercise_changed(payload))


if __name__ == "__main__":
	unittest.main()
