from __future__ import annotations

import unittest

from nvim_nvda_core import (
    LOCAL_WINDOWS_TARGET_ID, LOCAL_WINDOWS_TCP, REMOTE_SSH,
    ConnectionTarget, local_windows_target, remote_ssh_target,
)


class ConnectionTargetTests(unittest.TestCase):
    def test_remote_target_retains_profile_identity(self) -> None:
        target = remote_ssh_target("work-example-host", "Example host work")
        self.assertEqual(REMOTE_SSH, target.kind)
        self.assertEqual("work-example-host", target.identifier)
        self.assertEqual("work-example-host", target.profile_id)

    def test_local_target_has_no_ssh_profile(self) -> None:
        target = local_windows_target("This computer")
        self.assertEqual(LOCAL_WINDOWS_TCP, target.kind)
        self.assertEqual(LOCAL_WINDOWS_TARGET_ID, target.identifier)
        self.assertEqual("", target.profile_id)

    def test_invalid_cross_kind_fields_are_rejected(self) -> None:
        invalid = (
            ("unknown", "id", "Name", ""),
            (REMOTE_SSH, "remote", "Remote", ""),
            (LOCAL_WINDOWS_TCP, "local", "Local", "ssh-profile"),
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                ConnectionTarget(*arguments)


if __name__ == "__main__":
    unittest.main()
