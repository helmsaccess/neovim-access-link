from __future__ import annotations

import pathlib
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[2]
MAX_AGENTS_BYTES = 12 * 1024


class RepositoryPolicyTests(unittest.TestCase):
    def test_root_agents_instructions_fit_project_budget(self) -> None:
        agents_path = REPOSITORY_ROOT / "AGENTS.md"
        size = len(agents_path.read_bytes())
        self.assertLessEqual(
            size,
            MAX_AGENTS_BYTES,
            f"{agents_path} is {size} bytes; keep it at or below "
            f"{MAX_AGENTS_BYTES} bytes (12 KiB)",
        )


if __name__ == "__main__":
    unittest.main()
