"""Wizard parameter completeness, locale input and remembered profile values."""

import unittest
import time
from pathlib import Path
from unittest.mock import patch

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsRectangle, QgsSettings, QgsVectorLayer
from qgis.PyQt.QtTest import QTest

from savonia_responsible_forest_planning_tool.ui.wizard import ResponsibleForestPlanningWizard
from ui_fixture import Interface
from workflow_fixture import WorkflowFixtureMixin, fixture_sources, source_record


PRICE_KEY = "savonia-forest-planning/sawlog-price-eur-m3"


class WizardReadinessTests(WorkflowFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        settings = QgsSettings()
        previous = settings.value(PRICE_KEY)
        if previous is not None:
            self.addCleanup(settings.setValue, PRICE_KEY, previous)
        else:
            self.addCleanup(settings.remove, PRICE_KEY)
        settings.remove(PRICE_KEY)
        self.iface = Interface()
        self.addCleanup(self.iface.window.deleteLater)

    def wizard(self, language):
        wizard = ResponsibleForestPlanningWizard(self.iface, language)
        self.addCleanup(wizard.deleteLater)
        self.addCleanup(wizard.shutdown)
        wizard.output_folder.setText(self.temp.name)
        return wizard

    def register_inputs(self, layers, aoi):
        project = QgsProject.instance()
        for service_id, layer in layers.items():
            layer.setCustomProperty("savonia/service_id", service_id)
            project.addMapLayer(layer)
            self.addCleanup(project.removeMapLayer, layer.id())
        project.addMapLayer(aoi)
        self.addCleanup(project.removeMapLayer, aoi.id())

    def test_price_is_blank_localized_and_remembers_only_valid_current_values(self):
        for language, entered, formatted in (("fi", "74,35", "74,35"), ("en", "74.35", "74.35")):
            with self.subTest(language=language):
                QgsSettings().remove(PRICE_KEY)
                wizard = self.wizard(language)
                wizard.show()
                APP.processEvents()
                self.assertEqual(wizard.sawlog_price.text(), "")
                self.assertFalse(wizard.run_button.isEnabled())
                self.assertEqual(wizard.sawlog_price_label.text(),
                    "Tukkipuun kantohinta (€/m³)" if language == "fi" else "Sawlog stumpage price (€/m³)")
                wizard.sawlog_price.setText(entered)
                wizard.sawlog_price.editingFinished.emit()
                self.assertEqual(wizard.sawlog_price.text(), formatted)
                self.assertEqual(float(QgsSettings().value(PRICE_KEY)), 74.35)
                self.assertLess(wizard.area_group.y(), wizard.sawlog_price.y())
                self.assertLess(wizard.sawlog_price.y(), wizard.output_folder.y())
                state = wizard.capture_state()
                wizard.sawlog_price.clear()
                self.assertFalse(wizard.run_button.isEnabled())
                self.assertEqual(float(QgsSettings().value(PRICE_KEY)), 74.35)
                wizard.restore_state(state)
                self.assertEqual(wizard.sawlog_price.text(), formatted)
                reopened = self.wizard(language)
                self.assertEqual(reopened.sawlog_price.text(), formatted)
                for invalid in ("", "0", "-1", "nan", "inf", "1.001" if language == "en" else "1,001"):
                    reopened.sawlog_price.setText(invalid)
                    reopened.sawlog_price.editingFinished.emit()
                    self.assertEqual(float(QgsSettings().value(PRICE_KEY)), 74.35)
                    self.assertFalse(reopened.run_button.isEnabled())

    def test_run_tracks_current_area_price_sources_and_output_without_reading_remote_features(self):
        for language in ("fi", "en"):
            with self.subTest(language=language), self.scenario([], version="2.0.0") as (fixture, layers, aoi):
                self.register_inputs(layers, aoi)
                wizard = self.wizard(language)
                wizard.layer_combo.setLayer(aoi)
                wizard.sawlog_price.setText("75,25" if language == "fi" else "75.25")
                with patch.object(layers["forest_centre_stand"], "featureCount", side_effect=AssertionError("remote count")), patch.object(
                        layers["forest_centre_stand"], "getFeatures", side_effect=AssertionError("remote read")):
                    requests = list(fixture.requests)
                    self.assertTrue(wizard.run_button.isEnabled())
                    for invalid in ("", "0", "-1", "nan", "1,001" if language == "fi" else "1.001"):
                        wizard.sawlog_price.setText(invalid)
                        self.assertFalse(wizard.run_button.isEnabled())
                        self.assertEqual(float(QgsSettings().value(PRICE_KEY)), 75.25)
                    wizard.sawlog_price.setText("75,25" if language == "fi" else "75.25")
                    self.assertTrue(wizard.run_button.isEnabled())
                    wizard.output_folder.clear()
                    self.assertFalse(wizard.run_button.isEnabled())
                    blocked = Path(self.temp.name) / "a-file"
                    blocked.write_text("fixture", encoding="utf-8")
                    wizard.output_folder.setText(str(blocked))
                    self.assertFalse(wizard.run_button.isEnabled())
                    wizard.output_folder.setText(self.temp.name)
                    self.assertTrue(wizard.run_button.isEnabled())
                    aoi.selectAll()
                    wizard.selected_only.setChecked(False)
                    wizard.selected_only.setChecked(True)
                    aoi.removeSelection()
                    self.assertTrue(wizard.selected_only.isChecked())
                    self.assertFalse(wizard.run_button.isEnabled())
                    wizard.selected_only.setChecked(False)
                    self.assertTrue(wizard.run_button.isEnabled())
                    wizard.draw_mode.setChecked(True)
                    self.assertFalse(wizard.run_button.isEnabled())
                    wizard.restore_state({**wizard.capture_state(), "drawn_aoi": aoi})
                    self.assertTrue(wizard.run_button.isEnabled())
                    wizard.clear_drawn_aoi_button.click()
                    self.assertFalse(wizard.run_button.isEnabled())
                    wizard.extent_mode.setChecked(True)
                    self.iface.canvas.setDestinationCrs(aoi.crs())
                    self.iface.canvas.setExtent(QgsRectangle(350000, 6900000, 350100, 6900100))
                    self.assertTrue(wizard.run_button.isEnabled())
                    wizard.layer_mode.setChecked(True)
                    wizard.layer_combo.setLayer(layers["forest_centre_stand"])
                    self.assertTrue(wizard.run_button.isEnabled())
                    wizard.sawlog_price.clear()
                    wizard.run_analysis()
                    self.assertIsNone(wizard._analysis_task)
                    self.assertEqual(self.iface.message_levels[-1], "warning")
                    wizard.sawlog_price.setText("75,25" if language == "fi" else "75.25")
                    source = layers["forest_centre_stand"]
                    source.setCustomProperty("savonia/schema_changed_to", "other-type")
                    self.assertFalse(wizard.run_button.isEnabled())
                    source.setCustomProperty("savonia/schema_changed_to", "")
                    self.assertTrue(wizard.run_button.isEnabled())
                    habitat = QgsProject.instance().takeMapLayer(layers["forest_centre_habitat"])
                    self.assertFalse(wizard.run_button.isEnabled())
                    habitat.setCustomProperty("savonia/service_id", "")
                    QgsProject.instance().addMapLayer(habitat)
                    self.assertFalse(wizard.run_button.isEnabled())
                    habitat.setCustomProperty("savonia/service_id", "forest_centre_habitat")
                    self.assertTrue(wizard.run_button.isEnabled())
                    habitat.setCustomProperty("savonia/schema_changed_to", "replacement")
                    self.assertFalse(wizard.run_button.isEnabled())
                    habitat.setCustomProperty("savonia/schema_changed_to", "")
                    self.assertTrue(wizard.run_button.isEnabled())
                    self.assertEqual(fixture.requests, requests)
                wizard.shutdown()
                for layer in layers.values():
                    QgsProject.instance().removeMapLayer(layer.id())
                QgsProject.instance().removeMapLayer(aoi.id())

    def test_empty_local_aoi_edits_update_run_readiness(self):
        with self.scenario([], version="2.0.0") as (_, layers, _):
            aoi = QgsVectorLayer("Polygon?crs=EPSG:3067", "empty", "memory")
            self.register_inputs(layers, aoi)
            wizard = self.wizard("en")
            wizard.layer_combo.setLayer(aoi)
            wizard.sawlog_price.setText("75.25")
            self.assertFalse(wizard.run_button.isEnabled())
            aoi.startEditing()
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt("POLYGON ((0 0,10 0,10 10,0 10,0 0))"))
            aoi.addFeature(feature)
            self.assertTrue(wizard.run_button.isEnabled())
            aoi.deleteFeature(feature.id())
            self.assertFalse(wizard.run_button.isEnabled())
            aoi.rollBack()

    def test_run_captures_entered_price_disables_during_task_and_presents_overlap_warning(self):
        fields = fixture_sources()["forest_centre_stand"]
        stands = [source_record(fields), source_record({**fields, "standid": "second"}, x=350025, width=50)]
        with self.scenario([], stands, version="2.0.0") as (_, layers, aoi):
            before = set(QgsProject.instance().mapLayers())
            self.register_inputs(layers, aoi)
            wizard = self.wizard("fi")
            self.addCleanup(QgsProject.instance().removeMapLayers,
                list(set(QgsProject.instance().mapLayers()) - before))
            wizard.layer_combo.setLayer(aoi)
            wizard.sawlog_price.setText("94,15")
            self.assertTrue(wizard.run_button.isEnabled())
            wizard.run_button.click()
            self.assertFalse(wizard.run_button.isEnabled())
            self.assertTrue(wizard.cancel_button.isEnabled())
            deadline = time.monotonic() + 30
            while wizard._analysis_task is not None and time.monotonic() < deadline:
                APP.processEvents()
                QTest.qWait(5)
            self.assertIsNone(wizard._analysis_task)
            self.assertTrue(wizard.run_button.isEnabled())
            self.assertFalse(wizard.cancel_button.isEnabled())
            self.assertEqual(self.iface.message_levels[-2:], ["success", "warning"])
            self.assertIn("technical.log", self.iface.messages[-1][1])
            views = [layer for layer in QgsProject.instance().mapLayers().values()
                     if layer.customProperty("savonia/class_view", False)]
            self.assertEqual(len(views), 18)
            economic = next(layer for layer in views if layer.subsetString() == '\"class_all_out\" = \'ECONOMIC\'')
            self.assertEqual({f["stumpage_price_eur_m3"] for f in economic.getFeatures()}, {94.15})
            new_layer_ids = list(set(QgsProject.instance().mapLayers()) - before)
            wizard.shutdown()
            QgsProject.instance().removeMapLayers(new_layer_ids)


if __name__ == "__main__":
    unittest.main()
