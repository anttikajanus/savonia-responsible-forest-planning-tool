"""Load managed development dependencies after QGIS sets its Python paths."""

import argparse
from pathlib import Path
import runpy
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools-path", required=True, type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--module")
    target.add_argument("--script", type=Path)
    arguments, remaining = parser.parse_known_args(argv)
    site = arguments.tools_path.resolve()
    if not site.is_dir():
        parser.error(f"Managed tooling directory is missing: {site}. Run setup-dev-environment.ps1.")
    sys.path.insert(0, str(site))
    sys.argv = [arguments.module or str(arguments.script), *remaining]
    if arguments.module:
        runpy.run_module(arguments.module, run_name="__main__", alter_sys=True)
    else:
        runpy.run_path(str(arguments.script.resolve()), run_name="__main__")


if __name__ == "__main__":
    main()
