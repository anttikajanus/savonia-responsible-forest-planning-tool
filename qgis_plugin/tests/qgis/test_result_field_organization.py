"""Result lookup order, source labels and grouped forms survive publication."""

from pathlib import Path
import tempfile
import unittest


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.PyQt import sip
from qgis.core import Qgis, QgsAttributeEditorTextElement, QgsCoordinateTransformContext, QgsVectorLayer

from test_grid_publication import classified_row, workbook_rows
from savonia_responsible_forest_planning_tool.adapters.classified_result import create_classified_result_layer
from savonia_responsible_forest_planning_tool.adapters.excel_writer import write_workbook
from savonia_responsible_forest_planning_tool.adapters.geopackage_writer import write_geopackage
from savonia_responsible_forest_planning_tool.analysis.domain import METRIC_GROUPS
from savonia_responsible_forest_planning_tool.analysis.grid_indicators import summarize_indicator_rows
from savonia_responsible_forest_planning_tool.i18n import tr


EXPECTED_METRICS = (
    "total_volume_m3_ha", "sawtimber_volume_m3_ha", "growth_percent", "basal_area_m2_ha",
    "grid_total_volume_m3_ha", "pine_volume_m3_ha", "spruce_volume_m3_ha", "deciduous_volume_m3_ha",
    "share_under_20", "share_20_80", "share_over_80",
    "peatland_area_ha", "natural_mire_area_ha", "stumpage_price_eur_m3",
)


class ResultFieldOrganizationTests(unittest.TestCase):
    def assert_presentation(self, layer, language):
        names = [name for name in layer.fields().names() if name != "fid"]
        self.assertEqual(names[7:22], ["area_ha", *EXPECTED_METRICS])
        self.assertEqual(names[22], "indicator_status")
        self.assertNotIn("birch_volume_m3_ha", names)
        price_label = "Tukkipuun kantohinta (€/m³)" if language == "fi" else "Sawlog stumpage price (€/m³)"
        self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("stumpage_price_eur_m3")), price_label)
        feature = next(layer.getFeatures())
        for name, value in (("area_ha", 1), ("total_volume_m3_ha", 200),
                            ("sawtimber_volume_m3_ha", 80), ("growth_percent", 2),
                            ("basal_area_m2_ha", 20), ("grid_total_volume_m3_ha", 250),
                            ("pine_volume_m3_ha", 100), ("spruce_volume_m3_ha", 80),
                            ("deciduous_volume_m3_ha", 70), ("share_under_20", 100)):
            self.assertEqual(feature[name], value, name)
        for group, metrics in METRIC_GROUPS:
            if group == "price":
                continue
            prefix = ("Kuvio" if language == "fi" else "Stand") if group == "stand" else (
                "Hila" if language == "fi" else "Grid")
            for metric in metrics:
                alias = layer.attributeAlias(layer.fields().indexFromName(metric))
                self.assertTrue(alias.startswith(prefix + " "), alias)
                self.assertEqual(alias, tr(language, "metric_" + metric))
        config = layer.editFormConfig()
        self.assertEqual(config.layout(), Qgis.AttributeFormLayout.DragAndDrop)
        groups = config.invisibleRootContainer().children()
        self.assertEqual([group.name() for group in groups], [
            tr(language, "field_group_" + name) for name in (
                "result", "stand", "grid_volume", "grid_age", "grid_area", "price", "provenance")])
        form_fields = []
        for group in groups:
            self.assertEqual(group.type(), Qgis.AttributeEditorContainerType.Tab)
            children = group.children()
            if group == groups[0] or group == groups[1]:
                note = sip.cast(children[0], QgsAttributeEditorTextElement)
                self.assertFalse(note.showLabel())
                self.assertEqual(note.text(), tr(language, "note_area_definitions"))
                children = children[1:]
            form_fields.extend(child.name() for child in children)
        self.assertEqual(form_fields, names)

    def test_bilingual_groups_aliases_order_and_values_survive_geopackage_reopen(self):
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
                layer = create_classified_result_layer([classified_row()], language)
                self.assert_presentation(layer, language)
                path = str(Path(folder) / "grouped.gpkg")
                write_geopackage(path, layer, [], [{"service_id": "fixture", "status": "AVAILABLE"}],
                                 [{"run_id": "organization"}], QgsCoordinateTransformContext())
                reopened = QgsVectorLayer(path + "|layername=classified_forest_polygons", "result", "ogr")
                self.assertTrue(reopened.isValid())
                self.assert_presentation(reopened, language)
                del reopened, layer

    def test_workbook_summary_and_coverage_follow_documentation_order(self):
        reference = Path(__file__).resolve().parents[3] / "docs" / "architecture" / "output-schema.md"
        text = reference.read_text(encoding="utf-8")
        anchor = '<a id="per-polygon-fields"></a>'
        self.assertIn(anchor, text)
        section = text.split(anchor, 1)[1].split(
            "## Metric coverage", 1)[0]
        documented = [line.split("`", 2)[1] for line in section.splitlines() if line.startswith("| `")]
        self.assertEqual(documented, ["area_ha", *EXPECTED_METRICS])
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                row = summarize_indicator_rows([classified_row()])
                self.assertNotIn("birch_volume_m3_ha", row)
                self.assertNotIn("birch_volume_m3_ha", row["indicator_status"])
                self.assertNotIn("birch_volume_m3_ha", row["indicator_coverage"])
                row.update({"tier": "BAU", "class": "ECONOMIC"})
                path = str(Path(folder) / "grouped.xlsx")
                write_workbook(path, language, [row], [], [tr(language, "note_area_definitions")])
                workbook = workbook_rows(path)
                summary = workbook[tr(language, "sheet_summary")]
                self.assertEqual(summary[0][4:], [tr(language, "metric_" + name) for name in EXPECTED_METRICS])
                self.assertEqual(summary[1][4:12], [200, 80, 2, 20, 250, 100, 80, 70])
                coverage = workbook[tr(language, "sheet_metric_coverage")]
                self.assertEqual([row[2] for row in coverage[1:]], list(EXPECTED_METRICS))
                self.assertIn([tr(language, "note_area_definitions")], workbook[tr(language, "sheet_notes")])


if __name__ == "__main__":
    unittest.main()
