"""Run isolated PyQGIS preflight and integration checks in the QGIS runtime."""

import argparse
import faulthandler
from pathlib import Path
import sys
import unittest


TEST_ROOT = Path(__file__).resolve().parents[1] / "qgis_plugin" / "tests" / "qgis"


def main(argv=None):
    faulthandler.enable()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--pattern", default="test*.py")
    arguments = parser.parse_args(argv)
    sys.path.insert(0, str(TEST_ROOT))
    from qgis_test_environment import environment_root, qgis_application
    try:
        qgis_application()
    except (ImportError, RuntimeError) as error:
        print(f"QGIS environment preflight failed: {error}", file=sys.stderr)
        return 1
    from qgis.core import Qgis, QgsSettings
    print(f"QGIS {Qgis.QGIS_VERSION}; isolated environment: {environment_root()}", flush=True)
    print(f"Settings: {QgsSettings().fileName()}; cache: {QgsSettings().value('cache/directory')}", flush=True)
    if arguments.preflight_only:
        return 0
    suite = unittest.defaultTestLoader.discover(str(TEST_ROOT), pattern=arguments.pattern)
    if suite.countTestCases() == 0:
        print(f"No QGIS tests matched {arguments.pattern!r}.", file=sys.stderr)
        return 1
    # unittest added duration reporting in Python 3.12; retain older runtimes.
    timing = {"durations": 10} if sys.version_info >= (3, 12) else {}
    return 0 if unittest.TextTestRunner(verbosity=2, **timing).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
