"""Fail early on environment faults and keep QGIS writes inside test storage."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from qgis_test_environment import check_writable_directory, environment_root, qgis_application

APP = qgis_application()

from qgis.core import QgsApplication, QgsSettings
from qgis.PyQt.QtCore import QSettings


class QgisEnvironmentTests(unittest.TestCase):
    def test_application_settings_profile_and_cache_are_shared_and_isolated(self):
        self.assertIs(APP, qgis_application())
        self.assertIs(APP, QgsApplication.instance())
        self.assertEqual(APP.platformName(), "offscreen")
        root = environment_root()
        settings = QgsSettings()
        self.assertTrue(Path(settings.fileName()).resolve().is_relative_to(root))
        self.assertTrue(Path(QgsApplication.qgisSettingsDirPath()).resolve().is_relative_to(root))
        self.assertTrue(Path(os.environ["QGIS_AUTH_DB_DIR_PATH"]).resolve().is_relative_to(root))
        self.assertTrue(Path(settings.value("cache/directory")).resolve().is_relative_to(root))
        self.assertEqual(QSettings.defaultFormat(), QSettings.Format.IniFormat)
        key = "test-environment/round-trip"
        settings.setValue(key, "isolated")
        self.addCleanup(settings.remove, key)
        settings.sync()
        self.assertEqual(QgsSettings().value(key), "isolated")
        self.assertTrue(Path(settings.fileName()).is_file())

    def test_file_and_sqlite_round_trip_leaves_no_probe_files(self):
        with tempfile.TemporaryDirectory() as folder:
            check_writable_directory(folder)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_unusable_directory_has_an_actionable_environment_error(self):
        with tempfile.TemporaryDirectory() as folder:
            blocked = Path(folder) / "blocked"
            blocked.write_text("file instead of directory", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "QGIS test directory is not writable"):
                check_writable_directory(blocked)

    def test_preflight_failure_exits_before_test_discovery(self):
        with tempfile.TemporaryDirectory() as folder:
            blocked = Path(folder) / "blocked"
            blocked.write_text("file instead of directory", encoding="utf-8")
            environment = dict(os.environ, RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT=str(blocked))
            runner = Path(__file__).resolve().parents[3] / "scripts/run_qgis_tests.py"
            result = subprocess.run([sys.executable, str(runner), "--preflight-only"], env=environment,
                                    capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("QGIS environment preflight failed", result.stderr)
            self.assertIn("directory is not writable", result.stderr)
            self.assertNotIn("Ran ", result.stderr)


if __name__ == "__main__":
    unittest.main()
