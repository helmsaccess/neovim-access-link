from __future__ import annotations

import os
import json
import pathlib
import subprocess
import tempfile
import threading
import time
import unittest
import pexpect

from nvim_nvda_bridge import Bridge
from nvim_nvda_protocol import LocalTcpClient


class RecordingTransport:
	"""Record semantic bridge output without reintroducing the removed TCP protocol."""

	def __init__(self) -> None:
		self.events: list[dict] = []
		self.condition = threading.Condition()

	def start(self) -> None:
		pass

	def stop(self) -> None:
		pass

	def publish(self, event_type: str, payload: dict) -> bool:
		with self.condition:
			self.events.append({"type": event_type, "payload": payload})
			self.condition.notify_all()
		return True


class NvimBridgeTests(unittest.TestCase):
	def test_clipboard_control_uses_only_fixed_plugin_entry_points(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		state = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"changedtick": 4,
			"modeRaw": "n",
			"requestId": 5,
		}
		bridge._on_client_control("copyTextRequest", {**state, "source": "yankRegister"})
		bridge._on_client_control("pasteTextRequest", {**state, "text": "remote text"})
		bridge._on_client_control("setRegisterRequest", {**state, "text": "current register"})
		bridge._on_client_control("pasteTextRequest", {**state, "text": "bad\0text"})
		self.assertEqual(3, len(notifications))
		self.assertTrue(all(method == "nvim_exec_lua" for method, _ in notifications))
		self.assertIn("request_copy_text", notifications[0][1][0])
		self.assertIn("request_paste_text", notifications[1][1][0])
		self.assertIn("request_set_register", notifications[2][1][0])

	def test_terminal_control_uses_only_its_fixed_plugin_entry_point(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		state = {
			"bufferId": 1,
			"windowId": 2,
			"tabpageId": 3,
			"modeRaw": "t",
			"requestId": 5,
		}
		bridge._on_client_control("leaveTerminalInputRequest", state)
		bridge._on_client_control("leaveTerminalInputRequest", {**state, "modeRaw": "n"})
		self.assertEqual(1, len(notifications))
		self.assertEqual("nvim_exec_lua", notifications[0][0])
		self.assertIn("request_leave_terminal_input", notifications[0][1][0])

	def test_exploration_uses_only_fixed_bounded_plugin_entry_points(self) -> None:
		notifications = []
		bridge = Bridge.__new__(Bridge)
		bridge.nvim = type(
			"Nvim",
			(),
			{
				"notify": lambda _self, method, *parameters: notifications.append((method, parameters)),
			},
		)()
		payload = {
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "lineDown",
			"count": 1,
			"bufferId": 3,
			"windowId": 4,
			"tabpageId": 5,
			"changedtick": 6,
			"modeRaw": "n",
			"cursorLine": 7,
			"cursorByteColumn": 0,
			"cursorVirtualColumn": 0,
		}
		bridge._on_client_control("exploreTextRequest", payload)
		bridge._on_client_control(
			"endExplorationRequest",
			{
				"requestId": 2,
				"explorationId": 2,
			},
		)
		bridge._on_client_control("exploreTextRequest", {**payload, "action": "arbitrary"})
		self.assertEqual(2, len(notifications))
		self.assertIn("request_explore_text", notifications[0][1][0])
		self.assertIn("request_end_exploration", notifications[1][1][0])

	def test_bridge_publishes_clipboard_text_once_but_never_caches_it(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge.transport = transport
		bridge._on_nvim_event(
			"copyTextResult",
			{
				"mode": "normal",
				"requestId": 9,
				"ok": True,
				"resultCode": "copied",
				"clipboardText": "private text",
			},
		)
		self.assertEqual("private text", transport.events[-1]["payload"]["clipboardText"])
		self.assertNotIn("clipboardText", bridge.full_state())
		self.assertNotIn("requestId", bridge.full_state())

	def test_bridge_publishes_valid_exploration_once_but_never_caches_it(self) -> None:
		transport = RecordingTransport()
		bridge = Bridge.__new__(Bridge)
		bridge._state_lock = threading.Lock()
		bridge._state = {}
		bridge.transport = transport
		result = {
			"mode": "normal",
			"requestId": 1,
			"explorationId": 2,
			"actionIndex": 1,
			"action": "wordNext",
			"unit": "word",
			"ok": True,
			"resultCode": "moved",
			"text": "beta",
			"line": 1,
			"byteColumn": 6,
			"characterColumn": 6,
			"virtualColumn": 6,
		}
		bridge._on_nvim_event("exploreTextResult", result)
		self.assertEqual("beta", transport.events[-1]["payload"]["text"])
		self.assertNotIn("text", bridge.full_state())
		self.assertNotIn("explorationId", bridge.full_state())
		bridge._on_nvim_event("exploreTextResult", {**result, "action": "arbitrary"})
		self.assertEqual(1, len(transport.events))

	def test_real_tui_f12_claim_preserves_normal_and_insert_input(self) -> None:
		root = pathlib.Path.cwd()
		with tempfile.TemporaryDirectory() as directory:
			nvim_socket = os.path.join(directory, "nvim.sock")
			runtime = os.path.join(directory, "runtime")
			os.mkdir(runtime)
			process = pexpect.spawn(
				"nvim",
				[
					"-n",
					"-u",
					"NONE",
					"-i",
					"NONE",
					"--cmd",
					f"set runtimepath^={root / 'neovim-plugin'}",
					"--cmd",
					"runtime plugin/nvim_nvda.lua",
					"--listen",
					nvim_socket,
				],
				env={**os.environ, "TERM": "xterm-256color", "XDG_RUNTIME_DIR": runtime},
				encoding=None,
				timeout=3,
			)
			self._wait_socket(nvim_socket, process)
			registry_directory = pathlib.Path(runtime) / "nvim-nvda" / "sessions"
			deadline = time.monotonic() + 3
			registry = None
			while time.monotonic() < deadline and registry is None:
				matches = list(registry_directory.glob("*.json"))
				registry = matches[0] if len(matches) == 1 else None
				time.sleep(0.02)
			self.assertIsNotNone(registry, "F12 test registry timeout")
			try:
				process.send(b"\x1b[24~")
				deadline = time.monotonic() + 3
				value = {}
				while time.monotonic() < deadline:
					value = json.loads(registry.read_text(encoding="utf-8"))
					if value.get("claimSequence") == 1:
						break
					time.sleep(0.02)
				self.assertEqual(1, value.get("claimSequence"))
				time.sleep(0.1)
				output = subprocess.run(
					["nvim", "--server", nvim_socket, "--remote-expr", "mode(1)"],
					check=True,
					capture_output=True,
					text=True,
				).stdout.strip()
				self.assertEqual("n", output)
				process.send(b"i")
				deadline = time.monotonic() + 2
				while time.monotonic() < deadline:
					output = subprocess.run(
						["nvim", "--server", nvim_socket, "--remote-expr", "mode(1)"],
						check=True,
						capture_output=True,
						text=True,
					).stdout.strip()
					if output == "i":
						break
					time.sleep(0.02)
				self.assertEqual("i", output)
				process.send(b"\x1b[24~")
				deadline = time.monotonic() + 3
				while time.monotonic() < deadline:
					value = json.loads(registry.read_text(encoding="utf-8"))
					if value.get("claimSequence") == 2:
						break
					time.sleep(0.02)
				self.assertEqual(2, value.get("claimSequence"))
				process.send(b"x")
				time.sleep(0.1)
				output = subprocess.run(
					[
						"nvim",
						"--server",
						nvim_socket,
						"--remote-expr",
						"mode(1) . ':' . getline(1)",
					],
					check=True,
					capture_output=True,
					text=True,
				).stdout.strip()
				self.assertEqual("i:x", output)
			finally:
				process.terminate(force=True)

	def test_local_windows_loopback_client_receives_state_and_exploration_result(self) -> None:
		root = pathlib.Path.cwd()
		with tempfile.TemporaryDirectory() as directory:
			environment = {
				**os.environ,
				"LOCALAPPDATA": directory,
				"NVIM_NVDA_TEST_WINDOWS": "1",
			}
			process = subprocess.Popen(
				[
					"nvim",
					"--headless",
					"-n",
					"-u",
					"NONE",
					"--noplugin",
					"-i",
					"NONE",
					"--cmd",
					f"set runtimepath^={root / 'neovim-plugin'}",
					"-c",
					"lua vim.api.nvim_buf_set_lines(0,0,-1,true,{'alpha, beta','xy','gamma'}); "
					"vim.api.nvim_win_set_cursor(0,{3,0})",
					"-c",
					"runtime plugin/nvim_nvda.lua",
				],
				env=environment,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
			)
			client = None
			try:
				sessions = pathlib.Path(directory) / "nvim-nvda" / "sessions"
				registry = None
				deadline = time.monotonic() + 5
				while time.monotonic() < deadline and registry is None:
					matches = list(sessions.glob(f"{process.pid}-*.json"))
					registry = matches[0] if len(matches) == 1 else None
					if process.poll() is not None:
						self.fail("local Windows Neovim exited before registry creation")
					time.sleep(0.02)
				self.assertIsNotNone(registry, "local Windows registry timeout")
				value = json.loads(registry.read_text(encoding="utf-8"))
				self.assertEqual(
					("localWindowsTcp", "127.0.0.1"),
					(
						value["transportKind"],
						value["host"],
					),
				)
				events, states = [], []
				condition = threading.Condition()

				def receive_event(event):
					with condition:
						events.append(event)
						condition.notify_all()

				def receive_state(state):
					with condition:
						states.append(state)
						condition.notify_all()

				client = LocalTcpClient(
					value["host"],
					value["port"],
					receive_event,
					receive_state,
					session_nonce=value["sessionNonce"],
				)
				client.start()
				self._wait(condition, lambda: any(event["type"] == "fullState" for event in events))
				self.assertIn("connected", states)
				full_state = next(event for event in events if event["type"] == "fullState")
				self.assertEqual("windows-loopback-tcp", full_state["payload"]["_transport"]["kind"])
				self._wait(
					condition,
					lambda: any(
						event["payload"].get("lineText") == "gamma"
						and event["payload"].get("cursor", {}).get("line") == 3
						for event in events
					),
				)
				state = next(
					event["payload"]
					for event in reversed(events)
					if event["payload"].get("lineText") == "gamma"
					and event["payload"].get("cursor", {}).get("line") == 3
				)
				origin = {
					"explorationId": 1,
					"action": "wordPrevious",
					"count": 1,
					"bufferId": state["bufferId"],
					"windowId": state["windowId"],
					"tabpageId": state["tabpageId"],
					"changedtick": state["changedtick"],
					"modeRaw": state["modeRaw"],
					"cursorLine": state["cursor"]["line"],
					"cursorByteColumn": state["cursor"]["byteColumn"],
					"cursorVirtualColumn": state["cursor"]["virtualColumn"],
				}
				self.assertTrue(
					client.send_control(
						"exploreTextRequest",
						{**origin, "requestId": 1, "actionIndex": 1},
					)
				)
				self._wait(condition, lambda: any(event["type"] == "exploreTextResult" for event in events))
				result = next(
					event
					for event in events
					if event["type"] == "exploreTextResult" and event["payload"]["requestId"] == 1
				)
				self.assertEqual(
					(1, 1, "word", "xy", 2, 0),
					(
						result["payload"]["requestId"],
						result["payload"]["explorationId"],
						result["payload"]["unit"],
						result["payload"]["text"],
						result["payload"]["line"],
						result["payload"]["byteColumn"],
					),
				)
				self.assertTrue(
					client.send_control(
						"exploreTextRequest",
						{**origin, "requestId": 2, "actionIndex": 2},
					)
				)
				self._wait(
					condition,
					lambda: any(
						event["type"] == "exploreTextResult" and event["payload"]["requestId"] == 2
						for event in events
					),
				)
				result = next(
					event
					for event in events
					if event["type"] == "exploreTextResult" and event["payload"]["requestId"] == 2
				)
				self.assertEqual(
					("word", "beta", 1, 7),
					(
						result["payload"]["unit"],
						result["payload"]["text"],
						result["payload"]["line"],
						result["payload"]["byteColumn"],
					),
				)
				self.assertTrue(
					client.send_control(
						"exploreTextRequest",
						{**origin, "requestId": 3, "actionIndex": 3},
					)
				)
				self._wait(
					condition,
					lambda: any(
						event["type"] == "exploreTextResult" and event["payload"]["requestId"] == 3
						for event in events
					),
				)
				result = next(
					event
					for event in events
					if event["type"] == "exploreTextResult" and event["payload"]["requestId"] == 3
				)
				self.assertEqual(
					("word", ",", 1, 5),
					(
						result["payload"]["unit"],
						result["payload"]["text"],
						result["payload"]["line"],
						result["payload"]["byteColumn"],
					),
				)
			finally:
				if client is not None:
					client.stop()
				process.terminate()
				try:
					process.wait(timeout=3)
				except subprocess.TimeoutExpired:
					process.kill()
					process.wait(timeout=3)

	def test_real_tui_omnifunc_emits_popup_selection_and_close(self) -> None:
		root = pathlib.Path.cwd()
		with tempfile.TemporaryDirectory() as directory:
			nvim_socket = os.path.join(directory, "nvim.sock")
			process = pexpect.spawn(
				"nvim",
				[
					"-n",
					"-u",
					"NONE",
					"-i",
					"NONE",
					"--noplugin",
					"--cmd",
					"set packpath=",
					"--cmd",
					f"execute 'set runtimepath={root / 'neovim-plugin'},' . $VIMRUNTIME",
					"--cmd",
					"runtime plugin/nvim_nvda.lua",
					"--listen",
					nvim_socket,
				],
				env={
					**os.environ,
					"TERM": "xterm-256color",
					"XDG_DATA_HOME": os.path.join(directory, "data"),
					"XDG_CONFIG_HOME": os.path.join(directory, "config"),
					"XDG_STATE_HOME": os.path.join(directory, "state"),
					"XDG_CACHE_HOME": os.path.join(directory, "cache"),
				},
				encoding=None,
				timeout=3,
			)
			self._wait_socket(nvim_socket, process)
			transport = RecordingTransport()
			bridge = Bridge(nvim_socket, transport=transport)
			bridge.start()
			events, condition = transport.events, transport.condition
			try:
				self._wait(condition, lambda: any(e["type"] == "fullState" for e in events))
				bridge.nvim.notify(
					"nvim_exec_lua",
					"""
                    _G.NvimNvdaTestComplete = function(findstart, base)
                      if findstart == 1 then return 0 end
                      return {
                        {word='printf', abbr='printf(format, ...)', kind='f'},
                        {word='print', abbr='print(value)', kind='f'},
                      }
                    end
                    vim.bo.omnifunc = 'v:lua.NvimNvdaTestComplete'
                    """,
					[],
				)
				time.sleep(0.05)
				process.send(b"i\x18\x0f")  # Insert, CTRL-X CTRL-O.
				self._wait(condition, lambda: any(e["type"] == "menuSelectionChanged" for e in events))
				selected = next(e for e in reversed(events) if e["type"] == "menuSelectionChanged")
				initial_index = selected["payload"]["itemIndex"]
				expected_items = {
					1: ("printf", "format, ..."),
					2: ("print", "value"),
				}
				self.assertEqual(
					expected_items[initial_index],
					(
						selected["payload"]["item"]["label"],
						selected["payload"]["item"]["parameters"],
					),
				)
				prior_selection_count = sum(e["type"] == "menuSelectionChanged" for e in events)
				process.send(b"\x0e")  # CTRL-N selects the next item.
				self._wait(
					condition,
					lambda: sum(e["type"] == "menuSelectionChanged" for e in events) > prior_selection_count,
				)
				moved = next(e for e in reversed(events) if e["type"] == "menuSelectionChanged")
				self.assertNotEqual(initial_index, moved["payload"]["itemIndex"])
				self.assertEqual(
					expected_items[moved["payload"]["itemIndex"]],
					(
						moved["payload"]["item"]["label"],
						moved["payload"]["item"]["parameters"],
					),
				)
				process.send(b"\x1b")
				self._wait(condition, lambda: any(e["type"] == "menuClosed" for e in events))
				opened_index = next(i for i, e in enumerate(events) if e["type"] == "menuOpened")
				closed_index = next(
					i
					for i, e in enumerate(events[opened_index:], start=opened_index)
					if e["type"] == "menuClosed"
				)
				self.assertFalse(
					any(e["type"] == "textChanged" for e in events[opened_index : closed_index + 1])
				)
				prior = len(events)
				process.send(b":set wildm\t")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "menuSelectionChanged" and e["payload"].get("menuKind") == "wildmenu"
						for e in events[prior:]
					),
				)
				wildmenu = next(
					e
					for e in reversed(events[prior:])
					if e["type"] == "menuSelectionChanged" and e["payload"].get("menuKind") == "wildmenu"
				)
				self.assertGreater(wildmenu["payload"]["itemCount"], 1)
				process.send(b"\x03")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "modeChanged" and e["payload"].get("modeRaw") == "n"
						for e in events[prior:]
					),
				)
				prior = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.schedule(function() vim.ui.input({prompt=string.rep('a',2047)..'界'}, "
					"function() end) end)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptOpened" and e["payload"].get("promptKind") == "input"
						for e in events[prior:]
					),
				)
				bounded_prompt = next(
					e
					for e in reversed(events[prior:])
					if e["type"] == "promptOpened" and e["payload"].get("promptKind") == "input"
				)["payload"]["prompt"]
				self.assertEqual("a" * 2047, bounded_prompt)
				self.assertLessEqual(len(bounded_prompt.encode("utf-8")), 2048)
				# The semantic wrapper necessarily announces immediately
				# before Neovim enters the blocking input() command line. On
				# slower 0.10 runs, a fixed delay can still inject into Normal
				# mode. Wait for Neovim's structured command-line state
				# instead of requiring one particular event type or adding a
				# larger timing guess.
				self._wait(
					condition,
					lambda: any(
						e["type"] in {"commandLineChanged", "modeChanged"}
						and e["payload"].get("modeRaw") == "c"
						for e in events[prior:]
					),
				)
				process.send(b"feature\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptClosed"
						and e["payload"].get("promptKind") == "input"
						and e["payload"].get("accepted") is True
						for e in events[prior:]
					),
				)
				prior = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.schedule(function() vim.ui.input({prompt='Rename item'}, function() end) end)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptOpened" and e["payload"].get("promptKind") == "input"
						for e in events[prior:]
					),
				)
				process.send(b"\x1b")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptClosed"
						and e["payload"].get("promptKind") == "input"
						and e["payload"].get("accepted") is False
						for e in events[prior:]
					),
				)
				prior = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.schedule(function() vim.ui.select({'keep','replace'}, "
					"{prompt='Resolve conflict',kind='nvimtree_overwrite_rename'}, function() end) end)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "menuSelectionChanged" and e["payload"].get("menuKind") == "select"
						for e in events[prior:]
					),
				)
				process.send(b"2\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptClosed"
						and e["payload"].get("promptKind") == "select"
						and e["payload"].get("accepted") is True
						and e["payload"].get("selectedLabel") == "replace"
						for e in events[prior:]
					),
				)
				prior = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.schedule(function() vim.fn.confirm('Delete item?', '&Yes\\n&No', 2) end)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptOpened"
						and e["payload"].get("promptKind") == "confirm"
						and "Delete item?" in e["payload"].get("prompt", "")
						for e in events[prior:]
					),
				)
				process.send(b"n\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptClosed"
						and e["payload"].get("promptKind") == "confirm"
						and e["payload"].get("accepted") is True
						and e["payload"].get("selectedLabel") == "No"
						for e in events[prior:]
					),
				)
				confirm_events = [
					e
					for e in events[prior:]
					if e["type"] in {"promptOpened", "promptClosed"}
					and e["payload"].get("promptKind") == "confirm"
				]
				self.assertEqual(
					["promptOpened", "promptClosed"], [e["type"] for e in confirm_events], confirm_events
				)
				prior = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.schedule(function() local b=vim.api.nvim_create_buf(false,true); "
					"vim.api.nvim_buf_set_lines(b,0,-1,true,{'DELETE /private/example.txt','','[Y]es [N]o'}); "
					"vim.bo[b].filetype='oil_preview'; vim.api.nvim_open_win(b,true,{relative='editor',"
					"width=40,height=3,row=2,col=2,style='minimal'}); "
					"local close=function() vim.api.nvim_win_close(0,true) end; "
					"vim.keymap.set('n','n',close,{buffer=b}); "
					"vim.keymap.set('n','y',close,{buffer=b}) end)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptOpened"
						and e["payload"].get("reason") == "oilConfirmationFallback"
						for e in events[prior:]
					),
				)
				time.sleep(0.1)
				oil_opened = next(
					e
					for e in events[prior:]
					if e["type"] == "promptOpened" and e["payload"].get("reason") == "oilConfirmationFallback"
				)
				self.assertEqual(
					"Oil confirmation, delete 1 item. Y yes, N no",
					oil_opened["payload"].get("prompt"),
				)
				self.assertEqual("", oil_opened["payload"].get("lineText"))
				self.assertFalse(
					any(
						e["type"] in {"contextChanged", "textChanged", "cursorMoved"}
						and e["payload"].get("filetype") == "oil_preview"
						for e in events[prior:]
					)
				)
				process.send(b"n")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptClosed"
						and e["payload"].get("promptKind") == "confirm"
						and e["payload"].get("accepted") is False
						for e in events[prior:]
					),
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'section {{{','inside','end }}}','target'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); vim.wo.foldmethod='marker'; vim.wo.foldlevel=99; "
					"vim.bo.modified=false",
					[],
				)
				prior = len(events)
				process.send(b"zc")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "foldChanged"
						and e["payload"].get("foldAction") == "close"
						and e["payload"].get("endLine") == 3
						for e in events[prior:]
					),
				)
				process.send(b"zo")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "foldChanged" and e["payload"].get("foldAction") == "open"
						for e in events[prior:]
					),
				)
				prior = len(events)
				process.send(b"ma")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "markSet" and e["payload"].get("markName") == "a" for e in events[prior:]
					),
				)
				process.send(b"G'a")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "markMoved" and e["payload"].get("markName") == "a"
						for e in events[prior:]
					),
				)
				prior = len(events)
				process.send(b'"byy')
				self._wait(
					condition,
					lambda: any(
						e["type"] == "registerSelected" and e["payload"].get("registerName") == "b"
						for e in events[prior:]
					),
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "registerChanged" and e["payload"].get("registerName") == "b"
						for e in events[prior:]
					),
				)
				prior = len(events)
				process.send(b"qajq")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "macroRecordingStarted" and e["payload"].get("registerName") == "a"
						for e in events[prior:]
					),
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "macroRecordingStopped" and e["payload"].get("registerName") == "a"
						for e in events[prior:]
					),
				)
				process.send(b"@a")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "macroPlayed" and e["payload"].get("registerName") == "a"
						for e in events[prior:]
					),
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'alpha beta','beta tail'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); vim.bo.modified=false",
					[],
				)
				prior = len(events)
				process.send(b"Vj")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "selectionChanged"
						and e["payload"].get("selection", {}).get("kind") == "line"
						and len(e["payload"]["selection"].get("selectedLines", [])) == 2
						for e in events[prior:]
					),
				)
				line_selection = next(
					e
					for e in reversed(events)
					if e["type"] == "selectionChanged"
					and e["payload"].get("selection", {}).get("kind") == "line"
				)
				self.assertEqual(
					["alpha beta", "beta tail"],
					[item["text"] for item in line_selection["payload"]["selection"]["selectedLines"]],
				)
				process.send(b"\x1b")
				time.sleep(0.05)
				bridge.nvim.notify("nvim_win_set_cursor", 0, [1, 0])
				process.send(b"\x16jl")  # CTRL-V, down, right.
				self._wait(
					condition,
					lambda: any(
						e["type"] == "selectionChanged"
						and e["payload"].get("selection", {}).get("kind") == "block"
						and e["payload"]["selection"].get("text") == "al\nbe"
						for e in events
					),
				)
				process.send(b"\x1b")
				bridge.nvim.notify("nvim_win_set_cursor", 0, [1, 0])
				time.sleep(0.05)
				process.send(b"/beta\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "searchMatchChanged" and e["payload"].get("matchCount") == 2
						for e in events
					),
				)
				first_match = next(e for e in reversed(events) if e["type"] == "searchMatchChanged")
				self.assertEqual(
					(1, 2, 1),
					(
						first_match["payload"]["matchIndex"],
						first_match["payload"]["matchCount"],
						first_match["payload"]["matchLine"],
					),
				)
				# Let the TUI finish the search-result redraw before sending
				# the next physical key. The structured event may arrive a
				# few milliseconds before the terminal has consumed redraw.
				self._drain_tui_output(process)
				process.send(b"n")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "searchMatchChanged" and e["payload"].get("matchLine") == 2
						for e in events
					),
				)
				prior = len(events)
				process.send(b"N")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "searchMatchChanged"
						and e["payload"].get("matchLine") == 1
						and e["payload"].get("searchDirection") == "previous"
						for e in events[prior:]
					),
				)
				process.send(b"?alpha\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "searchMatchChanged"
						and e["payload"].get("matchCount") == 1
						and e["payload"].get("searchDirection") == "?"
						for e in events
					),
				)
				process.send(b":%s/beta/gamma/g\r")
				self._wait(condition, lambda: any(e["type"] == "replacementPerformed" for e in events))
				replacement = next(e for e in reversed(events) if e["type"] == "replacementPerformed")
				self.assertIn("replacementMessage", replacement["payload"])
				bridge.nvim.notify(
					"nvim_exec_lua",
					"local lines={'function demo() {','  return (x)','}'}; "
					"vim.api.nvim_buf_set_lines(0,0,-1,true,lines); "
					"vim.api.nvim_win_set_cursor(0,{1,lines[1]:find('{',1,true)-1})",
					[],
				)
				prior = len(events)
				process.send(b"%")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "matchingPairMoved"
						and e["payload"].get("cursor", {}).get("line") == 3
						and e["payload"].get("character") == "}"
						for e in events[prior:]
					),
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'plain text'}); vim.api.nvim_win_set_cursor(0,{1,0})",
					[],
				)
				prior = len(events)
				process.send(b"%")
				self._wait(
					condition,
					lambda: any(e["type"] == "matchingPairNotFound" for e in events[prior:]),
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{''}); vim.api.nvim_win_set_cursor(0,{1,0}); "
					"vim.opt.spelllang='en_us'; vim.wo.spell=true",
					[],
				)
				prior = len(events)
				process.send(b"imispelled ")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "spellingErrorTyped"
						and e["payload"].get("spellingError", {}).get("word") == "mispelled"
						for e in events[prior:]
					),
				)
				spelling_event_count = sum(e["type"] == "spellingErrorTyped" for e in events)
				process.send(b".")
				time.sleep(0.12)
				self.assertEqual(
					spelling_event_count,
					sum(e["type"] == "spellingErrorTyped" for e in events),
					"punctuation after a completed misspelling must not replay the sound",
				)
				process.send(b"\x1b")
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.wo.spell=false; local ns=vim.api.nvim_create_namespace('nvim_nvda_test_cspell'); "
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'bad wrd'}); vim.api.nvim_win_set_cursor(0,{1,5}); "
					"vim.diagnostic.set(ns,0,{{lnum=0,col=4,end_lnum=0,end_col=7,message='Unknown word',source='cspell'}})",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "diagnosticChanged"
						and e["payload"].get("spellingError", {}).get("source") == "cspell"
						for e in events
					),
				)
				bridge.nvim.notify("nvim_exec_lua", "require('nvim_nvda')._test_emit('diagnosticMoved')", [])
				self._wait(
					condition,
					lambda: any(
						e["type"] == "diagnosticMoved"
						and e["payload"].get("diagnostic", {}).get("source") == "cspell"
						for e in events
					),
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.notify('Accessible notice', vim.log.levels.INFO, {title='Test'})",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "messageReceived"
						and e["payload"].get("message") == "Accessible notice"
						and e["payload"].get("messageTitle") == "Test"
						for e in events
					),
				)
				prior = len(events)
				bridge.nvim.notify("nvim_command", "new")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "contextChanged" and e["payload"].get("windowCount") == 2
						for e in events[prior:]
					),
				)
				bridge.nvim.notify("nvim_command", "close!")
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.fn.setqflist({{filename='script.sh',lnum=4,col=2,text='SC2086 quote variable'}}); vim.cmd('copen')",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "contextChanged" and e["payload"].get("windowType") == "quickfix"
						for e in events
					),
				)
				bridge.nvim.notify("nvim_command", "cclose")
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'(x)'}); vim.api.nvim_win_set_cursor(0,{1,0})",
					[],
				)
				prior = len(events)
				process.send(b"%")
				try:
					self._wait(
						condition,
						lambda: any(
							e["type"] == "matchingPairMoved"
							and e["payload"].get("cursor", {}).get("line") == 1
							and e["payload"].get("character") == ")"
							for e in events[prior:]
						),
					)
				except AssertionError:
					diagnostics = next(
						(
							e["payload"].get("keyObserverDiagnostics")
							for e in reversed(events[prior:])
							if e["payload"].get("keyObserverDiagnostics")
						),
						{},
					)
					self.fail(f"matching-pair timeout; key observer diagnostics={diagnostics!r}")
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'modified'}); vim.bo.modified=true",
					[],
				)
				time.sleep(0.05)
				process.send(b":q\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "errorReceived" and "E37" in e["payload"].get("message", "")
						for e in events
					),
				)
			finally:
				bridge.stop()
				if process.isalive():
					process.terminate(force=True)

	def test_real_tui_terminal_control_and_process_exit_are_structured(self) -> None:
		root = pathlib.Path.cwd()
		with tempfile.TemporaryDirectory() as directory:
			nvim_socket = os.path.join(directory, "nvim.sock")
			process = pexpect.spawn(
				"nvim",
				[
					"-n",
					"-u",
					"NONE",
					"-i",
					"NONE",
					"--noplugin",
					"--cmd",
					"set packpath=",
					"--cmd",
					f"execute 'set runtimepath={root / 'neovim-plugin'},' . $VIMRUNTIME",
					"--cmd",
					"runtime plugin/nvim_nvda.lua",
					"--listen",
					nvim_socket,
				],
				env={
					**os.environ,
					"TERM": "xterm-256color",
					"XDG_DATA_HOME": os.path.join(directory, "data"),
					"XDG_CONFIG_HOME": os.path.join(directory, "config"),
					"XDG_STATE_HOME": os.path.join(directory, "state"),
					"XDG_CACHE_HOME": os.path.join(directory, "cache"),
				},
				encoding=None,
				timeout=3,
			)
			self._wait_socket(nvim_socket, process)
			transport = RecordingTransport()
			bridge = Bridge(nvim_socket, transport=transport)
			bridge.start()
			events, condition = transport.events, transport.condition
			try:
				self._wait(condition, lambda: any(e["type"] == "fullState" for e in events))
				bridge.nvim.notify("nvim_exec_lua", "vim.o.shell='sh'", [])
				prior = len(events)
				process.send(b":terminal\r")
				self._wait(
					condition,
					lambda: any(
						e["payload"].get("buftype") == "terminal"
						and e["payload"].get("mode") == "terminalNormal"
						for e in events[prior:]
					),
				)
				time.sleep(0.1)
				self.assertFalse(any(e["type"] == "characterMoved" for e in events[prior:]))
				process.send(b"i")
				self._wait(
					condition,
					lambda: any(
						e["payload"].get("buftype") == "terminal" and e["payload"].get("mode") == "terminal"
						for e in events[prior:]
					),
				)
				terminal_state = next(
					e["payload"]
					for e in reversed(events)
					if e["payload"].get("buftype") == "terminal" and e["payload"].get("mode") == "terminal"
				)
				prior = len(events)
				bridge._on_client_control(
					"leaveTerminalInputRequest",
					{
						"requestId": 51,
						"bufferId": terminal_state["bufferId"],
						"windowId": terminal_state["windowId"],
						"tabpageId": terminal_state["tabpageId"],
						"modeRaw": terminal_state["modeRaw"],
					},
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "leaveTerminalInputResult"
						and e["payload"].get("requestId") == 51
						and e["payload"].get("ok") is True
						for e in events[prior:]
					),
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "modeChanged"
						and e["payload"].get("buftype") == "terminal"
						and e["payload"].get("mode") == "terminalNormal"
						for e in events[prior:]
					),
				)
				prior = len(events)
				process.send(b":bp\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "messageReceived"
						and "no other listed buffer" in e["payload"].get("message", "")
						for e in events[prior:]
					),
				)
				self.assertTrue(
					any(
						e["type"] == "commandLineChanged"
						and e["payload"].get("commandLine") == "bp"
						and e["payload"].get("commandLineType") == ":"
						for e in events[prior:]
					)
				)
				prior = len(events)
				process.send(b"i")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "modeChanged"
						and e["payload"].get("buftype") == "terminal"
						and e["payload"].get("mode") == "terminal"
						for e in events[prior:]
					),
				)
				prior = len(events)
				process.send(b"exit\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "messageReceived"
						and e["payload"].get("terminalExitStatus") == 0
						and "status 0" in e["payload"].get("message", "")
						for e in events[prior:]
					),
				)
				prior = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.schedule(function() local b=vim.api.nvim_create_buf(false,true); "
					"vim.api.nvim_buf_set_lines(b,0,-1,true,{'  MOVE /private/old.txt -> /private/new.txt','','[Y]es [N]o'}); "
					"vim.bo[b].filetype='oil_preview'; vim.api.nvim_open_win(b,true,{relative='editor',"
					"width=56,height=3,row=2,col=2,style='minimal'}); "
					"local close=function() vim.api.nvim_win_close(0,true) end; "
					"vim.keymap.set('n','n',close,{buffer=b}); "
					"vim.keymap.set('n','y',close,{buffer=b}) end)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptOpened"
						and e["payload"].get("prompt")
						== "Oil confirmation, rename or move 1 item. Y yes, N no"
						for e in events[prior:]
					),
				)
				process.send(b"y")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "promptClosed"
						and e["payload"].get("promptKind") == "confirm"
						and e["payload"].get("accepted") is True
						for e in events[prior:]
					),
				)
			finally:
				bridge.stop()
				if process.isalive():
					process.terminate(force=True)

	def test_real_tui_running_terminal_bd_reports_guard_before_hit_enter(self) -> None:
		root = pathlib.Path.cwd()
		with tempfile.TemporaryDirectory() as directory:
			nvim_socket = os.path.join(directory, "nvim.sock")
			process = pexpect.spawn(
				"nvim",
				[
					"-n",
					"-u",
					"NONE",
					"-i",
					"NONE",
					"--noplugin",
					"--cmd",
					"set packpath=",
					"--cmd",
					f"execute 'set runtimepath={root / 'neovim-plugin'},' . $VIMRUNTIME",
					"--cmd",
					"runtime plugin/nvim_nvda.lua",
					"--listen",
					nvim_socket,
				],
				env={
					**os.environ,
					"TERM": "xterm-256color",
					"XDG_DATA_HOME": os.path.join(directory, "data"),
					"XDG_CONFIG_HOME": os.path.join(directory, "config"),
					"XDG_STATE_HOME": os.path.join(directory, "state"),
					"XDG_CACHE_HOME": os.path.join(directory, "cache"),
				},
				encoding=None,
				timeout=3,
			)
			self._wait_socket(nvim_socket, process)
			transport = RecordingTransport()
			bridge = Bridge(nvim_socket, transport=transport)
			bridge.start()
			events, condition = transport.events, transport.condition
			try:
				self._wait(condition, lambda: any(e["type"] == "fullState" for e in events))
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.cmd('enew'); vim.fn.termopen({'sh'}); vim.cmd('stopinsert')",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["payload"].get("buftype") == "terminal"
						and e["payload"].get("mode") == "terminalNormal"
						for e in events
					),
				)
				prior = len(events)
				process.send(b":bd\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "errorReceived"
						and "E89" in e["payload"].get("message", "")
						and "bd!" in e["payload"].get("message", "")
						and "Press Enter" in e["payload"].get("message", "")
						for e in events[prior:]
					),
				)
				self.assertTrue(any(e["payload"].get("buftype") == "terminal" for e in events[prior:]))
			finally:
				bridge.stop()
				if process.isalive():
					process.terminate(force=True)

	def test_neovim_restart_reconnects_and_pushes_full_state(self) -> None:
		root = pathlib.Path.cwd()
		with tempfile.TemporaryDirectory() as directory:
			nvim_socket = os.path.join(directory, "nvim.sock")
			process = self._start_nvim(root, nvim_socket)
			transport = RecordingTransport()
			bridge = Bridge(nvim_socket, transport=transport)
			bridge.start()
			events, condition = transport.events, transport.condition
			restarted = None
			try:
				self._wait(condition, lambda: any(e["payload"].get("modeRaw") == "n" for e in events))
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'a界z'}); vim.api.nvim_win_set_cursor(0,{1,0}); require('nvim_nvda')._test_emit('fullState')",
					[],
				)
				self._wait(condition, lambda: any(e["payload"].get("lineText") == "a界z" for e in events))
				routed_state = next(
					e["payload"] for e in reversed(events) if e["payload"].get("lineText") == "a界z"
				)
				bridge._on_client_control(
					"routeCursor",
					{
						"bufferId": routed_state["bufferId"],
						"windowId": routed_state["windowId"],
						"line": 1,
						"byteColumn": 1,
						"changedtick": routed_state["changedtick"],
					},
				)
				self._wait_cursor(nvim_socket, 2)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'hello world'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); vim.api.nvim_feedkeys('w','x',false)",
					[],
				)
				self._wait(condition, lambda: any(e["type"] == "wordMoved" for e in events))
				self.assertEqual(
					"world", next(e for e in reversed(events) if e["type"] == "wordMoved")["payload"]["word"]
				)
				word_event_count = sum(e["type"] == "wordMoved" for e in events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'hallo, wie geht es'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); vim.api.nvim_feedkeys('w','x',false)",
					[],
				)
				self._wait(
					condition, lambda: sum(e["type"] == "wordMoved" for e in events) > word_event_count
				)
				punctuation = next(e for e in reversed(events) if e["type"] == "wordMoved")["payload"]
				self.assertEqual(
					(",", ",", 5),
					(
						punctuation["word"],
						punctuation["character"],
						punctuation["cursor"]["byteColumn"],
					),
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'delete line','next'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); vim.api.nvim_feedkeys('dd','x',false)",
					[],
				)
				self._wait(condition, lambda: any(e["type"] == "textDeleted" for e in events))
				deleted_event = next(e for e in reversed(events) if e["type"] == "textDeleted")
				self.assertTrue(deleted_event["payload"]["linewise"])
				self.assertEqual("delete line", deleted_event["payload"]["beforeText"])
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'hello world'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); "
					"vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('cw<Esc>',true,false,true),'x',false)",
					[],
				)
				self._wait(condition, lambda: any(e["type"] == "textReplaced" for e in events))
				word_events_before_change = sum(e["type"] == "wordMoved" for e in events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'word ist next'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); "
					"vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('cwe<Esc>',true,false,true),'x',false)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "textReplaced" and e["payload"].get("lineText") == "e ist next"
						for e in events
					),
				)
				time.sleep(0.1)
				self.assertEqual(
					word_events_before_change,
					sum(e["type"] == "wordMoved" for e in events),
					"cw motion leaked as word navigation after first inserted character",
				)
				cancelled_edit_events = len(events)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{'abc'}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); "
					"vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('d<Esc>iX<Esc>',true,false,true),'x',false)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "textChanged" and e["payload"].get("lineText") == "Xabc"
						for e in events[cancelled_edit_events:]
					),
				)
				self.assertFalse(
					any(e["type"] == "textDeleted" for e in events[cancelled_edit_events:]),
					"cancelled d operator leaked into later insert",
				)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"vim.api.nvim_buf_set_lines(0,0,-1,true,{''}); "
					"vim.api.nvim_win_set_cursor(0,{1,0}); "
					"vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('id!?<Esc>',true,false,true),'x',false)",
					[],
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "textChanged" and e["payload"].get("lineText") == "d!?" for e in events
					),
				)
				prior = len(events)
				bridge.nvim.notify("nvim_input", ":lua print('command completed')\r")
				self._wait(
					condition,
					lambda: any(
						e["type"] == "commandLineChanged"
						and e["payload"].get("commandLine") == "lua print('command completed')"
						for e in events[prior:]
					),
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "modeChanged" and e["payload"].get("mode") == "commandLine"
						for e in events[prior:]
					),
				)
				self._wait(
					condition,
					lambda: any(
						e["type"] == "messageReceived"
						and e["payload"].get("message") == "command completed"
						and e["payload"].get("commandLineReturn") is True
						for e in events[prior:]
					),
				)
				command_mode_index = next(
					index
					for index, event in enumerate(events[prior:])
					if event["type"] == "modeChanged" and event["payload"].get("mode") == "commandLine"
				)
				command_message_index = next(
					index
					for index, event in enumerate(events[prior:])
					if event["type"] == "messageReceived"
					and event["payload"].get("message") == "command completed"
				)
				self.assertLess(command_mode_index, command_message_index)
				bridge.nvim.notify(
					"nvim_exec_lua",
					"local p=...; require('nvim_nvda').accessible_menu_open(p.items, p.options)",
					[
						{
							"options": {"kind": "omni", "selected": 1},
							"items": [
								{"word": "printf", "abbr": "printf(format, ...)", "kind": "f"},
								{"word": "print", "abbr": "print(value)", "kind": "f"},
							],
						}
					],
				)
				self._wait(condition, lambda: any(e["type"] == "menuSelectionChanged" for e in events))
				menu_event = next(e for e in reversed(events) if e["type"] == "menuSelectionChanged")
				self.assertEqual(
					("printf", "format, ..."),
					(
						menu_event["payload"]["item"]["label"],
						menu_event["payload"]["item"]["parameters"],
					),
				)
				self.assertEqual(
					(1, 2),
					(
						menu_event["payload"]["itemIndex"],
						menu_event["payload"]["itemCount"],
					),
				)
				bridge.nvim.notify("nvim_exec_lua", "require('nvim_nvda').accessible_menu_close()", [])
				self._wait(condition, lambda: any(e["type"] == "menuClosed" for e in events))
				process.terminate()
				process.wait(timeout=2)
				self._wait(
					condition,
					lambda: any(
						e["payload"].get("connection", {}).get("neovim") == "disconnected" for e in events
					),
				)
				restarted = self._start_nvim(root, nvim_socket)
				prior = len(events)
				self._wait(
					condition,
					lambda: any(e["payload"].get("modeRaw") == "n" for e in events[prior:]),
					timeout=4.0,
				)
			finally:
				bridge.stop()
				if restarted is not None:
					restarted.terminate()
					restarted.wait(timeout=2)
				elif process.poll() is None:
					process.terminate()
					process.wait(timeout=2)

	def _start_nvim(self, root: pathlib.Path, socket_path: str) -> subprocess.Popen:
		process = subprocess.Popen(
			[
				"nvim",
				"--headless",
				"-n",
				"-u",
				"NONE",
				"-i",
				"NONE",
				"--cmd",
				f"set runtimepath^={root / 'neovim-plugin'}",
				"--listen",
				socket_path,
			],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
		)
		deadline = time.monotonic() + 2
		while time.monotonic() < deadline:
			if os.path.exists(socket_path):
				return process
			if process.poll() is not None:
				self.fail("Neovim exited before creating RPC socket")
			time.sleep(0.01)
		process.terminate()
		self.fail("Neovim RPC socket timeout")

	def _wait_socket(self, socket_path: str, process) -> None:
		deadline = time.monotonic() + 2
		while time.monotonic() < deadline:
			if os.path.exists(socket_path):
				return
			if not process.isalive():
				self.fail("Neovim exited before creating RPC socket")
			time.sleep(0.01)
		process.terminate(force=True)
		self.fail("Neovim RPC socket timeout")

	@staticmethod
	def _drain_tui_output(process) -> None:
		try:
			while process.read_nonblocking(65536, timeout=0.01):
				pass
		except (pexpect.TIMEOUT, pexpect.EOF):
			pass

	def _wait(self, condition: threading.Condition, predicate, timeout: float = 3.0) -> None:
		deadline = time.monotonic() + timeout
		with condition:
			while not predicate():
				remaining = deadline - time.monotonic()
				if remaining <= 0:
					self.fail("condition timeout")
				condition.wait(remaining)

	def _wait_cursor(self, socket_path: str, expected_one_based_byte_column: int) -> None:
		deadline = time.monotonic() + 2
		while time.monotonic() < deadline:
			result = subprocess.run(
				["nvim", "--server", socket_path, "--remote-expr", "col('.')"],
				capture_output=True,
				text=True,
			)
			if result.returncode == 0 and int(result.stdout.strip()) == expected_one_based_byte_column:
				return
			time.sleep(0.02)
		self.fail("routed Neovim cursor timeout")


if __name__ == "__main__":
	unittest.main()
