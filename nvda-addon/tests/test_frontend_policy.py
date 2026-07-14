from __future__ import annotations

import unittest

from nvim_nvda_core import FrontendPolicy


def policy(frontends):
    return FrontendPolicy.from_mapping({"format": 1, "frontends": frontends})


class FrontendPolicyTests(unittest.TestCase):
    def test_only_implemented_enabled_adapter_is_allowed(self) -> None:
        value = policy([
            {
                "kind": "windowsTerminal", "status": "enabled",
                "appModule": "windowsterminal",
                "uiaClassNames": ["TermControl"], "requiresRuntimeId": True,
            },
            {
                "kind": "putty", "status": "planned",
                "appModule": "",
                "uiaClassNames": [], "requiresRuntimeId": False,
            },
        ])
        self.assertEqual(frozenset({"windowsTerminal"}), value.enabled_kinds)
        self.assertTrue(value.allows("windowsTerminal"))
        self.assertFalse(value.allows("putty"))
        self.assertEqual("windowsterminal", value.descriptor("windowsTerminal").app_module)

    def test_configuration_cannot_enable_unimplemented_putty_adapter(self) -> None:
        with self.assertRaisesRegex(ValueError, "no implemented adapter"):
            policy([{
                "kind": "putty", "status": "enabled",
                "appModule": "putty",
                "uiaClassNames": ["PuTTY"],
                "requiresRuntimeId": False,
            }])

    def test_enabled_adapter_requires_explicit_identity_constraints(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit UIA"):
            policy([{
                "kind": "windowsTerminal", "status": "enabled",
                "appModule": "windowsterminal",
                "uiaClassNames": [],
                "requiresRuntimeId": True,
            }])


if __name__ == "__main__":
    unittest.main()
