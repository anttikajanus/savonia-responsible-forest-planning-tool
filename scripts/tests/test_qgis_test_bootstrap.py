"""Keep QGIS integration initialization centralized and ahead of plugin imports."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2] / "qgis_plugin/tests/qgis"


class QgisTestBootstrapTests(unittest.TestCase):
    def test_integration_modules_initialize_the_shared_environment_before_qgis_or_plugin_imports(self):
        for path in sorted(ROOT.glob("test_*.py")):
            with self.subTest(module=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                initializers = [node.lineno for node in tree.body if isinstance(node, ast.Assign)
                                and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                                and node.value.func.id == "qgis_application"]
                self.assertEqual(len(initializers), 1, "Use APP = qgis_application() from the shared test environment")
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(("qgis.", "savonia_responsible_")):
                        self.assertGreater(node.lineno, initializers[0], "Bootstrap before importing QGIS or the plugin")
                    if isinstance(node, ast.Call):
                        self.assertFalse(isinstance(node.func, ast.Name) and node.func.id == "QgsApplication",
                                         "Construct QgsApplication only in qgis_test_environment.py")
                        self.assertFalse(isinstance(node.func, ast.Attribute) and node.func.attr == "initQgis",
                                         "Initialize QGIS only in qgis_test_environment.py")


if __name__ == "__main__":
    unittest.main()
