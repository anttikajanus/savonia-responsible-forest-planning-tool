"""Runtime routing, fail-fast prerequisites and complete local check logs."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check


class CheckRunnerTests(unittest.TestCase):
    def setUp(self):
        context = ExitStack()
        self.addCleanup(context.close)
        self.directory = context.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.directory)
        self.output = context.enter_context(redirect_stdout(StringIO()))
        self.error = context.enter_context(redirect_stderr(StringIO()))

    def test_failed_stage_keeps_stdout_stderr_and_reports_nonzero_exit(self):
        command = [sys.executable, "-c", "import sys; print('stdout marker'); print('stderr marker',file=sys.stderr); sys.exit(7)"]
        with self.assertRaisesRegex(check.CheckFailure, "exit 7"):
            check.execute_check("controlled-failure", command, self.root, os.environ.copy())
        text = (self.root / "controlled-failure.log").read_text(encoding="utf-8")
        self.assertIn("stdout marker", text)
        self.assertIn("stderr marker", text)

    def test_success_keeps_full_output_but_prints_a_summary(self):
        check.execute_check("verbose-success", [sys.executable, "-c", "print('detail\\n'*1000)"], self.root, os.environ.copy())
        self.assertEqual((self.root / "verbose-success.log").read_text().count("detail"), 1000)
        self.assertIn("PASS verbose-success", self.output.getvalue())
        self.assertNotIn("detail", self.output.getvalue())

    def test_missing_git_stops_before_selected_suites(self):
        with patch.object(check.shutil, "which", return_value=None), patch.object(check, "execute_check") as execute:
            result = check.main(["--checks", "tooling", "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("Git is missing", self.error.getvalue())
        execute.assert_not_called()
        self.assertEqual(len(list(self.root.glob("*/failure.log"))), 1)

    def test_plain_and_qgis_stages_use_separate_runtimes_and_clean_source_environment(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()
        calls = []

        def record(name, command, _logs, environment):
            calls.append((name, command[0], dict(environment)))

        with patch.object(check, "execute_check", side_effect=record), patch.dict(os.environ, {
                "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT": "stale-installed-plugin"}):
            result = check.main(["--qgis-python", str(launcher), "--logs-dir", str(self.root)])
        self.assertEqual(result, 0)
        by_name = {name: (runtime, environment) for name, runtime, environment in calls}
        for name in ("tooling", "unit"):
            self.assertEqual(by_name[name][0], sys.executable)
        for name in ("preflight-qgis", "lint", "qgis"):
            self.assertEqual(by_name[name][0], str(launcher.resolve()))
        for _name, _runtime, environment in calls:
            self.assertNotIn("RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT", environment)
        self.assertIn("RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT", by_name["qgis"][1])

    def test_qgis_preflight_failure_stops_before_product_checks(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()
        with patch.object(check, "execute_check", side_effect=check.CheckFailure("unwritable cache")) as execute:
            result = check.main(["--checks", "qgis", "--qgis-python", str(launcher), "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertEqual([call.args[0] for call in execute.call_args_list], ["preflight-qgis"])
        self.assertIn("unwritable cache", self.error.getvalue())

    @unittest.skipUnless(shutil.which("powershell"), "Windows entry point requires PowerShell")
    def test_windows_entry_point_propagates_preflight_failure_from_another_directory(self):
        runner = Path(__file__).resolve().parents[1] / "check.ps1"
        result = subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner),
            "-Python", sys.executable, "-Checks", "qgis", "-QgisPython", str(self.root / "missing.bat"),
            "-LogsDir", str(self.root),
        ], cwd=runner.parent, capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("QGIS Python launcher is missing", result.stderr)
        self.assertEqual(len(list(self.root.glob("*/failure.log"))), 1)

    @unittest.skipUnless(os.name == "nt", "QGIS batch launcher check requires Windows")
    def test_relative_qgis_launcher_resolves_from_the_callers_directory(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.write_text("@echo off\nexit /b 23\n", encoding="ascii")
        runner = Path(__file__).resolve().parents[1] / "check.py"
        result = subprocess.run([
            sys.executable, str(runner), "--checks", "qgis", "--qgis-python", launcher.name,
            "--logs-dir", str(self.root),
        ], cwd=self.root, capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight-qgis failed (exit 23)", result.stderr)


if __name__ == "__main__":
    unittest.main()
