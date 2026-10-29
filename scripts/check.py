"""Run local checks with separate plain-Python and QGIS runtimes and saved logs."""

import argparse
from collections import deque
from configparser import ConfigParser
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QGIS = os.environ.get("QGIS_PYTHON", "C:/Program Files/QGIS 4.2.3/bin/python-qgis.bat")
PLUGIN_ROOT_KEY = "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT"


class CheckFailure(Exception):
    """An actionable preflight or selected-check failure."""


def execute_check(name, command, logs, environment):
    log = logs / (name + ".log")
    started = time.monotonic()
    try:
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT,
                                    check=False)
    except OSError as error:
        log.write_text(str(error) + "\n", encoding="utf-8")
        raise CheckFailure(f"{name} could not start; see {log}: {error}") from error
    if result.returncode:
        with log.open(encoding="utf-8", errors="replace") as output:
            tail = "".join(deque(output, maxlen=12)).strip()
        raise CheckFailure(f"{name} failed (exit {result.returncode}); see {log}\n{tail}")
    print(f"PASS {name} ({time.monotonic() - started:.1f}s)", flush=True)


def qgis_check(name, arguments, qgis_python, logs, environment):
    # The parent owns cleanup, after the QGIS child releases Windows file handles.
    with tempfile.TemporaryDirectory(prefix="qgis-environment-", dir=logs) as folder:
        if not Path(folder).resolve().is_relative_to(logs.resolve()):
            raise CheckFailure("The QGIS environment must stay inside the check log directory.")
        isolated = dict(environment, RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT=folder)
        execute_check(name, [qgis_python, "scripts/run_qgis_tests.py", *arguments], logs, isolated)


def preflight(arguments, logs, environment):
    if sys.version_info < (3, 10):
        raise CheckFailure("Local checks require plain Python 3.10 or newer.")
    details = [f"Plain Python: {sys.executable}", f"Version: {sys.version.split()[0]}"]
    try:
        if "tooling" in arguments.checks:
            git = shutil.which("git", path=environment.get("PATH"))
            if git is None:
                raise CheckFailure("Git is missing from plain Python's PATH. Install Git or add its cmd directory to PATH.")
            details.append(f"Git: {git}")
            execute_check("preflight-git", [git, "--version"], logs, environment)
        if {"lint", "qgis"}.intersection(arguments.checks):
            if not Path(arguments.qgis_python).is_file():
                raise CheckFailure(f"QGIS Python launcher is missing: {arguments.qgis_python}. Use --qgis-python to select it.")
            details.append(f"QGIS launcher: {arguments.qgis_python}")
            qgis_check("preflight-qgis", ["--preflight-only"], arguments.qgis_python, logs, environment)
        if arguments.package:
            powershell = shutil.which("powershell", path=environment.get("PATH"))
            if powershell is None:
                raise CheckFailure("Package checks require Windows PowerShell on PATH.")
            details.append(f"PowerShell: {powershell}")
            return powershell
        return None
    finally:
        (logs / "preflight.log").write_text("\n".join(details) + "\n", encoding="utf-8")


def extracted_package(logs, environment, powershell):
    execute_check("package", [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                              "qgis_plugin/package.ps1"], logs, environment)
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
    environment = dict(os.environ, PYTHONUTF8="1", QT_QPA_PLATFORM="offscreen")
    for key in (PLUGIN_ROOT_KEY, "RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT"):
        environment.pop(key, None)
    powershell = preflight(arguments, logs, environment)
    if "tooling" in arguments.checks:
        execute_check("tooling", [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-v"], logs, environment)
    if "unit" in arguments.checks:
        execute_check("unit", [sys.executable, "-m", "unittest", "discover", "-s", "qgis_plugin/tests", "-v"], logs, environment)
    if "lint" in arguments.checks:
        execute_check("lint", [arguments.qgis_python, "-m", "pylint", "qgis_plugin", "scripts"], logs, environment)
    if "qgis" in arguments.checks:
        qgis_check("qgis", ["--pattern", arguments.qgis_pattern], arguments.qgis_python, logs, environment)
    if arguments.package:
        environment[PLUGIN_ROOT_KEY] = extracted_package(logs, environment, powershell)
        if "unit" in arguments.checks:
            execute_check("unit-package", [sys.executable, "-m", "unittest", "discover", "-s", "qgis_plugin/tests", "-v"], logs, environment)
        if "qgis" in arguments.checks:
            qgis_check("qgis-package", ["--pattern", arguments.qgis_pattern], arguments.qgis_python, logs, environment)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", nargs="+", choices=("tooling", "unit", "lint", "qgis"),
                        default=["tooling", "unit", "lint", "qgis"])
    parser.add_argument("--qgis-python", default=DEFAULT_QGIS)
    parser.add_argument("--qgis-pattern", default="test*.py")
    parser.add_argument("--package", action="store_true", help="Build the current version and repeat selected unit/QGIS suites on the ZIP")
    parser.add_argument("--logs-dir", type=Path, help="Parent directory for unique run logs (default: .local/checks)")
    arguments = parser.parse_args(argv)
    arguments.qgis_python = str(Path(arguments.qgis_python).expanduser().resolve())
    if not re.fullmatch(r"[A-Za-z0-9_.*?-]+", arguments.qgis_pattern):
        parser.error("QGIS patterns must contain only letters, digits, _, ., *, ? or -.")
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    logs = ((arguments.logs_dir or ROOT / ".local/checks") / name).resolve()
    logs.mkdir(parents=True)
    try:
        run_checks(arguments, logs)
    except CheckFailure as error:
        (logs / "failure.log").write_text(str(error) + "\n", encoding="utf-8")
        print(f"FAIL {error}\nLogs: {logs}", file=sys.stderr)
        return 1
    print(f"All selected checks passed. Logs: {logs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
