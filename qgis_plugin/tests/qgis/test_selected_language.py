"""The plugin selects its presentation language from the QGIS locale."""

import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsApplication
from savonia_responsible_forest_planning_tool.i18n import selected_language


class SelectedLanguageTests(unittest.TestCase):
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
