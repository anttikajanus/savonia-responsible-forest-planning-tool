"""End-to-end local WFS/Processing and wizard-owned input regressions."""

import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import (NULL, QgsApplication, QgsProcessingException, QgsProcessingFeedback, QgsProject, QgsVectorLayer)
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtTest import QTest
from qgis.gui import QgsMapCanvas

from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.worker_task import capture_worker_inputs, ResponsibleForestPlanningAnalysisTask
from savonia_responsible_forest_planning_tool.i18n import tr
from workflow_fixture import WorkflowFixtureMixin, coordinates, fixture_sources, source_record
from test_grid_publication import workbook_rows


class GridWorkflowTest(WorkflowFixtureMixin, unittest.TestCase):
    def test_boundary_grid_weights_and_localized_artifacts_in_both_languages(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        grid = [source_record({**fields, "GRIDCELLID": "left", "VOLUME": 100,
                              "VOLUMEPINE": 100, "VOLUMESPRUCE": 100, "VOLUMEDECIDUOUS": 100}, width=16, height=16),
                source_record({**fields, "GRIDCELLID": "right", "VOLUME": 300,
                              "VOLUMEPINE": 300, "VOLUMESPRUCE": 300, "VOLUMEDECIDUOUS": 300},
                              x=350016, width=16, height=16)]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario(grid,
                    aoi=[coordinates(350012, 6900000, 16, 16)]) as (fixture, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "boundary-" + language)
                layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
                feature, = list(layer.getFeatures())
                self.assertEqual(feature["area_ha"], 0.03)
                self.assertAlmostEqual(feature.geometry().area() / 10000, 0.0256)
                self.assertAlmostEqual(json.loads(feature["indicator_coverage"])
                    ["grid_total_volume_m3_ha"]["valid_area_ha"], 0.0256)
                for metric in ("grid_total_volume_m3_ha", "pine_volume_m3_ha",
                               "spruce_volume_m3_ha", "deciduous_volume_m3_ha"):
                    self.assertAlmostEqual(feature[metric], 250)
                self.assertEqual(feature["total_volume_m3_ha"], 200)
                self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("grid_total_volume_m3_ha")),
                                 tr(language, "metric_grid_total_volume_m3_ha"))
                self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("share_under_20")),
                                 tr(language, "metric_share_under_20"))
                self.assertIn("Grid mean age" if language == "en" else "Hila keski-ikä",
                              tr(language, "metric_share_under_20"))
                sheets = workbook_rows(result["EXCEL"])
                header = sheets[tr(language, "sheet_summary")][0]
                self.assertIn(tr(language, "metric_grid_total_volume_m3_ha"), header)
                grid_requests = [query for query in fixture.requests if query.get("request", "").lower() == "getfeature"
                                 and query.get("typename", "").endswith("forest_centre_gridcell")]
                self.assertEqual(len(grid_requests), 1)
                self.assertIn("bbox", grid_requests[0])

    def test_partial_summaries_use_valid_hectares_and_keep_observed_area_lower_bounds(self):
        fields = fixture_sources()
        stands = [source_record({**fields["forest_centre_stand"], "standid": "stand-left", "VOLUME": 100}),
                  source_record({**fields["forest_centre_stand"], "standid": "stand-right", "VOLUME": 300}, x=350100)]
        grid_fields = fields["forest_centre_gridcell"]
        grid = [source_record({**grid_fields, "GRIDCELLID": "quarter", "VOLUME": 100, "AGE": 10}, width=50, height=50),
                source_record({**grid_fields, "GRIDCELLID": "whole", "VOLUME": 300, "AGE": 90,
                              "SOILTYPE": 11, "DRAINAGESTATE": 1}, x=350100)]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario(grid, stands,
                    [coordinates(350000, 6900000, 200, 100)]) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "partial-" + language)
                sheets = workbook_rows(result["EXCEL"])
                summary = sheets[tr(language, "sheet_summary")]
                summary_row = next(row for row in summary[1:] if row[:2] == [tr(language, "tier_all_out"), tr(language, "class_economic")])
                metrics = dict(zip(summary[0], summary_row))
                for metric, expected in (("grid_total_volume_m3_ha", 260), ("total_volume_m3_ha", 200),
                                         ("share_under_20", 20), ("share_20_80", 0), ("share_over_80", 80)):
                    self.assertEqual(metrics[tr(language, "metric_" + metric)], expected)
                self.assertIsNone(metrics[tr(language, "metric_peatland_area_ha")])
                self.assertIsNone(metrics[tr(language, "metric_natural_mire_area_ha")])
                coverage_rows = sheets[tr(language, "sheet_metric_coverage")]
                age = next(row for row in coverage_rows[1:] if row[:3] == [tr(language, "tier_all_out"), tr(language, "class_economic"), "share_under_20"])
                self.assertEqual((age[6], age[7], age[9], age[11]), (1.25, 0.75, 0.25, 63))
                peat = next(row for row in coverage_rows[1:] if row[:3] == [tr(language, "tier_all_out"), tr(language, "class_economic"), "peatland_area_ha"])
                self.assertEqual((peat[5], peat[9]), ("PARTIAL", 0.25))
                gpkg = result["RESULT"].split("|", 1)[0]
                snapshot = QgsVectorLayer(gpkg + "|layername=forest_centre_gridcell", "grid", "ogr")
                self.assertEqual(snapshot.featureCount(), 2)
                feature = next(snapshot.getFeatures())
                self.assertEqual(feature["TREEDATADATE"], "2021-06-01")
                self.assertEqual(feature["UPDATETIME"], "2026-10-01")
                metadata = QgsVectorLayer(gpkg + "|layername=run_metadata", "metadata", "ogr")
                run = next(metadata.getFeatures())
                self.assertEqual(run["project_name"], tr(language, "project_name"))
                self.assertEqual(run["project_status"], "personal_learning_prototype")
                self.assertEqual(run["prototype_notice"], tr(language, "prototype_notice"))
                self.assertIn(tr(language, "prototype_notice"), json.loads(run["limitations"]))
                exact = json.loads(run["metric_coverage"])["share_under_20"]
                self.assertEqual(exact["coverage_percent_exact"], 62.5)
                self.assertEqual(exact["coverage_percent"], 63)
                dates = json.loads(run["grid_source_dates"])
                self.assertEqual(dates["treedatadate"]["observed_values"], ["2021-06-01"])
                self.assertEqual(dates["updatetime"]["observed_values"], ["2026-10-01"])

    def test_worker_inputs_match_processing_across_canvas_scales_and_dissolved_aoi(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([source_record(fields)], aoi=[
                    coordinates(350000, 6900000, 75, 100), coordinates(350025, 6900000, 75, 100)
            ]) as (fixture, layers, aoi):
                canvas = QgsMapCanvas()
                canvas.resize(800, 600)
                canvas.setExtent(aoi.extent())
                grid = layers["forest_centre_gridcell"]
                grid.setScaleBasedVisibility(True)
                grid.setMinimumScale(300)
                canvas.zoomScale(200)
                near = self.run_algorithm(layers, aoi, language, "near-" + language)
                canvas.zoomScale(500)
                snapshot = capture_worker_inputs(aoi, layers, False, QgsProject.instance().transformContext(),
                                                 language, self.temp.name, "worker-far-" + language, sawlog_price_eur_m3=75.25)
                def assert_no_qobjects(value):
                    self.assertNotIsInstance(value, QObject)
                    if isinstance(value, dict):
                        for child in value.values():
                            assert_no_qobjects(child)
                    elif isinstance(value, (tuple, list)):
                        for child in value:
                            assert_no_qobjects(child)
                assert_no_qobjects(snapshot)
                completed = []
                task = ResponsibleForestPlanningAnalysisTask("fixture", snapshot, lambda finished, success: completed.append(success))
                QgsApplication.taskManager().addTask(task)
                deadline = time.monotonic() + 30
                while not completed and time.monotonic() < deadline:
                    APP.processEvents()
                    QTest.qWait(5)
                self.assertEqual(completed, [True], str(task.error) + repr(fixture.requests))
                near_layer = QgsVectorLayer(near["RESULT"], "near", "ogr")
                far_layer = QgsVectorLayer(task.result["gpkg_path"] + "|layername=classified_forest_polygons", "far", "ogr")
                near_row, = list(near_layer.getFeatures())
                far_row, = list(far_layer.getFeatures())
                self.assertEqual(near_row["area_ha"], 1)
                for field in ("total_volume_m3_ha", "grid_total_volume_m3_ha", "share_under_20",
                              "indicator_coverage", "check_section10", "check_protected"):
                    self.assertEqual(near_row[field], far_row[field])
                self.assertTrue(all("bbox" in request for request in fixture.requests
                                    if request.get("request", "").lower() == "getfeature"))
                canvas.close()

    def test_storage_tolerance_fragments_are_skipped_without_fatal_partition_errors(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        tiny = source_record(fields, x=349984.000000005, width=16, height=1)
        with self.scenario([tiny]) as (_, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "tiny-fragment")
            layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
            feature, = list(layer.getFeatures())
            self.assertEqual(feature["grid_total_volume_m3_ha"], NULL)
            self.assertEqual(feature["total_volume_m3_ha"], 200)
            gpkg = result["RESULT"].split("|", 1)[0]
            snapshot = QgsVectorLayer(gpkg + "|layername=forest_centre_gridcell", "grid", "ogr")
            self.assertEqual(snapshot.featureCount(), 0)

    def test_fresh_processing_sources_work_before_any_rendering_or_iterator_initialization(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        with self.scenario([source_record(fields)], prime=False) as (fixture, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "unprimed-processing")
            layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
            feature, = list(layer.getFeatures())
            self.assertEqual(feature["grid_total_volume_m3_ha"], 250)
            self.assertEqual(feature["total_volume_m3_ha"], 200)
            self.assertTrue(all("bbox" in query for query in fixture.requests
                                if query.get("request", "").lower() == "getfeature"))

    def test_empty_and_invalid_grid_values_never_fall_back_to_stands(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        variants = {"empty": [], "invalid": [source_record({**fields, "VOLUME": None,
            "VOLUMEPINE": 0, "VOLUMESPRUCE": -1, "VOLUMEDECIDUOUS": None,
            "AGE": None, "SOILTYPE": 999, "DRAINAGESTATE": 1.5})]}
        for label, records in variants.items():
            with self.subTest(label=label), self.scenario(records) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, "en", label)
                layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
                feature, = list(layer.getFeatures())
                self.assertEqual(feature["total_volume_m3_ha"], 200)
                statuses = {metric: item["status"] for metric, item in json.loads(feature["indicator_coverage"]).items() if "status" in item}
                for metric in ("grid_total_volume_m3_ha", "spruce_volume_m3_ha", "deciduous_volume_m3_ha",
                               "share_under_20", "share_20_80", "share_over_80", "peatland_area_ha", "natural_mire_area_ha"):
                    self.assertEqual(feature[metric], NULL)
                    self.assertEqual(statuses[metric], "UNKNOWN_FIELD_OR_VALUE")
                if label == "invalid":
                    self.assertEqual(feature["pine_volume_m3_ha"], 0)
                    self.assertEqual(statuses["pine_volume_m3_ha"], "AVAILABLE")
                self.assertNotIn("birch_volume_m3_ha", layer.fields().names())
                self.assertNotIn("birch_volume_m3_ha", statuses)
                self.assertEqual(statuses["stumpage_price_eur_m3"], "AVAILABLE")

    def test_duplicate_records_deduplicate_and_conflicts_or_overlaps_publish_nothing(self):
        schemas = fixture_sources()
        first = source_record(schemas["forest_centre_gridcell"])
        with self.scenario([first, first]) as (_, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "identical")
            gpkg = result["RESULT"].split("|", 1)[0]
            snapshot = QgsVectorLayer(gpkg + "|layername=forest_centre_gridcell", "grid", "ogr")
            self.assertEqual(snapshot.featureCount(), 1)
        variants = [([first, source_record({**schemas["forest_centre_gridcell"], "VOLUME": 999})], None, ["cell-1"]),
                    ([first, source_record({**schemas["forest_centre_gridcell"], "GRIDCELLID": "cell-2"}, x=350050)], None, ["cell-1", "cell-2"]),
                    ([], [source_record({**schemas["forest_centre_stand"], "standid": "stand-1"}),
                          source_record({**schemas["forest_centre_stand"], "standid": "stand-2"}, x=350050)], ["stand-1", "stand-2"])]
        for language in ("en", "fi"):
            for index, (grid, stands, identifiers) in enumerate(variants):
                name = "fatal-%s-%d" % (language, index)
                with self.subTest(language=language, variant=index), self.scenario(grid, stands) as (_, layers, aoi):
                    with self.assertRaises(QgsProcessingException) as error:
                        self.run_algorithm(layers, aoi, language, name)
                    for identifier in identifiers:
                        self.assertIn(identifier, str(error.exception))
                    self.assertEqual(list(Path(self.temp.name).glob(name + ".*")), [])

    def test_cancellation_and_workbook_failure_remove_both_output_artifacts(self):
        class CancelAfterGeopackage(QgsProcessingFeedback):
            def setProgress(self, value):
                super().setProgress(value)
                if value >= 94:
                    self.cancel()

        fields = fixture_sources()["forest_centre_gridcell"]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([source_record(fields)]) as (_, layers, aoi):
                name = "cancel-" + language
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, name, CancelAfterGeopackage())
                self.assertIn(tr(language, "error_cancelled"), str(error.exception))
                self.assertEqual(list(Path(self.temp.name).glob(name + ".*")), [])

            with self.subTest(language=language), self.scenario([source_record(fields)]) as (_, layers, aoi):
                # The external ZIP/file boundary fails after the GeoPackage is
                # written, exercising paired cleanup through the full algorithm.
                import zipfile
                original_zip = zipfile.ZipFile
                def failing_output(path, mode="r", *args, **kwargs):
                    if mode == "w" and str(path).endswith(".xlsx"):
                        raise OSError("controlled workbook write failure")
                    return original_zip(path, mode, *args, **kwargs)
                name = "write-failure-" + language
                with patch.object(zipfile, "ZipFile", side_effect=failing_output), self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, name)
                self.assertIn("controlled workbook write failure", str(error.exception))
                self.assertEqual(list(Path(self.temp.name).glob(name + ".*")), [])

    def test_failed_grid_request_stops_instead_of_publishing_empty_grid_coverage(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        for mode in ("http", "ows-exception"):
            with self.subTest(mode=mode), self.scenario([source_record(fields)]) as (fixture, layers, aoi):
                failures = fixture.feature_failures if mode == "http" else fixture.service_exceptions
                failures.add("forest_centre_gridcell")
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, "en", "failed-request")
                self.assertIn("forest_centre_gridcell", str(error.exception))
                self.assertEqual(list(Path(self.temp.name).glob("failed-request.*")), [])

    def test_worker_request_failure_is_fatal_and_successful_reads_clear_stale_errors(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        with self.scenario([source_record(fields)]) as (fixture, layers, aoi):
            fixture.feature_failures.add("forest_centre_gridcell")
            snapshot = capture_worker_inputs(aoi, layers, False, QgsProject.instance().transformContext(),
                                             "fi", self.temp.name, "worker-failed-request", sawlog_price_eur_m3=75.25)
            completed = []
            task = ResponsibleForestPlanningAnalysisTask("fixture failure", snapshot, lambda finished, success: completed.append(success))
            QgsApplication.taskManager().addTask(task)
            deadline = time.monotonic() + 30
            while not completed and time.monotonic() < deadline:
                APP.processEvents()
                QTest.qWait(5)
            self.assertEqual(completed, [False])
            self.assertIn("forest_centre_gridcell", str(task.error))
            self.assertEqual(list(Path(self.temp.name).glob("worker-failed-request.*")), [])
        # A provider's earlier diagnostic must not poison a later valid read.
        with self.scenario([source_record(fields)]) as (_, layers, aoi):
            layers["forest_centre_gridcell"].dataProvider().pushError("Previous request failed")
            result = self.run_algorithm(layers, aoi, "en", "fresh-success")
            layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
            feature, = list(layer.getFeatures())
            self.assertEqual(feature["grid_total_volume_m3_ha"], 250)


if __name__ == "__main__":
    unittest.main()
