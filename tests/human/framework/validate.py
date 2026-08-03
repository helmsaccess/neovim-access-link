#!/usr/bin/env python3
"""Validate human-test plans and machine-readable result files."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


HUMAN_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = HUMAN_ROOT.parents[1]
PLANS_ROOT = HUMAN_ROOT / "plans"
LOCALES_ROOT = HUMAN_ROOT / "locales"
FIXTURES_ROOT = HUMAN_ROOT / "fixtures"
DEPENDENCIES_PATH = HUMAN_ROOT / "dependencies.json"

PLAN_FIELDS = {
	"schemaVersion",
	"id",
	"order",
	"titleKey",
	"descriptionKey",
	"suites",
	"profile",
	"fixture",
	"steps",
}
STEP_FIELDS = {
	"id",
	"category",
	"titleKey",
	"contextKey",
	"actionKey",
	"expectedKey",
	"manualReasons",
	"requires",
	"automatedEvidence",
}
RESULT_FIELDS = {
	"schemaVersion",
	"runId",
	"createdAt",
	"completedAt",
	"repository",
	"environment",
	"plans",
}
RESULT_PLAN_FIELDS = {"id", "profile", "steps"}
RESULT_STEP_FIELDS = {"id", "status", "note"}
ALLOWED_SUITES = {"smoke", "compatibility"}
ALLOWED_PROFILES = {
	"native",
	"diagnostics",
	"c-diagnostics",
	"markdown-diagnostics",
	"cmp",
	"blink",
	"focus",
}
ALLOWED_CATEGORIES = {
	"language-intelligence",
	"completion",
	"diagnostics",
	"session-integration",
}
ALLOWED_REASONS = {
	"physicalNvdaKey",
	"speechPerception",
	"physicalBraille",
	"audioPerception",
	"windowsFocus",
	"latencyUsability",
}
ALLOWED_CAPABILITIES = {"audio", "braille"}
ALLOWED_STATUSES = {"pass", "fail", "blocked", "skipped", "notApplicable", "pending"}
NOTE_REQUIRED_STATUSES = {"fail", "blocked", "skipped"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
	pass


@dataclass(frozen=True)
class ResultAssessment:
	state: str
	counts: dict[str, int]

	@property
	def exit_code(self) -> int:
		return {"pass": 0, "fail": 2, "incomplete": 3}[self.state]


def _read_json(path: Path) -> Any:
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except (OSError, UnicodeError, json.JSONDecodeError) as error:
		raise ValidationError(f"cannot read JSON {path}: {error}") from error


def _object(value: Any, label: str) -> dict[str, Any]:
	if not isinstance(value, dict):
		raise ValidationError(f"{label} must be a JSON object")
	return value


def _array(value: Any, label: str) -> list[Any]:
	if not isinstance(value, list):
		raise ValidationError(f"{label} must be a JSON array")
	return value


def _string(value: Any, label: str, *, allow_empty: bool = False) -> str:
	if not isinstance(value, str) or (not allow_empty and not value.strip()):
		qualifier = "a string" if allow_empty else "a non-empty string"
		raise ValidationError(f"{label} must be {qualifier}")
	return value


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
	missing = sorted(expected - value.keys())
	unexpected = sorted(value.keys() - expected)
	if missing or unexpected:
		raise ValidationError(f"{label} fields differ; missing={missing!r}, unexpected={unexpected!r}")


def _id(value: Any, label: str) -> str:
	result = _string(value, label)
	if not ID_PATTERN.fullmatch(result):
		raise ValidationError(f"{label} is not a stable lowercase ID: {result!r}")
	return result


def _string_set(
	value: Any,
	label: str,
	allowed: set[str],
	*,
	empty_allowed: bool = False,
) -> set[str]:
	entries = _array(value, label)
	if not entries and not empty_allowed:
		raise ValidationError(f"{label} must not be empty")
	strings = [_string(entry, f"{label} entry") for entry in entries]
	if len(strings) != len(set(strings)):
		raise ValidationError(f"{label} contains duplicates")
	result = set(strings)
	unknown = sorted(result - allowed)
	if unknown:
		raise ValidationError(f"{label} contains unsupported values: {unknown!r}")
	return result


def load_locales() -> dict[str, dict[str, str]]:
	locales: dict[str, dict[str, str]] = {}
	for language in ("de", "en"):
		raw = _object(_read_json(LOCALES_ROOT / f"{language}.json"), f"locale {language}")
		messages: dict[str, str] = {}
		for key, value in raw.items():
			messages[_string(key, f"locale {language} key")] = _string(
				value, f"locale {language} value for {key}"
			)
		locales[language] = messages
	de_keys = set(locales["de"])
	en_keys = set(locales["en"])
	if de_keys != en_keys:
		raise ValidationError(
			"locale keys differ; "
			f"missing in de={sorted(en_keys - de_keys)!r}, "
			f"missing in en={sorted(de_keys - en_keys)!r}"
		)
	return locales


def validate_dependencies() -> dict[str, Any]:
	dependencies = _object(_read_json(DEPENDENCIES_PATH), "dependencies")
	_exact_fields(dependencies, {"schemaVersion", "plugins", "tools"}, "dependencies")
	if dependencies["schemaVersion"] != 1:
		raise ValidationError("dependencies has unsupported schemaVersion")
	plugins = _object(dependencies["plugins"], "dependencies plugins")
	expected_plugins = {"nvimCmp", "cmpNvimLsp", "blinkCmp", "nvimLint"}
	if set(plugins) != expected_plugins:
		raise ValidationError(
			"dependency plugins differ; "
			f"missing={sorted(expected_plugins - set(plugins))!r}, "
			f"unexpected={sorted(set(plugins) - expected_plugins)!r}"
		)
	for name, raw_plugin in plugins.items():
		plugin = _object(raw_plugin, f"dependency plugin {name}")
		_exact_fields(plugin, {"source", "revision"}, f"dependency plugin {name}")
		source = _string(plugin["source"], f"dependency plugin {name} source")
		if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git", source):
			raise ValidationError(f"dependency plugin {name} source is not an HTTPS GitHub URL")
		revision = _string(plugin["revision"], f"dependency plugin {name} revision")
		if not re.fullmatch(r"[0-9a-f]{40}", revision):
			raise ValidationError(f"dependency plugin {name} revision must be a full commit ID")
	tools = _object(dependencies["tools"], "dependencies tools")
	_exact_fields(
		tools,
		{"pyright", "pyrightSha512", "ruff", "clangTidy", "markdownlintCli2"},
		"dependencies tools",
	)
	for name in ("pyright", "ruff", "clangTidy", "markdownlintCli2"):
		version = tools[name]
		value = _string(version, f"dependency tool {name} version")
		if not VERSION_PATTERN.fullmatch(value):
			raise ValidationError(f"dependency tool {name} must use an exact X.Y.Z version")
	pyright_sha512 = _string(tools["pyrightSha512"], "Pyright archive SHA-512")
	if not re.fullmatch(r"[0-9a-f]{128}", pyright_sha512):
		raise ValidationError("Pyright archive SHA-512 must be 128 lowercase hexadecimal characters")
	return dependencies


def _validate_message_key(key: Any, label: str, message_keys: set[str]) -> str:
	result = _string(key, label)
	if result not in message_keys:
		raise ValidationError(f"{label} references missing locale key {result!r}")
	return result


def _repository_file(relative: Any, label: str) -> str:
	value = _string(relative, label)
	path = Path(value)
	if path.is_absolute() or ".." in path.parts:
		raise ValidationError(f"{label} must be a repository-relative path: {value!r}")
	resolved = (REPOSITORY_ROOT / path).resolve()
	if REPOSITORY_ROOT.resolve() not in resolved.parents or not resolved.is_file():
		raise ValidationError(f"{label} does not identify a repository file: {value!r}")
	return value


def load_plans() -> dict[str, dict[str, Any]]:
	validate_dependencies()
	locales = load_locales()
	message_keys = set(locales["de"])
	for category in ALLOWED_CATEGORIES:
		_validate_message_key(
			f"category.{category}",
			f"category {category} locale key",
			message_keys,
		)
	plans: dict[str, dict[str, Any]] = {}
	files = sorted(PLANS_ROOT.glob("*.json"))
	if not files:
		raise ValidationError("no human-test plans found")
	for path in files:
		plan = _object(_read_json(path), f"plan {path.name}")
		_exact_fields(plan, PLAN_FIELDS, f"plan {path.name}")
		if plan["schemaVersion"] != 2:
			raise ValidationError(f"plan {path.name} has unsupported schemaVersion")
		plan_id = _id(plan["id"], f"plan {path.name} id")
		if plan_id in plans:
			raise ValidationError(f"duplicate plan id {plan_id!r}")
		if path.stem != plan_id:
			raise ValidationError(f"plan filename {path.name!r} must match id {plan_id!r}")
		order = plan["order"]
		if type(order) is not int or order < 1:
			raise ValidationError(f"plan {plan_id} order must be a positive integer")
		_validate_message_key(plan["titleKey"], f"plan {plan_id} titleKey", message_keys)
		_validate_message_key(plan["descriptionKey"], f"plan {plan_id} descriptionKey", message_keys)
		_string_set(plan["suites"], f"plan {plan_id} suites", ALLOWED_SUITES)
		profile = _string(plan["profile"], f"plan {plan_id} profile")
		if profile not in ALLOWED_PROFILES:
			raise ValidationError(f"plan {plan_id} has unsupported profile {profile!r}")
		fixture_name = _string(plan["fixture"], f"plan {plan_id} fixture")
		fixture = Path(fixture_name)
		if fixture.is_absolute() or ".." in fixture.parts:
			raise ValidationError(f"plan {plan_id} fixture must be relative")
		if not (FIXTURES_ROOT / fixture).is_file():
			raise ValidationError(f"plan {plan_id} fixture does not exist: {fixture_name!r}")
		steps = _array(plan["steps"], f"plan {plan_id} steps")
		if not steps:
			raise ValidationError(f"plan {plan_id} must contain at least one step")
		step_ids: set[str] = set()
		for index, raw_step in enumerate(steps):
			step = _object(raw_step, f"plan {plan_id} step {index}")
			_exact_fields(step, STEP_FIELDS, f"plan {plan_id} step {index}")
			step_id = _id(step["id"], f"plan {plan_id} step {index} id")
			if step_id in step_ids:
				raise ValidationError(f"plan {plan_id} has duplicate step id {step_id!r}")
			step_ids.add(step_id)
			category = _string(step["category"], f"plan {plan_id} step {step_id} category")
			if category not in ALLOWED_CATEGORIES:
				raise ValidationError(
					f"plan {plan_id} step {step_id} has unsupported category {category!r}"
				)
			_validate_message_key(step["titleKey"], f"plan {plan_id} step {step_id} titleKey", message_keys)
			_validate_message_key(
				step["contextKey"], f"plan {plan_id} step {step_id} contextKey", message_keys
			)
			_validate_message_key(step["actionKey"], f"plan {plan_id} step {step_id} actionKey", message_keys)
			_validate_message_key(
				step["expectedKey"],
				f"plan {plan_id} step {step_id} expectedKey",
				message_keys,
			)
			_string_set(
				step["manualReasons"],
				f"plan {plan_id} step {step_id} manualReasons",
				ALLOWED_REASONS,
			)
			_string_set(
				step["requires"],
				f"plan {plan_id} step {step_id} requires",
				ALLOWED_CAPABILITIES,
				empty_allowed=True,
			)
			evidence = _array(
				step["automatedEvidence"],
				f"plan {plan_id} step {step_id} automatedEvidence",
			)
			if not evidence:
				raise ValidationError(f"plan {plan_id} step {step_id} needs related automated evidence")
			for evidence_index, entry in enumerate(evidence):
				_repository_file(
					entry,
					f"plan {plan_id} step {step_id} automatedEvidence[{evidence_index}]",
				)
		plans[plan_id] = plan
	for suite in ALLOWED_SUITES:
		suite_orders = [plan["order"] for plan in plans.values() if suite in plan["suites"]]
		if len(suite_orders) != len(set(suite_orders)):
			raise ValidationError(f"plan order values must be unique in suite {suite}")
	return plans


def _parse_timestamp(value: Any, label: str, *, allow_empty: bool = False) -> str:
	text = _string(value, label, allow_empty=allow_empty)
	if not text and allow_empty:
		return text
	try:
		datetime.fromisoformat(text.replace("Z", "+00:00"))
	except ValueError as error:
		raise ValidationError(f"{label} is not an ISO-8601 timestamp") from error
	return text


def _bool(value: Any, label: str) -> bool:
	if type(value) is not bool:
		raise ValidationError(f"{label} must be a boolean")
	return value


def _sha256_tree(root: Path, files: list[Path]) -> str:
	digest = hashlib.sha256()
	for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
		relative = path.relative_to(root).as_posix().encode("utf-8")
		digest.update(len(relative).to_bytes(4, "big"))
		digest.update(relative)
		data = path.read_bytes()
		digest.update(len(data).to_bytes(8, "big"))
		digest.update(data)
	return digest.hexdigest()


def definition_fingerprint() -> str:
	files = [
		DEPENDENCIES_PATH,
		HUMAN_ROOT / "framework" / "init.lua",
		HUMAN_ROOT / "framework" / "linter_readiness.lua",
		HUMAN_ROOT / "framework" / "run.ps1",
		HUMAN_ROOT / "framework" / "validate.py",
	]
	for directory in (PLANS_ROOT, LOCALES_ROOT, FIXTURES_ROOT):
		files.extend(path for path in directory.rglob("*") if path.is_file())
	return _sha256_tree(HUMAN_ROOT, files)


def environment_fingerprint() -> str:
	"""Fingerprint only inputs that can change the isolated tool environment."""
	return _sha256_tree(
		HUMAN_ROOT,
		[
			DEPENDENCIES_PATH,
			HUMAN_ROOT / "framework" / "init.lua",
			HUMAN_ROOT / "framework" / "linter_readiness.lua",
		],
	)


def component_fingerprint(path: Path) -> str:
	root = path.resolve()
	files: list[Path] = []
	for directory_name in ("lua", "plugin"):
		directory = root / directory_name
		if not directory.is_dir():
			raise ValidationError(f"component directory is missing: {directory}")
		files.extend(candidate for candidate in directory.rglob("*.lua") if candidate.is_file())
	if not files:
		raise ValidationError(f"component contains no Lua runtime files: {root}")
	return _sha256_tree(root, files)


def validate_result(path: Path) -> ResultAssessment:
	definitions = load_plans()
	result = _object(_read_json(path), "result")
	_exact_fields(result, RESULT_FIELDS, "result")
	if result["schemaVersion"] != 3:
		raise ValidationError("result has unsupported schemaVersion")
	_string(result["runId"], "result runId")
	_parse_timestamp(result["createdAt"], "result createdAt")
	completed_at = _parse_timestamp(result["completedAt"], "result completedAt", allow_empty=True)
	repository = _object(result["repository"], "result repository")
	_exact_fields(repository, {"commit", "dirty"}, "result repository")
	commit = _string(repository["commit"], "result repository commit")
	if commit != "unknown" and not re.fullmatch(r"[0-9a-f]{7,40}", commit):
		raise ValidationError("result repository commit must be a Git object ID or 'unknown'")
	_bool(repository["dirty"], "result repository dirty")
	environment = _object(result["environment"], "result environment")
	_exact_fields(
		environment,
		{
			"language",
			"suite",
			"selectedTests",
			"neovimVersion",
			"audio",
			"braille",
			"definitionSha256",
			"accessLinkPluginSha256",
			"addonVersion",
			"nvdaVersion",
		},
		"result environment",
	)
	language = _string(environment["language"], "result environment language")
	if language not in {"de", "en"}:
		raise ValidationError("result environment language must be de or en")
	suite = _string(environment["suite"], "result environment suite")
	if suite not in {*ALLOWED_SUITES, "all", "custom"}:
		raise ValidationError("result environment suite is unsupported")
	available_tests = {
		f"{plan_id}.{step['id']}": (plan_id, step["id"])
		for plan_id, plan in definitions.items()
		for step in plan["steps"]
	}
	selected_tests = [
		_id(value, "result environment selectedTests entry")
		for value in _array(environment["selectedTests"], "result environment selectedTests")
	]
	if not selected_tests:
		raise ValidationError("result environment selectedTests must not be empty")
	if len(selected_tests) != len(set(selected_tests)):
		raise ValidationError("result environment selectedTests contains duplicates")
	unknown_tests = sorted(set(selected_tests) - set(available_tests))
	if unknown_tests:
		raise ValidationError(
			f"result environment selectedTests contains unknown tests: {unknown_tests!r}"
		)
	if suite != "custom":
		expected_suite_tests = {
			f"{plan_id}.{step['id']}"
			for plan_id, plan in definitions.items()
			if suite == "all" or suite in plan["suites"]
			for step in plan["steps"]
		}
		if set(selected_tests) != expected_suite_tests:
			raise ValidationError("result selectedTests differ from selected suite")
	_string(environment["neovimVersion"], "result environment neovimVersion")
	definition_sha256 = _string(environment["definitionSha256"], "result environment definitionSha256")
	if not SHA256_PATTERN.fullmatch(definition_sha256):
		raise ValidationError("result environment definitionSha256 must be lowercase SHA-256")
	if definition_sha256 != definition_fingerprint():
		raise ValidationError("result uses a different human-test definition revision")
	plugin_sha256 = _string(
		environment["accessLinkPluginSha256"],
		"result environment accessLinkPluginSha256",
	)
	if not SHA256_PATTERN.fullmatch(plugin_sha256):
		raise ValidationError("result environment accessLinkPluginSha256 must be lowercase SHA-256")
	expected_plugin_sha256 = component_fingerprint(REPOSITORY_ROOT / "neovim-plugin")
	if plugin_sha256 != expected_plugin_sha256:
		raise ValidationError("result uses a different Neovim plugin runtime revision")
	_string(environment["addonVersion"], "result environment addonVersion")
	_string(environment["nvdaVersion"], "result environment nvdaVersion")
	capabilities = {
		"audio": _bool(environment["audio"], "result environment audio"),
		"braille": _bool(environment["braille"], "result environment braille"),
	}
	selected_by_plan: dict[str, set[str]] = {}
	for test_id in selected_tests:
		plan_id, step_id = available_tests[test_id]
		selected_by_plan.setdefault(plan_id, set()).add(step_id)
	expected_plan_ids = set(selected_by_plan)
	result_plans = _array(result["plans"], "result plans")
	actual_plan_ids: set[str] = set()
	statuses: list[str] = []
	for plan_index, raw_plan in enumerate(result_plans):
		result_plan = _object(raw_plan, f"result plan {plan_index}")
		_exact_fields(result_plan, RESULT_PLAN_FIELDS, f"result plan {plan_index}")
		plan_id = _id(result_plan["id"], f"result plan {plan_index} id")
		if plan_id in actual_plan_ids:
			raise ValidationError(f"result contains duplicate plan {plan_id!r}")
		actual_plan_ids.add(plan_id)
		if plan_id not in definitions:
			raise ValidationError(f"result references unknown plan {plan_id!r}")
		definition = definitions[plan_id]
		if result_plan["profile"] != definition["profile"]:
			raise ValidationError(f"result plan {plan_id} profile differs from definition")
		expected_steps = {
			step["id"]: step
			for step in definition["steps"]
			if step["id"] in selected_by_plan[plan_id]
		}
		result_steps = _array(result_plan["steps"], f"result plan {plan_id} steps")
		actual_steps: set[str] = set()
		for step_index, raw_step in enumerate(result_steps):
			result_step = _object(raw_step, f"result plan {plan_id} step {step_index}")
			_exact_fields(
				result_step,
				RESULT_STEP_FIELDS,
				f"result plan {plan_id} step {step_index}",
			)
			step_id = _id(result_step["id"], f"result plan {plan_id} step {step_index} id")
			if step_id in actual_steps:
				raise ValidationError(f"result plan {plan_id} duplicates step {step_id!r}")
			actual_steps.add(step_id)
			if step_id not in expected_steps:
				raise ValidationError(f"result plan {plan_id} has unknown step {step_id!r}")
			status = _string(result_step["status"], f"result {plan_id}.{step_id} status")
			if status not in ALLOWED_STATUSES:
				raise ValidationError(f"result {plan_id}.{step_id} status is unsupported")
			note = _string(result_step["note"], f"result {plan_id}.{step_id} note", allow_empty=True)
			if status in NOTE_REQUIRED_STATUSES and not note.strip():
				raise ValidationError(f"result {plan_id}.{step_id} status {status} needs a note")
			missing_requirement = any(
				not capabilities[requirement] for requirement in expected_steps[step_id]["requires"]
			)
			if status == "notApplicable" and not missing_requirement:
				raise ValidationError(
					f"result {plan_id}.{step_id} is notApplicable although requirements are met"
				)
			if missing_requirement and status != "notApplicable":
				raise ValidationError(
					f"result {plan_id}.{step_id} must be notApplicable because a capability is absent"
				)
			statuses.append(status)
		if actual_steps != set(expected_steps):
			raise ValidationError(
				f"result plan {plan_id} steps differ; "
				f"missing={sorted(set(expected_steps) - actual_steps)!r}, "
				f"unexpected={sorted(actual_steps - set(expected_steps))!r}"
			)
	if actual_plan_ids != expected_plan_ids:
		raise ValidationError(
			"result plans differ from selected tests; "
			f"missing={sorted(expected_plan_ids - actual_plan_ids)!r}, "
			f"unexpected={sorted(actual_plan_ids - expected_plan_ids)!r}"
		)
	counts = dict(sorted(Counter(statuses).items()))
	if any(status in counts for status in ("pending", "blocked", "skipped")):
		state = "incomplete"
	elif "fail" in counts:
		state = "fail"
	else:
		state = "pass"
	if state == "incomplete" and completed_at:
		raise ValidationError("incomplete result must have an empty completedAt")
	if state != "incomplete" and not completed_at:
		raise ValidationError("complete result must contain completedAt")
	return ResultAssessment(state=state, counts=counts)


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	subparsers = parser.add_subparsers(dest="command", required=True)
	subparsers.add_parser("plans", help="validate plans, locales, fixtures, and evidence")
	result_parser = subparsers.add_parser("result", help="validate and assess one result JSON")
	result_parser.add_argument("path", type=Path)
	result_parser.add_argument("--json", action="store_true", help="print assessment as JSON")
	subparsers.add_parser("fingerprint", help="print the current test-definition SHA-256")
	subparsers.add_parser(
		"environment-fingerprint",
		help="fingerprint inputs that affect the isolated tool environment",
	)
	component_parser = subparsers.add_parser(
		"component-fingerprint", help="fingerprint the Lua runtime of one plugin tree"
	)
	component_parser.add_argument("path", type=Path)
	return parser.parse_args()


def main() -> int:
	arguments = _parse_args()
	try:
		if arguments.command == "plans":
			plans = load_plans()
			print(f"OK: {len(plans)} human-test plans, 2 locales, and pinned dependencies are valid")
			return 0
		if arguments.command == "fingerprint":
			print(definition_fingerprint())
			return 0
		if arguments.command == "environment-fingerprint":
			print(environment_fingerprint())
			return 0
		if arguments.command == "component-fingerprint":
			print(component_fingerprint(arguments.path))
			return 0
		assessment = validate_result(arguments.path)
		if arguments.json:
			print(json.dumps({"state": assessment.state, "counts": assessment.counts}))
		else:
			counts = ", ".join(f"{name}={count}" for name, count in assessment.counts.items())
			print(f"{assessment.state.upper()}: {counts}")
		return assessment.exit_code
	except ValidationError as error:
		print(f"INVALID: {error}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
