"""Run local checks with separate plain-Python and QGIS runtimes and saved logs."""

import argparse
from collections import deque
from configparser import ConfigParser
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
import zipfile

from check_report import record_stage, source_state, write_summary
from dev_environment import default_qgis, managed_tools


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT_KEY = "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT"
DEFAULT_TIMEOUT = 600


class CheckFailure(Exception):
    """An actionable preflight or selected-check failure."""

    def __init__(self, message, stage=None):
        super().__init__(message)
        self.stage = stage


def failure_details(log):
    failures = []
    last_test = None
    tail = deque(maxlen=12)
    with log.open(encoding="utf-8", errors="replace") as output:
        for line in output:
            tail.append(line)
            if re.match(r"^(FAIL|ERROR): \S+ \(.+\)", line) and line.strip() not in failures:
                failures.append(line.strip())
            test = re.match(r"^(\S+ \([^)]+\))", line)
            if test:
                last_test = test[1]
    summary = "Failing tests:\n" + "\n".join(failures) if failures else ""
    if not failures and last_test:
        summary = f"Last test reported: {last_test}"
    return "\n".join(part for part in (summary, "".join(tail).strip()) if part)


def terminate_check(process, output):
    """Stop descendants too: Windows QGIS launchers are batch files."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=output, stderr=subprocess.STDOUT, check=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as error:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            raise CheckFailure(f"Could not terminate the complete check process tree: {error}") from error
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def execute_check(name, command, logs, environment, timeout=DEFAULT_TIMEOUT):
    log = logs / (name + ".log")
    started = time.monotonic()
    try:
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=os.name != "nt")
            try:
                process.wait(timeout=timeout)
                failure = f"failed (exit {process.returncode})" if process.returncode else None
            except subprocess.TimeoutExpired:
                failure = f"timed out after {timeout:g}s"
                try:
                    terminate_check(process, output)
                except (CheckFailure, OSError, subprocess.SubprocessError) as error:
                    failure += f"; cleanup failed: {error}"
    except OSError as error:
        with log.open("a", encoding="utf-8") as output:
            output.write(str(error) + "\n")
        record_stage(logs, name, "failed", time.monotonic() - started)
        raise CheckFailure(f"{name} could not start; see {log}: {error}", stage=name) from error
    result = record_stage(logs, name, "timed_out" if failure and "timed out" in failure else
                          "failed" if failure else "passed", time.monotonic() - started, process.returncode)
    if failure:
        raise CheckFailure(f"{name} {failure}; see {log}\n{failure_details(log)}", stage=name)
    count = f"; {result['tests']['run']} tests" if result["tests"] is not None else ""
    print(f"PASS {name} ({time.monotonic() - started:.1f}s{count})", flush=True)


def qgis_check(name, arguments, qgis_python, logs, environment, timeout):
    # The parent owns cleanup, after the QGIS child releases Windows file handles.
    with tempfile.TemporaryDirectory(prefix="qgis-environment-", dir=logs) as folder:
        if not Path(folder).resolve().is_relative_to(logs.resolve()):
            raise CheckFailure("The QGIS environment must stay inside the check log directory.")
        isolated = dict(environment, RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT=folder)
        execute_check(name, [qgis_python, "scripts/run_qgis_tests.py", *arguments], logs, isolated, timeout)


def preflight(arguments, logs, environment):
    if sys.version_info < (3, 10):
        raise CheckFailure("Local checks require plain Python 3.10 or newer.")
    details = [f"Plain Python: {sys.executable}", f"Version: {sys.version.split()[0]}"]
    try:
        if "tooling" in arguments.checks:
            git = shutil.which("git", path=environment.get("PATH"))
            if git is None:
                raise CheckFailure("Git is missing from plain Python's PATH. Install Git or add its cmd directory to PATH.",
                                   stage="preflight-git")
            details.append(f"Git: {git}")
            execute_check("preflight-git", [git, "--version"], logs, environment, arguments.timeout)
            execute_check("preflight-tooling", [sys.executable, "scripts/check_tooling_environment.py"],
                          logs, environment, arguments.timeout)
            print((logs / "preflight-tooling.log").read_text(encoding="utf-8"), end="", flush=True)
        if {"lint", "qgis"}.intersection(arguments.checks):
            if not Path(arguments.qgis_python).is_file():
                raise CheckFailure(f"QGIS Python launcher is missing: {arguments.qgis_python}. Use --qgis-python to select it.",
                                   stage="preflight-qgis")
            details.append(f"QGIS launcher: {arguments.qgis_python}")
            qgis_check("preflight-qgis", ["--preflight-only"], arguments.qgis_python, logs, environment, arguments.timeout)
        if "lint" in arguments.checks:
            command = [arguments.qgis_python, "scripts/check_lint_environment.py"]
            if arguments.tools_path:
                command = [arguments.qgis_python, str(ROOT / "scripts/run_dev_tool.py"),
                           "--tools-path", arguments.tools_path, "--script",
                           str(ROOT / "scripts/check_lint_environment.py")]
            execute_check("preflight-lint", [*command, "--qgis-python", arguments.qgis_python],
                          logs, environment, arguments.timeout)
            print((logs / "preflight-lint.log").read_text(encoding="utf-8"), end="", flush=True)
        if arguments.package:
            powershell = shutil.which("powershell", path=environment.get("PATH"))
            if powershell is None:
                raise CheckFailure("Package checks require Windows PowerShell on PATH.")
            details.append(f"PowerShell: {powershell}")
            return powershell
        return None
    finally:
        (logs / "preflight.log").write_text("\n".join(details) + "\n", encoding="utf-8")


def extracted_package(logs, environment, powershell, timeout):
    execute_check("package", [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                              "qgis_plugin/package.ps1"], logs, environment, timeout)
    metadata = ConfigParser(interpolation=None)
    metadata.read(ROOT / "qgis_plugin/savonia_responsible_forest_planning_tool/metadata.txt", encoding="utf-8")
    archive = ROOT / "qgis_plugin/dist" / ("savonia_responsible_forest_planning_tool-" + metadata["general"]["version"] + ".zip")
    destination = logs / "installed-plugin"
    destination.mkdir()
    with zipfile.ZipFile(archive) as package:
        if any(not (destination / name).resolve().is_relative_to(destination.resolve()) for name in package.namelist()):
            raise CheckFailure("Plugin ZIP contains a path outside the extraction directory.")
        package.extractall(destination)
    return str(destination)


def run_checks(arguments, logs):
    environment = dict(os.environ, PYTHONUTF8="1", PYTHONFAULTHANDLER="1", QT_QPA_PLATFORM="offscreen")
    for key in (PLUGIN_ROOT_KEY, "RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT"):
        environment.pop(key, None)
    powershell = preflight(arguments, logs, environment)
    if "tooling" in arguments.checks:
        execute_check("tooling", [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-v"], logs, environment, arguments.timeout)
    if "unit" in arguments.checks:
        execute_check("unit", [sys.executable, "-m", "unittest", "discover", "-s", "qgis_plugin/tests", "-v"], logs, environment, arguments.timeout)
    if "lint" in arguments.checks:
        command = [arguments.qgis_python, "-m", "pylint"]
        if arguments.tools_path:
            command = [arguments.qgis_python, str(ROOT / "scripts/run_dev_tool.py"),
                       "--tools-path", arguments.tools_path, "--module", "pylint"]
        execute_check("lint", [*command, "qgis_plugin", "scripts"], logs, environment, arguments.timeout)
    if "qgis" in arguments.checks:
        qgis_check("qgis", ["--pattern", arguments.qgis_pattern], arguments.qgis_python, logs, environment, arguments.timeout)
    if arguments.package:
        environment[PLUGIN_ROOT_KEY] = extracted_package(logs, environment, powershell, arguments.timeout)
        if "unit" in arguments.checks:
            execute_check("unit-package", [sys.executable, "-m", "unittest", "discover", "-s", "qgis_plugin/tests", "-v"], logs, environment, arguments.timeout)
        if "qgis" in arguments.checks:
            qgis_check("qgis-package", ["--pattern", arguments.qgis_pattern], arguments.qgis_python, logs, environment, arguments.timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", nargs="+", choices=("tooling", "unit", "lint", "qgis"),
                        default=["tooling", "unit", "lint", "qgis"])
    parser.add_argument("--qgis-python")
    parser.add_argument("--tools-path", help="Managed dependencies loaded after QGIS initializes Python")
    parser.add_argument("--qgis-pattern", default="test*.py")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="Maximum seconds per subprocess, including preflight and packaging (default: 600)")
    parser.add_argument("--package", action="store_true", help="Build the current version and repeat selected unit/QGIS suites on the ZIP")
    parser.add_argument("--logs-dir", type=Path, help="Parent directory for unique run logs (default: .local/checks)")
    arguments = parser.parse_args(argv)
    if not math.isfinite(arguments.timeout) or arguments.timeout <= 0:
        parser.error("--timeout must be positive and finite.")
    if not re.fullmatch(r"[A-Za-z0-9_.*?-]+", arguments.qgis_pattern):
        parser.error("QGIS patterns must contain only letters, digits, _, ., *, ? or -.")
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    logs = ((arguments.logs_dir or ROOT / ".local/checks") / name).resolve()
    logs.mkdir(parents=True)
    source = source_state(ROOT)
    arguments.plain_python = sys.executable
    status, failure = "failed", None
    try:
        config = managed_tools(ROOT)
        arguments.qgis_python = str(Path(arguments.qgis_python or default_qgis(ROOT)).expanduser().resolve())
        arguments.tools_path = arguments.tools_path or config.get("tooling_path")
        if arguments.tools_path:
            arguments.tools_path = str(Path(arguments.tools_path).expanduser().resolve())
        run_checks(arguments, logs)
    except (CheckFailure, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        failure = error
        (logs / "failure.log").write_text(str(error) + "\n", encoding="utf-8")
        print(f"FAIL {error}\nLogs: {logs}", file=sys.stderr)
        return 1
    else:
        status = "passed"
    finally:
        report = write_summary(arguments, logs, source, status, failure)
        print(f"Selected checks: {', '.join(arguments.checks)}")
        omitted = [name for name in ("tooling", "unit", "lint", "qgis") if name not in arguments.checks]
        print("Not selected: " + (", ".join(omitted) or "none"))
        results = json.loads(report.read_text(encoding="utf-8"))
        not_run = [name for name, item in results["stages"].items() if item["status"] == "not_run"]
        print("Not run: " + (", ".join(not_run) or "none"))
        print(f"Summary: {report}")
    print(f"All selected checks passed. Logs: {logs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
