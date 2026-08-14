from __future__ import annotations

import unittest

from nvim_nvda_protocol.cursor_routing import MAX_COMMAND_LINE_BYTES, valid_route_cursor_request


def editor_request() -> dict:
	return {
		"target": "editor",
		"bufferId": 1,
		"windowId": 2,
		"line": 3,
		"byteColumn": 4,
		"changedtick": 5,
		"modeRaw": "i",
	}


def command_line_request() -> dict:
	return {
		"target": "commandLine",
		"bufferId": 1,
		"windowId": 2,
		"byteColumn": 1,
		"changedtick": 5,
		"modeRaw": "c",
		"commandLine": "a界z",
		"commandLineType": ":",
	}


class CursorRoutingValidationTests(unittest.TestCase):
	def test_valid_editor_and_command_line_requests(self) -> None:
		self.assertTrue(valid_route_cursor_request(editor_request()))
		self.assertTrue(valid_route_cursor_request(command_line_request()))

	def test_numeric_fields_require_bounded_integers(self) -> None:
		for field in ("bufferId", "windowId", "byteColumn", "changedtick"):
			for invalid_value in (True, -1, "1", None):
				with self.subTest(field=field, invalid_value=invalid_value):
					request = editor_request()
					request[field] = invalid_value
					self.assertFalse(valid_route_cursor_request(request))
		for invalid_line in (True, 0, -1, "1", None):
			with self.subTest(line=invalid_line):
				request = editor_request()
				request["line"] = invalid_line
				self.assertFalse(valid_route_cursor_request(request))

	def test_request_has_an_exact_shape_and_target_mode_pair(self) -> None:
		for request in (editor_request(), command_line_request()):
			with self.subTest(target=request["target"], mutation="extra"):
				request["extra"] = True
				self.assertFalse(valid_route_cursor_request(request))
		for request, field in ((editor_request(), "line"), (command_line_request(), "commandLine")):
			with self.subTest(target=request["target"], mutation=f"missing-{field}"):
				del request[field]
				self.assertFalse(valid_route_cursor_request(request))
		for request, mode in ((editor_request(), "c"), (command_line_request(), "n")):
			with self.subTest(target=request["target"], mode=mode):
				request["modeRaw"] = mode
				self.assertFalse(valid_route_cursor_request(request))

	def test_command_line_text_is_bounded_and_column_is_a_utf8_boundary(self) -> None:
		for byte_column in (2, 3, 5, 6):
			with self.subTest(byte_column=byte_column):
				request = command_line_request()
				request["byteColumn"] = byte_column
				expected = byte_column == 5
				self.assertEqual(expected, valid_route_cursor_request(request))
		for command_line in ("x" * (MAX_COMMAND_LINE_BYTES + 1), "nul\0text"):
			with self.subTest(command_line=command_line[-8:]):
				request = command_line_request()
				request["commandLine"] = command_line
				self.assertFalse(valid_route_cursor_request(request))

	def test_text_metadata_is_nonempty_bounded_and_nul_free(self) -> None:
		for field, invalid_value in (
			("modeRaw", ""),
			("modeRaw", "x" * 17),
			("modeRaw", "n\0"),
			("commandLineType", ""),
			("commandLineType", "x" * 9),
			("commandLineType", ":\0"),
		):
			with self.subTest(field=field, invalid_value=invalid_value):
				request = command_line_request() if field == "commandLineType" else editor_request()
				request[field] = invalid_value
				self.assertFalse(valid_route_cursor_request(request))


if __name__ == "__main__":
	unittest.main()
