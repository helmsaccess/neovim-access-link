from __future__ import annotations

import unittest

from nvim_nvda_protocol import (
	MAX_PLUGIN_MANAGER_OVERVIEW_BYTES,
	plugin_manager_public_state,
	valid_plugin_manager_operation,
)


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

	def test_overview_is_bounded_and_tied_to_public_lazy_identity(self) -> None:
		payload = {
			"buftype": "nofile",
			"filetype": "lazy",
			"pluginManagerOverview": "lazy.nvim Install (I)",
		}
		self.assertEqual(payload, plugin_manager_public_state(payload))
		for replacement in (
			{"buftype": ""},
			{"filetype": "lazy-lookalike"},
			{"pluginManagerOverview": ""},
			{"pluginManagerOverview": "x" * (MAX_PLUGIN_MANAGER_OVERVIEW_BYTES + 1)},
			{"pluginManagerOverview": "\ud800"},
			{"pluginManagerOverview": object()},
		):
			with self.subTest(replacement=replacement):
				cleaned = plugin_manager_public_state({**payload, **replacement})
				self.assertNotIn("pluginManagerOverview", cleaned)

	def test_current_entry_state_is_boolean_and_tied_to_public_lazy_identity(self) -> None:
		payload = {
			"buftype": "nofile",
			"filetype": "lazy",
			"pluginManagerEntryExpanded": False,
		}
		self.assertIs(
			plugin_manager_public_state(payload)["pluginManagerEntryExpanded"],
			False,
		)
		for replacement in (
			{"buftype": ""},
			{"filetype": "lazy-lookalike"},
			{"pluginManagerEntryExpanded": 0},
			{"pluginManagerEntryExpanded": "false"},
		):
			with self.subTest(replacement=replacement):
				cleaned = plugin_manager_public_state({**payload, **replacement})
				self.assertNotIn("pluginManagerEntryExpanded", cleaned)


if __name__ == "__main__":
	unittest.main()
