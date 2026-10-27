"""Published fields are rounded without changing calculation inputs."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.PyQt.QtCore import QLocale
from qgis.core import (
    QgsApplication, QgsCoordinateTransformContext,
    QgsRangeFieldFormatter, QgsVectorLayer,
)

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()

from test_grid_publication import classified_row
from savonia_responsible_forest_planning_tool.adapters.classified_result import create_classified_result_layer
from savonia_responsible_forest_planning_tool.adapters.geopackage_writer import write_geopackage
from savonia_responsible_forest_planning_tool.adapters.excel_writer import write_workbook
from savonia_responsible_forest_planning_tool.analysis.grid_indicators import summarize_indicator_rows
from test_grid_publication import workbook_rows
from savonia_responsible_forest_planning_tool.i18n import tr


class ResultPrecisionTests(unittest.TestCase):
    def assert_formatted_result(self, layer, locale):
        feature = next(layer.getFeatures())
        for name, value, precision in (("grid_total_volume_m3_ha", 137, 0),
                                       ("total_volume_m3_ha", 176, 0), ("area_ha", 1.0, 2)):
            index = layer.fields().indexFromName(name)
            widget = layer.editorWidgetSetup(index)
            self.assertEqual(widget.type(), "Range")
            self.assertEqual(widget.config().get("Precision"), precision)
            self.assertEqual(feature[name], value)
            self.assertEqual(
                QgsRangeFieldFormatter().representValue(layer, index, widget.config(), None, value),
                locale.toString(float(value), "f", precision),
            )
        self.assertEqual(json.loads(feature["indicator_coverage"])["grid_total_volume_m3_ha"]
                         ["represented_volume_m3"], 0.625 * 136.59723544429696)
        self.assertEqual(feature["share_under_20"], 100)
        self.assertNotEqual(layer.editorWidgetSetup(layer.fields().indexFromName("share_under_20"))
                            .config().get("Precision"), 2)

    def test_published_precision_in_memory_and_reopened_geopackage_in_both_locales(self):
        previous = QLocale()
        try:
            for language, locale in (("fi", QLocale("fi_FI")), ("en", QLocale("en_GB"))):
                QLocale.setDefault(locale)
                with self.subTest(language=language), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
                    layer = create_classified_result_layer(
                        [classified_row(grid_volume=136.59723544429696, stand_volume=175.83)], language)
                    self.assert_formatted_result(layer, locale)
                    path = str(Path(folder) / "result.gpkg")
                    write_geopackage(path, layer, [], [{"service_id": "fixture", "status": "AVAILABLE"}],
                                     [{"run_id": "precision-test"}], QgsCoordinateTransformContext())
                    reopened = QgsVectorLayer(path + "|layername=classified_forest_polygons", "result", "ogr")
                    self.assertTrue(reopened.isValid())
                    self.assert_formatted_result(reopened, locale)
                    del reopened, layer
        finally:
            QLocale.setDefault(previous)

    def test_summary_uses_full_precision_after_result_layer_is_created(self):
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                rows = [classified_row(grid_area=0.6, grid_volume=100.4),
                        classified_row(grid_area=0.4, grid_volume=101.4)]
                layer = create_classified_result_layer(rows, language)
                self.assertEqual([f["grid_total_volume_m3_ha"] for f in layer.getFeatures()], [100, 101])
                summary = summarize_indicator_rows(rows)
                self.assertAlmostEqual(summary["grid_total_volume_m3_ha"], 100.8)
                summary.update({"tier": "bau", "class": "ECONOMIC"})
                path = str(Path(folder) / "summary.xlsx")
                write_workbook(path, language, [summary], [], [])
                sheet = workbook_rows(path)[tr(language, "sheet_summary")]
                self.assertEqual(sheet[1][sheet[0].index(tr(language, "metric_grid_total_volume_m3_ha"))], 101)
                self.assertEqual(rows[0]["indicators"]["grid_total_volume_m3_ha"], 100.4)
                self.assertAlmostEqual(summary["indicator_coverage"]["grid_total_volume_m3_ha"]
                                       ["represented_volume_m3"], 100.8)


if __name__ == "__main__":
    unittest.main()
