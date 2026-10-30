"""Probe real parser imports before tooling discovery can obscure their errors."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ToolingPreflightTests(unittest.TestCase):
    def probe(self, markdown=None, yaml=None, namespace=False, deny_source=False):
        with tempfile.TemporaryDirectory() as directory:
            modules = Path(directory)
            (modules / "markdown_it").mkdir()
            if not namespace:
                (modules / "markdown_it/__init__.py").write_text(
                    markdown if markdown is not None else
                    "class MarkdownIt:\n    def render(self, text): return '<h1>preflight</h1>\\n'\n",
                    encoding="utf-8")
            (modules / "yaml.py").write_text(
                yaml if yaml is not None else "def safe_load(text): return {'preflight': True}\n",
                encoding="utf-8")
            probe = (
                "import runpy,sys; from pathlib import Path; "
                "sys.path.insert(0,sys.argv.pop(1)); "
            )
            if namespace:
                # Hide installed copies so the fixture resolves as a namespace.
                probe += (
                    "sys.path[:]=[p for p in sys.path "
                    "if not (Path(p)/'markdown_it'/'__init__.py').is_file()]; "
                )
            if deny_source:
                # Reproduce a namespace package whose initializer is unreadable
                # without changing machine ACLs or requiring Windows privileges.
                probe += (
                    "original_open=Path.open; "
                    "Path.open=lambda self,*a,**k: (_ for _ in ()).throw("
                    "PermissionError('controlled source access denied')) "
                    "if self.name=='__init__.py' and self.parent.name=='markdown_it' "
                    "else original_open(self,*a,**k); "
                )
            probe += "runpy.run_path(sys.argv.pop(1),run_name='__main__')"
            result = subprocess.run([
                sys.executable, "-c", probe, str(modules),
                str(ROOT / "scripts/check_tooling_environment.py"),
            ], cwd=ROOT, capture_output=True, text=True, check=False, timeout=15)
            return result, modules

    def test_success_reports_interpreter_and_actual_import_paths(self):
        result, modules = self.probe()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(sys.executable, result.stdout)
        self.assertIn(str(modules / "markdown_it/__init__.py"), result.stdout)
        self.assertIn(str(modules / "yaml.py"), result.stdout)

    def test_broken_imports_missing_symbols_and_broken_parsers_fail(self):
        cases = (
            {"markdown": "raise ModuleNotFoundError('controlled missing package')\n"},
            {"markdown": "raise PermissionError('controlled import denied')\n"},
            {"markdown": "other = 1\n"},
            {"markdown": "class MarkdownIt:\n    def render(self, text): raise ValueError('broken parser')\n"},
            {"markdown": "class MarkdownIt:\n    def render(self, text): return 'wrong output'\n"},
            {"yaml": "safe_load = None\n"},
            {"yaml": "def safe_load(text): raise ValueError('broken YAML')\n"},
            {"yaml": "def safe_load(text): return {}\n"},
        )
        for case in cases:
            with self.subTest(case=case):
                result, modules = self.probe(**case)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 1, output)
                self.assertIn("Tooling dependency preflight failed", output)
                self.assertIn(str(modules), output)
                self.assertIn("-m pip install", output)
                self.assertIn(str(ROOT / "requirements-dev.txt"), output)
                self.assertNotIn("Traceback", output)

    def test_namespace_package_reports_initializer_location(self):
        result, modules = self.probe(namespace=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(str(modules / "markdown_it/__init__.py"), result.stdout)
        self.assertIn("FileNotFoundError", result.stdout)
        self.assertIn("file permissions", result.stdout)

    def test_unreadable_namespace_initializer_exposes_permission_error(self):
        result, modules = self.probe(namespace=True, deny_source=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(str(modules / "markdown_it/__init__.py"), result.stdout)
        self.assertIn("PermissionError: controlled source access denied", result.stdout)
        self.assertIn("file permissions", result.stdout)

    def test_runner_reports_broken_dependency_before_discovery_and_keeps_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "markdown_it.py").write_text("wrong_symbol = 1\n", encoding="utf-8")
            logs = root / "logs"
            environment = dict(os.environ, PYTHONPATH=str(root))
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/check.py"), "--checks", "tooling",
                "--logs-dir", str(logs),
            ], cwd=ROOT, env=environment, capture_output=True, text=True, check=False, timeout=15)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("preflight-tooling failed", result.stderr)
            run, = list(logs.iterdir())
            self.assertFalse((run / "tooling.log").exists())
            diagnostics = (run / "preflight-tooling.log").read_text(encoding="utf-8")
            self.assertIn(str(root / "markdown_it.py"), diagnostics)
            self.assertIn("MarkdownIt is missing", diagnostics)
            self.assertIn("-m pip install", diagnostics)
            self.assertIn("preflight-tooling", (run / "failure.log").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
