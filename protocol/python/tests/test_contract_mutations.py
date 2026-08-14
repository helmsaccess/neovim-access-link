from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROTOCOL_PYTHON_ROOT = Path(__file__).parents[1]
PROTOCOL_PACKAGE = PROTOCOL_PYTHON_ROOT / "nvim_nvda_protocol"
TEST_ROOT = Path(__file__).parent


class TargetedContractMutationTests(unittest.TestCase):
    def assert_mutation_is_killed(
        self,
        *,
        relative_source: str,
        original: str,
        mutation: str,
        test_name: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mutant_root = Path(directory)
            mutant_package = mutant_root / PROTOCOL_PACKAGE.name
            shutil.copytree(PROTOCOL_PACKAGE, mutant_package)
            source_path = mutant_package / relative_source
            source = source_path.read_text(encoding="utf-8")
            self.assertEqual(1, source.count(original), relative_source)
            source_path.write_text(source.replace(original, mutation), encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment.pop("PYTHONPYCACHEPREFIX", None)
            environment["PYTHONPATH"] = os.pathsep.join(
                part for part in (str(mutant_root), environment.get("PYTHONPATH", "")) if part
            )
            completed = subprocess.run(
                (sys.executable, "-m", "unittest", "-v", test_name),
                cwd=TEST_ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=20,
                check=False,
            )
        self.assertNotEqual(0, completed.returncode, completed.stdout)

    def test_security_and_state_contract_mutations_are_killed(self) -> None:
        mutations = (
            {
                "relative_source": "codec.py",
                "original": (
                    'not isinstance(message["sequence"], int)\n'
                    '        or isinstance(message["sequence"], bool)'
                ),
                "mutation": ('not isinstance(message["sequence"], int)\n        or False'),
                "test_name": (
                    "test_protocol.CodecTests.test_boolean_and_negative_integer_fields_are_rejected"
                ),
            },
            {
                "relative_source": "codec.py",
                "original": "if len(payload) > max_frame_bytes:",
                "mutation": "if len(payload) >= max_frame_bytes:",
                "test_name": "test_protocol.CodecTests.test_exact_frame_size_limit_is_accepted",
            },
            {
                "relative_source": "cursor_routing.py",
                "original": (
                    'and set(payload) == {\n\t\t\t\t"target",\n\t\t\t\t"bufferId",\n'
                    '\t\t\t\t"windowId",\n\t\t\t\t"line",'
                ),
                "mutation": (
                    'and set(payload) >= {\n\t\t\t\t"target",\n\t\t\t\t"bufferId",\n'
                    '\t\t\t\t"windowId",\n\t\t\t\t"line",'
                ),
                "test_name": "test_cursor_routing.CursorRoutingTests.test_exact_field_sets",
            },
            {
                "relative_source": "session.py",
                "original": (
                    "if self.session_id is None:\n"
                    '            if message["type"] != "fullState" or sequence != 0:'
                ),
                "mutation": (
                    "if self.session_id is None:\n"
                    '            if message["type"] != "fullState" or sequence < 0:'
                ),
                "test_name": (
                    "test_protocol.SessionTests.test_first_message_must_be_full_state_sequence_zero"
                ),
            },
        )
        for mutation in mutations:
            with self.subTest(source=mutation["relative_source"], test=mutation["test_name"]):
                self.assert_mutation_is_killed(**mutation)


if __name__ == "__main__":
    unittest.main()
