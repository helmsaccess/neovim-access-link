"""Drive guided Neovim workflows and verify their real local protocol output."""

from __future__ import annotations

from contextlib import contextmanager
from itertools import dropwhile, takewhile
import json
import os
from pathlib import Path
import queue
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

import msgpack

from nvim_nvda_protocol.local_client import LocalTcpClient

from protocol.python.tests.test_local_client_socket import ROOT, open_editor, request


HUMAN = ROOT / "tests" / "human"
FIXTURE_NAMES = ("lsp_features.py", "lsp_rename_consumer.py")
DEPENDENCIES = json.loads((HUMAN / "dependencies.json").read_text(encoding="utf-8"))
ENGLISH = json.loads((HUMAN / "locales" / "en.json").read_text(encoding="utf-8"))
LINTER_ENV = {
    "diagnostics": "ACCESS_LINK_HUMAN_RUFF",
    "c-diagnostics": "ACCESS_LINK_HUMAN_CLANG_TIDY",
    "markdown-diagnostics": "ACCESS_LINK_HUMAN_MARKDOWNLINT",
}
LINTER_CONFIG = {"c-diagnostics": ".clang-tidy", "markdown-diagnostics": ".markdownlint.json"}
LAZY_PLUGIN_NAMES = ("access-link-stable-target", "access-link-update-target")
COMPLETION_PLUGINS = {
    "cmp": {"nvimCmp": "nvim-cmp", "cmpNvimLsp": "cmp-nvim-lsp"},
    "blink": {"blinkCmp": "blink.cmp"},
}


@contextmanager
def guided_scratch(test_id: str):
    directory = tempfile.TemporaryDirectory(prefix=f"guided-{test_id.lower()}-")
    try:
        yield Path(directory.name)
    finally:
        deadline = time.monotonic() + 3
        while True:
            try:
                directory.cleanup()
            except PermissionError as error:
                if getattr(error, "winerror", None) != 32 or time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
            else:
                break


