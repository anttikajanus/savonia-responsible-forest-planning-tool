"""Negligible result polygons are excluded before sampling and publication."""

import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsGeometry, QgsProcessingException, QgsVectorLayer

from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.workflow_steps.spatial_classification import classify_source_features
from savonia_responsible_forest_planning_tool.i18n import tr
from test_classification_geometry import rectangle, record
from test_grid_publication import workbook_rows
from workflow_fixture import WorkflowFixtureMixin, fixture_sources, source_record


def classify(geometries, language, evidence=(), feedback=None, sampler=None):
    sources = {source: [] for source in SERVICE_DEFINITIONS}
    sources["forest_centre_stand"] = [
        record("forest_centre_stand", identifier, geometry)
        for identifier, geometry in geometries
    ]
    for item in evidence:
        sources[item["service_id"]].append(item)
    retrieved = {"source_features": sources, "protected_areas_status": "AVAILABLE",
                 "coverage": [{"service_id": source, "status": "AVAILABLE"}
                              for source in SERVICE_DEFINITIONS]}
    if sampler is not None:
        retrieved["grid_sampler"] = sampler
    return classify_source_features({"language": language, "sawlog_price_eur_m3": 75.25,
                                    "source_display_names": {s: s for s in sources}},
                                   retrieved, feedback)


class ResultFragmentTests(unittest.TestCase):
    def test_tiny_whole_polygon_is_excluded_before_sampling_in_both_languages(self):
        for language in ("en", "fi"):
            with self.subTest(language=language):
                sampler = Mock()
                sampler.sample.return_value = []
                feedback = Mock()
                feedback.isCanceled.return_value = False
                result = classify([("tiny", rectangle(0, 0, 0.02, 0.1)),
                                   ("small-real", rectangle(10, 0, 0.5, 1))], language,
                                  feedback=feedback, sampler=sampler)
                self.assertEqual([r["source_stand_id"] for r in result["result_rows"]], ["small-real"])
                self.assertEqual(sampler.sample.call_count, 1)
                self.assertAlmostEqual(result["result_rows"][0]["area_ha"], 0.00005)
                summary = result["result_geometry_filter"]
                self.assertEqual(summary["maximum_excluded_area_m2"], 0.01)
                self.assertEqual(summary["excluded_piece_count"], 1)
                self.assertEqual(summary["excluded_stand_count"], 1)
                self.assertAlmostEqual(summary["excluded_area_m2"], 0.002)
                feedback.pushInfo.assert_any_call(tr(language, "progress_result_fragments",
                                                    count=1, area="0,002000" if language == "fi" else "0.002000"))

    def test_threshold_is_inclusive_and_above_threshold_is_retained(self):
        # Origin coordinates make the exact boundary independent of national-grid rounding.
        at_threshold = QgsGeometry.fromWkt("POLYGON ((0 0,1 0,1 0.02,0 0))")
        above_threshold = QgsGeometry.fromWkt("POLYGON ((2 0,3 0,3 0.020002,2 0))")
        result = classify([("boundary", at_threshold), ("above", above_threshold)], "en")
        self.assertEqual([r["source_stand_id"] for r in result["result_rows"]], ["above"])

    def test_long_thin_fragment_from_reported_export_is_excluded(self):
        geometry = QgsGeometry.fromWkt(
            "MULTIPOLYGON (((510380.433 7074749.965,510395.293 7074753.3882,"
            "510395.29300921387 7074753.388176374,510380.433 7074749.965)))"
        )
        result = classify([("30728888", geometry), ("real", rectangle(0, 0, 10, 10))], "en")
        self.assertEqual([r["source_stand_id"] for r in result["result_rows"]], ["real"])
        self.assertEqual(result["result_geometry_filter"]["excluded_piece_count"], 1)

    def test_multipart_component_is_filtered_without_criteria(self):
        geometry = QgsGeometry.collectGeometry([rectangle(0, 0, 10, 10), rectangle(20, 0, 0.02, 0.1)])
        result = classify([("multipart", geometry)], "en")
        row, = result["result_rows"]
        self.assertAlmostEqual(row["geometry"].area(), 100)
        self.assertEqual(result["result_geometry_filter"]["excluded_piece_count"], 1)
        self.assertAlmostEqual(geometry.area(), 100.002)

    def test_tiny_remainder_from_criterion_split_is_filtered(self):
        protected = record("syke_protected_areas_state_owned", "protected",
                           rectangle(0, 0, 99.99998, 100),
                           {"olotila": "Voimassa", "tyyppilyhenne": "VSA"})
        result = classify([("stand", rectangle(0, 0, 100, 100))], "en", [protected])
        row, = result["result_rows"]
        self.assertEqual(row["classes"]["all_out"], "SENSITIVE")
        self.assertAlmostEqual(row["geometry"].area(), 9999.998, places=6)
        self.assertEqual(result["result_geometry_filter"]["excluded_piece_count"], 1)

    def test_all_excluded_stops_with_no_stands_error(self):
        for language in ("en", "fi"):
            with self.subTest(language=language), self.assertRaises(QgsProcessingException) as error:
                classify([("tiny", rectangle(0, 0, 0.02, 0.1))], language)
            self.assertIn(tr(language, "error_no_stands"), str(error.exception))


class ResultFragmentWorkflowTests(WorkflowFixtureMixin, unittest.TestCase):
    def test_processing_publishes_only_retained_results_and_filter_metadata(self):
        fields = fixture_sources()["forest_centre_stand"]
        stands = [source_record(fields, width=10, height=10),
                  source_record({**fields, "standid": "tiny"}, x=350020, width=0.02, height=0.1)]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([], stands=stands) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "fragments-" + language)
                output = QgsVectorLayer(result["RESULT"], "result", "ogr")
                self.assertEqual(output.featureCount(), 1)
                path = result["RESULT"].split("|")[0]
                metadata = QgsVectorLayer(path + "|layername=run_metadata", "metadata", "ogr")
                row, = list(metadata.getFeatures())
                self.assertEqual(int(row["result_feature_count"]), 1)
                self.assertEqual(int(row["skipped_stand_count"]), 1)
                summary = json.loads(row["result_geometry_filter"])
                self.assertEqual(summary["excluded_piece_count"], 1)
                self.assertAlmostEqual(summary["excluded_area_m2"], 0.002)
                snapshot = QgsVectorLayer(path + "|layername=forest_centre_stand", "stands", "ogr")
                self.assertEqual(snapshot.featureCount(), 2)
                sheets = workbook_rows(result["EXCEL"])
                rows = sheets[tr(language, "sheet_summary")]
                count_column = rows[0].index(tr(language, "column_features"))
                summary_rows = [r for r in rows[1:] if len(r) == len(rows[0])]
                self.assertEqual(len(summary_rows), 18)
                self.assertEqual(sum(r[count_column] for r in summary_rows), 6)
                self.assertTrue(all(r[count_column] in (0, 1) for r in summary_rows))

    def test_processing_all_excluded_leaves_no_output_files(self):
        fields = fixture_sources()["forest_centre_stand"]
        stands = [source_record(fields, width=0.02, height=0.1)]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([], stands=stands) as (_, layers, aoi):
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, "all-fragments-" + language)
                self.assertIn(tr(language, "error_no_stands"), str(error.exception))
                self.assertEqual(list(Path(self.temp.name).glob("*.gpkg")), [])
                self.assertEqual(list(Path(self.temp.name).glob("*.xlsx")), [])


if __name__ == "__main__":
    unittest.main()
