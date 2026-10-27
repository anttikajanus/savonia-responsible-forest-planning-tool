"""The plugin follows QGIS's language and ignores the former plugin override."""

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication, QgsSettings
from savonia_responsible_forest_planning_tool.i18n import selected_language

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()


class SelectedLanguageTests(unittest.TestCase):
    def test_qgis_language_wins_over_the_legacy_plugin_setting(self):
        settings = QgsSettings()
        key = "savonia_responsible_forest_planning_tool/language"
        old = settings.value(key) if settings.contains(key) else None
        try:
            for locale, expected, saved in (("fi_FI", "fi", "en"), ("en_GB", "en", "fi"),
                                             ("de_DE", "en", "fi")):
                with self.subTest(locale=locale):
                    settings.setValue(key, saved)
                    with patch.object(QgsApplication, "locale", return_value=locale):
                        self.assertEqual(selected_language(), expected)
        finally:
            if old is None:
                settings.remove(key)
            else:
                settings.setValue(key, old)

    def test_supported_locale_variants_and_english_fallback(self):
        for locale, expected in (
            ("fi", "fi"), ("fi_FI", "fi"), ("fi-FI", "fi"), ("FI_fi", "fi"),
            ("en", "en"), ("en_US", "en"), ("sv_SE", "en"), ("fil", "en"),
            ("", "en"),
        ):
            with self.subTest(locale=locale), patch.object(QgsApplication, "locale", return_value=locale):
                self.assertEqual(selected_language(), expected)


if __name__ == "__main__":
    unittest.main()
