"""Wizard completion, map publication, cancellation and active-task unload."""

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

from qgis.core import QgsApplication, QgsProject

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], True)
    APP.initQgis()

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
        self.assertTrue(self.wizard.run_button.isEnabled())
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
            with self.subTest(language=language), self.scenario([]) as (_, layers, aoi):
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
                self.assertEqual(len(added) - len(views), 8)
                self.assertEqual({layer.subsetString() for layer in views}, {
                    '"class_{0}" = \'{1}\''.format(tier, value)
                    for tier in ("all_out", "bau", "light", "balance", "protection", "superprotection")
                    for value in ("SENSITIVE", "ECONOMIC", "UNKNOWN")})
                self.assertIn(self.iface.active_layer, views)
                for layer in added:
                    node = project.layerTreeRoot().findLayer(layer.id())
                    self.assertEqual(node.isVisible(), layer in views and '"class_all_out"' in layer.subsetString())
                    if layer in views:
                        subset = layer.subsetString()
                        expected = int(('"class_superprotection"' in subset and "'SENSITIVE'" in subset)
                                       or ('"class_superprotection"' not in subset and "'ECONOMIC'" in subset))
                    else:
                        expected = int("|layername=forest_centre_stand" in layer.source())
                    self.assertEqual(layer.featureCount(), expected, layer.source())
                    self.assertEqual(len(list(layer.getFeatures())), expected, layer.source())

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
