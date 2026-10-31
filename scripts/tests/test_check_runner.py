"""Runtime routing, fail-fast prerequisites and complete local check logs."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check
import run_qgis_tests


class CheckRunnerTests(unittest.TestCase):
    def setUp(self):
        context = ExitStack()
        self.addCleanup(context.close)
        self.directory = context.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.directory)
        self.output = context.enter_context(redirect_stdout(StringIO()))
        self.error = context.enter_context(redirect_stderr(StringIO()))
        context.enter_context(patch.object(check, "managed_tools", return_value={}))

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

    def test_expected_failure_is_not_counted_as_an_unexpected_failure(self):
        code = ("import unittest\nclass Case(unittest.TestCase):\n"
                "    @unittest.expectedFailure\n    def test_expected(self): self.fail('expected')\n"
                "unittest.main()\n")
        check.execute_check("expected", [sys.executable, "-c", code], self.root, os.environ.copy())
        result = json.loads((self.root / "expected.result.json").read_text())
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["tests"]["expected_failures"], 1)
        self.assertEqual(result["tests"]["failures"], 0)

    def test_failed_test_names_are_reported_even_outside_the_log_tail(self):
        probe = """import sys, unittest
class Case(unittest.TestCase):
    def test_bad(self):
        with self.subTest(value=3):
            self.fail('controlled failure')
    def test_error(self):
        raise RuntimeError('controlled error')
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Case))
print('detail\\n'*30, file=sys.stderr)
sys.exit(not result.wasSuccessful())
"""
        command = [sys.executable, "-c", probe]
        with self.assertRaises(check.CheckFailure) as failure:
            check.execute_check("failed-tests", command, self.root, os.environ.copy())
        self.assertIn("Failing tests:", str(failure.exception))
        self.assertIn("FAIL: test_bad (__main__.Case.test_bad) (value=3)", str(failure.exception))
        self.assertIn("ERROR: test_error (__main__.Case.test_error)", str(failure.exception))

    def test_timeout_preserves_output_and_identifies_the_last_test(self):
        command = [sys.executable, "-c", "import time; print('test_hung (suite.Case) ... ', flush=True); time.sleep(60)"]
        with self.assertRaises(check.CheckFailure) as failure:
            check.execute_check("hung", command, self.root, os.environ.copy(), timeout=0.5)
        self.assertIn("timed out after 0.5s", str(failure.exception))
        self.assertIn("Last test reported: test_hung (suite.Case)", str(failure.exception))
        self.assertIn("test_hung", (self.root / "hung.log").read_text())

    def test_timeout_must_be_positive_and_finite(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as failure:
                check.main(["--timeout", value, "--logs-dir", str(self.root)])
            self.assertEqual(failure.exception.code, 2)
        self.assertIn("--timeout must be positive and finite", self.error.getvalue())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_direct_qgis_runner_enables_fault_handler_before_bootstrap(self):
        probe = (
            "import faulthandler, sys, types; faulthandler.disable(); "
            f"sys.path.insert(0, {str(Path(run_qgis_tests.__file__).parent)!r}); "
            "bootstrap = types.ModuleType('qgis_test_environment'); "
            "exec(\"def initialize():\\n"
            "    assert faulthandler.is_enabled(), 'fault handler disabled'\\n"
            "    raise RuntimeError('controlled bootstrap failure')\", "
            "{'faulthandler': faulthandler}, bootstrap.__dict__); "
            "bootstrap.qgis_application = bootstrap.initialize; bootstrap.environment_root = lambda: ''; "
            "sys.modules['qgis_test_environment'] = bootstrap; "
            "import run_qgis_tests; sys.exit(run_qgis_tests.main(['--preflight-only']))"
        )
        result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("controlled bootstrap failure", result.stderr)
        self.assertNotIn("fault handler disabled", result.stderr)

    @unittest.skipUnless(os.name == "nt", "Windows batch launcher process tree")
    def test_timeout_stops_the_python_child_of_a_batch_launcher(self):
        marker = self.root / "child-open-file"
        child = self.root / "child.py"
        child.write_text("import time\n" + f"with open({str(marker)!r}, 'w') as output:\n"
                         "    print('child running', flush=True)\n    time.sleep(60)\n", encoding="utf-8")
        launcher = self.root / "launcher.bat"
        launcher.write_text(f'@echo off\n"{sys.executable}" "{child}"\n', encoding="utf-8")
        with self.assertRaisesRegex(check.CheckFailure, "timed out") as failure:
            check.execute_check("batch-hung", [str(launcher)], self.root, os.environ.copy(), timeout=1.5)
        self.assertNotIn("cleanup failed", str(failure.exception))
        self.assertIn("child running", (self.root / "batch-hung.log").read_text())
        # The child keeps this handle open while running; Windows denies deletion.
        marker.unlink()

    @unittest.skipUnless(shutil.which("powershell"), "Windows entry point requires PowerShell")
    def test_windows_entry_point_forwards_timeout_and_saves_failure_summary(self):
        launcher = self.root / "hung.bat"
        launcher.write_text('@echo off\n"' + sys.executable + '" -c "import time; time.sleep(60)"\n', encoding="utf-8")
        runner = Path(check.__file__).with_suffix(".ps1")
        result = subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner),
            "-Python", sys.executable, "-Checks", "qgis", "-QgisPython", str(launcher),
            "-LogsDir", str(self.root), "-TimeoutSeconds", "0.5",
        ], capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertIn("preflight-qgis timed out after 0.5s", result.stderr)
        summary = next(self.root.glob("*/failure.log")).read_text()
        self.assertIn("timed out after 0.5s", summary)
        self.assertNotIn("cleanup failed", summary)

    @unittest.skipUnless(shutil.which("powershell"), "Windows entry point requires PowerShell")
    def test_entry_point_without_git_still_reaches_python_preflight_and_summary(self):
        powershell = shutil.which("powershell")
        runner = Path(check.__file__).with_suffix(".ps1")
        result = subprocess.run([
            powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner),
            "-Python", sys.executable, "-Checks", "qgis", "-QgisPython", str(self.root / "missing.bat"),
            "-LogsDir", str(self.root),
        ], env=dict(os.environ, PATH=""), capture_output=True, text=True, check=False, timeout=20)
        self.assertEqual(result.returncode, 1)
        self.assertIn("QGIS Python launcher is missing", result.stderr)
        self.assertEqual(len(list(self.root.glob("*/summary.json"))), 1)

    def test_missing_git_stops_before_selected_suites(self):
        with patch.object(check.shutil, "which", return_value=None), patch.object(check, "execute_check") as execute:
            result = check.main(["--checks", "tooling", "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("Git is missing", self.error.getvalue())
        execute.assert_not_called()
        self.assertEqual(len(list(self.root.glob("*/failure.log"))), 1)

    def test_qgis_subset_summary_identifies_omitted_groups_and_actual_test_count(self):
        launcher = self.root / "qgis.bat"
        launcher.touch()

        def qgis_stage(name, _arguments, _launcher, logs, environment, timeout):
            code = ("import unittest; "
                    "suite=unittest.TestSuite([unittest.FunctionTestCase(lambda: None)]); "
                    "unittest.TextTestRunner().run(suite)")
            check.execute_check(name, [sys.executable, "-c", code], logs, environment, timeout)

        with patch.object(check, "qgis_check", side_effect=qgis_stage):
            result = check.main(["--checks", "qgis", "--qgis-python", str(launcher),
                                 "--logs-dir", str(self.root)])
        self.assertEqual(result, 0)
        report = json.loads(next(self.root.glob("*/summary.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["selected_checks"], ["qgis"])
        self.assertEqual(report["not_selected_checks"], ["tooling", "unit", "lint"])
        self.assertEqual(report["stages"]["unit"]["status"], "not_selected")
        self.assertEqual(report["stages"]["qgis"]["tests"]["run"], 1)
        self.assertIsNone(report["stages"]["lint"]["tests"])
        self.assertIn("Not selected: tooling, unit, lint", self.output.getvalue())
        self.assertIn("revision", report["source"])
        self.assertIn("dirty", report["source"])

    def test_preflight_failure_summary_marks_unexecuted_selected_suites(self):
        result = check.main(["--checks", "qgis", "--qgis-python", str(self.root / "missing.bat"),
                             "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        report = json.loads(next(self.root.glob("*/summary.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["stages"]["preflight-qgis"]["status"], "failed")
        self.assertEqual(report["stages"]["qgis"]["status"], "not_run")
        self.assertIsNone(report["stages"]["qgis"]["tests"])
        self.assertIn("missing.bat", report["error"])
        self.assertIn("Not run: qgis", self.output.getvalue())

    def test_environment_discovery_failure_still_writes_a_failed_summary(self):
        with patch.object(check, "default_qgis", side_effect=ValueError("fixture invalid runtime inventory")):
            result = check.main(["--checks", "qgis", "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        report = json.loads(next(self.root.glob("*/summary.json")).read_text())
        self.assertEqual(report["status"], "failed")
        self.assertIn("invalid runtime inventory", report["error"])
        self.assertEqual(report["stages"]["qgis"]["status"], "not_run")

    def test_failed_unit_suite_summary_preserves_revision_dirty_state_and_failure_counts(self):
        if not shutil.which("git"):
            self.skipTest("Git is required")
        suite = self.root / "qgis_plugin/tests"
        suite.mkdir(parents=True)
        (suite / "test_fixture.py").write_text(
            "import unittest\nclass Case(unittest.TestCase):\n"
            "    def test_failure(self): self.fail('fixture failure')\n"
            "    @unittest.skip('fixture skip')\n    def test_skipped(self): pass\n", encoding="utf-8")
        subprocess.run(["git", "init", str(self.root)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture"],
                       capture_output=True, check=True)
        revision = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.strip()
        (suite / "test_fixture.py").write_text((suite / "test_fixture.py").read_text() + "\n# edited\n")
        with patch.object(check, "ROOT", self.root):
            result = check.main(["--checks", "unit", "--qgis-python", str(self.root / "unused.bat"),
                                 "--logs-dir", str(self.root / ".local/checks")])
        self.assertEqual(result, 1)
        report = json.loads(next(self.root.glob(".local/checks/*/summary.json")).read_text())
        self.assertEqual(report["source"]["revision"], revision)
        self.assertTrue(report["source"]["dirty"])
        self.assertEqual(report["stages"]["unit"]["status"], "failed")
        self.assertEqual(report["stages"]["unit"]["tests"]["run"], 2)
        self.assertEqual(report["stages"]["unit"]["tests"]["failures"], 1)
        self.assertEqual(report["stages"]["unit"]["tests"]["skipped"], 1)

    def test_plain_and_qgis_stages_use_separate_runtimes_and_clean_source_environment(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()
        calls = []

        def record(name, command, _logs, environment, timeout):
            calls.append((name, command[0], dict(environment), timeout))
            if name == "preflight-lint":
                (_logs / "preflight-lint.log").write_text("Pylint/Astroid import details\n", encoding="utf-8")
            if name == "preflight-tooling":
                (_logs / "preflight-tooling.log").write_text("Markdown/YAML import details\n", encoding="utf-8")

        with patch.object(check, "execute_check", side_effect=record), patch.dict(os.environ, {
                "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT": "stale-installed-plugin"}):
            result = check.main(["--qgis-python", str(launcher), "--logs-dir", str(self.root), "--timeout", "42"])
        self.assertEqual(result, 0)
        self.assertIn("Pylint/Astroid import details", self.output.getvalue())
        self.assertIn("Markdown/YAML import details", self.output.getvalue())
        by_name = {name: (runtime, environment) for name, runtime, environment, _timeout in calls}
        for name in ("preflight-tooling", "tooling", "unit"):
            self.assertEqual(by_name[name][0], sys.executable)
        for name in ("preflight-qgis", "preflight-lint", "lint", "qgis"):
            self.assertEqual(by_name[name][0], str(launcher.resolve()))
        for _name, _runtime, environment, timeout in calls:
            self.assertNotIn("RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT", environment)
            self.assertEqual(environment["PYTHONFAULTHANDLER"], "1")
            self.assertEqual(timeout, 42)
        self.assertIn("RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT", by_name["qgis"][1])

    def test_qgis_preflight_failure_stops_before_product_checks(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()
        with patch.object(check, "execute_check", side_effect=check.CheckFailure("unwritable cache")) as execute:
            result = check.main(["--checks", "qgis", "--qgis-python", str(launcher), "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertEqual([call.args[0] for call in execute.call_args_list], ["preflight-qgis"])
        self.assertIn("unwritable cache", self.error.getvalue())

    def test_lint_preflight_failure_stops_before_all_selected_suites(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()

        def reject_stale_tools(name, _command, logs, *_arguments):
            if name == "preflight-tooling":
                (logs / "preflight-tooling.log").write_text("parser imports checked\n", encoding="utf-8")
            if name == "preflight-lint":
                raise check.CheckFailure("Astroid 4.0.4 is too old; upgrade requirements-dev.txt")

        with patch.object(check, "execute_check", side_effect=reject_stale_tools) as execute:
            result = check.main(["--qgis-python", str(launcher), "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("Astroid 4.0.4", self.error.getvalue())
        self.assertNotIn("tooling", [call.args[0] for call in execute.call_args_list])
        self.assertEqual(execute.call_args_list[-1].args[1],
                         [str(launcher.resolve()), "scripts/check_lint_environment.py",
                          "--qgis-python", str(launcher.resolve())])

    def test_tooling_preflight_failure_stops_before_all_selected_suites(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()

        def reject_parsers(name, *_arguments):
            if name == "preflight-tooling":
                raise check.CheckFailure("markdown_it initializer: PermissionError: access denied")

        with patch.object(check, "execute_check", side_effect=reject_parsers) as execute:
            result = check.main(["--qgis-python", str(launcher), "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("PermissionError", self.error.getvalue())
        self.assertEqual([call.args[0] for call in execute.call_args_list], ["preflight-git", "preflight-tooling"])
        self.assertEqual(execute.call_args_list[-1].args[1],
                         [sys.executable, "scripts/check_tooling_environment.py"])

    def test_tooling_and_lint_dependencies_are_not_checked_for_other_selections(self):
        launcher = self.root / "qgis-launcher.bat"
        launcher.touch()
        for selection, names in (("unit", ["unit"]), ("qgis", ["preflight-qgis", "qgis"])):
            with self.subTest(selection=selection), patch.object(check, "execute_check") as execute:
                result = check.main(["--checks", selection, "--qgis-python", str(launcher),
                                     "--logs-dir", str(self.root)])
                self.assertEqual(result, 0)
                self.assertEqual([call.args[0] for call in execute.call_args_list], names)

    @unittest.skipUnless(os.name == "nt", "Batch launcher requires Windows")
    def test_launcher_replacing_pythonpath_cannot_hide_stale_imported_tools(self):
        shadow = self.root / "launcher-tools"
        shadow.mkdir()
        (shadow / "pylint.py").write_text("__version__ = '4.1.3'\n", encoding="utf-8")
        (shadow / "astroid.py").write_text("__version__ = '4.0.4'\n", encoding="utf-8")
        launcher = self.root / "qgis-launcher.bat"
        launcher.write_text(f'@echo off\nset "PYTHONPATH={shadow}"\n"{sys.executable}" %*\n', encoding="utf-8")
        with patch.object(check, "qgis_check"), patch.dict(os.environ, {"PYTHONPATH": "discarded-override"}):
            result = check.main(["--checks", "lint", "--qgis-python", str(launcher),
                                 "--logs-dir", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("Astroid: 4.0.4", self.error.getvalue())
        self.assertIn(str(shadow / "astroid.py"), self.error.getvalue())
        self.assertIn("-m pip install --user --upgrade", self.error.getvalue())
        self.assertEqual(list(self.root.glob("*/lint.log")), [])

    @unittest.skipUnless(os.name == "nt", "QGIS batch launcher requires Windows")
    def test_managed_lint_imports_survive_a_launcher_replacing_pythonpath(self):
        stale, managed = self.root / "stale", self.root / "managed"
        stale.mkdir()
        managed.mkdir()
        for folder, version in ((stale, "4.0.4"), (managed, "4.3.4")):
            (folder / "astroid.py").write_text(f"__version__ = {version!r}\n", encoding="utf-8")
            (folder / "pylint.py").write_text(
                "__version__ = '4.1.3'\nif __name__ == '__main__': print('managed lint ran')\n", encoding="utf-8")
        launcher = self.root / "launcher.bat"
        launcher.write_text(f'@echo off\nset "PYTHONPATH={stale}"\n"{sys.executable}" %*\n', encoding="utf-8")
        with patch.object(check, "qgis_check"):
            result = check.main(["--checks", "lint", "--qgis-python", str(launcher),
                                 "--tools-path", str(managed), "--logs-dir", str(self.root)])
        self.assertEqual(result, 0)
        log = next(self.root.glob("*/preflight-lint.log")).read_text(encoding="utf-8")
        self.assertIn(str(managed.resolve() / "astroid.py"), log)
        self.assertIn("managed lint ran", next(self.root.glob("*/lint.log")).read_text())

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
