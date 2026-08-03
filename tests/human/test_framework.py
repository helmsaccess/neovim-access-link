from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HUMAN_ROOT = Path(__file__).resolve().parent
VALIDATOR_PATH = HUMAN_ROOT / "framework" / "validate.py"
SPEC = importlib.util.spec_from_file_location("human_test_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


def timestamp() -> str:
	return datetime.now(timezone.utc).isoformat()


def complete_result(
	suite: str = "smoke",
	*,
	selected_tests: set[str] | None = None,
	audio: bool = True,
	braille: bool = True,
	status: str = "pass",
) -> dict[str, object]:
	plans = validator.load_plans()
	if suite == "custom":
		selected_tests = selected_tests or {"c-diagnostics.clang-tidy-presentation"}
	else:
		selected_tests = {
			f"{plan_id}.{step['id']}"
			for plan_id, plan in plans.items()
			if suite == "all" or suite in plan["suites"]
			for step in plan["steps"]
		}
	result_plans = []
	for plan_id, plan in plans.items():
		steps = []
		for step in plan["steps"]:
			if f"{plan_id}.{step['id']}" not in selected_tests:
				continue
			missing = any(
				not {"audio": audio, "braille": braille}[requirement] for requirement in step["requires"]
			)
			step_status = "notApplicable" if missing else status
			steps.append(
				{
					"id": step["id"],
					"status": step_status,
					"note": "test note" if step_status in {"fail", "blocked", "skipped"} else "",
				}
			)
		if steps:
			result_plans.append({"id": plan_id, "profile": plan["profile"], "steps": steps})
	incomplete = status in {"pending", "blocked", "skipped"}
	return {
		"schemaVersion": 3,
		"runId": "3bc529a4-d12c-44de-b581-6dc09696ab4f",
		"createdAt": timestamp(),
		"completedAt": "" if incomplete else timestamp(),
		"repository": {"commit": "a" * 40, "dirty": False},
		"environment": {
			"language": "de",
			"suite": suite,
			"selectedTests": sorted(selected_tests),
			"neovimVersion": "NVIM v0.12.3",
			"audio": audio,
			"braille": braille,
			"definitionSha256": validator.definition_fingerprint(),
			"accessLinkPluginSha256": validator.component_fingerprint(
				validator.REPOSITORY_ROOT / "neovim-plugin"
			),
			"addonVersion": "development-build-under-test",
			"nvdaVersion": "2026.1.1",
		},
		"plans": result_plans,
	}


class HumanTestFrameworkTests(unittest.TestCase):
	def write_result(self, directory: str, value: dict[str, object]) -> Path:
		path = Path(directory) / "result.json"
		path.write_text(json.dumps(value), encoding="utf-8")
		return path

	def test_repository_plans_locales_dependencies_and_evidence_are_valid(self) -> None:
		plans = validator.load_plans()
		self.assertEqual(
			{
				"blink-cmp",
				"c-diagnostics",
				"diagnostics",
				"focus-isolation",
				"lsp-native",
				"markdown-diagnostics",
				"nvim-cmp",
			},
			set(plans),
		)
		self.assertEqual(set(validator.load_locales()["de"]), set(validator.load_locales()["en"]))
		dependencies = validator.validate_dependencies()
		self.assertRegex(dependencies["tools"]["pyrightSha512"], r"^[0-9a-f]{128}$")
		self.assertEqual("22.1.8", dependencies["tools"]["clangTidy"])
		self.assertEqual("0.23.2", dependencies["tools"]["markdownlintCli2"])
		for plugin in dependencies["plugins"].values():
			self.assertRegex(plugin["revision"], r"^[0-9a-f]{40}$")
		smoke = sorted(
			(plan for plan in plans.values() if "smoke" in plan["suites"]),
			key=lambda plan: plan["order"],
		)
		self.assertEqual(
			["lsp-native", "diagnostics", "focus-isolation"],
			[plan["id"] for plan in smoke],
		)
		self.assertEqual(
			["navigation-presentation", "held-diagnostics"],
			[step["id"] for step in plans["diagnostics"]["steps"]],
		)
		self.assertEqual(
			["status-presentation", "held-parameters", "completion-presentation"],
			[step["id"] for step in plans["lsp-native"]["steps"]],
		)
		self.assertEqual(1, len(plans["focus-isolation"]["steps"]))
		self.assertEqual(
			validator.ALLOWED_CATEGORIES,
			{step["category"] for plan in plans.values() for step in plan["steps"]},
		)
		self.assertEqual(
			validator.ALLOWED_PROFILES,
			{plan["profile"] for plan in plans.values()},
		)

	def test_every_human_step_has_reason_and_automated_evidence(self) -> None:
		for plan in validator.load_plans().values():
			for step in plan["steps"]:
				with self.subTest(plan=plan["id"], step=step["id"]):
					self.assertTrue(step["manualReasons"])
					self.assertIn(step["category"], validator.ALLOWED_CATEGORIES)
					self.assertTrue(step["automatedEvidence"])
					self.assertTrue(step["titleKey"])
					self.assertTrue(step["contextKey"])
					for relative in step["automatedEvidence"]:
						self.assertTrue((validator.REPOSITORY_ROOT / relative).is_file())

	def test_runner_is_isolated_and_plans_are_not_executable(self) -> None:
		runner = (HUMAN_ROOT / "framework" / "run.ps1").read_text(encoding="utf-8")
		self.assertIn('"-u", $TestInitPath', runner)
		self.assertIn('"tmp\\human-test-state"', runner)
		self.assertNotIn("Copy-Item", runner)
		self.assertNotIn("Invoke-Expression", runner)
		self.assertIn("Sort-Object { [int]$_.order }", runner)
		self.assertIn("Invoke-TestNvim -Profile ([string]$plan.profile)", runner)
		self.assertNotIn('"install", "--prefix", $NodeRoot', runner)
		self.assertIn('"pack", "--pack-destination", $PackageRoot, "--ignore-scripts"', runner)
		self.assertIn("Get-FileHash -LiteralPath $archive -Algorithm SHA512", runner)
		self.assertLess(runner.index("Get-FileHash -LiteralPath $archive"), runner.index('"-xzf"'))
		self.assertIn('"data\\nvim-data\\site\\pack\\core\\opt"', runner)
		self.assertIn('"config\\nvim\\nvim-pack-lock.json"', runner)
		self.assertIn('schemaVersion = 4', runner)
		self.assertIn('schemaVersion = 3', runner)
		self.assertIn('[string[]]$TestId = @()', runner)
		self.assertIn('selectedTests = @(', runner)
		self.assertIn('function Select-CustomTests', runner)
		self.assertIn('$needsClangTidy = $profiles -contains "c-diagnostics"', runner)
		self.assertIn('$needsMarkdownlint = $profiles -contains "markdown-diagnostics"', runner)
		self.assertIn('"clang-tidy==$($dependencies.tools.clangTidy)"', runner)
		self.assertIn('"markdownlint-cli2@$($dependencies.tools.markdownlintCli2)"', runner)
		self.assertIn('environmentSha256 = Get-EnvironmentFingerprint', runner)
		setup_cache = runner[
			runner.index("function Test-SetupCurrent") : runner.index(
				"function Install-TestEnvironment"
			)
		]
		self.assertNotIn("Get-DefinitionFingerprint", setup_cache)
		self.assertIn('$ruffVersion.Text.Trim() -eq "ruff $($dependencies.tools.ruff)"', runner)
		self.assertIn('Install-TestEnvironment -Repair', runner)
		self.assertIn('"GIT_CONFIG_GLOBAL"', runner)
		self.assertIn('$lines = @("[safe]")', runner)
		self.assertIn("Get-EquivalentPaths -Path $RepositoryRoot", runner)
		self.assertIn('directory = `"$safeDirectory`"', runner)
		self.assertNotIn('"config", "--global"', runner)
		self.assertIn("function Invoke-ExternalText", runner)
		self.assertIn("function Invoke-OptionalExternalText", runner)
		self.assertIn("Windows cannot resolve a linked Linux worktree", runner)
		self.assertIn('$output = @(& $Command @Arguments 2>&1)', runner)
		self.assertEqual(1, runner.count("2>&1"))
		self.assertIn('$versionResult = Invoke-ExternalText', runner)
		self.assertIn('$result = Invoke-ExternalText -Command $python.Command', runner)
		self.assertIn('$head = Invoke-OptionalExternalText', runner)
		self.assertIn('$status = Invoke-OptionalExternalText', runner)
		self.assertNotIn('& $git.Source -C $RepositoryRoot', runner)
		run_plans = runner[runner.index("function Run-Plans") :]
		self.assertLess(
			run_plans.index('$script:SelectedTestIds = @($result.environment.selectedTests)'),
			run_plans.index("Confirm-TestEnvironment"),
		)
		for plan in validator.load_plans().values():
			self.assertEqual(validator.PLAN_FIELDS, set(plan))
			for step in plan["steps"]:
				self.assertEqual(validator.STEP_FIELDS, set(step))

	def test_test_neovim_repeats_one_task_and_starts_diagnostics_on_error(self) -> None:
		configuration = (HUMAN_ROOT / "framework" / "init.lua").read_text(encoding="utf-8")
		readiness = (HUMAN_ROOT / "framework" / "linter_readiness.lua").read_text(
			encoding="utf-8"
		)
		self.assertIn('"<F2>"', configuration)
		self.assertIn("ACCESS_LINK_HUMAN_CONTEXT", configuration)
		self.assertIn("ACCESS_LINK_HUMAN_TASK", configuration)
		self.assertIn("ACCESS_LINK_HUMAN_EXPECTED", configuration)
		self.assertIn("{ 1, 15 }", configuration)
		self.assertIn('lint.try_lint(linter_name, { cwd = process_directory })', configuration)
		self.assertIn('diagnostics_ready = "Diagnosen bereit:', configuration)
		self.assertIn("local readiness_pending = false", configuration)
		self.assertIn("local ready = vim.wait(15000", configuration)
		self.assertIn("return linter_diagnostics_ready()", configuration)
		self.assertIn('vim.env.TEMP or vim.env.TMP', configuration)
		self.assertIn('table.insert(lint.linters.ruff.args, 2, "--isolated")', configuration)
		self.assertIn('dofile(vim.fs.joinpath(framework_root, "linter_readiness.lua"))', configuration)
		self.assertIn("linter_readiness.evaluate(", configuration)
		self.assertIn('text(diagnostic.code) == "F401"', readiness)
		self.assertIn("warning_count >= 2", readiness)
		self.assertIn("first_line_warnings >= 2", readiness)
		self.assertIn('text(diagnostic.code) == "F821"', readiness)
		self.assertIn('linter_name = "clangtidy"', configuration)
		self.assertIn('text(diagnostic.code) == "clang-diagnostic-error"', readiness)
		self.assertIn('linter_name = "markdownlint-cli2"', configuration)
		self.assertIn('text(diagnostic.message):find("MD025"', readiness)
		self.assertIn('reportUnusedImport = "none"', configuration)
		self.assertNotIn("warning_starts_at_cursor", configuration)
		self.assertIn('prepare_insert_probe("completion_probe = calculate_")', configuration)
		self.assertIn('vim.api.nvim_win_set_cursor(0, { 2, 0 })', configuration)
		self.assertIn('Access Link human test: query a clean diagnostic position', configuration)
		self.assertIn('assert_callable_choices_ready()', configuration)
		self.assertIn('assert_completion_choices_ready()', configuration)
		self.assertIn("rich_signatures >= 2", configuration)
		self.assertIn("#item.parameters >= 3", configuration)
		for candidate in ("calculate_total", "calculate_tax", "calculate_tip"):
			self.assertIn(f'"{candidate}"', configuration)
		self.assertIn('cmp_config.get().mapping[cmp_keymap.normalize("<F5>")]', configuration)
		self.assertIn('cmp_config.get_source_config("nvim_lsp")', configuration)
		self.assertIn('require("blink.cmp.keymap").get_mappings(', configuration)
		self.assertIn('vim.tbl_contains(blink_config.sources.default, "lsp")', configuration)
		self.assertLess(
			configuration.index('if profile == "cmp" then', configuration.index("local function assert_completion_profile_ready")),
			configuration.index('vim.fn.maparg("<F5>"', configuration.index("local function assert_completion_profile_ready")),
		)
		self.assertNotIn('"<F4>"', configuration)

	def test_human_fixtures_offer_real_choices_for_every_cycle_instruction(self) -> None:
		lsp_fixture = (HUMAN_ROOT / "fixtures" / "lsp_features.py").read_text(encoding="utf-8")
		diagnostic_fixture = (HUMAN_ROOT / "fixtures" / "diagnostics.py").read_text(
			encoding="utf-8"
		)
		self.assertEqual(2, lsp_fixture.count("@overload"))
		self.assertGreaterEqual(lsp_fixture.count("discount: float"), 3)
		for candidate in ("calculate_total", "calculate_tax", "calculate_tip"):
			self.assertIn(f"def {candidate}(", lsp_fixture)
		self.assertEqual("from os import path, sep", diagnostic_fixture.splitlines()[0])
		self.assertIn("return missing;", (HUMAN_ROOT / "fixtures" / "diagnostics.c").read_text())
		self.assertEqual(
			2,
			(HUMAN_ROOT / "fixtures" / "diagnostics.md").read_text().count("# "),
		)

		locales = validator.load_locales()
		for language in ("de", "en"):
			with self.subTest(language=language):
				parameter_expectation = locales[language]["plan.lspNative.parameters.expected"]
				diagnostic_expectation = locales[language]["plan.diagnostics.held.expected"]
				earcon_expectation = locales[language]["plan.diagnostics.navigation.expected"]
				for value in ("price", "quantity", "discount", "j/k", "h/l"):
					self.assertIn(value, parameter_expectation)
				for value in ("path", "sep", "j/k"):
					self.assertIn(value, diagnostic_expectation)
				for value in ("five", "fünf"):
					if value in earcon_expectation.lower():
						break
				else:
					self.fail(f"{language} earcon expectation does not name all five sounds")

	def test_windows_ci_exercises_powershell_runner_and_dry_run(self) -> None:
		workflow = (validator.REPOSITORY_ROOT / ".github" / "workflows" / "repository-tests.yml").read_text(
			encoding="utf-8"
		)
		self.assertIn("human-test-runner-windows:", workflow)
		self.assertIn("runs-on: windows-2025", workflow)
		self.assertIn("-DryRun", workflow)
		self.assertIn('.\\tests\\human\\framework\\run.ps1 list -Language en', workflow)
		self.assertIn('-TestId "c-diagnostics.clang-tidy-presentation"', workflow)
		self.assertIn("63daa0a0374f2255d2fb4c0867fcacc64a09c8d7ec1c349f781aff1b8350a8ad", workflow)

	def test_definition_fingerprint_changes_with_human_test_inputs(self) -> None:
		fingerprint = validator.definition_fingerprint()
		self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
		with mock.patch.object(validator, "_sha256_tree", return_value="fingerprint") as digest:
			self.assertEqual("fingerprint", validator.definition_fingerprint())
			self.assertIn(
				validator.HUMAN_ROOT / "framework" / "linter_readiness.lua",
				digest.call_args.args[1],
			)
		result = complete_result()
		result["environment"]["definitionSha256"] = "0" * 64
		with tempfile.TemporaryDirectory() as directory:
			path = self.write_result(directory, result)
			with self.assertRaisesRegex(validator.ValidationError, "definition revision"):
				validator.validate_result(path)

	def test_environment_fingerprint_is_separate_from_result_definition(self) -> None:
		fingerprint = validator.environment_fingerprint()
		self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
		self.assertNotEqual(fingerprint, validator.definition_fingerprint())
		with mock.patch.object(validator, "_sha256_tree", return_value="fingerprint") as digest:
			self.assertEqual("fingerprint", validator.environment_fingerprint())
			self.assertEqual(
				{
					validator.DEPENDENCIES_PATH,
					validator.HUMAN_ROOT / "framework" / "init.lua",
					validator.HUMAN_ROOT / "framework" / "linter_readiness.lua",
				},
				set(digest.call_args.args[1]),
			)
		runner = (HUMAN_ROOT / "framework" / "run.ps1").read_text(encoding="utf-8")
		self.assertIn('Invoke-PythonText @($ValidatorPath, "environment-fingerprint")', runner)

	def test_perception_workflows_do_not_relaunch_only_for_audio(self) -> None:
		plans = validator.load_plans()
		for plan_id in ("lsp-native", "diagnostics", "nvim-cmp", "blink-cmp"):
			with self.subTest(plan=plan_id):
				self.assertFalse(
					any(step["requires"] == ["audio"] for step in plans[plan_id]["steps"])
				)
		combined = {
			"lsp-native": "completion-presentation",
			"diagnostics": "navigation-presentation",
			"nvim-cmp": "menu-presentation",
			"blink-cmp": "menu-presentation",
		}
		for plan_id, step_id in combined.items():
			step = next(step for step in plans[plan_id]["steps"] if step["id"] == step_id)
			self.assertIn("audioPerception", step["manualReasons"])

	def test_result_from_a_different_plugin_runtime_is_rejected(self) -> None:
		result = complete_result()
		result["environment"]["accessLinkPluginSha256"] = "0" * 64
		with tempfile.TemporaryDirectory() as directory:
			path = self.write_result(directory, result)
			with self.assertRaisesRegex(validator.ValidationError, "plugin runtime revision"):
				validator.validate_result(path)

	def test_plugin_runtime_fingerprint_ignores_non_runtime_files(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / "lua").mkdir()
			(root / "plugin").mkdir()
			(root / "lua" / "module.lua").write_text("return {}\n", encoding="utf-8")
			(root / "plugin" / "entry.lua").write_text("return true\n", encoding="utf-8")
			before = validator.component_fingerprint(root)
			(root / "README.md").write_text("ignored\n", encoding="utf-8")
			self.assertEqual(before, validator.component_fingerprint(root))
			(root / "lua" / "module.lua").write_text("return { changed = true }\n", encoding="utf-8")
			self.assertNotEqual(before, validator.component_fingerprint(root))

	def test_passing_result_is_machine_checkable(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			assessment = validator.validate_result(self.write_result(directory, complete_result()))
		self.assertEqual("pass", assessment.state)
		self.assertEqual(0, assessment.exit_code)

	def test_custom_result_can_contain_one_individually_selected_task(self) -> None:
		selected = {"markdown-diagnostics.markdownlint-presentation"}
		with tempfile.TemporaryDirectory() as directory:
			assessment = validator.validate_result(
				self.write_result(
					directory,
					complete_result(suite="custom", selected_tests=selected),
				)
			)
		self.assertEqual("pass", assessment.state)

	def test_custom_result_supports_exact_subsets_within_and_across_plans(self) -> None:
		selections = (
			{
				"diagnostics.navigation-presentation",
				"diagnostics.held-diagnostics",
			},
			{
				"c-diagnostics.clang-tidy-presentation",
				"markdown-diagnostics.markdownlint-presentation",
			},
		)
		for selected in selections:
			with self.subTest(selected=sorted(selected)), tempfile.TemporaryDirectory() as directory:
				assessment = validator.validate_result(
					self.write_result(
						directory,
						complete_result(suite="custom", selected_tests=selected),
					)
				)
				self.assertEqual("pass", assessment.state)

	def test_custom_result_rejects_invalid_selection_lists(self) -> None:
		selected = {"c-diagnostics.clang-tidy-presentation"}
		cases = {}
		empty = complete_result(suite="custom", selected_tests=selected)
		empty["environment"]["selectedTests"] = []
		cases["must not be empty"] = empty
		duplicate = complete_result(suite="custom", selected_tests=selected)
		duplicate["environment"]["selectedTests"].append(next(iter(selected)))
		cases["contains duplicates"] = duplicate
		unknown = complete_result(suite="custom", selected_tests=selected)
		unknown["environment"]["selectedTests"] = ["unknown-profile.unknown-task"]
		cases["contains unknown tests"] = unknown
		for message, result in cases.items():
			with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
				path = self.write_result(directory, result)
				with self.assertRaisesRegex(validator.ValidationError, message):
					validator.validate_result(path)

	def test_custom_result_must_exactly_match_selected_steps_and_profiles(self) -> None:
		selected = {
			"diagnostics.navigation-presentation",
			"diagnostics.held-diagnostics",
		}
		missing = complete_result(suite="custom", selected_tests=selected)
		missing["plans"][0]["steps"].pop()
		wrong_profile = complete_result(suite="custom", selected_tests=selected)
		wrong_profile["plans"][0]["profile"] = "native"
		cases = {
			"steps differ": missing,
			"profile differs": wrong_profile,
		}
		for message, result in cases.items():
			with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
				path = self.write_result(directory, result)
				with self.assertRaisesRegex(validator.ValidationError, message):
					validator.validate_result(path)

	def test_standard_suite_cannot_omit_a_selected_task(self) -> None:
		result = complete_result()
		result["environment"]["selectedTests"].pop()
		with tempfile.TemporaryDirectory() as directory:
			path = self.write_result(directory, result)
			with self.assertRaisesRegex(validator.ValidationError, "selectedTests differ"):
				validator.validate_result(path)

	def test_failed_result_has_distinct_machine_exit(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			assessment = validator.validate_result(
				self.write_result(directory, complete_result(status="fail"))
			)
		self.assertEqual("fail", assessment.state)
		self.assertEqual(2, assessment.exit_code)

	def test_pending_or_blocked_result_is_incomplete(self) -> None:
		for status in ("pending", "blocked", "skipped"):
			with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
				assessment = validator.validate_result(
					self.write_result(directory, complete_result(status=status))
				)
				self.assertEqual("incomplete", assessment.state)
				self.assertEqual(3, assessment.exit_code)

	def test_failure_does_not_hide_an_incomplete_step(self) -> None:
		result = complete_result(status="fail")
		result["plans"][0]["steps"][0]["status"] = "blocked"
		result["completedAt"] = ""
		with tempfile.TemporaryDirectory() as directory:
			assessment = validator.validate_result(self.write_result(directory, result))
		self.assertEqual("incomplete", assessment.state)
		self.assertEqual(3, assessment.exit_code)

	def test_absent_optional_capabilities_are_not_failures(self) -> None:
		with tempfile.TemporaryDirectory() as directory:
			assessment = validator.validate_result(
				self.write_result(
					directory,
					complete_result(audio=False, braille=False),
				)
			)
		self.assertEqual("pass", assessment.state)
		self.assertGreater(assessment.counts["notApplicable"], 0)

	def test_not_applicable_is_rejected_when_capability_exists(self) -> None:
		result = complete_result()
		result["plans"][0]["steps"][0]["status"] = "notApplicable"
		with tempfile.TemporaryDirectory() as directory:
			path = self.write_result(directory, result)
			with self.assertRaisesRegex(validator.ValidationError, "requirements are met"):
				validator.validate_result(path)

	def test_failure_block_and_skip_require_a_note(self) -> None:
		for status in ("fail", "blocked", "skipped"):
			result = complete_result(status=status)
			result["plans"][0]["steps"][0]["note"] = ""
			with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
				path = self.write_result(directory, result)
				with self.assertRaisesRegex(validator.ValidationError, "needs a note"):
					validator.validate_result(path)


if __name__ == "__main__":
	unittest.main()
