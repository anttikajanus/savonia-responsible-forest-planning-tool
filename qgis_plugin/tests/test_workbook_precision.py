"""Workbook number formats must not round the stored source statistics."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])),
))

from savonia_responsible_forest_planning_tool.adapters.excel_writer import write_workbook
from savonia_responsible_forest_planning_tool.i18n import tr

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class WorkbookPrecisionTests(unittest.TestCase):
    def test_published_fields_are_rounded_but_coverage_statistics_remain_exact(self):
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "precision.xlsx"
                value = 136.59723544429696
                write_workbook(path, language, [{
                    "tier": "bau", "class": "ECONOMIC", "area_ha": 12.322180212728027,
                    "feature_count": 6, "grid_total_volume_m3_ha": value,
                    "share_under_20": 0,
                    "indicator_coverage": {"grid_total_volume_m3_ha": {
                        "valid_area_ha": 12.322180212728027, "represented_volume_m3": 1683.1757517050676}},
                }], [], [])
                with zipfile.ZipFile(path) as archive:
                    styles = ET.fromstring(archive.read("xl/styles.xml"))
                    formats = styles.find("s:cellXfs", NS)
                    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
                    self.assertTrue(any(rel.get("Type", "").endswith("/styles") for rel in relationships))
                    types = ET.fromstring(archive.read("[Content_Types].xml"))
                    self.assertTrue(any(item.get("PartName") == "/xl/styles.xml" for item in types))
                    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                    cells = {cell.get("r"): cell for cell in sheet.findall("s:sheetData/s:row/s:c", NS)}
                    volume_header = next(cell.get("r") for cell in cells.values()
                                         if cell.find("s:is/s:t", NS) is not None
                                         and cell.find("s:is/s:t", NS).text == tr(language, "metric_grid_total_volume_m3_ha"))
                    volume_cell = cells[volume_header.rstrip("1") + "2"]
                    self.assertEqual(formats[int(cells["C2"].get("s", "0"))].get("numFmtId"), "2")
                    self.assertEqual(float(cells["C2"].find("s:v", NS).text), 12.32)
                    self.assertEqual(formats[int(volume_cell.get("s", "0"))].get("numFmtId"), "0")
                    self.assertEqual(float(volume_cell.find("s:v", NS).text), 137)
                    self.assertEqual(cells["D2"].find("s:v", NS).text, "6")
                    self.assertEqual(formats[int(cells["D2"].get("s", "0"))].get("numFmtId"), "0")
                    coverage = ET.fromstring(archive.read("xl/worksheets/sheet3.xml"))
                    volume_row = next(row for row in coverage.findall("s:sheetData/s:row", NS)
                                      if any(cell.find("s:is/s:t", NS) is not None
                                             and cell.find("s:is/s:t", NS).text == "grid_total_volume_m3_ha"
                                             for cell in row))
                    valid_area = volume_row.find("s:c[@r='G" + volume_row.get("r") + "']", NS)
                    self.assertEqual(formats[int(valid_area.get("s", "0"))].get("numFmtId"), "2")
                    self.assertEqual(float(valid_area.find("s:v", NS).text), 12.322180212728027)


if __name__ == "__main__":
    unittest.main()
