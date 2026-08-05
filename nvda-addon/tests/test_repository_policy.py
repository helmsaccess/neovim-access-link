from __future__ import annotations

import os
import pathlib
import runpy
import tempfile
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[2]
MAX_AGENTS_BYTES = 12 * 1024
REQUIRED_AGENTS_PATHS = {
    pathlib.Path("AGENTS.md"),
    pathlib.Path("bridge/AGENTS.md"),
    pathlib.Path("docs/AGENTS.md"),
    pathlib.Path("neovim-plugin/AGENTS.md"),
    pathlib.Path("nvda-addon/AGENTS.md"),
    pathlib.Path("protocol/AGENTS.md"),
}
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "tmp",
}
FORBIDDEN_DOCUMENTATION_WORKFLOW_PHRASES = {
    "agent instructions",
    "agentenanweisung",
    "coding agent",
    "conversation history",
    "root-agentenanweisung",
    "user-to-agent",
}


def discover_agents_paths() -> set[pathlib.Path]:
    discovered: set[pathlib.Path] = set()
    for current_root, directory_names, file_names in os.walk(REPOSITORY_ROOT):
        directory_names[:] = sorted(
            name for name in directory_names if name not in IGNORED_DIRECTORY_NAMES
        )
        current_path = pathlib.Path(current_root)
        if "AGENTS.md" in file_names:
            discovered.add((current_path / "AGENTS.md").relative_to(REPOSITORY_ROOT))
        if {"AGENTS.md", "AGENTS.override.md"} <= set(file_names):
            raise AssertionError(f"{current_path} contains both AGENTS.md and AGENTS.override.md")
    return discovered


