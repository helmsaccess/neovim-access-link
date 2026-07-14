from __future__ import annotations

import unittest

from nvim_nvda_core import (
    parse_profile, parse_profiles,
    remove_profile, save_profile, unique_profile_id,
)


class ConnectionProfileTests(unittest.TestCase):
    def test_explicit_linux_user_is_independent_and_builds_target(self) -> None:
        profile = parse_profile({
            "id": "work-example-host", "name": "Example host work", "host": "editor.example.invalid",
            "user": "remote-editor", "port": 2222,
            "identityFile": r"C:\Users\local-user\.ssh\work_key", "authentication": "openSsh",
        })
        self.assertEqual("remote-editor@editor.example.invalid", profile.ssh_target)
        self.assertEqual("remote-editor", profile.user)
        self.assertNotIn("local-user", profile.ssh_target)

    def test_empty_user_delegates_only_to_openssh_configuration(self) -> None:
        profile = parse_profile({"id": "alias", "name": "Alias", "host": "example-host"})
        self.assertEqual("example-host", profile.ssh_target)
        self.assertEqual("", profile.user)
        password = parse_profile({
            "id": "password", "name": "Password", "host": "host",
            "user": "remote", "authentication": "password",
        })
        self.assertEqual("password", password.authentication)
        self.assertNotIn("password", password.as_dict().keys())

    def test_duplicate_ids_and_targets(self) -> None:
        values = [
            {"id": "one", "name": "One", "host": "one.example"},
            {"id": "two", "name": "Two", "host": "two.example", "user": "dev"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_profiles([values[0], values[0]])

    def test_rejects_option_injection_controls_and_unsupported_auth(self) -> None:
        base = {"id": "safe", "name": "Safe", "host": "example.org"}
        invalid = (
            {**base, "id": "../bad"},
            {**base, "host": "-oProxyCommand=bad"},
            {**base, "host": "host name"},
            {**base, "host": "user@host"},
            {**base, "user": "bad user"},
            {**base, "port": 0},
            {**base, "port": True},
            {**base, "identityFile": "-malicious"},
            {**base, "identityFile": "line\nbreak"},
            {**base, "authentication": "agentMagic"},
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_profile(value)

    def test_duplicate_targets_are_allowed_but_stable_ids_remain_unique(self) -> None:
        first = {"id": "example-host", "name": "Example host one", "host": "example-host", "user": "editor"}
        second = {"id": "example-host-2", "name": "Example host two", "host": "example-host", "user": "editor"}
        profiles = parse_profiles([first, second])
        self.assertEqual(["editor@example-host", "editor@example-host"], [profile.ssh_target for profile in profiles])
        self.assertEqual("example-host-3", unique_profile_id("Example host", {"example-host", "example-host-2"}))
        hosts = parse_profiles([
            {"id": "ipv4", "name": "IPv4", "host": "127.0.0.1", "user": "editor"},
            {"id": "ipv6", "name": "IPv6", "host": "::1", "user": "editor"},
        ])
        self.assertEqual(["editor@127.0.0.1", "editor@::1"], [profile.ssh_target for profile in hosts])

    def test_add_edit_remove_preserve_order(self) -> None:
        one = {"id": "one", "name": "One", "host": "one"}
        two = {"id": "two", "name": "Two", "host": "two", "user": "dev"}
        profiles = save_profile([one], two)
        edited = {**two, "name": "Two edited", "port": 2222}
        profiles = save_profile([profile.as_dict() for profile in profiles], edited, "two")
        self.assertEqual(["one", "two"], [profile.identifier for profile in profiles])
        self.assertEqual(("Two edited", 2222), (profiles[1].name, profiles[1].port))
        profiles = remove_profile([profile.as_dict() for profile in profiles], "two")
        self.assertEqual(["one"], [profile.identifier for profile in profiles])
        with self.assertRaisesRegex(ValueError, "does not exist"):
            remove_profile([one], "missing")


if __name__ == "__main__":
    unittest.main()
