from __future__ import annotations

import ast
import pathlib
import unittest


ADDON_ROOT = pathlib.Path(__file__).parents[1] / "addon"
PLUGIN_ROOT = ADDON_ROOT / "globalPlugins" / "NeovimAccessLink"


class AddonArchitectureTests(unittest.TestCase):
	def test_global_plugin_is_only_a_composition_lifetime_adapter(self) -> None:
		source = (PLUGIN_ROOT / "__init__.py").read_text(encoding="utf-8")
		tree = ast.parse(source)
		plugin = next(
			node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GlobalPlugin"
		)
		methods = [node.name for node in plugin.body if isinstance(node, ast.FunctionDef)]
		self.assertEqual(["__init__", "terminate"], methods)
		self.assertIn("self._runtime = create_runtime()", source)

	def test_transport_controls_have_exactly_one_production_gateway(self) -> None:
		owners = []
		for path in PLUGIN_ROOT.rglob("*.py"):
			tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
			tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
			tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
		source = (ADDON_ROOT / "appModules" / "windowsterminal.py").read_text(encoding="utf-8")
		tree = ast.parse(source)
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
		combined = "\n".join(
			path.read_text(encoding="utf-8")
			for root in (PLUGIN_ROOT, core_root)
			for path in root.rglob("*.py")
		)
		self.assertNotIn("runScriptModalDialog", combined)
		self.assertNotIn("stop_all", combined)

	def test_ui_worker_results_return_through_the_runtime_scheduler(self) -> None:
		source = (PLUGIN_ROOT / "nvda_ui.py").read_text(encoding="utf-8")
		tree = ast.parse(source)
		imports = {
			node.names[0].name for node in tree.body if isinstance(node, ast.Import) and len(node.names) == 1
		}
		self.assertNotIn("queueHandler", imports)
		self.assertIn("self._queueMainThread", source)

	def test_braille_adapter_uses_a_static_consumer_port(self) -> None:
		source = (PLUGIN_ROOT / "nvda_braille.py").read_text(encoding="utf-8")
		self.assertIn("from .adapter_ports import BrailleAdapterPort", source)
		self.assertIn("def _get_braille_adapter() -> BrailleAdapterPort | None", source)

	def test_local_plugin_import_graph_is_acyclic(self) -> None:
		paths = {path.stem: path for path in PLUGIN_ROOT.glob("*.py")}
		edges = {name: set() for name in paths}
		for name, path in paths.items():
			tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