class RepositoryPolicyTests(unittest.TestCase):
    def test_documentation_example_sync_tool_updates_marked_blocks(self) -> None:
        namespace = runpy.run_path(
            str(REPOSITORY_ROOT / "tools/sync_documentation_examples.py"),
            run_name="documentation_example_sync_test",
        )
        with tempfile.TemporaryDirectory() as directory:
            temporary = pathlib.Path(directory)
            source = temporary / "example.lua"
            target = temporary / "manual.md"
            source.write_text('print("current")\n', encoding="utf-8")
            target.write_text(
                "before\n<!-- BEGIN lazy-python-example -->\n"
                "```lua\nprint(\"stale\")\n```\n"
                "<!-- END lazy-python-example -->\nafter\n",
                encoding="utf-8",
            )
            synchronize = namespace["_synchronize"]
            synchronize.__globals__["SOURCE"] = source
            self.assertTrue(synchronize(target, write=False))
            self.assertTrue(synchronize(target, write=True))
            self.assertFalse(synchronize(target, write=False))
            self.assertIn('```lua\nprint("current")\n```', target.read_text(encoding="utf-8"))

    def test_lazy_python_example_is_identical_in_both_manuals(self) -> None:
        example = (
            REPOSITORY_ROOT / "examples/neovim-lazy-python/init.lua"
        ).read_text(encoding="utf-8").rstrip("\n")
        start_marker = "<!-- BEGIN lazy-python-example -->"
        end_marker = "<!-- END lazy-python-example -->"

        for relative_path in (
            "docs/de/manual/example-configuration.md",
            "docs/en/manual/example-configuration.md",
        ):
            with self.subTest(path=relative_path):
                content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertEqual(1, content.count(start_marker))
                self.assertEqual(1, content.count(end_marker))
                marked = content.split(start_marker, 1)[1].split(end_marker, 1)[0].strip()
                self.assertTrue(marked.startswith("```lua\n"))
                self.assertTrue(marked.endswith("\n```"))
                embedded = marked[len("```lua\n") : -len("\n```")]
                self.assertEqual(example, embedded)

    def test_agents_instruction_layout_is_scoped_and_unambiguous(self) -> None:
        discovered = discover_agents_paths()
        self.assertTrue(REQUIRED_AGENTS_PATHS <= discovered)
        self.assertFalse((REPOSITORY_ROOT / "AGENTS.override.md").exists())

    def test_agents_instructions_fit_component_budget(self) -> None:
        for relative_path in sorted(discover_agents_paths()):
            agents_path = REPOSITORY_ROOT / relative_path
            with self.subTest(path=str(relative_path)):
                size = len(agents_path.read_bytes())
                self.assertLessEqual(
                    size,
                    MAX_AGENTS_BYTES,
                    f"{agents_path} is {size} bytes; keep it at or below "
                    f"{MAX_AGENTS_BYTES} bytes (12 KiB)",
                )

    def test_published_documentation_excludes_agent_workflow_instructions(self) -> None:
        documentation_roots = (
            REPOSITORY_ROOT / "docs/de",
            REPOSITORY_ROOT / "docs/en",
        )
        for documentation_root in documentation_roots:
            for path in sorted(documentation_root.rglob("*.md")):
                content = path.read_text(encoding="utf-8").casefold()
                for phrase in FORBIDDEN_DOCUMENTATION_WORKFLOW_PHRASES:
                    with self.subTest(path=str(path), phrase=phrase):
                        self.assertNotIn(phrase, content)

    def test_ssh_and_socket_presets_remain_separate(self) -> None:
        runner = runpy.run_path(
            str(REPOSITORY_ROOT / "tools/run_tests.py"),
            run_name="repository_test_runner",
        )
        presets = runner["PRESETS"]
        self.assertEqual(("unit", "package", "lua"), presets["all-safe"])
        self.assertNotIn("ssh", presets["all-safe"])
        self.assertNotIn("socket", presets["all-safe"])
        self.assertEqual(("unit", "package", "lua", "ssh", "socket"), presets["all"])

    def test_runner_keeps_nested_ci_socket_paths_below_the_unix_limit(self) -> None:
        runner = runpy.run_path(
            str(REPOSITORY_ROOT / "tools/run_tests.py"),
            run_name="repository_test_runner",
        )
        representative_ci_root = pathlib.Path("/") / ("r" * 54)
        probe = runner["nested_socket_path_probe"](representative_ci_root)
        self.assertEqual(55, len(os.fsencode(representative_ci_root)))
        self.assertLessEqual(
            len(os.fsencode(probe)),
            runner["UNIX_SOCKET_PATH_MAX"],
        )
        runner["validate_socket_path_budget"](representative_ci_root)
        with self.assertRaisesRegex(ValueError, "checkout path is too long"):
            runner["validate_socket_path_budget"](
                pathlib.Path("/") / ("r" * 90),
            )

    def test_ci_runs_safe_ssh_and_socket_groups_as_separate_jobs(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/repository-tests.yml").read_text(
            encoding="utf-8"
        )
        for command in (
            "python3 tools/run_tests.py all-safe",
            "python3 tools/run_tests.py ssh",
            "python3 tools/run_tests.py socket -j 1",
        ):
            with self.subTest(command=command):
                self.assertEqual(1, workflow.count(command))
        self.assertEqual(
            3,
            workflow.count(
                "python3 -m pip install --requirement tools/requirements-ci.txt"
            ),
        )

    def test_ci_builds_the_complete_documentation_set(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/repository-tests.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(1, workflow.count("run: bash tools/build_documentation.sh"))
        self.assertIn("German and English documentation build", workflow)

    def test_ci_pins_real_completion_plugin_matrix(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/repository-tests.yml").read_text(
            encoding="utf-8"
        )
        for expected in (
            "Neovim 0.10.1 / blink.cmp v1",
            "Neovim 0.12.3 / blink.cmp v1",
            "Neovim 0.12.3 / blink.cmp v2",
            "2ffe79f1f021def8dd1fcd81deb16f1bb0d989f3",
            "78336bc89ee5365633bcf754d93df01678b5c08f",
            "d33327a0ed7bfe3cd5dfa2fdd2738ad74f9e0ea3",
            "5876dd95deeb70aadbe9f1c0b7117a135061cdac",
            "4867de01a17f6083f902f8aa5215b40b0ed3a36e83cc0293de3f11708f1f9793",
            "c441b547142860bf01bcce39e36cbed185c41112813e15443b16e5237750724d",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, workflow)
        self.assertEqual(
            1,
            workflow.count("bash tools/test_completion_plugins.sh"),
        )


if __name__ == "__main__":
    unittest.main()
