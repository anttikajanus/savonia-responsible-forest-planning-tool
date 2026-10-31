"""Wizard completion, map publication, cancellation and active-task unload."""

import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsApplication, QgsProject


from savonia_responsible_forest_planning_tool import RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX as PREFIX
from savonia_responsible_forest_planning_tool.analysis.worker_task import ResponsibleForestPlanningAnalysisTask
from savonia_responsible_forest_planning_tool.i18n import tr
from savonia_responsible_forest_planning_tool.ui.plugin import ResponsibleForestPlanningPlugin
from ui_fixture import Interface
from workflow_fixture import WorkflowFixtureMixin


class WizardCompletionTests(WorkflowFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(QgsApplication, "qgisSettingsDirPath", return_value=self.temp.name))
        self.iface = Interface()
        self.addCleanup(self.iface.window.deleteLater)
        self.plugin = ResponsibleForestPlanningPlugin(self.iface)
        self.addCleanup(self.plugin.unload)
        self.plugin.initGui()
        self.wizard = self.plugin.wizard
        # Remove only layers created by this test, retaining any preexisting project state.
        previous = set(QgsProject.instance().mapLayers())
        self.addCleanup(self.remove_test_layers, previous)

    def remove_test_layers(self, previous):
        self.iface.setActiveLayer(None)
        QgsProject.instance().removeMapLayers(list(set(QgsProject.instance().mapLayers()) - previous))
        # Complete deferred provider/UI work while the temporary GeoPackages exist.
        APP.processEvents()

    def task(self):
        task = ResponsibleForestPlanningAnalysisTask("completion fixture", {}, self.wizard._analysis_task_finished)
        self.wizard._analysis_task = task
        self.wizard.run_button.setEnabled(False)
        self.wizard.cancel_button.setEnabled(True)
        return task

    def assert_ready(self):
        self.assertIsNone(self.wizard._analysis_task)
        self.assertFalse(self.wizard.run_button.isEnabled())
        self.assertFalse(self.wizard.cancel_button.isEnabled())
        self.assertEqual(self.wizard.cancel_button.text(), tr(self.wizard.language, "cancel_analysis"))

    def test_failure_cancellation_and_result_reopen_failure_restore_controls(self):
        for language in ("en", "fi"):
            self.wizard.set_language(language)
            with self.subTest(language=language, outcome="failure"):
                task = self.task()
                task.error = RuntimeError("controlled source failure")
                task.finished(False)
                self.assert_ready()
                self.assertEqual(self.iface.message_levels[-1], "critical")
                self.assertIn("controlled source failure", self.iface.messages[-1][1])
            with self.subTest(language=language, outcome="cancelled"):
                task = self.task()
                with patch.object(task, "cancel", wraps=task.cancel) as cancel:
                    self.wizard.cancel_analysis()
                    self.wizard.cancel_analysis()
                    cancel.assert_called_once()
                task.finished(False)
                self.assert_ready()
                self.assertEqual(self.iface.message_levels[-1], "warning")
                self.assertEqual(self.iface.messages[-1][1], tr(language, "error_cancelled"))
            with self.subTest(language=language, outcome="reopen failure"), patch.object(
                    self.wizard, "_add_result_layer", side_effect=OSError("controlled reopen failure")):
                task = self.task()
                task.result = {"gpkg_path": "fixture.gpkg", "xlsx_path": "fixture.xlsx"}
                task.finished(True)
                self.assert_ready()
                self.assertEqual(self.iface.message_levels[-1], "critical")
                self.assertIn("controlled reopen failure", self.iface.messages[-1][1])

    def test_success_adds_filtered_views_and_snapshots_without_replacing_previous_runs(self):
        for language in ("en", "fi"):
            self.wizard.set_language(language)
            with self.subTest(language=language), self.scenario([]) as (fixture, layers, aoi):
                fixture.records["syke_rantaviiva_lake"] = [{
                    "attributes": {"objectid": "lake-1", "muutospvm": "2026-10-02"},
                    "coordinates": "350010,6900010 350090,6900010 350090,6900090 350010,6900090 350010,6900010",
                }]
                result = self.run_algorithm(layers, aoi, language, "wizard-" + language)
                task = self.task()
                task.result = {"gpkg_path": result["RESULT"].split("|", 1)[0], "xlsx_path": result["EXCEL"]}
                before = set(QgsProject.instance().mapLayers())
                previous_counts = {key: layer.featureCount() for key, layer in QgsProject.instance().mapLayers().items()
                                   if layer.customProperty(PREFIX + "class_view", False)}
                task.finished(True)
                self.assert_ready()
                self.assertEqual(self.iface.message_levels[-1], "success")
                for path in task.result.values():
                    self.assertIn(path, self.iface.messages[-1][1])
                project = QgsProject.instance()
                self.assertLessEqual(before, set(project.mapLayers()))
                self.assertEqual({key: project.mapLayer(key).featureCount() for key in previous_counts}, previous_counts)
                added = [layer for key, layer in project.mapLayers().items() if key not in before]
                views = [layer for layer in added if layer.customProperty(PREFIX + "class_view", False)]
                self.assertEqual(len(views), 18)
                self.assertEqual(len(added) - len(views), 9)
                self.assertEqual({layer.subsetString() for layer in views}, {
                    '"class_{0}" = \'{1}\''.format(tier, value)
                    for tier in ("all_out", "bau", "light", "balance", "protection", "superprotection")
                    for value in ("SENSITIVE", "ECONOMIC", "UNKNOWN")})
                self.assertIn(self.iface.active_layer, views)
                for layer in added:
                    node = project.layerTreeRoot().findLayer(layer.id())
                    self.assertTrue(node.itemVisibilityChecked())
                    self.assertEqual(node.isVisible(), layer in views and '"class_all_out"' in layer.subsetString())
                    if layer in views:
                        subset = layer.subsetString()
                        tier = next(value for value in ("all_out", "bau", "light", "balance", "protection", "superprotection")
                                    if '"class_{0}"'.format(value) in subset)
                        class_code = next(value for value in ("SENSITIVE", "ECONOMIC", "UNKNOWN")
                                          if "'{0}'".format(value) in subset)
                        expected = int(
                            class_code == "SENSITIVE" and tier in ("balance", "protection", "superprotection")
                            or class_code == "ECONOMIC" and tier in ("all_out", "bau", "light")
                        )
                    else:
                        expected = int(any("|layername=" + layer_id in layer.source() for layer_id in (
                            "forest_centre_stand", "buffered_water_evidence",
                        )))
                        self.assertFalse(node.parent().itemVisibilityChecked())
                        node.parent().setItemVisibilityChecked(True)
                        self.assertTrue(node.isVisible())
                        node.parent().setItemVisibilityChecked(False)
                    self.assertEqual(layer.featureCount(), expected, layer.source())
                    self.assertEqual(len(list(layer.getFeatures())), expected, layer.source())
                    if "|layername=buffered_water_evidence" in layer.source():
                        self.assertEqual(layer.name(), "{0} ({1})".format(
                            tr(language, "water_evidence_layer"), tr(language, "run_input_suffix")))
                for view in views:
                    node = project.layerTreeRoot().findLayer(view.id())
                    parent = node.parent()
                    self.assertEqual(parent.itemVisibilityChecked(), '"class_all_out"' in view.subsetString())
                    parent.setItemVisibilityChecked(True)
                    self.assertTrue(node.isVisible())
                    parent.setItemVisibilityChecked('"class_all_out"' in view.subsetString())

    def test_success_warning_is_presented_after_layer_publication(self):
        for language in ("en", "fi"):
            self.wizard.set_language(language)
            with self.subTest(language=language), self.scenario([]) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "warning-" + language)
                task = self.task()
                warning = tr(language, "warning_stand_overlaps", path="profile/technical.log")
                task.result = {"gpkg_path": result["RESULT"].split("|", 1)[0],
                               "xlsx_path": result["EXCEL"], "warnings": [warning]}
                before = set(QgsProject.instance().mapLayers())
                task.finished(True)
                self.assertGreater(len(set(QgsProject.instance().mapLayers()) - before), 0)
                self.assertEqual(self.iface.message_levels[-2:], ["success", "warning"])
                self.assertEqual(self.iface.messages[-1][1], warning)

    def test_unload_cancels_active_task_and_detaches_late_completion(self):
        task = self.task()
        messages = list(self.iface.messages)
        self.plugin.unload()
        self.assertTrue(task.cancellation_requested())
        # Completion after unload must never call a deleted wizard or mutate the project.
        task.finished(False)
        APP.processEvents()
        self.assertEqual(self.iface.messages, messages)
        self.assertIsNone(self.plugin.wizard)


if __name__ == "__main__":
    unittest.main()
