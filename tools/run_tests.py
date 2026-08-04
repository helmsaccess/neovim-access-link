#!/usr/bin/env python3
"""Run isolated test groups concurrently without sharing runtime directories."""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
PYTHON_TEST_PATH = os.pathsep.join(
    str(ROOT / path)
    for path in (
        "",
        "protocol/python",
        "bridge/python",
        "nvda-addon/core",
        "protocol/python/tests",
        "bridge/python/tests",
        "nvda-addon/tests",
    )
)
DEFAULT_JOBS = min(8, os.cpu_count() or 1)
UNIX_SOCKET_PATH_MAX = 107
TEMPORARY_NAME_SAMPLE = "tmp12345678"
REAL_BRIDGE_TESTS = (
    "test_real_tui_f12_claim_preserves_normal_and_insert_input",
    "test_real_tui_spell_choices_are_structured_and_accept_the_native_index",
    "test_local_windows_loopback_client_receives_semantic_results",
    "test_real_tui_omnifunc_emits_popup_selection_and_close",
    "test_real_tui_terminal_control_and_process_exit_are_structured",
    "test_real_tui_running_terminal_bd_reports_guard_before_hit_enter",
    "test_cursor_routing_publishes_immediately_in_insert_and_command_line_modes",
    "test_braille_line_navigation_preserves_insert_virtual_column",
    "test_repeated_braille_routing_actions_preserve_insert_and_line_semantics",
    "test_braille_exploration_is_read_only_in_insert_and_independent",
    "test_neovim_restart_reconnects_and_pushes_full_state",
)
MOCK_BRIDGE_TESTS = (
    "test_active_parameter_transition_is_validated_before_publication",
    "test_bridge_accepts_only_the_exact_active_numbered_choice",
    "test_braille_exploration_uses_separate_fixed_capability_gated_entry_points",
    "test_cursor_routing_uses_only_fixed_validated_plugin_entry_point",
    "test_braille_line_navigation_uses_only_fixed_capability_gated_entry_point",
    "test_repeated_braille_routing_uses_only_fixed_capability_gated_entry_point",
    "test_clipboard_control_uses_only_fixed_plugin_entry_points",
    "test_terminal_control_uses_only_its_fixed_plugin_entry_point",
    "test_exploration_uses_only_fixed_bounded_plugin_entry_points",
    "test_developer_context_uses_only_fixed_capability_gated_entry_points",
    "test_bridge_publishes_developer_context_once_but_never_caches_it",
    "test_bridge_publishes_clipboard_text_once_but_never_caches_it",
    "test_bridge_publishes_braille_exploration_once_but_never_caches_it",
    "test_bridge_publishes_valid_exploration_once_but_never_caches_it",
)
GROUPS = ("unit", "package", "lua", "ssh", "socket")
PRESETS = {
    "quick": ("unit",),
    "safe": ("unit", "package", "lua"),
    "all-safe": ("unit", "package", "lua"),
    "all": GROUPS,
}


@dataclass(frozen=True)
class Job:
    name: str
    group: str
    command: tuple[str, ...]
    cwd: Path
    source: Path


@dataclass(frozen=True)
class Result:
    job: Job
    returncode: int
    elapsed: float
    output: str
    test_count: int


def python_file(group: str, component: str, relative: str) -> Job:
    path = ROOT / relative
    return Job(
        name=f"{component}:{path.stem}",
        group=group,
        command=(sys.executable, "-m", "unittest", "-v", str(path)),
        cwd=ROOT,
        source=path,
    )


