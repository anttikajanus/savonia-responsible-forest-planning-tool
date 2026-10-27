"""Run with QGIS Python; exercises real WFS providers and Processing outputs."""

import json
import os
from pathlib import Path
import string
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    Qgis, QgsApplication, QgsFeature, QgsFeatureRequest, QgsGeometry, QgsProcessingContext,
    QgsProcessingException, QgsProcessingFeedback, QgsProject, QgsRectangle, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.gui import QgsMapCanvas

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()

from savonia_responsible_forest_planning_tool.adapters.source_layers import verify_source_layer
from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.i18n import TEXT, source_readiness_message, tr
from savonia_responsible_forest_planning_tool.processing.provider import ResponsibleForestPlanningInputsAlgorithm
from savonia_responsible_forest_planning_tool import classFactory
from wfs_fixture import LocalWfs


from workflow_fixture import fixture_sources


class SourceFieldWorkflowChecks:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.fixture = self.enterContext(LocalWfs(fixture_sources()))
        definitions = {
            source: {**definition, "endpoint": self.fixture.endpoint}
            for source, definition in SERVICE_DEFINITIONS.items()
        }
        self.enterContext(patch.dict(SERVICE_DEFINITIONS, definitions))
        self.layers = {}
        saved_schemas = ("", "null", "not-json", "{}", '[{"name":"obsolete"}]', '"text"', "42", "[]")
        for source, saved in zip(definitions, saved_schemas):
            typename = "fixture:" + source
            uri = "url='{0}' typename='{1}' version='1.0.0' restrictToRequestBBOX='1'".format(self.fixture.endpoint, typename)
            layer = QgsVectorLayer(uri, source, "WFS")
            self.assertTrue(layer.isValid(), layer.error().message())
            layer.setCustomProperty("savonia/endpoint", self.fixture.endpoint)
            layer.setCustomProperty("savonia/feature_type", typename)
            layer.setCustomProperty("savonia/schema_json", saved)
            self.layers[source] = layer
        self.aoi = QgsVectorLayer("Polygon?crs=EPSG:3067", "AOI", "memory")
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt(
            "POLYGON ((350000 6900000,350100 6900000,350100 6900100,350000 6900100,350000 6900000))"
        ))
        self.assertTrue(self.aoi.dataProvider().addFeatures([feature])[0])
        self.aoi.updateExtents()

    def run_algorithm(self, language, output_name):
        algorithm = ResponsibleForestPlanningInputsAlgorithm()
        algorithm.initAlgorithm()
        parameters = {
            algorithm.AOI: self.aoi, algorithm.SELECTED_ONLY: False,
            algorithm.OUTPUT_FOLDER: self.temp.name, algorithm.OUTPUT_NAME: output_name,
        }
        for parameter, source in zip(
            (algorithm.STANDS, algorithm.HABITATS, algorithm.PROTECTED, algorithm.PROTECTED_PRIVATE,
             algorithm.PROTECTED_WILDERNESS, algorithm.PROGRAMME, algorithm.GROUNDWATER, algorithm.GRIDCELLS),
            SERVICE_DEFINITIONS,
        ):
            parameters[parameter] = self.layers[source]
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        with patch("savonia_responsible_forest_planning_tool.processing.provider.selected_language", return_value=language):
            return algorithm.processAlgorithm(parameters, context, QgsProcessingFeedback())

    def test_processing_outputs_ignore_saved_schemas_in_both_languages(self):
        sheet_label = "Yhteenveto" if self.language == "fi" else "Summary"
        language = self.language
        result = self.run_algorithm(language, "success-" + language)
        layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.crs().authid(), "EPSG:3067")
        feature, = list(layer.getFeatures())
        self.assertAlmostEqual(feature["area_ha"], 1.0)
        self.assertAlmostEqual(feature["total_volume_m3_ha"], 200.0)
        self.assertAlmostEqual(feature["grid_total_volume_m3_ha"], 250.0)
        self.assertAlmostEqual(feature["pine_volume_m3_ha"], 70.0)
        self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("grid_total_volume_m3_ha")),
                         tr(language, "metric_grid_total_volume_m3_ha"))
        self.assertEqual(feature["class_all_out"], "SENSITIVE")
        source_ids = json.loads(feature["source_ids"])
        self.assertEqual(set(source_ids["protected"]), {"state-1", "private-1", "wild-1"})
        self.assertEqual(json.loads(feature["programme_info"])[0]["Subtype"], "original")
        gpkg = result["RESULT"].split("|", 1)[0]
        coverage_layer = QgsVectorLayer(gpkg + "|layername=source_coverage", "coverage", "ogr")
        coverage = {row["service_id"]: row for row in coverage_layer.getFeatures()}
        self.assertIn("basal_area_m2_ha", json.loads(coverage["forest_centre_stand_indicators"]["mapped_metrics"]))
        for source, category in zip(tuple(SERVICE_DEFINITIONS)[2:5], ("VSA", "YSA", "EMA")):
            self.assertEqual(json.loads(coverage[source]["observed_category_counts"]), {category: 1})
        snapshot = QgsVectorLayer(gpkg + "|layername=syke_protected_areas_private_land", "snapshot", "ogr")
        original, = list(snapshot.getFeatures())
        self.assertEqual(original["KohdeTyyppi"], "YSA")
        with zipfile.ZipFile(result["EXCEL"]) as workbook:
            root = ET.fromstring(workbook.read("xl/workbook.xml"))
            sheets = root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
            self.assertEqual(sheets[0].attrib["name"], sheet_label)
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertIn(tr(language, "class_sensitive"), sheet)

    def test_missing_required_provider_field_is_localized_before_outputs(self):
        source = "forest_centre_habitat"
        # A real WFS provider's fields are used; redirect this source to the
        # groundwater feature type which lacks habitattype but has valid geometry.
        replacement = self.layers["syke_groundwater_areas"]
        replacement.setCustomProperty("savonia/schema_json", '[{"name":"habitattype"}]')
        self.layers[source] = replacement
        language = self.language
        metadata, error = verify_source_layer(replacement, source, language)
        self.assertIsNone(metadata)
        self.assertEqual(error["reason_code"], "REQUIRED_FIELDS_MISSING")
        with self.assertRaises(QgsProcessingException) as caught:
            self.run_algorithm(language, "missing-" + language)
        self.assertIn(tr(language, "habitat_layer"), str(caught.exception))
        self.assertIn("habitattype", str(caught.exception))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_unknown_private_value_identifies_actual_source(self):
        self.fixture.sources["syke_protected_areas_private_land"]["KohdeTyyppi"] = "unknown-code"
        language = self.language
        with self.assertRaises(QgsProcessingException) as caught:
            self.run_algorithm(language, "unknown-" + language)
        self.assertIn(tr(language, "protected_private_layer"), str(caught.exception))
        self.assertIn("private-1", str(caught.exception))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])


