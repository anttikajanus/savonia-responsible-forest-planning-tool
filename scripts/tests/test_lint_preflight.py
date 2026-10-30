"""Check imported lint tools rather than potentially unrelated package metadata."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LintPreflightTests(unittest.TestCase):
    def probe(self, pylint="4.1.3", astroid="4.3.4"):
        with tempfile.TemporaryDirectory() as directory:
            modules = Path(directory)
            for name, version in (("pylint", pylint), ("astroid", astroid)):
                content = ("raise ImportError('controlled missing tool')\n" if version is None
                           else f"__version__ = {version!r}\n")
                (modules / f"{name}.py").write_text(content, encoding="utf-8")
            # Inject at the interpreter boundary: a QGIS launcher can replace PYTHONPATH.
            command = [sys.executable, "-c",
                       "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); "
                       "runpy.run_path(sys.argv.pop(1),run_name='__main__')",
                       str(modules), str(ROOT / "scripts/check_lint_environment.py"),
                       "--qgis-python", "C:/QGIS O'Brien/bin/python-qgis.bat"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            return result, modules

    def test_supported_imports_report_versions_and_actual_paths(self):
        for version in ("4.3.4", "4.3.5", "4.10.0"):
            with self.subTest(astroid=version):
                result, modules = self.probe(astroid=version)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"Pylint: 4.1.3; path: {modules / 'pylint.py'}", result.stdout)
                self.assertIn(f"Astroid: {version}; path: {modules / 'astroid.py'}", result.stdout)

    def test_stale_or_unusable_imports_stop_with_corrective_launcher_command(self):
        for versions in (("4.0.10", "4.3.4"), ("4.1.4", "4.3.4"),
                         ("4.1.3", "4.0.4"), ("4.1.3", "4.3.3"),
                         ("4.1.3", "4.3.4rc1"), ("4.1.3", "unknown"),
                         (None, "4.3.4"), ("4.1.3", None)):
            with self.subTest(versions=versions):
                result, _modules = self.probe(*versions)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("Pylint:", result.stdout)
                self.assertIn("Astroid:", result.stdout)
                self.assertIn("& 'C:/QGIS O''Brien/bin/python-qgis.bat' -m pip install --user --upgrade -r '",
                              result.stdout)
                self.assertIn(str(ROOT / "requirements-dev.txt"), result.stdout)


if __name__ == "__main__":
    unittest.main()
