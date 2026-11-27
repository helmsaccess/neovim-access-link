from __future__ import annotations

import hashlib
import io
import os
import pathlib
import runpy
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import zipfile
from unittest import mock

import buildVars
from tools import distribution_build, documentation_archive

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
        directory_names[:] = sorted(name for name in directory_names if name not in IGNORED_DIRECTORY_NAMES)
        current_path = pathlib.Path(current_root)
        if "AGENTS.md" in file_names:
            discovered.add((current_path / "AGENTS.md").relative_to(REPOSITORY_ROOT))
        if {"AGENTS.md", "AGENTS.override.md"} <= set(file_names):
            raise AssertionError(f"{current_path} contains both AGENTS.md and AGENTS.override.md")
    return discovered


class RepositoryPolicyTests(unittest.TestCase):
    def test_platform_builds_prepare_only_verified_pandoc_executables(self) -> None:
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr(distribution_build.PANDOC_WINDOWS_MEMBER, b"windows pandoc")
        payload = archive_bytes.getvalue()
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(
                distribution_build,
                "PANDOC_WINDOWS_SHA256",
                hashlib.sha256(payload).hexdigest(),
            ),
            mock.patch.object(
                distribution_build.urllib.request,
                "urlopen",
                return_value=io.BytesIO(payload),
            ),
            mock.patch.object(distribution_build.shutil, "which", return_value=None),
        ):
            pandoc = distribution_build.prepare_windows_pandoc(pathlib.Path(directory))
            self.assertEqual(b"windows pandoc", pandoc.read_bytes())
            self.assertEqual("pandoc.exe", pandoc.name)

        archive_bytes = io.BytesIO()
        with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
            payload_info = tarfile.TarInfo(distribution_build.PANDOC_LINUX_MEMBER)
            payload_info.size = len(b"linux pandoc")
            archive.addfile(payload_info, io.BytesIO(b"linux pandoc"))
        payload = archive_bytes.getvalue()
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(
                distribution_build,
                "PANDOC_LINUX_SHA256",
                hashlib.sha256(payload).hexdigest(),
            ),
            mock.patch.object(
                distribution_build.urllib.request,
                "urlopen",
                return_value=io.BytesIO(payload),
            ),
        ):
            pandoc = distribution_build.prepare_linux_pandoc(pathlib.Path(directory))
            self.assertEqual(b"linux pandoc", pandoc.read_bytes())
            if os.name == "posix":
                self.assertTrue(pandoc.stat().st_mode & 0o100)

    def test_windows_build_reuses_local_pandoc_only_when_it_matches_the_renderer(self) -> None:
        compatible = pathlib.Path("C:/Tools/Pandoc/pandoc.exe")
        with (
            mock.patch.object(distribution_build.shutil, "which", return_value=str(compatible)),
            mock.patch.object(
                distribution_build.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    (), 0, "pandoc.exe 3.1.11.1\r\nFeatures: +server +lua\r\n", "",
                ),
            ),
            mock.patch.object(distribution_build, "_download_verified") as download,
        ):
            self.assertEqual(
                compatible,
                distribution_build.prepare_windows_pandoc(pathlib.Path("unused")),
            )
        download.assert_not_called()

        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(distribution_build.shutil, "which", return_value=str(compatible)),
            mock.patch.object(
                distribution_build.subprocess,
                "run",
                return_value=subprocess.CompletedProcess((), 0, "pandoc 3.1.9\nFeatures: +server +lua\n", ""),
            ),
            mock.patch.object(distribution_build, "_download_verified") as download,
            mock.patch.object(zipfile, "ZipFile", side_effect=zipfile.BadZipFile("test stop")),
            self.assertRaisesRegex(RuntimeError, "archive is invalid"),
        ):
            distribution_build.prepare_windows_pandoc(pathlib.Path(directory))
        download.assert_called_once()

    def test_documentation_archive_contains_exactly_eight_reproducible_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "documentation"
            source.mkdir()
            for index, path in enumerate(documentation_archive.expected_sources(source)):
                path.write_text(f"document {index}\n", encoding="utf-8")
            first = documentation_archive.build(source, root / "first")
            second = documentation_archive.build(source, root / "second")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    [path.name for path in documentation_archive.expected_sources(source)],
                    archive.namelist(),
                )

    def test_windows_build_snapshot_accepts_clean_local_development_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = pathlib.Path(directory) / "repository"
            subprocess.run(
                ("git", "init", "--initial-branch=feature", str(repository)),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ("git", "-C", str(repository), "config", "user.name", "Test User"),
                check=True,
            )
            subprocess.run(
                ("git", "-C", str(repository), "config", "user.email", "test@example.invalid"),
                check=True,
            )
            (repository / "tracked.txt").write_text("state\n", encoding="utf-8")
            subprocess.run(
                ("git", "-C", str(repository), "add", "tracked.txt"),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ("git", "-C", str(repository), "commit", "-m", "State"),
                check=True,
                capture_output=True,
            )
            with mock.patch.object(buildVars, "development_build", 1):
                snapshot = distribution_build.development_source_snapshot(repository)
                self.assertEqual("feature", snapshot.branch)
                self.assertRegex(snapshot.commit, r"^[0-9a-f]{40}$")
                (repository / "scratch.txt").write_text("local scratch\n", encoding="utf-8")
                self.assertEqual(snapshot, distribution_build.development_source_snapshot(repository))
                (repository / "tracked.txt").write_text("modified\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "changes to versioned files"):
                    distribution_build.development_source_snapshot(repository)

    def test_windows_build_snapshot_rejects_release_metadata(self) -> None:
        with mock.patch.object(buildVars, "development_build", None):
            with self.assertRaisesRegex(RuntimeError, "development build number"):
                distribution_build.development_source_snapshot(REPOSITORY_ROOT)

    def test_shared_distribution_build_uses_an_isolated_temporary_environment(self) -> None:
        environment_builder = mock.Mock()
        artifact_version = buildVars.artifact_version()
        product_slug = buildVars.product_slug()

        def complete_build(command, **_kwargs):
            command = tuple(str(value) for value in command)
            if command[1:4] == ("-m", "SCons", "-Q"):
                output_variable = next(value for value in command if value.startswith("OUTPUT_DIRECTORY="))
                output = pathlib.Path(output_variable.split("=", 1)[1])
                (output / f"NeovimAccessLink-{artifact_version}.nvda-addon").write_bytes(b"addon")
            elif command[-2].endswith("documentation") and command[-1].endswith("artifacts"):
                pathlib.Path(
                    command[-1],
                    f"{product_slug}-{artifact_version}-documentation.zip",
                ).write_bytes(b"docs")

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            snapshot = mock.Mock(return_value=distribution_build.SourceSnapshot("main", "a" * 40))
            with (
                mock.patch.object(
                    distribution_build.venv,
                    "EnvBuilder",
                    return_value=environment_builder,
                ),
                mock.patch.object(
                    distribution_build.subprocess,
                    "run",
                    side_effect=complete_build,
                ) as run,
                mock.patch.object(buildVars, "artifact_version", return_value=artifact_version),
                mock.patch.object(buildVars, "product_slug", return_value=product_slug),
                mock.patch.object(distribution_build, "_publish", return_value=()),
                mock.patch.object(sys.modules["builtins"], "print"),
            ):
                distribution_build.build_distributions(
                    root,
                    bash=pathlib.Path("/bin/bash"),
                    snapshot=snapshot,
                    prepare_pandoc=lambda _root: pathlib.Path("/tmp/pandoc"),
                    temporary_prefix="test-distributable-",
                )

        environment = environment_builder.create.call_args.args[0]
        self.assertFalse(environment.exists())
        self.assertEqual(4, run.call_count)
        install_command = run.call_args_list[0].args[0]
        documentation_command = run.call_args_list[1].args[0]
        build_command = run.call_args_list[2].args[0]
        self.assertIn("--isolated", install_command)
        self.assertIn("--no-input", install_command)
        self.assertEqual(
            str(root / "tools/requirements-build.txt"),
            install_command[-1],
        )
        self.assertIn("--output-only", documentation_command)
        self.assertEqual(("-m", "SCons", "-Q", "addon"), build_command[1:5])
        self.assertIn("DOCUMENTATION_DIRECTORY", {str(value).split("=")[0] for value in build_command[5:]})
        self.assertEqual("1", run.call_args_list[0].kwargs["env"]["PYTHONNOUSERSITE"])
        self.assertEqual(2, snapshot.call_count)

    def test_scons_builds_and_reuses_an_isolated_addon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            artifacts = root / "addon archive"
            command = (
                sys.executable, "-m", "SCons", "-Q", "addon",
                f"OUTPUT_DIRECTORY={artifacts}",
                f"SCONS_STATE_DIRECTORY={root / 'signatures'}",
            )
            first = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            (artifact,) = artifacts.iterdir()
            with zipfile.ZipFile(artifact) as archive:
                self.assertIsNone(archive.testzip())
                self.assertTrue(all(entry.create_system == 3 for entry in archive.infolist()))
                self.assertIn("doc/en/readme.html", archive.namelist())
                self.assertIn("locale/de/manifest.ini", archive.namelist())
                self.assertIn("locale/de/LC_MESSAGES/nvda.mo", archive.namelist())
                self.assertFalse(any(path.endswith((".po", ".pot")) for path in archive.namelist()))
                root_plugin = "globalPlugins/NeovimAccessLink"
                for relative in ("build_info.py", "vendor/msgpack/fallback.py", "vendor/MSGPACK-LICENSE.txt"):
                    self.assertNotIn(b"\r\n", archive.read(f"{root_plugin}/{relative}"))
            second = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("up to date", second.stdout)

    def test_windows_and_linux_entry_points_share_the_distribution_builder(self) -> None:
        windows = runpy.run_path(str(REPOSITORY_ROOT / "build.py"), run_name="windows_build_test")
        linux = runpy.run_path(
            str(REPOSITORY_ROOT / "tools/build_release.py"),
            run_name="linux_release_build_test",
        )
        windows_builder = mock.Mock(return_value=())
        linux_builder = mock.Mock(return_value=())
        with (
            mock.patch.object(windows["sys"], "argv", ["build.py"]),
            mock.patch.dict(
                windows["build"].__globals__,
                {
                    "_require_windows": mock.Mock(),
                    "_find_bash": mock.Mock(return_value=pathlib.Path("/bin/bash")),
                },
            ),
            mock.patch.object(
                windows["distribution_build"],
                "build_distributions",
                windows_builder,
            ),
        ):
            windows["build"]()
        with (
            mock.patch.object(linux["sys"], "argv", ["build_release.py"]),
            mock.patch.object(linux["os"], "name", "posix"),
            mock.patch.dict(
                linux["build"].__globals__,
                {"_find_bash": mock.Mock(return_value=pathlib.Path("/bin/bash"))},
            ),
            mock.patch.object(
                linux["distribution_build"],
                "build_distributions",
                linux_builder,
            ),
        ):
            linux["build"]()
        self.assertIs(
            windows_builder.call_args.kwargs["prepare_pandoc"],
            distribution_build.prepare_windows_pandoc,
        )
        self.assertIs(
            linux_builder.call_args.kwargs["prepare_pandoc"],
            distribution_build.prepare_linux_pandoc,
        )

    def test_documentation_layout_is_an_internal_library(self) -> None:
        self.assertFalse((REPOSITORY_ROOT / "tools/sync_installed_documentation.py").exists())
        self.assertTrue((REPOSITORY_ROOT / "tools/documentation_layout.py").is_file())
        for caller in ("build_nvda_addon.py", "documentation_archive.py"):
            text = (REPOSITORY_ROOT / "tools" / caller).read_text(encoding="utf-8")
            self.assertIn("documentation_layout", text)

    def test_linux_release_snapshot_requires_release_metadata_clean_main(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = pathlib.Path(directory) / "repository"
            subprocess.run(
                ("git", "init", "--initial-branch=main", str(repository)),
                check=True,
                capture_output=True,
            )
            subprocess.run(("git", "-C", str(repository), "config", "user.name", "Test"), check=True)
            subprocess.run(
                ("git", "-C", str(repository), "config", "user.email", "test@example.invalid"),
                check=True,
            )
            tracked = repository / "tracked.txt"
            tracked.write_text("clean\n", encoding="utf-8")
            subprocess.run(("git", "-C", str(repository), "add", "tracked.txt"), check=True)
            subprocess.run(
                ("git", "-C", str(repository), "commit", "-m", "Initial"),
                check=True,
                capture_output=True,
            )
            with self.assertRaisesRegex(RuntimeError, "development_build"):
                distribution_build.release_source_snapshot(repository)
            with mock.patch.object(buildVars, "development_build", None):
                snapshot = distribution_build.release_source_snapshot(repository)
                self.assertEqual("main", snapshot.branch)
                subprocess.run(
                    ("git", "-C", str(repository), "switch", "-c", "feature"),
                    check=True,
                    capture_output=True,
                )
                with self.assertRaisesRegex(RuntimeError, "from main"):
                    distribution_build.release_source_snapshot(repository)
                subprocess.run(
                    ("git", "-C", str(repository), "switch", "main"),
                    check=True,
                    capture_output=True,
                )
                tracked.write_text("dirty\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "changes to versioned files"):
                    distribution_build.release_source_snapshot(repository)

    def test_optional_windows_launcher_is_parameterless_and_keeps_results_visible(self) -> None:
        launcher = (REPOSITORY_ROOT / "build.cmd").read_text(encoding="utf-8")
        self.assertIn('pushd "%~dp0"', launcher)
        self.assertIn("py -3 build.py", launcher)
        self.assertIn("python build.py", launcher)
        self.assertIn("pause", launcher)
        self.assertNotIn("tools\\build_nvda_addon.py", launcher)

    def test_windows_workspace_hooks_only_queue_safe_versioned_state_sync(self) -> None:
        synchronizer = (REPOSITORY_ROOT / "tools/windows_workspace_sync.py").read_text(encoding="utf-8")
        self.assertIn('"--no-overwrite-ignore"', synchronizer)
        self.assertIn("refs/nal-sync/heads", synchronizer)
        self.assertIn('"--prune"', synchronizer)
        for forbidden in ('"clean"', '"reset", "--hard"', '"--discard-changes"'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, synchronizer)
        for hook_name in ("post-checkout", "reference-transaction"):
            hook = REPOSITORY_ROOT / ".githooks" / hook_name
            with self.subTest(hook=hook_name):
                self.assertTrue(hook.is_file())
                self.assertTrue(os.access(hook, os.X_OK))

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
                '```lua\nprint("stale")\n```\n'
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
            (REPOSITORY_ROOT / "examples/neovim-lazy-python/init.lua")
            .read_text(encoding="utf-8")
            .rstrip("\n")
        )
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
                    f"{agents_path} is {size} bytes; keep it at or below {MAX_AGENTS_BYTES} bytes (12 KiB)",
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

    def test_guided_groups_list_all_cases_without_a_guest(self) -> None:
        command = (sys.executable, str(REPOSITORY_ROOT / "tools/run_tests.py"))
        result = subprocess.run(
            (*command, "guided-desktop", "guided-audio", "--list"),
            cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True, timeout=20,
        )
        listed = dict(line.split() for line in result.stdout.splitlines())
        self.assertEqual(len(result.stdout.splitlines()), len(listed))
        self.assertEqual({"C1", "C2", "C3", "D1", "D3", "D4"},
                         {case for case, group in listed.items() if group == "audio"})
        self.assertEqual({"L1", "L2", "L3", "L4", "L5", "L6", "D2", "S1", "P1", "P2", "P3", "P4"},
                         {case for case, group in listed.items() if group == "desktop"})

        invalid = subprocess.run(
            (*command, "guided-audio", "--list", "--guided-case", "P4"),
            cwd=REPOSITORY_ROOT, capture_output=True, text=True, timeout=20,
        )
        self.assertNotEqual(0, invalid.returncode)
        self.assertIn("outside the group", invalid.stderr)

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

    def test_runner_reports_successful_skips_and_warnings(self) -> None:
        runner = runpy.run_path(
            str(REPOSITORY_ROOT / "tools/run_tests.py"),
            run_name="repository_test_runner",
        )
        output = "\n".join(
            (
                "test_first (Example.test_first) ... ok",
                "test_second (Example.test_second) ... skipped 'requires Windows'",
                "/tmp/example.py:17: ResourceWarning: unclosed resource",
                "Ran 2 tests in 0.001s",
                "OK (skipped=1)",
            )
        )

        count, skip_reasons, warnings = runner["parse_unittest_observations"](output)

        self.assertEqual(2, count)
        self.assertEqual(("requires Windows",), skip_reasons)
        self.assertEqual(
            ("/tmp/example.py:17: ResourceWarning: unclosed resource",),
            warnings,
        )

    @unittest.skipUnless(os.name == "posix", "POSIX process-group contract")
    def test_runner_timeout_terminates_the_complete_process_group(self) -> None:
        runner = runpy.run_path(
            str(REPOSITORY_ROOT / "tools/run_tests.py"),
            run_name="repository_test_runner",
        )
        child_script = (
            "import subprocess,sys,time; "
            "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
            "print(child.pid,flush=True); time.sleep(30)"
        )
        job = runner["Job"](
            name="process-tree-timeout",
            group="unit",
            command=(sys.executable, "-c", child_script),
            cwd=REPOSITORY_ROOT,
            source=pathlib.Path(__file__),
        )
        with tempfile.TemporaryDirectory() as directory:
            result = runner["run_job"](job, pathlib.Path(directory) / "job", 3.0)

        self.assertEqual(124, result.returncode)
        pid_line = result.output.splitlines()[0]
        self.assertTrue(pid_line.isdecimal(), result.output)
        child_pid = int(pid_line)
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            status = pathlib.Path(f"/proc/{child_pid}/stat")
            if status.exists() and status.read_text(encoding="utf-8").split()[2] == "Z":
                break
            time.sleep(0.01)
        else:
            self.fail(f"timed-out child process {child_pid} is still running")

    def test_ci_runs_safe_ssh_and_socket_groups_as_separate_jobs(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/repository-tests.yml").read_text(encoding="utf-8")
        for command in (
            "python3 tools/run_tests.py all-safe",
            "python3 tools/run_tests.py ssh",
            "python3 tools/run_tests.py socket -j 1",
        ):
            with self.subTest(command=command):
                self.assertEqual(1, workflow.count(command))
        self.assertEqual(
            4,
            workflow.count("python3 -m pip install --requirement tools/requirements-ci.txt"),
        )

    def test_ci_builds_the_complete_documentation_set(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/repository-tests.yml").read_text(encoding="utf-8")
        self.assertEqual(1, workflow.count("run: bash tools/build_documentation.sh --test-only"))
        self.assertIn("German and English documentation build", workflow)
        self.assertNotIn("git diff --exit-code -- nvda-addon/addon/doc", workflow)

    def test_ci_pins_real_completion_plugin_matrix(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/repository-tests.yml").read_text(encoding="utf-8")
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
