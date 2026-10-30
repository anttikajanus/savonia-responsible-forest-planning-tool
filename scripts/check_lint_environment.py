"""Validate the lint tools imported by the selected QGIS Python launcher."""

import argparse
import importlib
from pathlib import Path
import re
import sys


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements-dev.txt"


def stable_version(value):
    """The toolchain requires stable major.minor.patch releases."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError(f"unsupported stable version: {value!r}")
    return tuple(int(part) for part in value.split("."))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qgis-python", required=True)
    arguments = parser.parse_args(argv)
    print(f"Lint Python: {sys.executable}; version: {sys.version.split()[0]}")
    requirements = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    errors = []
    for name in ("pylint", "astroid"):
        try:
            module = importlib.import_module(name)
        except Exception as error:  # Broken installations must also get the corrective command.
            print(f"{name.capitalize()}: import failed: {error}")
            errors.append(f"Cannot import {name}")
            continue
        version = str(getattr(module, "__version__", "unknown"))
        print(f"{name.capitalize()}: {version}; path: {getattr(module, '__file__', 'unknown')}")
        # Only stable pins/minima are supported. Imported versions must be used;
        # package metadata can describe a different installation.
        requirement = next((line.strip() for line in requirements if line.startswith(name)), "")
        match = re.fullmatch(rf"{name}(==|>=)(\d+\.\d+\.\d+)", requirement)
        try:
            if match is None:
                raise ValueError(f"missing or unsupported requirement for {name}: {requirement!r}")
            actual, required = stable_version(version), stable_version(match[2])
            if (actual != required if match[1] == "==" else actual < required):
                errors.append(f"{name} {version} does not satisfy {requirement}")
        except ValueError as error:
            errors.append(f"{name}: {error}")
    if errors:
        print("Lint toolchain preflight failed: " + "; ".join(errors))
        launcher = arguments.qgis_python.replace("'", "''")
        requirements_path = str(REQUIREMENTS).replace("'", "''")
        print("Corrective command (PowerShell):")
        print(f"& '{launcher}' -m pip install --user --upgrade -r '{requirements_path}'")
        print("Rerun checks and inspect the imported paths; the QGIS launcher may replace PYTHONPATH.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
