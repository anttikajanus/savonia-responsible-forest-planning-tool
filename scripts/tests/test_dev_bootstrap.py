"""Observable readiness and failure behavior of the local environment command."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import setup_dev_environment as bootstrap


class DevelopmentBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        isolation = patch.dict(os.environ, {"ProgramFiles": str(self.root / "ProgramFiles")})
        isolation.start()
        self.addCleanup(isolation.stop)
        (self.root / "scripts").mkdir()
        runtimes = [{"version": version, "version_int": number, "launcher": "python-qgis.bat",
                     "sha256": pin * 64, "installer": version + ".msi"}
                    for version, number, pin in (("3.44.0", 34400, "a"), ("4.2.3", 40203, "b"))]
        (self.root / "scripts/qgis-runtimes.json").write_text(json.dumps({
            "base_url": "https://example.invalid", "default_version": "4.2.3", "runtimes": runtimes,
        }), encoding="utf-8")
        (self.root / "requirements-dev.txt").write_text("pylint==4.1.3\n", encoding="utf-8")
        self.commands = []
        self.parser_failure = False
        self.real_run = subprocess.run
        self.launcher = self.root / "runtime/bin/python-qgis.bat"
        self.launcher.parent.mkdir(parents=True)
        self.launcher.touch()

    def process(self, command, **kwargs):
        if command[0] == "git":
            return self.real_run(command, **kwargs)
        self.commands.append(command)
        if self.parser_failure and any(str(item).endswith("check_tooling_environment.py") for item in command):
            raise subprocess.CalledProcessError(1, command)
        if command[1:3] == ["-m", "venv"]:
            environment = Path(command[-1])
            executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.touch()
            site = environment / ("Lib/site-packages" if os.name == "nt" else
                                  f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
            site.mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(command, 0)

    def invoke(self, *arguments, runtime_error=None):
        with patch.object(bootstrap, "ROOT", self.root), patch.object(
                bootstrap.subprocess, "run", side_effect=self.process), patch.object(
                bootstrap.runtime, "setup_runtime", side_effect=runtime_error,
                return_value=self.launcher), redirect_stdout(StringIO()) as output, redirect_stderr(StringIO()):
            code = bootstrap.main(list(arguments))
        return code, output.getvalue()

    def test_selected_baseline_prepares_shared_tools_and_probes_actual_imports(self):
        code, output = self.invoke("--version", "3.44.0")
        self.assertEqual(code, 0)
        config = json.loads((self.root / ".local/dev-environment/environment.json").read_text())
        self.assertTrue(config["tooling_ready"])
        self.assertEqual(config["runtimes"]["3.44.0"]["status"], "ready")
        self.assertEqual(config["runtimes"]["4.2.3"]["status"], "not_selected")
        self.assertTrue(Path(config["python"]).is_absolute())
        self.assertTrue((Path(config["tooling_path"]) / "sitecustomize.py").is_file())
        probes = [" ".join(command) for command in self.commands]
        self.assertTrue(any("check_tooling_environment.py" in command for command in probes))
        self.assertTrue(any("check_lint_environment.py" in command and "run_dev_tool.py" in command
                            for command in probes))
        self.assertTrue(any("-m pip install --upgrade -r" in command for command in probes))
        self.assertIn("4.2.3: not_selected", output)
        self.commands.clear()
        self.assertEqual(self.invoke("--version", "3.44.0")[0], 0)
        self.assertFalse(any(command[1:3] == ["-m", "venv"] for command in self.commands))

    def test_failed_runtime_cannot_be_reported_ready(self):
        code, _output = self.invoke("--version", "4.2.3", runtime_error=RuntimeError("fixture extraction failure"))
        self.assertEqual(code, 1)
        config = json.loads((self.root / ".local/dev-environment/environment.json").read_text())
        self.assertEqual(config["status"], "failed")
        self.assertEqual(config["runtimes"]["4.2.3"]["status"], "failed")
        self.assertIn("fixture extraction failure", config["runtimes"]["4.2.3"]["error"])

    def test_existing_system_runtime_is_probed_without_downloading_another_copy(self):
        installed = self.root / "ProgramFiles/QGIS 4.2.3/bin/python-qgis.bat"
        installed.parent.mkdir(parents=True)
        installed.touch()
        code, _output = self.invoke("--version", "4.2.3", runtime_error=AssertionError("Unexpected download"))
        self.assertEqual(code, 0)
        config = json.loads((self.root / ".local/dev-environment/environment.json").read_text())
        self.assertEqual(Path(config["runtimes"]["4.2.3"]["launcher_path"]), installed.resolve())
        self.assertEqual(config["runtimes"]["4.2.3"]["status"], "ready")

    def test_failed_parser_probe_invalidates_previous_tooling_readiness(self):
        self.assertEqual(self.invoke("--version", "3.44.0")[0], 0)
        self.parser_failure = True
        self.assertEqual(self.invoke("--version", "3.44.0")[0], 1)
        config = json.loads((self.root / ".local/dev-environment/environment.json").read_text())
        self.assertFalse(config["tooling_ready"])
        self.assertEqual(config["status"], "failed")
        self.assertEqual(config["runtimes"]["3.44.0"]["status"], "not_run")


if __name__ == "__main__":
    unittest.main()
