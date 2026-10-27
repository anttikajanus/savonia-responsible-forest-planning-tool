"""Localized source credits survive an independently shared XLSX output."""

from pathlib import Path
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))

from savonia_responsible_forest_planning_tool.data_attribution import data_attribution
from savonia_responsible_forest_planning_tool.adapters.excel_writer import write_workbook
from savonia_responsible_forest_planning_tool.i18n import tr


class DataAttributionOutputTests(unittest.TestCase):
    def test_workbook_keeps_readable_credits_in_both_languages(self):
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "attribution.xlsx"
                notice = tr(language, "data_attribution_changes")
                self.assertNotEqual(notice, "data_attribution_changes")
                self.assertIn("EPSG:3067", notice)
                credits = data_attribution(
                    ["forest_centre_stand", "syke_groundwater_areas"], notice,
                )
                write_workbook(path, language, [], [], [], [{"data_attribution": credits}])
                with zipfile.ZipFile(path) as archive:
                    text = archive.read("xl/worksheets/sheet4.xml").decode("utf-8")
                for item in credits.values():
                    self.assertIn(item["attribution"], text)
                    self.assertIn(item["license_url"], text)
                    self.assertIn(item["modifications"], text)


if __name__ == "__main__":
    unittest.main()