def class_test_methods(path: Path, class_name: str) -> tuple[str, ...]:
    syntax = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    test_class = next(
        node for node in syntax.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return tuple(
        node.name
        for node in test_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    )


def python_shards(
    group: str,
    component: str,
    relative: str,
    class_name: str,
    shard_count: int,
) -> tuple[Job, ...]:
    path = ROOT / relative
    methods = class_test_methods(path, class_name)
    shards = tuple(methods[index::shard_count] for index in range(shard_count))
    prefix = f"{path.stem}.{class_name}."
    return tuple(
        Job(
            name=f"{component}:{path.stem}-{index + 1}-of-{shard_count}",
            group=group,
            command=(sys.executable, "-m", "unittest", "-v", *(prefix + method for method in shard)),
            cwd=ROOT,
            source=path,
        )
        for index, shard in enumerate(shards)
        if shard
    )


def bridge_methods(group: str, name: str, methods: tuple[str, ...]) -> Job:
    source = ROOT / "bridge/python/tests/test_nvim_bridge.py"
    prefix = "test_nvim_bridge.NvimBridgeTests."
    return Job(
        name=f"bridge:{name}",
        group=group,
        command=(sys.executable, "-m", "unittest", "-v", *(prefix + method for method in methods)),
        cwd=ROOT,
        source=source,
    )


def lua_spec(group: str, relative: str) -> Job:
    path = ROOT / relative
    arguments = [
        "nvim",
        "--headless",
        "-n",
        "-u",
        "NONE",
        "-i",
        "NONE",
        "--cmd",
        "set packpath=",
    ]
    if path.name == "file_manager_spec.lua":
        arguments.extend(
            (
                "--cmd",
                "set packpath^=$VIMRUNTIME",
                "--cmd",
                "if isdirectory($VIMRUNTIME . '/pack/dist/opt/netrw') | "
                "packadd netrw | else | runtime plugin/netrwPlugin.vim | endif",
            )
        )
    arguments.extend(("-l", str(path)))
    return Job(
        name=f"lua:{path.stem}",
        group=group,
        command=tuple(arguments),
        cwd=ROOT,
        source=path,
    )


def validate_inventory(configured: tuple[Job, ...]) -> None:
    expected_python = {
        *ROOT.glob("protocol/python/tests/test_*.py"),
        *ROOT.glob("bridge/python/tests/test_*.py"),
        *ROOT.glob("nvda-addon/tests/test_*.py"),
    }
    expected_lua = set(ROOT.glob("neovim-plugin/tests/*_spec.lua"))
    expected_human = set(ROOT.glob("tests/human/test_*.py"))
    configured_sources = {job.source for job in configured}
    expected = expected_python | expected_lua | expected_human
    missing = sorted(expected - configured_sources)
    unexpected = sorted(configured_sources - expected)
    if missing or unexpected:
        raise RuntimeError(
            f"test group inventory mismatch; missing={missing!r}, unexpected={unexpected!r}"
        )
    bridge_source = ROOT / "bridge/python/tests/test_nvim_bridge.py"
    bridge_methods_in_source = set(class_test_methods(bridge_source, "NvimBridgeTests"))
    configured_bridge_methods = set(MOCK_BRIDGE_TESTS) | set(REAL_BRIDGE_TESTS)
    if bridge_methods_in_source != configured_bridge_methods:
        raise RuntimeError(
            "test_nvim_bridge classification mismatch; "
            f"missing={sorted(bridge_methods_in_source - configured_bridge_methods)!r}, "
            f"unexpected={sorted(configured_bridge_methods - bridge_methods_in_source)!r}"
        )


def jobs() -> tuple[Job, ...]:
    result: list[Job] = []
    for file_name in (
        "test_braille_exploration.py",
        "test_braille_navigation.py",
        "test_braille_routing_actions.py",
        "test_clipboard.py",
        "test_developer_context.py",
        "test_exploration.py",
        "test_local_client.py",
        "test_numbered_choice.py",
        "test_nvim_rpc.py",
        "test_protocol.py",
        "test_signature_help.py",
        "test_terminal_control.py",
    ):
        result.append(python_file("unit", "protocol", f"protocol/python/tests/{file_name}"))
    for file_name in ("test_cli.py", "test_session_registry.py", "test_stdio.py"):
        result.append(python_file("unit", "bridge", f"bridge/python/tests/{file_name}"))
    result.append(bridge_methods("unit", "mocked-nvim", MOCK_BRIDGE_TESTS))
    result.append(python_file("unit", "human", "tests/human/test_framework.py"))
    for file_name in (
        "test_braille_exploration.py",
        "test_braille_routing_repeats.py",
        "test_connection_coordinator.py",
        "test_connection_instances.py",
        "test_connection_profiles.py",
        "test_connection_targets.py",
        "test_control_dispatcher.py",
        "test_exploration.py",
        "test_frontend_policy.py",
        "test_gettext_catalog.py",
        "test_held_context.py",
        "test_local_install.py",
        "test_local_sessions.py",
        "test_numbered_choice.py",
        "test_repository_policy.py",
        "test_service_registrar.py",
        "test_speech.py",
    ):
        result.append(python_file("unit", "addon", f"nvda-addon/tests/{file_name}"))
    result.extend(
        python_shards(
            "package",
            "addon",
            "nvda-addon/tests/test_built_addon.py",
            "BuiltAddonTests",
            2,
        )
    )
    for file_name in (
        "braille_exploration_spec.lua",
        "braille_navigation_spec.lua",
        "braille_routing_actions_spec.lua",
        "call_context_spec.lua",
        "clipboard_spec.lua",
        "completion_adapters_spec.lua",
        "diagnostic_navigation_spec.lua",
        "diagnostics_spec.lua",
        "developer_context_spec.lua",
        "developer_context_lsp_integration_spec.lua",
        "exploration_spec.lua",
        "example_lazy_python_config_spec.lua",
        "file_manager_navigation_spec.lua",
        "file_manager_spec.lua",
        "file_manager_workflows_spec.lua",
        "human_test_config_spec.lua",
        "human_test_linter_readiness_spec.lua",
        "lsp_hover_spec.lua",
        "lsp_status_spec.lua",
        "menu_spec.lua",
        "native_completion_spec.lua",
        "navigation_spec.lua",
        "selection_spec.lua",
        "signature_help_spec.lua",
        "signature_help_automatic_spec.lua",
        "spelling_spec.lua",
    ):
        result.append(lua_spec("lua", f"neovim-plugin/tests/{file_name}"))
    result.extend(
        (
            python_file("ssh", "protocol", "protocol/python/tests/test_stdio_client.py"),
            python_file("ssh", "addon", "nvda-addon/tests/test_ssh_install.py"),
            python_file("ssh", "addon", "nvda-addon/tests/test_ssh_sessions.py"),
        )
    )
    result.extend(
        bridge_methods("socket", f"real-{index}", (method,))
        for index, method in enumerate(REAL_BRIDGE_TESTS, start=1)
    )
    result.extend(
        (
            lua_spec("socket", "neovim-plugin/tests/local_windows_session_spec.lua"),
            lua_spec("socket", "neovim-plugin/tests/session_registry_spec.lua"),
        )
    )
    configured = tuple(result)
    validate_inventory(configured)
    return configured


def selected_groups(arguments: tuple[str, ...]) -> tuple[str, ...]:
    selected: list[str] = []
    for value in arguments:
        expanded = PRESETS.get(value, (value,))
        for group in expanded:
            if group not in selected:
                selected.append(group)
    return tuple(selected)


def nested_socket_path_probe(repository_root: Path, job_index: int = 99) -> Path:
    """Model the longest nested socket path created by the real TUI tests."""
    return (
        repository_root
        / "tmp"
        / "r-12345678"
        / f"j{job_index}"
        / "t"
        / TEMPORARY_NAME_SAMPLE
        / "nvim.sock"
    )


def validate_socket_path_budget(repository_root: Path) -> None:
    probe = nested_socket_path_probe(repository_root)
    byte_length = len(os.fsencode(probe))
    if byte_length > UNIX_SOCKET_PATH_MAX:
        raise ValueError(
            f"checkout path is too long for disposable Unix sockets "
            f"({byte_length} > {UNIX_SOCKET_PATH_MAX} bytes): {probe}"
        )


def run_job(job: Job, job_directory: Path) -> Result:
    runtime = job_directory / "r"
    temporary = job_directory / "t"
    runtime.mkdir(parents=True)
    runtime.chmod(0o700)
    temporary.mkdir()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (PYTHON_TEST_PATH, environment.get("PYTHONPATH", "")) if part
    )
    if job.group == "package":
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        environment["PYTHONPYCACHEPREFIX"] = str(job_directory / "pycache")
    else:
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment.pop("PYTHONPYCACHEPREFIX", None)
    environment["TMPDIR"] = str(temporary)
    environment["XDG_RUNTIME_DIR"] = str(runtime)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            job.command,
            cwd=job.cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            check=False,
        )
        returncode = completed.returncode
        output = completed.stdout
    except OSError as error:
        returncode = 127
        output = f"{type(error).__name__}: {error}\n"
    elapsed = time.monotonic() - started
    match = re.search(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE)
    return Result(job, returncode, elapsed, output, int(match.group(1)) if match else 0)


