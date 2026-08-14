from __future__ import annotations

import ast
import pathlib
import unittest


ADDON_ROOT = pathlib.Path(__file__).parents[1] / "addon"
PLUGIN_ROOT = ADDON_ROOT / "globalPlugins" / "NeovimAccessLink"


def parse_python(path: pathlib.Path) -> ast.Module:
	return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class AddonArchitectureTests(unittest.TestCase):
	def test_global_plugin_is_only_a_composition_lifetime_adapter(self) -> None:
		tree = parse_python(PLUGIN_ROOT / "__init__.py")
		plugin = next(
			node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GlobalPlugin"
		)
		methods = [node.name for node in plugin.body if isinstance(node, ast.FunctionDef)]
		self.assertEqual(["__init__", "terminate"], methods)
		runtime_assignments = [
			node
			for node in ast.walk(plugin)
			if isinstance(node, ast.Assign)
			and any(
				isinstance(target, ast.Attribute)
				and isinstance(target.value, ast.Name)
				and target.value.id == "self"
				and target.attr == "_runtime"
				for target in node.targets
			)
		]
		self.assertEqual(1, len(runtime_assignments))
		factory_call = runtime_assignments[0].value
		self.assertIsInstance(factory_call, ast.Call)
		self.assertIsInstance(factory_call.func, ast.Name)
		self.assertEqual("create_runtime", factory_call.func.id)
		self.assertEqual([], factory_call.args)
		self.assertEqual([], factory_call.keywords)

	def test_transport_controls_have_exactly_one_production_gateway(self) -> None:
		owners = []
		for path in PLUGIN_ROOT.rglob("*.py"):
			tree = parse_python(path)
			for node in ast.walk(tree):
				if (
					isinstance(node, ast.Call)
					and isinstance(node.func, ast.Attribute)
					and node.func.attr == "send_control"
				):
					owners.append(path.relative_to(PLUGIN_ROOT).as_posix())
		self.assertEqual(["control_dispatcher.py"], owners)

	def test_client_shutdown_has_exactly_one_production_gateway(self) -> None:
		owners = []
		core_root = pathlib.Path(__file__).parents[1] / "core" / "nvim_nvda_core"
		for path in (*PLUGIN_ROOT.rglob("*.py"), *core_root.rglob("*.py")):
			tree = parse_python(path)
			for node in ast.walk(tree):
				if (
					isinstance(node, ast.Call)
					and isinstance(node.func, ast.Attribute)
					and node.func.attr == "stop"
					and isinstance(node.func.value, ast.Attribute)
					and node.func.value.attr == "client"
				):
					owners.append(path.name)
		self.assertEqual(["client_stopper.py"], owners)

	def test_control_dispatcher_shutdown_has_one_lifetime_owner(self) -> None:
		owners = []
		for path in PLUGIN_ROOT.rglob("*.py"):
			tree = parse_python(path)
			for node in ast.walk(tree):
				if (
					isinstance(node, ast.Attribute)
					and node.attr == "close"
					and isinstance(node.value, ast.Attribute)
					and node.value.attr == "_controlDispatcher"
				):
					owners.append(path.relative_to(PLUGIN_ROOT).as_posix())
		self.assertEqual(["addon_runtime.py"], owners)

	def test_app_module_uses_only_the_public_adapter_module(self) -> None:
		tree = parse_python(ADDON_ROOT / "appModules" / "windowsterminal.py")
		imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
		plugin_imports = [
			node
			for node in imports
			if (isinstance(node, ast.ImportFrom) and node.module == "globalPlugins.NeovimAccessLink")
		]
		self.assertEqual(1, len(plugin_imports))
		self.assertEqual(["adapter_api"], [alias.name for alias in plugin_imports[0].names])

	def test_deprecated_modal_helper_and_legacy_stop_all_are_absent(self) -> None:
		core_root = pathlib.Path(__file__).parents[1] / "core" / "nvim_nvda_core"
		forbidden_references = []
		paths = (path for root in (PLUGIN_ROOT, core_root) for path in root.rglob("*.py"))
		for path in paths:
			for node in ast.walk(parse_python(path)):
				if isinstance(node, ast.Name) and node.id in {"runScriptModalDialog", "stop_all"}:
					forbidden_references.append((path.name, node.id))
				if isinstance(node, ast.Attribute) and node.attr in {
					"runScriptModalDialog",
					"stop_all",
				}:
					forbidden_references.append((path.name, node.attr))
		self.assertEqual([], forbidden_references)

	def test_connection_dialogs_use_nvda_modal_lifetime_tracking(self) -> None:
		tree = parse_python(PLUGIN_ROOT / "connection_dialogs.py")
		modal_imports = [
			alias.name
			for node in ast.walk(tree)
			if isinstance(node, ast.ImportFrom) and node.module == "gui.message"
			for alias in node.names
		]
		self.assertEqual(["displayDialogAsModal"], modal_imports)
		calls = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)]
		self.assertTrue(
			any(
				isinstance(function, ast.Name) and function.id == "displayDialogAsModal" for function in calls
			)
		)
		self.assertFalse(
			any(isinstance(function, ast.Attribute) and function.attr == "ShowModal" for function in calls)
		)

	def test_temporary_binding_state_machine_has_one_dedicated_owner(self) -> None:
		connection_tree = parse_python(PLUGIN_ROOT / "connection_workflow.py")
		binding_tree = parse_python(PLUGIN_ROOT / "temporary_binding.py")
		connection_class = next(
			node
			for node in connection_tree.body
			if isinstance(node, ast.ClassDef) and node.name == "ConnectionWorkflow"
		)
		binding_class = next(
			node
			for node in binding_tree.body
			if isinstance(node, ast.ClassDef) and node.name == "TemporaryBindingWorkflow"
		)
		connection_methods = {
			node.name for node in connection_class.body if isinstance(node, ast.FunctionDef)
		}
		binding_methods = {node.name for node in binding_class.body if isinstance(node, ast.FunctionDef)}
		owned_methods = {
			"offer_temporary_binding",
			"activate_remembered_binding",
			"request_remembered_binding_state",
		}
		self.assertTrue(owned_methods <= binding_methods)
		self.assertTrue(owned_methods.isdisjoint(connection_methods))

	def test_ui_worker_results_return_through_the_runtime_scheduler(self) -> None:
		tree = parse_python(PLUGIN_ROOT / "nvda_ui.py")
		imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
		imports.update(node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module)
		self.assertNotIn("queueHandler", imports)
		self.assertTrue(
			any(
				isinstance(node, ast.Call)
				and isinstance(node.func, ast.Attribute)
				and isinstance(node.func.value, ast.Name)
				and node.func.value.id == "self"
				and node.func.attr == "_queueMainThread"
				for node in ast.walk(tree)
			)
		)

	def test_braille_adapter_uses_a_static_consumer_port(self) -> None:
		tree = parse_python(PLUGIN_ROOT / "nvda_braille.py")
		port_imports = [
			alias.name
			for node in tree.body
			if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "adapter_ports"
			for alias in node.names
		]
		self.assertIn("BrailleAdapterPort", port_imports)
		adapter_function = next(
			node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name == "_get_braille_adapter"
		)
		self.assertEqual("BrailleAdapterPort | None", ast.unparse(adapter_function.returns))

	def test_local_plugin_import_graph_is_acyclic(self) -> None:
		paths = {path.stem: path for path in PLUGIN_ROOT.glob("*.py")}
		edges = {name: set() for name in paths}
		for name, path in paths.items():
			tree = parse_python(path)
			for node in ast.walk(tree):
				if isinstance(node, ast.ImportFrom) and node.level and node.module:
					target = node.module.split(".", 1)[0]
					if target in paths:
						edges[name].add(target)

		visited = set()
		active = set()

		def visit(name):
			if name in active:
				self.fail(f"cyclic local import through {name}")
			if name in visited:
				return
			active.add(name)
			for target in edges[name]:
				visit(target)
			active.remove(name)
			visited.add(name)

		for name in paths:
			visit(name)


if __name__ == "__main__":
	unittest.main()