class SourceFieldWorkflowEnglishTest(SourceFieldWorkflowChecks, unittest.TestCase):
    language = "en"


class SourceFieldWorkflowFinnishTest(SourceFieldWorkflowChecks, unittest.TestCase):
    language = "fi"


class SourceFieldFixtureTest(unittest.TestCase):
    def test_populated_initial_reads_preserve_processing_outputs_in_both_languages(self):
        vector_layer = QgsVectorLayer
        for test_class in (SourceFieldWorkflowEnglishTest, SourceFieldWorkflowFinnishTest):
            initial_requests = {}

            def source_layer(*args, **kwargs):
                layer = vector_layer(*args, **kwargs)
                if layer.providerType() != "WFS":
                    return layer
                get_features = layer.getFeatures

                def first_read(request=None):
                    layer.getFeatures = get_features
                    if request is None:
                        # Return real fixture records even on local runtimes
                        # whose unrestricted first read happens to be empty.
                        list(get_features())
                        return get_features(QgsFeatureRequest().setFilterRect(
                            QgsRectangle(350000, 6900000, 350100, 6900100)))
                    initial_requests[layer.name()] = request
                    return get_features(request)

                layer.getFeatures = first_read
                return layer

            with self.subTest(language=test_class.language), patch.object(
                    sys.modules[__name__], "QgsVectorLayer", side_effect=source_layer):
                case = test_class("test_processing_outputs_ignore_saved_schemas_in_both_languages")
                outcome = unittest.TestResult()
                case.run(outcome)
                self.assertTrue(outcome.wasSuccessful(), "\n".join(
                    traceback for _, traceback in outcome.errors + outcome.failures))
                self.assertEqual(set(initial_requests), set(SERVICE_DEFINITIONS))
                for request in initial_requests.values():
                    self.assertEqual(request.filterType(), Qgis.FeatureRequestFilterType.Fids)
                    self.assertFalse(request.filterFids())
                    self.assertEqual(request.limit(), 0)
                    self.assertEqual(request.filterRect(), case.aoi.extent())


class TranslationTest(unittest.TestCase):
    def test_translation_keys_and_placeholders_match(self):
        self.assertEqual(set(TEXT["fi"]), set(TEXT["en"]))
        formatter = string.Formatter()
        for key, template in TEXT["en"].items():
            fields = {field for _, field, _, _ in formatter.parse(template) if field}
            translated_fields = {field for _, field, _, _ in formatter.parse(TEXT["fi"][key]) if field}
            self.assertEqual(fields, translated_fields, key)
            for language in ("en", "fi"):
                tr(language, key, **{field: 1 for field in fields})
        for language in ("en", "fi"):
            message = source_readiness_message(language, {"reason_code": "REQUIRED_FIELDS_MISSING", "missing_fields": ["olotila"]})
            self.assertIn("olotila", message)


class PluginLifecycleTest(unittest.TestCase):
    def test_load_wizard_processing_registration_and_unload_in_both_languages(self):
        from unittest.mock import MagicMock

        window = QMainWindow()
        canvas = QgsMapCanvas(window)
        iface = MagicMock()
        iface.mainWindow.return_value = window
        iface.iconSize.return_value = QSize(16, 16)
        iface.mapCanvas.return_value = canvas
        iface.addToolBar.side_effect = window.addToolBar
        iface.addDockWidget.side_effect = window.addDockWidget
        iface.removeDockWidget.side_effect = window.removeDockWidget
        registry = QgsApplication.processingRegistry()
        for language in ("en", "fi"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as settings_dir:
                # Exercise real logging without touching the user's QGIS profile.
                with patch.object(QgsApplication, "qgisSettingsDirPath", return_value=settings_dir), patch(
                    "savonia_responsible_forest_planning_tool.ui.plugin.selected_language", return_value=language
                ):
                    plugin = classFactory(iface)
                    try:
                        plugin.initGui()
                        self.assertIsNotNone(registry.providerById("savonia_forest_planning"))
                        self.assertIsNotNone(registry.algorithmById("savonia_forest_planning:prepare_forest_scenario_inputs"))
                        self.assertEqual(plugin.wizard_action.text(), tr(language, "open_wizard"))
                        self.assertEqual(plugin.dock.windowTitle(), tr(language, "wizard_title"))
                        self.assertEqual(plugin.wizard.language, language)
                    finally:
                        plugin.unload()
                    self.assertIsNone(registry.providerById("savonia_forest_planning"))
        window.close()


if __name__ == "__main__":
    unittest.main()