class GuidedWorkflowSocketTests(unittest.TestCase):
    def test_guided_l6_keys_replace_two_buffers(self) -> None:
        self.verify_guided_l6(remove_matches_from_second_buffer=False)

    def test_guided_l6_incomplete_fixture_does_not_report_two_buffers(self) -> None:
        self.verify_guided_l6(remove_matches_from_second_buffer=True)

    @contextmanager
    def open_guided_editor(
        self, test_id: str, *, remove_matches_from_second_buffer: bool = False,
        pyright: Path | None = None, linter: Path | None = None, lazy: Path | None = None,
    ):
        version = subprocess.check_output(("nvim", "--version"), text=True).splitlines()[0]
        if not version.startswith("NVIM v0.12."):
            self.skipTest(f"guided profiles require Neovim 0.12.x, found {version}")
        plans = (json.loads(path.read_text(encoding="utf-8")) for path in (HUMAN / "plans").glob("*.json"))
        (plan, step), = (
            (plan, step) for plan in plans for step in plan["steps"] if step["testId"] == test_id
        )
        plugins = {}
        if plan["profile"] in COMPLETION_PLUGINS:
            if not (directory := os.environ.get("NAL_GUIDED_COMPLETION_ROOT")):
                self.skipTest("set NAL_GUIDED_COMPLETION_ROOT to the pinned completion checkouts")
            for key, name in COMPLETION_PLUGINS[plan["profile"]].items():
                plugins[key] = (Path(directory) / key, name)
        if linter:
            plugins["nvimLint"] = (Path(os.environ["NAL_GUIDED_NVIM_LINT"]), "nvim-lint")
        if lazy:
            plugins["lazyNvim"] = (lazy, "lazy.nvim")
        with guided_scratch(test_id) as scratch:
            fixture = scratch / "project"
            fixture.mkdir()
            names = FIXTURE_NAMES if plan["fixture"] == FIXTURE_NAMES[0] else (plan["fixture"],)
            for name in names:
                shutil.copyfile(HUMAN / "fixtures" / name, fixture / name)
            if remove_matches_from_second_buffer:
                secondary = fixture / FIXTURE_NAMES[1]
                secondary.write_bytes(secondary.read_bytes().replace(b"calculate_tip", b"unrelated_tip"))
            original = {name: (fixture / name).read_bytes() for name in names}
            env = {
                **os.environ,
                "LOCALAPPDATA": str(scratch),
                "NVIM_NVDA_TEST_WINDOWS": "1",
                "XDG_CONFIG_HOME": str(scratch / "config"),
                "XDG_DATA_HOME": str(scratch / "data"),
                "XDG_STATE_HOME": str(scratch / "state"),
                "XDG_CACHE_HOME": str(scratch / "cache"),
                "ACCESS_LINK_HUMAN_PROFILE": plan["profile"],
                "ACCESS_LINK_HUMAN_TEST_ID": test_id,
                "ACCESS_LINK_HUMAN_STEP_ID": step["id"],
                "ACCESS_LINK_HUMAN_LANGUAGE": "en",
                "ACCESS_LINK_HUMAN_PURPOSE": ENGLISH[step["purposeKey"]],
                "ACCESS_LINK_HUMAN_TASK": ENGLISH[step["actionKey"]],
                "ACCESS_LINK_HUMAN_EXPECTED": ENGLISH[step["expectedKey"]],
                # Native search and replacement do not use a language server.
                "ACCESS_LINK_HUMAN_DRY_RUN": "1",
                "NAL_SOCKET_TEST_RUNTIME": (ROOT / "neovim-plugin").as_posix(),
            }
            if pyright or linter or lazy:
                env.update(
                    ACCESS_LINK_HUMAN_DRY_RUN="0",
                    ACCESS_LINK_HUMAN_PLUGIN=(ROOT / "neovim-plugin").as_posix(),
                    ACCESS_LINK_HUMAN_DEPENDENCIES=(HUMAN / "dependencies.json").as_posix(),
                )
            if pyright:
                shutil.copyfile(HUMAN / "fixtures" / "pyrightconfig.json", fixture / "pyrightconfig.json")
                env["ACCESS_LINK_HUMAN_PYRIGHT"] = pyright.as_posix()
            if linter:
                env[LINTER_ENV[plan["profile"]]] = linter.as_posix()
                if config := LINTER_CONFIG.get(plan["profile"]):
                    shutil.copyfile(HUMAN / "fixtures" / config, fixture / config)
            if lazy:
                base = scratch / "lazy-source"
                subprocess.run(("git", "init", "--quiet", "--initial-branch=main", str(base)), check=True, timeout=10)
                shutil.copyfile(HUMAN / "fixtures" / "lazy-plugin-b.lua", base / "fixture.lua")
                subprocess.run((
                    "git", "-C", str(base), "-c", "core.autocrlf=false", "add", "fixture.lua",
                ), check=True, timeout=10)
                subprocess.run((
                    "git", "-C", str(base), "-c", "user.name=Access Link Test",
                    "-c", "user.email=human-test.invalid", "-c", "commit.gpgSign=false",
                    "commit", "--quiet", "-m", "Lazy window fixture",
                ), check=True, timeout=10)
                revision = subprocess.check_output(("git", "-C", str(base), "rev-parse", "HEAD"), text=True).strip()
                plugin_root = scratch / "lazy-plugins"
                plugin_root.mkdir()
                specifications = []
                for name in LAZY_PLUGIN_NAMES:
                    origin = scratch / f"{name}.git"
                    subprocess.run(("git", "clone", "--quiet", "--bare", str(base), str(origin)),
                                   check=True, timeout=10)
                    subprocess.run(("git", "clone", "--quiet", str(origin), str(plugin_root / name)),
                                   check=True, timeout=10)
                    specifications.append({"name": name, "url": origin.as_posix(), "expectedRevision": revision})
                configuration = scratch / "lazy-fixture.json"
                configuration.write_text(json.dumps({
                    "schemaVersion": 1,
                    "root": str(plugin_root),
                    "lockfile": str(scratch / "lazy-lock.json"),
                    "plugins": specifications,
                }), encoding="utf-8")
                env["ACCESS_LINK_HUMAN_LAZY_FIXTURE"] = str(configuration)
            app_data_name = "nvim-data" if os.name == "nt" else "nvim"
            pack = scratch / "data" / app_data_name / "site" / "pack" / "core" / "opt"
            for key, (checkout, name) in plugins.items():
                source_checkout = checkout.resolve(strict=True)
                destination = pack / name
                subprocess.run((
                    "git", "clone", "--no-hardlinks", "--quiet", str(source_checkout), str(destination),
                ), check=True, timeout=30)
                revision = subprocess.check_output(
                    ("git", "-C", str(destination), "rev-parse", "HEAD"), text=True,
                ).strip()
                self.assertEqual(DEPENDENCIES["plugins"][key]["revision"], revision)
                subprocess.run((
                    "git", "-C", str(destination), "remote", "set-url", "origin",
                    DEPENDENCIES["plugins"][key]["source"],
                ), check=True, timeout=10)
            arguments = [
                "--cmd", "lua vim.opt.runtimepath:prepend(vim.env.NAL_SOCKET_TEST_RUNTIME)",
                "-u", str(HUMAN / "framework" / "init.lua"), names[0],
            ]
            with open_editor(scratch, env, arguments, cwd=fixture) as (editor, session):
                with self.capture_guided_input(session) as capture:
                    yield editor, fixture, original, capture

    def pinned_pyright(self) -> Path:
        if not (configured := os.environ.get("NAL_GUIDED_PYRIGHT")):
            self.skipTest("set NAL_GUIDED_PYRIGHT to the pinned Pyright langserver.index.js")
        executable = Path(configured).resolve(strict=True)
        package = json.loads((executable.parent / "package.json").read_text(encoding="utf-8"))
        self.assertEqual("pyright", package["name"])
        self.assertEqual(DEPENDENCIES["tools"]["pyright"], package["version"])
        self.assertEqual("langserver.index.js", executable.name)
        self.assertIsNotNone(shutil.which("node"))
        return executable

    def wait_for_pyright(self, endpoint: tuple[str, int], *, attached: bool = True) -> None:
        deadline = time.monotonic() + 30
        while request(endpoint, "nvim_exec_lua", [
            "return vim.iter(vim.lsp.get_clients({bufnr = 0, name = 'pyright'}))"
            ":any(function(client) return client.initialized end)", [],
        ]) is not attached:
            self.assertLess(time.monotonic(), deadline, f"Pyright attached state did not become {attached}")
            time.sleep(0.05)

    @contextmanager
    def capture_guided_input(self, session: dict):
        endpoint = (session["host"], session["port"])
        events = queue.Queue()
        states = queue.Queue()
        client = LocalTcpClient(*endpoint, events.put, states.put, session_nonce=session["sessionNonce"])
        observed: list[dict] = []

        def read_through(event_type: str | tuple[str, ...], *, message_contains: str | None = None,
                         fields=None) -> dict:
            event_types = (event_type,) if isinstance(event_type, str) else event_type
            deadline = time.monotonic() + 6
            while (remaining := deadline - time.monotonic()) > 0:
                try:
                    event = events.get(timeout=remaining)
                except queue.Empty:
                    break
                observed.append(event)
                payload = event["payload"]
                if (
                    event["type"] in event_types
                    and (message_contains is None or message_contains in payload.get("message", ""))
                    and all(payload.get(key) == value for key, value in (fields or {}).items())
                ):
                    return payload
            event_summary = [
                (event["type"], event["payload"].get("reason"), event["payload"].get("message"),
                 {key: event["payload"].get(key) for key in fields or {}})
                for event in observed
            ]
            self.fail(f"Missing {event_type} {message_contains!r} {fields!r}; received {event_summary!r}")

        def press(key: str) -> None:
            self.assertGreater(request(endpoint, "nvim_input", [key]), 0, key)

        client.start()
        try:
            self.assertEqual("connecting", states.get(timeout=6))
            self.assertEqual("connected", states.get(timeout=6))
            read_through("fullState")
            observed.clear()
            yield endpoint, press, read_through, observed
        finally:
            client.stop()

    def verify_guided_l6(self, *, remove_matches_from_second_buffer: bool) -> None:
        incomplete = remove_matches_from_second_buffer
        with self.open_guided_editor(
            "L6", remove_matches_from_second_buffer=incomplete,
        ) as (editor, fixture, original, (endpoint, press, read_through, observed)):
            press("<F3>")
            summary = read_through("replacementPerformed")
            expected_count = 1 if incomplete else 2
            self.assertEqual("buffers", summary["replacementScope"])
            self.assertEqual(expected_count, summary["changedBufferCount"])
            self.assertEqual(expected_count, summary["modifiedBufferCount"])
            self.assertTrue(
                {"contextChanged", "cursorMoved", "textChanged"}.isdisjoint(
                    event["type"] for event in observed
                ),
                observed,
            )
            for index, (name, data) in enumerate(original.items()):
                expected = data.decode("utf-8").replace("calculate_tip", "calculate_tip_buffered")
                buffer_id = request(endpoint, "nvim_call_function", ["bufnr", [name]])
                self.assertGreater(buffer_id, 0)
                self.assertEqual(
                    expected.splitlines(), request(endpoint, "nvim_buf_get_lines", [buffer_id, 0, -1, True]),
                )
                self.assertEqual(not incomplete or index == 0,
                                 request(endpoint, "nvim_buf_get_option", [buffer_id, "modified"]))
                self.assertEqual(data, (fixture / name).read_bytes(), f"{name} was saved")

            press("<F4>")
            if incomplete:
                read_through("messageReceived", message_contains="replacement is not fully visible")
            else:
                read_through("messageReceived", message_contains=(
                    f"1 of 2, {FIXTURE_NAMES[0]}: 2 occurrences of calculate_tip_buffered"
                ))
                press("<F4>")
                read_through("messageReceived", message_contains=(
                    f"2 of 2, {FIXTURE_NAMES[1]}: 2 occurrences of calculate_tip_buffered"
                ))
            # A distinct final notification on the real channel delimits the
            # observed messages before quitting. It is not a workflow result.
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided L6 capture complete')", []])
            read_through("messageReceived", message_contains="Guided L6 capture complete")
            types = [event["type"] for event in observed]
            self.assertEqual(1, types.count("replacementPerformed"), observed)
            self.assertEqual(2 if incomplete else 3, types.count("messageReceived"), observed)
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))
            for name, data in original.items():
                self.assertEqual(data, (fixture / name).read_bytes(), f"{name} was saved on exit")

    def test_guided_l4_search_quickfix_and_confirmed_replacement(self) -> None:
        with self.open_guided_editor(
            "L4",
        ) as (editor, fixture, original, (endpoint, press, read_through, observed)):
            pattern = "calculate_tip"
            press("/" + pattern)
            preview = read_through("searchMatchChanged", fields={"searchPattern": pattern, "searchPreview": True})
            self.assertEqual(2, preview["matchCount"])
            press("<CR>")
            first = read_through("searchMatchChanged", fields={"searchPattern": pattern, "searchPreview": False})
            press("n")
            second = read_through("searchMatchChanged", fields={"searchPattern": pattern, "searchDirection": "next"})
            self.assertNotEqual(first["matchLine"], second["matchLine"])

            press("<F3>")
            result = read_through("resultListChanged")
            expected = sorted(
                (name, line_number, line.index(pattern) + 1)
                for name, data in original.items()
                for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1)
                if pattern in line
            )
            self.assertEqual(len(expected), result["itemCount"])
            items = request(endpoint, "nvim_exec_lua", [
                "return vim.tbl_map(function(q) return {"
                "vim.fs.basename(vim.api.nvim_buf_get_name(q.bufnr)), q.lnum, q.col"
                "} end, vim.fn.getqflist())", [],
            ])
            self.assertEqual(expected, sorted(tuple(item) for item in items))

            for key, indexes, boundary in (
                ("<F4>", [2, 3, 4], "Already at the last Quickfix result."),
                ("<F5>", [3, 2, 1], "Already at the first Quickfix result."),
            ):
                for index in indexes:
                    press(key)
                    deadline = time.monotonic() + 3
                    while request(endpoint, "nvim_call_function", ["getqflist", [{"idx": 0}]])["idx"] != index:
                        self.assertLess(time.monotonic(), deadline, f"{key} did not select Quickfix item {index}")
                        time.sleep(0.02)
                press(key)
                read_through("messageReceived", message_contains=boundary)
                self.assertEqual(indexes[-1], request(endpoint, "nvim_call_function", [
                    "getqflist", [{"idx": 0}],
                ])["idx"])

            observed.clear()
            press("<F6>")
            for answer, (name, line_number, column) in zip(("y", "n", "a"), expected, strict=False):
                prompt = read_through("promptOpened", fields={"promptKind": "confirmSub"})
                self.assertEqual(name, Path(prompt["bufferName"]).name)
                self.assertEqual(line_number, prompt["cursor"]["line"])
                self.assertEqual(column - 1, prompt["cursor"]["byteColumn"])
                self.assertIn(pattern, prompt["lineText"])
                press(answer)
                read_through("promptClosed", fields={"promptKind": "confirmSub", "answered": True})
            summary = read_through("replacementPerformed")
            self.assertEqual(2, summary["changedBufferCount"])
            self.assertEqual(2, summary["modifiedBufferCount"])

            for name, data in original.items():
                expected_lines = data.decode("utf-8").splitlines()
                for target_name, line_number, column in expected:
                    if target_name == name and (target_name, line_number, column) != expected[1]:
                        source_line = expected_lines[line_number - 1]
                        expected_lines[line_number - 1] = source_line.replace(pattern, "calculate_tip_checked")
                buffer_id = request(endpoint, "nvim_call_function", ["bufnr", [name]])
                self.assertGreater(buffer_id, 0)
                self.assertEqual(
                    expected_lines, request(endpoint, "nvim_buf_get_lines", [buffer_id, 0, -1, True]),
                )
                self.assertTrue(request(endpoint, "nvim_buf_get_option", [buffer_id, "modified"]))
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided L4 capture complete')", []])
            read_through("messageReceived", message_contains="Guided L4 capture complete")
            events = [event["type"] for event in observed]
            self.assertEqual(3, events.count("promptOpened"), events)
            self.assertEqual(3, events.count("promptClosed"), events)
            self.assertEqual(1, events.count("replacementPerformed"), events)
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))
            for name, data in original.items():
                self.assertEqual(data, (fixture / name).read_bytes(), f"{name} was saved on exit")

    def test_guided_l1_reports_only_attached_pyright(self) -> None:
        with self.open_guided_editor(
            "L1", pyright=self.pinned_pyright(),
        ) as (editor, _, _, (endpoint, press, read_through, _)):
            self.wait_for_pyright(endpoint)
            press("<F3>")
            live = read_through("lspStatus")
            self.assertEqual(["pyright"], live["clients"])
            self.assertEqual(1, live["clientCount"])
            request(endpoint, "nvim_exec_lua", ["vim.lsp.enable('pyright', false)", []])
            self.wait_for_pyright(endpoint, attached=False)
            press("<F3>")
            stopped = read_through("lspStatus")
            self.assertEqual(0, stopped["clientCount"])
            self.assertFalse(stopped["clients"])
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))

    def test_guided_l5_renames_with_pinned_pyright(self) -> None:
        with self.open_guided_editor(
            "L5", pyright=self.pinned_pyright(),
        ) as (editor, fixture, original, (endpoint, press, read_through, observed)):
            self.wait_for_pyright(endpoint)
            initial = request(endpoint, "nvim_call_function", ["bufnr", ["%"]])
            position = request(endpoint, "nvim_win_get_cursor", [0])
            line = original[FIXTURE_NAMES[0]].decode("utf-8").splitlines()[position[0] - 1]
            self.assertEqual("calculate_tip", line[position[1]:][:len("calculate_tip")])
            press("<F3>")
            prompt = read_through("promptOpened", fields={"promptKind": "input"})
            self.assertFalse(prompt["defaultValuePresent"])
            # Check the rename transaction after the real prompt is ready.
            observed.clear()
            press("calculate_gratuity<CR>")
            read_through("promptClosed", fields={"promptKind": "input", "accepted": True})
            result = read_through("lspRenameCompleted", fields={"renameResult": "changesObserved"})
            self.assertEqual(2, result["changedBufferCount"])
            self.assertEqual(2, result["modifiedBufferCount"])
            self.assertTrue(
                {"contextChanged", "cursorMoved", "bufferChanged", "textChanged"}.isdisjoint(
                    event["type"] for event in observed
                ),
                [event["type"] for event in observed],
            )
            for index in (1, 2):
                press("<F4>")
                message = read_through("messageReceived", message_contains=f"Renamed reference {index} of 2")
                self.assertIn("calculate_gratuity", message["message"])
                self.assertEqual(initial, request(endpoint, "nvim_call_function", ["bufnr", ["%"]]))
            for name, data in original.items():
                buffer_id = request(endpoint, "nvim_call_function", ["bufnr", [name]])
                expected = data.decode("utf-8").replace("calculate_tip", "calculate_gratuity").splitlines()
                self.assertEqual(expected, request(endpoint, "nvim_buf_get_lines", [buffer_id, 0, -1, True]))
                self.assertTrue(request(endpoint, "nvim_buf_get_option", [buffer_id, "modified"]))
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided L5 capture complete')", []])
            read_through("messageReceived", message_contains="Guided L5 capture complete")
            self.assertEqual(1, sum(event["type"] == "lspRenameCompleted" for event in observed))
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))
            for name, data in original.items():
                self.assertEqual(data, (fixture / name).read_bytes(), f"{name} was saved on exit")

    def test_guided_l2_follows_real_signature_help(self) -> None:
        with self.open_guided_editor(
            "L2", pyright=self.pinned_pyright(),
        ) as (editor, _, _, (endpoint, press, read_through, observed)):
            self.wait_for_pyright(endpoint)
            request(endpoint, "nvim_exec_lua", [
                "vim.g.guided_signatures_completed = 0;"
                "vim.api.nvim_create_autocmd('LspRequest', {callback = function(event)"
                " local req = event.data.request;"
                " if req.method == 'textDocument/signatureHelp' and req.type == 'complete' then"
                " vim.g.guided_signatures_completed = vim.g.guided_signatures_completed + 1 end end})", [],
            ])
            press("<F3>")
            for keys, index, name in (("", 1, "price"), ("3.5, ", 2, "quantity"), ("2, ", 3, "discount")):
                if keys:
                    press(keys)
                hint = read_through("activeParameterChanged", fields={"activeParameter": index})
                self.assertEqual("calculate_total", hint["callName"])
                self.assertTrue(hint["parameter"].startswith(name + ":"), hint)

            def move_after_provider_response(key: str) -> int:
                completed = request(endpoint, "nvim_get_var", ["guided_signatures_completed"])
                press(key)
                deadline = time.monotonic() + 4
                while request(endpoint, "nvim_get_var", ["guided_signatures_completed"]) <= completed:
                    self.assertLess(time.monotonic(), deadline, f"No real signature response for {key}")
                    time.sleep(0.02)
                return request(endpoint, "nvim_win_get_cursor", [0])[1]

            cursor = move_after_provider_response("0.1")
            line = request(endpoint, "nvim_get_current_line", [])
            self.assertIn("calculate_total(3.5, 2, 0.1)", line)
            first_argument = line.index("3.5")
            # Word navigation may stop at the decimal point and commas.
            for _ in range(len("3.5, 2, 0.1")):
                if cursor < first_argument + 3:
                    break
                previous = cursor
                cursor = move_after_provider_response("<C-Left>")
                self.assertLess(cursor, previous)
            self.assertIn(cursor, range(first_argument, first_argument + 3), (line, cursor))
            read_through("activeParameterChanged", fields={"activeParameter": 1})
            if cursor == first_argument:
                cursor = move_after_provider_response("<Right>")
            observed.clear()
            for key, expected_column in (("<Left>", cursor - 1), ("<Right>", cursor)):
                self.assertEqual(expected_column, move_after_provider_response(key))
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided L2 capture complete')", []])
            read_through("messageReceived", message_contains="Guided L2 capture complete")
            self.assertNotIn("activeParameterChanged", [event["type"] for event in observed])
            press("<Esc><F10>")
            self.assertEqual(0, editor.wait(timeout=6))

    def test_guided_c1_navigates_and_accepts_native_pyright_completion(self) -> None:
        with self.open_guided_editor(
            "C1", pyright=self.pinned_pyright(),
        ) as (editor, _, _, (endpoint, press, read_through, observed)):
            self.wait_for_pyright(endpoint)
            press("<F3>")
            read_through("modeChanged", fields={"mode": "insert"})
            original = request(endpoint, "nvim_get_current_line", [])
            press("<C-n>")
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided C1 pre-menu check')", []])
            read_through("messageReceived", message_contains="Guided C1 pre-menu check")
            self.assertEqual(original, request(endpoint, "nvim_get_current_line", []))
            self.assertEqual(0, request(endpoint, "nvim_call_function", ["pumvisible", []]))
            self.assertNotIn("menuOpened", [event["type"] for event in observed])

            press("<F5>")
            opened = read_through("menuOpened")
            actual_items = request(endpoint, "nvim_call_function", ["complete_info", [["items"]]])["items"]
            labels = [item["abbr"] or item["word"] for item in actual_items]
            self.assertEqual({"calculate_total", "calculate_tax", "calculate_tip"}, set(labels))
            self.assertEqual(3, opened["itemCount"])
            for index, label in enumerate(labels, start=1):
                press("<C-n>")
                selected = read_through("menuSelectionChanged")
                self.assertEqual((index, label), (selected["itemIndex"], selected["item"]["label"]))
            press("<C-n>")
            read_through("menuSelectionCleared")
            self.assertEqual(-1, request(endpoint, "nvim_call_function", ["complete_info", [["selected"]]])["selected"])
            press("<C-p>")
            selected = read_through("menuSelectionChanged")
            self.assertEqual((3, labels[-1]), (selected["itemIndex"], selected["item"]["label"]))
            press("<C-y>")
            read_through("menuClosed")
            line = request(endpoint, "nvim_get_current_line", [])
            self.assertEqual(f"completion_probe = {labels[-1]}()", line)
            self.assertEqual(line.index(")"), request(endpoint, "nvim_win_get_cursor", [0])[1])
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided C1 capture complete')", []])
            read_through("messageReceived", message_contains="Guided C1 capture complete")
            emitted = [event["type"] for event in observed]
            self.assertEqual(1, emitted.count("menuOpened"), emitted)
            self.assertEqual(1, emitted.count("menuClosed"), emitted)
            press("<Esc><F10>")
            self.assertEqual(0, editor.wait(timeout=6))
    def test_guided_d1_navigates_real_ruff_diagnostics(self) -> None:
        if not os.environ.get("NAL_GUIDED_NVIM_LINT"):
            self.skipTest("set NAL_GUIDED_NVIM_LINT to the pinned nvim-lint checkout")
        ruff_path = shutil.which("ruff")
        self.assertIsNotNone(ruff_path)
        version = subprocess.check_output((ruff_path, "--version"), text=True).strip()
        self.assertEqual("ruff " + DEPENDENCIES["tools"]["ruff"], version)
        with self.open_guided_editor(
            "D1", pyright=self.pinned_pyright(), linter=Path(ruff_path),
        ) as (editor, fixture, original, (endpoint, press, read_through, observed)):
            self.wait_for_pyright(endpoint)
            press("<F6>")
            read_through("messageReceived", message_contains="Diagnostics ready")
            direct = subprocess.run(
                (ruff_path, "check", "--isolated", "--output-format=json", "diagnostics.py"),
                cwd=fixture, check=False, capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            self.assertEqual(1, direct.returncode)
            expected_ruff = sorted(
                (item["code"], item["location"]["row"], item["location"]["column"] - 1)
                for item in json.loads(direct.stdout)
            )
            diagnostics = request(endpoint, "nvim_exec_lua", [
                "return vim.tbl_map(function(d)"
                " return {d.source, tostring(d.code), d.lnum + 1, d.col, d.message} end, vim.diagnostic.get(0))", [],
            ])
            self.assertEqual(expected_ruff, sorted(
                (code, line, column) for source, code, line, column, _ in diagnostics if source.casefold() == "ruff"
            ))
            observed.clear()

            press("<F7>")
            first = read_through("diagnosticMoved")["diagnostic"]
            self.assertEqual(("F401", 1, len(diagnostics)), (first["code"], first["index"], first["count"]))
            reached = {(
                first["source"].casefold(), first["code"], first["message"],
            )}
            for index in range(2, len(diagnostics) + 1):
                press("<F9>")
                payload = read_through("diagnosticMoved")
                self.assertEqual(index, payload["diagnostic"]["index"])
                item = payload["diagnostic"]
                reached.add((item["source"].casefold(), item["code"], item["message"]))
                self.assertEqual(payload["cursor"]["line"], request(endpoint, "nvim_win_get_cursor", [0])[0])
            self.assertEqual({(source.casefold(), code, message) for source, code, _, _, message in diagnostics}, reached)
            press("<F9>")
            self.assertEqual(1, read_through("diagnosticMoved")["diagnostic"]["index"])
            press("<F8>")
            last = read_through("diagnosticMoved")["diagnostic"]
            self.assertEqual(("F821", len(diagnostics)), (last["code"], last["index"]))
            press("<F5>")
            read_through("diagnosticMoved", fields={"diagnostic": None})
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided D1 capture complete')", []])
            read_through("messageReceived", message_contains="Guided D1 capture complete")
            self.assertEqual(len(diagnostics) + 3, sum(event["type"] == "diagnosticMoved" for event in observed))
            self.assertEqual(2, request(endpoint, "nvim_win_get_cursor", [0])[0])
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))
            self.assertEqual(original["diagnostics.py"], (fixture / "diagnostics.py").read_bytes())

    def test_guided_d3_clang_tidy_reports_and_wraps_real_errors(self) -> None:
        tool = self.external_linter("NAL_GUIDED_CLANG_TIDY")
        version = subprocess.check_output((str(tool), "--version"), text=True)
        self.assertIn("version " + DEPENDENCIES["tools"]["clangTidy"], version)
        with self.open_guided_editor("D3", linter=tool) as (editor, fixture, original, capture):
            endpoint, press, read_through, observed = capture
            press("<F2>")
            instruction = read_through("messageReceived", message_contains="Test ID D3.")["message"]
            self.assertTrue(instruction.startswith("Test ID D3."))
            self.assertIn("Diagnostics ready", instruction)
            press("<F6>")
            read_through("messageReceived", message_contains="Diagnostics ready")
            probe = subprocess.run(
                (str(tool), "--quiet", "--config-file=.clang-tidy", "diagnostics.c", "--", "-std=c11"),
                cwd=fixture, check=False, capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            self.assertNotEqual(0, probe.returncode)
            errors = re.findall(
                r"diagnostics\.c:(\d+):(\d+): error:.*?\b(missing_first|missing_second)\b",
                probe.stdout + probe.stderr,
            )
            self.assertEqual(["missing_first", "missing_second"], [row[2] for row in errors])
            observed.clear()
            for key, index in (("<F7>", 1), ("<F9>", 2), ("<F9>", 1), ("<F8>", 2)):
                press(key)
                event = read_through("diagnosticMoved")
                diagnostic = event["diagnostic"]
                line, column, identifier = errors[index - 1]
                self.assertEqual((index, 2), (diagnostic["index"], diagnostic["count"]))
                self.assertEqual("clang-diagnostic-error", diagnostic["code"])
                self.assertEqual("error", diagnostic["severity"])
                self.assertIn(identifier, diagnostic["message"])
                self.assertEqual([int(line), int(column) - 1],
                                 request(endpoint, "nvim_win_get_cursor", [0]))
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided D3 capture complete')", []])
            read_through("messageReceived", message_contains="Guided D3 capture complete")
            self.assertEqual(4, sum(event["type"] == "diagnosticMoved" for event in observed))
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))
            self.assertEqual(original["diagnostics.c"], (fixture / "diagnostics.c").read_bytes())

    def external_linter(self, variable: str) -> Path:
        if not os.environ.get("NAL_GUIDED_NVIM_LINT"):
            self.skipTest("set NAL_GUIDED_NVIM_LINT to the pinned nvim-lint checkout")
        if not (path := os.environ.get(variable)):
            self.skipTest(f"set {variable} to the pinned linter executable")
        return Path(path).resolve(strict=True)

    def test_guided_d4_markdownlint_reports_without_editing(self) -> None:
        tool = self.external_linter("NAL_GUIDED_MARKDOWNLINT")
        with self.open_guided_editor("D4", linter=tool) as (editor, fixture, original, capture):
            endpoint, press, read_through, observed = capture
            press("<F6>")
            read_through("messageReceived", message_contains="Diagnostics ready")
            probe = subprocess.run(
                (str(tool), "--config", ".markdownlint.json", "diagnostics.md"),
                cwd=fixture, check=False, capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            self.assertEqual(1, probe.returncode)
            self.assertIn("markdownlint-cli2 v" + DEPENDENCIES["tools"]["markdownlintCli2"],
                          probe.stdout + probe.stderr)
            matches = re.findall(r"diagnostics\.md:(\d+)(?::\d+)?\s+error MD025\b", probe.stdout + probe.stderr)
            self.assertEqual(["3"], matches)
            self.assertEqual(
                original["diagnostics.md"].decode("utf-8").splitlines(),
                request(endpoint, "nvim_buf_get_lines", [0, 0, -1, True]),
            )
            self.assertFalse(request(endpoint, "nvim_buf_get_option", [0, "modified"]))
            observed.clear()
            for key in ("<F7>", "<F9>"):
                press(key)
                payload = read_through("diagnosticMoved")
                diagnostic = payload["diagnostic"]
                self.assertRegex(diagnostic["message"], r"\bMD025\b")
                self.assertEqual("warning", diagnostic["severity"])
                self.assertEqual((1, 1), (diagnostic["index"], diagnostic["count"]))
                self.assertEqual(3, payload["cursor"]["line"])
                self.assertEqual(3, request(endpoint, "nvim_win_get_cursor", [0])[0])
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided D4 capture complete')", []])
            read_through("messageReceived", message_contains="Guided D4 capture complete")
            self.assertEqual(2, sum(event["type"] == "diagnosticMoved" for event in observed))
            press("<F10>")
            self.assertEqual(0, editor.wait(timeout=6))
            self.assertEqual(original["diagnostics.md"], (fixture / "diagnostics.md").read_bytes())

    def test_guided_p1_renders_and_navigates_actual_lazy_window(self) -> None:
        if not (configured := os.environ.get("NAL_GUIDED_LAZY")):
            self.skipTest("set NAL_GUIDED_LAZY to the pinned lazy.nvim checkout")
        lazy = Path(configured).resolve(strict=True)
        with self.open_guided_editor("P1", lazy=lazy) as (editor, _, _, capture):
            endpoint, press, read_through, _ = capture
            buffer_number = "return vim.api.nvim_get_current_buf()"
            original = request(endpoint, "nvim_exec_lua", [buffer_number, []])
            with socket.create_connection(endpoint, timeout=2) as ui:
                ui.sendall(msgpack.packb([0, 1, "nvim_ui_attach", [126, 40, {"ext_linegrid": True}]]))
                redraws = msgpack.Unpacker(raw=False, max_buffer_size=262_144)

                def see_grid(text: str) -> None:
                    deadline = time.monotonic() + 6
                    while (remaining := deadline - time.monotonic()) > 0:
                        for message in redraws:
                            if message[:2] == [1, 1]:
                                self.assertIsNone(message[2])
                            if message[:2] != [2, "redraw"]:
                                continue
                            for name, *updates in message[2]:
                                if name == "grid_line":
                                    for _, _, _, cells, *_ in updates:
                                        line = "".join(cell[0] * (cell[2] if len(cell) > 2 else 1) for cell in cells)
                                        if text in line:
                                            return
                        ui.settimeout(remaining)
                        try:
                            packet = ui.recv(65536)
                        except TimeoutError:
                            break
                        self.assertTrue(packet, f"Neovim UI disconnected while waiting for {text!r}")
                        redraws.feed(packet)
                    self.fail(f"Missing {text!r} in Neovim UI grid updates")

                marker = "This buffer belongs to the isolated lazy.nvim guided test."
                see_grid(marker)
                press("<F3>")
                see_grid("Install (I)")
                buffer_id = request(endpoint, "nvim_exec_lua", [buffer_number, []])
                self.assertNotEqual(original, buffer_id)
                lines = request(endpoint, "nvim_buf_get_lines", [buffer_id, 0, -1, True])
                row_events = ("cursorMoved", "lineChanged", "textChanged", "contextChanged")
                rendered = [line.strip() for line in lines]
                overview = " ".join(takewhile(bool, dropwhile(lambda line: not line, rendered)))
                self.assertIn("Install (I)", overview)
                self.assertIn("Help (?)", overview)
                read_through(row_events, fields={"filetype": "lazy", "pluginManagerOverview": overview})

                names = LAZY_PLUGIN_NAMES
                for name in names:
                    self.assertTrue(any(name in line for line in lines), lines)
                rows = [next(i for i, line in enumerate(lines, 1) if name in line) for name in names]
                cursor = request(endpoint, "nvim_win_get_cursor", [0])
                self.assertLess(cursor[0], rows[0])
                gap = rows[1] - rows[0]
                self.assertGreater(gap, 0)
                for key, index in (("j" * (rows[0] - cursor[0]), 0), ("j" * gap, 1), ("k" * gap, 0)):
                    press(key)
                    row = read_through(row_events, fields={
                        "pluginManagerEntryExpanded": False, "lineText": lines[rows[index] - 1],
                    })
                    self.assertEqual(rows[index], row["cursor"]["line"])
                    self.assertEqual(rows[index], request(endpoint, "nvim_win_get_cursor", [0])[0])

                press("<CR>")
                see_grid("dir ")
                row = read_through(row_events, fields={"pluginManagerEntryExpanded": True})
                self.assertIn(names[0], row["lineText"])
                details = request(endpoint, "nvim_buf_get_lines", [buffer_id, rows[0], rows[0] + 1, True])
                self.assertRegex(details[0], r"^\s*dir\s+.*" + names[0])
                press("<CR>")
                row = read_through(row_events, fields={"pluginManagerEntryExpanded": False})
                self.assertIn(names[0], row["lineText"])
                self.assertEqual(lines, request(endpoint, "nvim_buf_get_lines", [buffer_id, 0, -1, True]))
                press("?")
                see_grid("Keyboard Shortcuts")
                press("?")
                see_grid(names[0])
                press("q")
                read_through("contextChanged", fields={"bufferId": original})
                self.assertEqual(original, request(endpoint, "nvim_exec_lua", [buffer_number, []]))
                press("<F10>")
                self.assertEqual(0, editor.wait(timeout=6))

    def test_guided_c2_uses_actual_nvim_cmp_lsp_menu(self) -> None:
        self.verify_plugin_completion(
            "C2", "require('cmp').visible()", "require('cmp').get_entries()", "item:get_completion_item().label",
        )

    def test_guided_c3_uses_actual_blink_lsp_menu(self) -> None:
        self.verify_plugin_completion(
            "C3", "require('blink.cmp').is_menu_visible()", "require('blink.cmp').get_items()", "item.label",
        )

    def verify_plugin_completion(self, test_id: str, visible: str, items: str, label: str) -> None:
        with self.open_guided_editor(test_id, pyright=self.pinned_pyright()) as (editor, _, _, capture):
            endpoint, press, read_through, observed = capture
            self.wait_for_pyright(endpoint)
            press("<F3>")
            read_through("modeChanged", fields={"mode": "insert"})
            original = request(endpoint, "nvim_get_current_line", [])
            press("<C-n>")
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided completion pre-menu check')", []])
            read_through("messageReceived", message_contains="Guided completion pre-menu check")
            self.assertEqual(original, request(endpoint, "nvim_get_current_line", []))
            self.assertFalse(request(endpoint, "nvim_exec_lua", ["return " + visible, []]))
            self.assertNotIn("menuOpened", [event["type"] for event in observed])

            press("<F5>")
            read_through("menuOpened")
            expected_labels = {"calculate_total", "calculate_tax", "calculate_tip"}
            deadline = time.monotonic() + 6
            while True:
                labels = request(endpoint, "nvim_exec_lua", [
                    f"return {visible} and vim.tbl_map(function(item) return {label} end, {items}) or {{}}", [],
                ])
                if len(labels) == len(expected_labels) and set(labels) == expected_labels:
                    break
                self.assertLess(time.monotonic(), deadline, f"Provider never displayed the expected choices: {labels}")
                time.sleep(0.02)
            for index, expected in enumerate(labels, start=1):
                press("<C-n>")
                selected = read_through("menuSelectionChanged")
                self.assertEqual((index, expected), (selected["itemIndex"], selected["item"]["label"]))
            press("<C-p>")
            selected = read_through("menuSelectionChanged")
            self.assertEqual((2, labels[1]), (selected["itemIndex"], selected["item"]["label"]))
            tick = request(endpoint, "nvim_buf_get_changedtick", [0])
            press("<C-y>")
            read_through("menuClosed")
            # Blink closes its menu before resolving and applying the selected LSP item.
            deadline = time.monotonic() + 6
            while request(endpoint, "nvim_buf_get_changedtick", [0]) == tick:
                self.assertLess(time.monotonic(), deadline, "Completion closed without editing the buffer")
                time.sleep(0.02)
            line = request(endpoint, "nvim_get_current_line", [])
            self.assertEqual(f"completion_probe = {labels[1]}()", line)
            self.assertEqual(line.index(")"), request(endpoint, "nvim_win_get_cursor", [0])[1])
            request(endpoint, "nvim_exec_lua", ["vim.notify('Guided completion capture complete')", []])
            read_through("messageReceived", message_contains="Guided completion capture complete")
            emitted = [event["type"] for event in observed]
            self.assertEqual(1, emitted.count("menuOpened"), emitted)
            self.assertEqual(1, emitted.count("menuClosed"), emitted)
            press("<Esc><F10>")
            self.assertEqual(0, editor.wait(timeout=6))
