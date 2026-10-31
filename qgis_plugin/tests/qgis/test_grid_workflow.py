"""End-to-end local WFS/Processing and wizard-owned input regressions."""

import json
from pathlib import Path
import sqlite3
import time
import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import (NULL, QgsApplication, QgsGeometry, QgsProcessingException, QgsProcessingFeedback, QgsProject, QgsVectorLayer)
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtTest import QTest
from qgis.gui import QgsMapCanvas

from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.worker_task import capture_worker_inputs, ResponsibleForestPlanningAnalysisTask
from savonia_responsible_forest_planning_tool.i18n import tr
from workflow_fixture import WorkflowFixtureMixin, coordinates, fixture_sources, source_record
from test_grid_publication import workbook_rows
from wfs_fixture import request_has_bbox


class GridWorkflowTest(WorkflowFixtureMixin, unittest.TestCase):
    def test_empty_water_sources_publish_available_no_match_and_source_failure_publishes_nothing(self):
        line_id = "syke_rantaviiva_line_river"
        with self.scenario([]) as (_, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "empty-water")
            classified = QgsVectorLayer(result["RESULT"], "classified", "ogr")
            feature, = list(classified.getFeatures())
            self.assertEqual(feature["check_riparian_buffer"], "NO_MATCH")
            self.assertEqual(feature["class_balance"], "ECONOMIC")
            gpkg_path = result["RESULT"].split("|", 1)[0]
            evidence = QgsVectorLayer(gpkg_path + "|layername=buffered_water_evidence", "evidence", "ogr")
            self.assertTrue(evidence.isValid())
            self.assertEqual(evidence.attributeAlias(evidence.fields().indexFromName("source_refs")),
                             tr("en", "water_source_refs"))
            self.assertEqual(evidence.featureCount(), 0)
            coverage = QgsVectorLayer(gpkg_path + "|layername=source_coverage", "coverage", "ogr")
            derived, = [row for row in coverage.getFeatures()
                        if row["service_id"] == "derived_riparian_buffer_evidence"]
            self.assertEqual(derived["status"], "AVAILABLE")

        with self.scenario([]) as (fixture, layers, aoi):
            fixture.feature_failures.add(line_id)
            with self.assertRaises(QgsProcessingException):
                self.run_algorithm(layers, aoi, "en", "failed-water")
            self.assertFalse(any(Path(self.temp.name).glob("failed-water.*")))

    def test_riparian_classification_and_combined_evidence_publish_as_one_pair(self):
        line_id = "syke_rantaviiva_line_river"
        lake_id = "syke_rantaviiva_lake"
        with self.scenario([]) as (fixture, layers, aoi):
            fixture.records[line_id] = [{
                "attributes": {"objectid": "line-1", "muutospvm": "2026-10-01"},
                "coordinates": "350025,6900050 350075,6900050",
            }]
            fixture.records[lake_id] = [{
                "attributes": {"objectid": "lake-1", "muutospvm": "2026-10-02"},
                "coordinates": coordinates(350060, 6900000, 20, 100),
            }]
            result = self.run_algorithm(layers, aoi, "en", "riparian-pair")
            gpkg_path = result["RESULT"].split("|", 1)[0]
            classified = QgsVectorLayer(gpkg_path + "|layername=classified_forest_polygons", "classified", "ogr")
            self.assertTrue(classified.isValid())
            pieces = list(classified.getFeatures())
            self.assertGreater(len(pieces), 1)
            self.assertAlmostEqual(sum(feature.geometry().area() for feature in pieces), 10000, delta=0.01)
            riparian = [feature for feature in pieces if feature["check_riparian_buffer"] == "MATCH"]
            self.assertTrue(riparian)
            self.assertTrue(all(feature["class_all_out"] == "ECONOMIC" for feature in pieces))
            self.assertTrue(all(feature["class_balance"] == "SENSITIVE" for feature in riparian))
            self.assertTrue(all(feature["class_balance"] == "ECONOMIC" for feature in pieces if feature not in riparian))
            for feature in riparian:
                rules = json.loads(feature["tier_rule_ids"])
                self.assertIn("riparian_buffer", rules["balance"]["criteria"])
                self.assertEqual(rules["balance"]["source_ids"], [
                    lake_id + ":lake-1", line_id + ":line-1",
                ])

            evidence = QgsVectorLayer(gpkg_path + "|layername=buffered_water_evidence", "evidence", "ogr")
            self.assertTrue(evidence.isValid())
            evidence_row, = list(evidence.getFeatures())
            expected_water = QgsGeometry.unaryUnion([
                QgsGeometry.fromWkt("LINESTRING (350025 6900050,350075 6900050)").buffer(30, 8),
                QgsGeometry.fromWkt("POLYGON ((350060 6900000,350080 6900000,350080 6900100,350060 6900100,350060 6900000))").buffer(30, 8),
            ]).intersection(next(aoi.getFeatures()).geometry())
            self.assertLess(evidence_row.geometry().symDifference(expected_water).area(), 0.1)
            self.assertEqual(json.loads(evidence_row["source_refs"]), [lake_id + ":lake-1", line_id + ":line-1"])
            dates = json.loads(evidence_row["source_update_dates"])
            self.assertEqual({item["muutospvm"] for item in dates}, {"2026-10-01", "2026-10-02"})
            self.assertEqual(evidence_row["source_retrieved_feature_count"], 2)
            self.assertEqual(evidence_row["buffers_generated_count"], 2)
            self.assertEqual(evidence_row["aoi_contributing_buffer_feature_count"], 2)

            coverage = QgsVectorLayer(gpkg_path + "|layername=source_coverage", "coverage", "ogr")
            derived, = [row for row in coverage.getFeatures()
                        if row["service_id"] == "derived_riparian_buffer_evidence"]
            self.assertEqual(derived["status"], "AVAILABLE")
            self.assertEqual(json.loads(derived["source_refs"]), [lake_id + ":lake-1", line_id + ":line-1"])
            metadata = QgsVectorLayer(gpkg_path + "|layername=run_metadata", "metadata", "ogr")
            run, = list(metadata.getFeatures())
            buffer_metadata = json.loads(run["water_buffer_evidence"])
            self.assertEqual(buffer_metadata["combined_output_feature_count"], 1)
            retrieval = buffer_metadata["source_retrieval"][line_id]
            self.assertEqual(retrieval["source_crs"], "EPSG:3067")
            self.assertTrue(retrieval["spatial_filter"])
            self.assertEqual(retrieval["request_bbox_crs"], "EPSG:3067")
            self.assertEqual(retrieval["request_bbox"], {
                "xmin": 349969.0, "ymin": 6899969.0, "xmax": 350131.0, "ymax": 6900131.0,
            })
            self.assertIn("objectid", retrieval["provider_fields"])
            self.assertIn("muutospvm", retrieval["provider_fields"])

            with sqlite3.connect(gpkg_path) as database:
                tables = {row[0] for row in database.execute(
                    "SELECT table_name FROM gpkg_contents WHERE data_type='features'")}
            self.assertIn("buffered_water_evidence", tables)
            self.assertTrue(tables.isdisjoint({line_id, "syke_rantaviiva_polygon_river", lake_id}))

            sheets = workbook_rows(result["EXCEL"])
            self.assertEqual(len(sheets), 4)
            summary = sheets[tr("en", "sheet_summary")]
            balance_sensitive = next(row for row in summary[1:] if row[:2] == [
                tr("en", "tier_balance"), tr("en", "class_sensitive")])
            expected_balance_area = sum(feature.geometry().area() for feature in riparian) / 10000
            self.assertAlmostEqual(balance_sensitive[2], round(expected_balance_area, 2), delta=0.01)
            self.assertIn(tr("en", "note_water_buffer"), [row[0] for row in sheets[tr("en", "sheet_notes")]])

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
                self.assertTrue(request_has_bbox(grid_requests[0]))

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
                self.assertTrue(all(request_has_bbox(request) for request in fixture.requests
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
            self.assertTrue(all(request_has_bbox(query) for query in fixture.requests
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

    def test_duplicate_grid_records_deduplicate_and_grid_conflicts_or_overlaps_publish_nothing(self):
        schemas = fixture_sources()
        first = source_record(schemas["forest_centre_gridcell"])
        with self.scenario([first, first]) as (_, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "identical")
            gpkg = result["RESULT"].split("|", 1)[0]
            snapshot = QgsVectorLayer(gpkg + "|layername=forest_centre_gridcell", "grid", "ogr")
            self.assertEqual(snapshot.featureCount(), 1)
        variants = [([first, source_record({**schemas["forest_centre_gridcell"], "VOLUME": 999})], None, ["cell-1"]),
                    ([first, source_record({**schemas["forest_centre_gridcell"], "GRIDCELLID": "cell-2"}, x=350050)], None, ["cell-1", "cell-2"])]
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
