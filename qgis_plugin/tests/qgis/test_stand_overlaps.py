"""Nonfatal stand overlaps at Processing, worker and published-output seams."""

import json
from pathlib import Path
import time
import unittest

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsApplication, QgsProcessingFeedback, QgsProject, QgsVectorLayer
from qgis.PyQt.QtTest import QTest

from savonia_responsible_forest_planning_tool import app_logging
from savonia_responsible_forest_planning_tool.analysis.worker_task import (
    capture_worker_inputs, ResponsibleForestPlanningAnalysisTask,
)
from workflow_fixture import WorkflowFixtureMixin, coordinates, fixture_sources, source_record


class WarningFeedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.warnings = []

    def pushWarning(self, message):
        self.warnings.append(message)
        super().pushWarning(message)


class StandOverlapTests(WorkflowFixtureMixin, unittest.TestCase):
    def test_split_parents_keep_duplicate_contributions_and_warn_after_publication(self):
        fields = fixture_sources()
        stands = [source_record({**fields["forest_centre_stand"], "standid": "parent"}, width=60),
                  source_record({**fields["forest_centre_stand"], "standid": "overlapping"}, x=350050, width=40),
                  source_record({**fields["forest_centre_stand"], "standid": "unrelated"}, x=350090, width=10)]
        self.addCleanup(app_logging.shutdown_logging)
        folder = Path(app_logging.configure_logging())
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([], stands, version="2.0.0") as (fixture, layers, aoi):
                fixture.records["syke_groundwater_areas"] = [source_record(
                    fields["syke_groundwater_areas"], width=25)]
                feedback = WarningFeedback()
                result = self.run_algorithm(layers, aoi, language, "overlap-" + language, feedback)
                layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
                alias = layer.attributeAlias(layer.fields().indexFromName("stand_has_overlap"))
                self.assertIn("Parent stand" if language == "en" else "Emokuvio", alias)
                features = list(layer.getFeatures())
                self.assertGreater(len([f for f in features if f["source_stand_id"] == "parent"]), 1)
                self.assertAlmostEqual(sum(f.geometry().area() for f in features), 11000)
                for feature in features:
                    self.assertEqual(bool(feature["stand_has_overlap"]), feature["source_stand_id"] != "unrelated")
                self.assertEqual(len(feedback.warnings), 1)
                self.assertIn("päällekkäisiä" if language == "fi" else "overlapping", feedback.warnings[0])
                self.assertIn(str(folder / "technical.log"), feedback.warnings[0])
                self.assertTrue(Path(result["EXCEL"]).is_file())

                snapshot = capture_worker_inputs(aoi, layers, False, QgsProject.instance().transformContext(),
                                                 language, self.temp.name, "worker-overlap-" + language, sawlog_price_eur_m3=75.25)
                completed = []
                task = ResponsibleForestPlanningAnalysisTask("overlap fixture", snapshot,
                    lambda finished, success: completed.append(success))
                QgsApplication.taskManager().addTask(task)
                deadline = time.monotonic() + 30
                while not completed and time.monotonic() < deadline:
                    APP.processEvents()
                    QTest.qWait(5)
                self.assertEqual(completed, [True], str(task.error))
                self.assertEqual(task.result["warnings"], feedback.warnings)
                self.assertEqual(task.result["stand_overlap_summary"]["pair_count"], 1)
        app_logging.shutdown_logging()
        technical = (folder / "technical.log").read_text(encoding="utf-8")
        pair_records = [line for line in technical.splitlines() if "event=stand_overlap_pair " in line]
        aggregate_records = [line for line in technical.splitlines() if "event=stand_overlaps " in line]
        self.assertEqual(len(pair_records), 4)
        self.assertEqual(len(aggregate_records), 4)
        self.assertTrue(all("first=parent second=overlapping" in line and "overlap_area_m2=1000" in line
                            for line in pair_records))
        self.assertTrue(all("pair_count=1 affected_stand_count=2" in line for line in aggregate_records))
        business = (folder / "business-actions.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("overlap", business)
        self.assertTrue(all(isinstance(json.loads(line), dict) for line in business.splitlines()))

    def test_overlap_outside_aoi_does_not_flag_or_warn(self):
        fields = fixture_sources()["forest_centre_stand"]
        stands = [source_record(fields), source_record({**fields, "standid": "right"}, x=350050)]
        with self.scenario([], stands, aoi=[coordinates(350000, 6900000, 50, 100),
                coordinates(350100, 6900000, 50, 100)], version="2.0.0") as (_, layers, aoi):
            feedback = WarningFeedback()
            result = self.run_algorithm(layers, aoi, "en", "outside", feedback)
            layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
            self.assertEqual(layer.featureCount(), 2)
            self.assertFalse(any(bool(f["stand_has_overlap"]) for f in layer.getFeatures()))
            self.assertEqual(feedback.warnings, [])


if __name__ == "__main__":
    unittest.main()