def parse_args() -> argparse.Namespace:
    names = (*GROUPS, *PRESETS)
    parser = argparse.ArgumentParser(
        description="Run independent test processes in parallel. The default preset is 'safe'.",
    )
    parser.add_argument(
        "groups",
        nargs="*",
        default=None,
        choices=names,
        help="group or preset to run (may be repeated)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"maximum parallel processes (default: {DEFAULT_JOBS})",
    )
    parser.add_argument("--list", action="store_true", help="list selected jobs without running them")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.jobs < 1:
        raise SystemExit("--jobs must be at least 1")
    groups = selected_groups(tuple(arguments.groups or ("safe",)))
    selected = tuple(job for job in jobs() if job.group in groups)
    if arguments.list:
        for job in selected:
            print(f"{job.group:7} {job.name}")
        print(f"{len(selected)} jobs; groups: {', '.join(groups)}")
        return 0

    print(
        f"Running {len(selected)} isolated jobs from groups {', '.join(groups)} "
        f"with up to {min(arguments.jobs, len(selected))} workers"
    )
    started = time.monotonic()
    results: list[Result] = []
    batches = (selected,)
    socket_jobs = tuple(job for job in selected if job.group == "socket")
    ssh_jobs = tuple(job for job in selected if job.group == "ssh")
    safe_jobs = tuple(job for job in selected if job.group not in {"ssh", "socket"})
    separated_batches = tuple(batch for batch in (safe_jobs, ssh_jobs, socket_jobs) if batch)
    if len(separated_batches) > 1:
        batches = separated_batches
    if socket_jobs:
        validate_socket_path_budget(ROOT)
    temporary_parent = ROOT / "tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="r-",
        dir=temporary_parent,
    ) as temporary_name:
        temporary_root = Path(temporary_name)
        submitted_index = 0
        for batch_index, batch in enumerate(batches, start=1):
            if len(batches) > 1:
                phase = {
                    "ssh": "isolated SSH phase",
                    "socket": "isolated socket phase",
                }.get(batch[0].group, "sandbox-safe phase")
                print(f"Phase {batch_index}/{len(batches)}: {phase}", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.jobs) as executor:
                futures = {}
                for job in batch:
                    submitted_index += 1
                    futures[
                        executor.submit(
                            run_job,
                            job,
                            temporary_root / f"j{submitted_index}",
                        )
                    ] = job
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    results.append(result)
                    status = "PASS" if result.returncode == 0 else "FAIL"
                    print(
                        f"[{len(results):02d}/{len(selected):02d}] {status} "
                        f"{result.job.name} ({result.elapsed:.2f}s)",
                        flush=True,
                    )

    failures = [result for result in results if result.returncode != 0]
    for result in failures:
        print(f"\n===== {result.job.name} ({result.job.group}) =====", file=sys.stderr)
        print(result.output.rstrip(), file=sys.stderr)
    elapsed = time.monotonic() - started
    tests = sum(result.test_count for result in results)
    if failures:
        print(
            f"\nFAILED: {len(failures)} of {len(results)} jobs failed; "
            f"{tests} unittest cases completed in {elapsed:.2f}s",
            file=sys.stderr,
        )
        return 1
    print(f"\nOK: {len(results)} jobs, {tests} unittest cases in {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
