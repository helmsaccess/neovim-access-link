from __future__ import annotations

import unittest

from nvim_nvda_protocol import valid_plugin_manager_operation


class PluginManagerValidationTests(unittest.TestCase):
	def test_lifecycle_fields_are_fixed_allowlists(self) -> None:
		payload = {
			"pluginManagerKind": "lazyNvim",
			"pluginManagerOperation": "update",
			"pluginManagerPhase": "started",
		}
		self.assertTrue(valid_plugin_manager_operation(payload))
		for replacement in (
			{"pluginManagerOperation": "arbitrary"},
			{"pluginManagerPhase": "successful"},
			{"pluginManagerKind": "other"},
		):
			with self.subTest(replacement=replacement):
				self.assertFalse(valid_plugin_manager_operation({**payload, **replacement}))


if __name__ == "__main__":
	unittest.main()
