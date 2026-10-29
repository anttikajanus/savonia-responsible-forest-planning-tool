"""Local PyQGIS regressions for exact grid sampling and source partitions."""

from pathlib import Path
import unittest


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsCoordinateTransformContext, QgsFeature, QgsGeometry,
                       QgsProcessingException, QgsProcessingFeedback, QgsVectorLayer)


from savonia_responsible_forest_planning_tool.analysis.grid_indicators import calculate_grid_indicators
from savonia_responsible_forest_planning_tool.analysis.workflow_steps.grid_sampling import GridCellSampler
from savonia_responsible_forest_planning_tool.analysis.workflow_steps.source_loading import retrieve_sources
from savonia_responsible_forest_planning_tool.analysis.workflow_steps.spatial_classification import classify_source_features
from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS


def rectangle(x, y, width, height):
    return QgsGeometry.fromWkt("POLYGON (({0} {1},{2} {1},{2} {3},{0} {3},{0} {1}))".format(
        x, y, x + width, y + height))


def record(identifier, geometry, volume=100):
    values = {"gridcellid": identifier, "volume": volume, "volumepine": volume,
              "volumespruce": volume, "volumedeciduous": volume,
              "age": 10, "soiltype": 60, "drainagestate": 6}
    return {"source_id": identifier, "service_id": "forest_centre_gridcell",
            "geometry": geometry, "values": values, "attributes": values.copy()}


def grid_layer(records, crs="EPSG:3067"):
    layer = QgsVectorLayer("MultiPolygon?crs=" + crs + "&field=GRIDCELLID:string"
                           "&field=VOLUME:double&field=VOLUMEPINE:double&field=VOLUMESPRUCE:double"
                           "&field=VOLUMEDECIDUOUS:double&field=AGE:double&field=SOILTYPE:integer"
                           "&field=DRAINAGESTATE:integer&field=TREEDATADATE:string&field=UPDATETIME:string",
                           "local grid", "memory")
    features = []
    for item in records:
        feature = QgsFeature(layer.fields())
        geometry = QgsGeometry(item["geometry"])
        geometry.convertToMultiType()
        feature.setGeometry(geometry)
        attrs = item["attributes"]
        feature.setAttributes([attrs.get(field.name().lower()) for field in layer.fields()])
        features.append(feature)
    assert layer.dataProvider().addFeatures(features)[0]
    layer.updateExtents()
    return layer


def retrieval_inputs(layer, aoi):
    source = "forest_centre_gridcell"
    return {"sawlog_price_eur_m3": 75.25, "run_id": "grid-test", "language": "en", "service_ids": (source,),
            "source_display_names": {source: "Grid"}, "layers": {source: layer}, "aoi": aoi,
            "transform_context": QgsCoordinateTransformContext(), "source_metadata": {source: {
                "endpoint": "local-fixture", "feature_type": "fixture:gridcell", "properties": None,
                "query_time": "fixture", "provider_fields": [field.name() for field in layer.fields()],
                "field_map": {field.name().lower(): field.name() for field in layer.fields()},
            }}}


class GridSamplingTest(unittest.TestCase):
    def test_projected_irregular_boundaries_preserve_complete_metric_coverage(self):
        # This triangle's disjoint grid intersections used to exceed its area
        # by 3.6e-8 m2 solely from overlay rounding at Finnish northings.
        triangle = QgsGeometry.fromWkt(
            "POLYGON ((349945.246332713694 6899988.535251180641,"
            "350040.694414364407 6899982.337780965492,"
            "350050.901080778916 6899987.071121039800,"
            "349945.246332713694 6899988.535251180641))"
        )
        cells = [record(str((x, y)), rectangle(x, y, 16, 16))
                 for x in range(349936, 350064, 16)
                 for y in range(6899936, 6900064, 16)]
        irregular = QgsGeometry.fromWkt(
            (Path(__file__).parent / "fixtures/grid-area-closure.wkt").read_text(encoding="utf-8"))
        for preclip, polygon in ((False, triangle), (True, triangle), (False, irregular), (True, irregular)):
            for language in ("en", "fi"):
                with self.subTest(area_m2=polygon.area(), preclip=preclip, language=language):
                    # Retrieval clips in projected coordinates before sampling;
                    # direct sampler callers can also supply full source cells.
                    sampler = (retrieve_sources(retrieval_inputs(grid_layer(cells), polygon))["grid_sampler"]
                               if preclip else GridCellSampler(cells))
                    retrieved = {
                        "source_features": {"forest_centre_stand": [{
                            "source_id": "precision-stand", "geometry": polygon,
                            "attributes": {"volume": 200}, "values": {"volume": 200},
                        }]},
                        "coverage": [{"service_id": source, "status": "AVAILABLE"}
                                     for source in SERVICE_DEFINITIONS],
                        "protected_areas_status": "AVAILABLE", "grid_sampler": sampler,
                    }
                    classified = classify_source_features({"sawlog_price_eur_m3": 75.25,
                        "language": language,
                        "source_display_names": {source: source for source in SERVICE_DEFINITIONS},
                    }, retrieved)
                    row, = classified["result_rows"]
                    self.assertTrue(row["geometry"].isTopologicallyEqual(polygon))
                    self.assertAlmostEqual(row["indicators"]["grid_total_volume_m3_ha"], 100)
                    self.assertEqual(row["indicators"]["share_under_20"], 100)
                    for metric in ("grid_total_volume_m3_ha", "peatland_area_ha", "natural_mire_area_ha"):
                        self.assertEqual(row["indicator_coverage"][metric]["status"], "AVAILABLE")
                        self.assertEqual(row["indicator_coverage"][metric]["unknown_area_ha"], 0)
                    self.assertAlmostEqual(row["indicators"]["peatland_area_ha"], polygon.area() / 10000)

    def test_projected_half_square_metre_gap_remains_unknown(self):
        polygon = rectangle(350000, 6900000, 16, 16)
        # A real 0.5 m2 gap is much larger than coordinate roundoff and must
        # remain unknown, including for the all-or-nothing area indicators.
        sampler = GridCellSampler([record("partial", rectangle(350000.03125, 6900000, 16, 16))])
        result = calculate_grid_indicators(0.0256, sampler.sample(polygon))
        for metric in ("grid_total_volume_m3_ha", "peatland_area_ha", "natural_mire_area_ha"):
            self.assertEqual(result["indicator_coverage"][metric]["status"], "PARTIAL")
            self.assertAlmostEqual(result["indicator_coverage"][metric]["unknown_area_ha"], 0.00005)
        self.assertIsNone(result["indicators"]["peatland_area_ha"])
        self.assertIsNone(result["indicators"]["natural_mire_area_ha"])

    def test_boundary_and_sub_square_metre_intersections_keep_actual_hectares(self):
        sampler = GridCellSampler([
            record("left", rectangle(0, 0, 16, 16), 100),
            record("right", rectangle(16, 0, 16, 16), 300),
        ], "en")
        parts = sampler.sample(rectangle(12, 0, 16, 16))
        result = calculate_grid_indicators(0.0256, parts)
        self.assertAlmostEqual(result["indicators"]["grid_total_volume_m3_ha"], 250)
        small = sampler.sample(rectangle(-0.5, 0, 1, 1))
        self.assertEqual(len(small), 1)
        self.assertAlmostEqual(small[0]["area_ha"], 0.00005)
        self.assertEqual(sampler.sample(rectangle(-1, 0, 1, 1)), [])

    def test_identical_cell_ids_deduplicate_but_versions_and_overlaps_stop(self):
        first = record("cell-1", rectangle(0, 0, 16, 16))
        duplicate = record("cell-1", rectangle(0, 0, 16, 16))
        sampler = GridCellSampler([first, duplicate], "en")
        self.assertEqual(len(sampler.sample(rectangle(0, 0, 16, 16))), 1)
        self.assertEqual(sampler.duplicate_count, 1)
        for language in ("fi", "en"):
            with self.subTest(language=language):
                with self.assertRaises(QgsProcessingException) as conflict:
                    GridCellSampler([first, record("cell-1", rectangle(0, 0, 16, 16), 200)], language)
                self.assertIn("cell-1", str(conflict.exception))
                with self.assertRaises(QgsProcessingException) as overlap:
                    GridCellSampler([first, record("cell-2", rectangle(15.96875, 0, 16, 16))], language)
                self.assertIn("cell-1", str(overlap.exception))
                self.assertIn("cell-2", str(overlap.exception))
        touching = GridCellSampler([first, record("cell-2", rectangle(16, 0, 16, 16))])
        self.assertEqual(len(touching.records), 2)

    def test_retrieval_deduplicates_clipped_snapshot_and_keeps_source_dates(self):
        first = record("cell-1", rectangle(0, 0, 16, 16))
        first["attributes"].update({"treedatadate": "2021-06-01", "updatetime": "2026-10-01"})
        outside = record("outside", rectangle(1000, 1000, 16, 16))
        layer = grid_layer([first, first, outside])
        retrieved = retrieve_sources(retrieval_inputs(layer, rectangle(0, 0, 8, 16)))
        self.assertEqual(len(retrieved["source_features"]["forest_centre_gridcell"]), 1)
        snapshot = retrieved["snapshots"][0][1]
        self.assertEqual(snapshot.featureCount(), 1)
        feature, = list(snapshot.getFeatures())
        self.assertAlmostEqual(feature.geometry().area(), 128)
        self.assertEqual(feature["TREEDATADATE"], "2021-06-01")
        self.assertEqual(feature["UPDATETIME"], "2026-10-01")
        self.assertEqual(retrieved["coverage"][0]["deduplicated_feature_count"], 1)
        self.assertEqual(retrieved["coverage"][0]["inspected_feature_count"], 2)
        self.assertIn("grid_sampler", retrieved)
        conflicting = record("cell-1", rectangle(0, 0, 32, 16))
        conflicting["attributes"].update(first["attributes"])
        with self.assertRaises(QgsProcessingException):
            retrieve_sources(retrieval_inputs(grid_layer([first, conflicting]), rectangle(0, 0, 8, 16)))

    def test_shared_classification_samples_without_splitting_and_retains_stand_overlap(self):
        stands = [{"source_id": "stand-1", "geometry": rectangle(12, 0, 16, 16),
                   "attributes": {"volume": 200}, "values": {"volume": 200}}]
        grid = [record("left", rectangle(0, 0, 16, 16), 100),
                record("right", rectangle(16, 0, 16, 16), 300)]
        inputs = {"sawlog_price_eur_m3": 75.25, "language": "en", "source_display_names": {source: source for source in SERVICE_DEFINITIONS}}
        retrieved = {"source_features": {"forest_centre_stand": stands, "forest_centre_gridcell": grid},
                     "coverage": [{"service_id": source, "status": "AVAILABLE"} for source in SERVICE_DEFINITIONS],
                     "protected_areas_status": "AVAILABLE", "grid_sampler": GridCellSampler(grid)}
        classified = classify_source_features(inputs, retrieved)
        self.assertEqual(len(classified["result_rows"]), 1)
        row = classified["result_rows"][0]
        self.assertAlmostEqual(row["geometry"].area(), 256)
        self.assertAlmostEqual(row["indicators"]["grid_total_volume_m3_ha"], 250)
        self.assertEqual(row["indicators"]["total_volume_m3_ha"], 200)
        self.assertEqual(row["classes"]["all_out"], "ECONOMIC")
        stands.append({"source_id": "stand-2", "geometry": rectangle(27.5, 0, 16, 16),
                       "attributes": {"volume": 300}, "values": {"volume": 300}})
        rows = classify_source_features(inputs, retrieved)["result_rows"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["stand_has_overlap"] for row in rows))
        self.assertAlmostEqual(sum(row["geometry"].area() for row in rows), 512)

    def test_stand_overlaps_above_numerical_tolerance_succeed_in_both_languages(self):
        for language in ("fi", "en"):
            for overlap_m2 in (0, 1e-9, 0.5, 1, 1.01, 128):
                with self.subTest(language=language, overlap_m2=overlap_m2):
                    stands = [{"source_id": identifier, "geometry": geometry,
                               "attributes": {"volume": 200}, "values": {"volume": 200}}
                              for identifier, geometry in (
                                  ("stand-1", rectangle(0, 0, 16, 16)),
                                  ("stand-2", rectangle(16 - overlap_m2 / 16, 0, 16, 16)),
                              )]
                    grid = [record("grid", rectangle(0, 0, 32, 16))]
                    inputs = {"sawlog_price_eur_m3": 75.25, "language": language,
                              "source_display_names": {source: source for source in SERVICE_DEFINITIONS}}
                    retrieved = {
                        "source_features": {"forest_centre_stand": stands, "forest_centre_gridcell": grid},
                        "coverage": [{"service_id": source, "status": "AVAILABLE"}
                                     for source in SERVICE_DEFINITIONS],
                        "protected_areas_status": "AVAILABLE", "grid_sampler": GridCellSampler(grid),
                    }
                    classified = classify_source_features(inputs, retrieved)
                    rows = classified["result_rows"]
                    self.assertEqual(len(rows), 2)
                    self.assertEqual(classified["stand_overlap_summary"]["pair_count"], int(overlap_m2 > 1e-8))
                    for row in rows:
                        self.assertEqual(row["stand_has_overlap"], overlap_m2 > 1e-8)
                        self.assertAlmostEqual(row["geometry"].area(), 256)
                        self.assertAlmostEqual(row["indicators"]["grid_total_volume_m3_ha"], 100)

    def test_transformed_multipart_cells_are_measured_in_epsg3067(self):
        pieces = [rectangle(350000, 6900000, 8, 16), rectangle(350024, 6900000, 8, 16)]
        multipart = QgsGeometry.collectGeometry(pieces)
        projected = QgsGeometry(multipart)
        projected.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:3067"),
                            QgsCoordinateReferenceSystem("EPSG:4326"), QgsCoordinateTransformContext()))
        layer = grid_layer([record("multipart", projected)], "EPSG:4326")
        retrieved = retrieve_sources(retrieval_inputs(layer, rectangle(350004, 6900000, 24, 16)))
        clipped = retrieved["source_features"]["forest_centre_gridcell"][0]["geometry"]
        self.assertTrue(clipped.isMultipart())
        self.assertAlmostEqual(clipped.area(), 128, places=4)
        intersections = retrieved["grid_sampler"].sample(rectangle(350004, 6900000, 24, 16))
        self.assertEqual(len(intersections), 1)
        self.assertAlmostEqual(intersections[0]["area_ha"], 0.0128, places=8)

    def test_repairable_grid_geometry_reports_source_id_and_invalid_geometry_stops(self):
        bowtie = QgsGeometry.fromWkt("POLYGON ((0 0,16 16,0 16,16 0,0 0))")
        retrieved = retrieve_sources(retrieval_inputs(grid_layer([record("repair-me", bowtie)]),
                                                     rectangle(-1, -1, 18, 18)))
        coverage = retrieved["coverage"][0]
        self.assertEqual(coverage["geometry_repaired_feature_count"], 1)
        self.assertIn("repair-me", coverage["geometry_repaired_feature_id_sample"])
        self.assertAlmostEqual(retrieved["source_features"]["forest_centre_gridcell"][0]["geometry"].area(), 128)
        for geometry in (QgsGeometry(), QgsGeometry.fromWkt("LINESTRING (0 0,16 16)"), bowtie):
            with self.subTest(geometry=geometry.asWkt()), self.assertRaises(QgsProcessingException):
                GridCellSampler([record("invalid", geometry)])

    def test_cancellation_stops_sampling_even_when_no_cell_matches(self):
        feedback = QgsProcessingFeedback()
        sampler = GridCellSampler([record("cell", rectangle(0, 0, 16, 16))], feedback=feedback)
        feedback.cancel()
        with self.assertRaises(QgsProcessingException):
            sampler.sample(rectangle(1000, 1000, 16, 16))
        with self.assertRaises(QgsProcessingException):
            GridCellSampler([record("cell", rectangle(0, 0, 16, 16))], feedback=feedback)
        with self.assertRaises(QgsProcessingException):
            retrieve_sources(retrieval_inputs(grid_layer([]), rectangle(0, 0, 16, 16)), feedback)

    def test_invalid_source_crs_stops_before_retrieval(self):
        layer = grid_layer([record("cell", rectangle(0, 0, 16, 16))])
        layer.setCrs(QgsCoordinateReferenceSystem())
        with self.assertRaises(QgsProcessingException) as invalid:
            retrieve_sources(retrieval_inputs(layer, rectangle(0, 0, 16, 16)))
        self.assertIn("forest_centre_gridcell", str(invalid.exception))

    def test_missing_values_retain_coverage_without_indicator_diagnostic_payloads(self):
        grid = [record("cell-" + str(index), rectangle(index, 0, 1, 1)) for index in range(24)]
        for item in grid:
            item["values"]["volume"] = None
        inputs = {"sawlog_price_eur_m3": 75.25, "language": "en", "source_display_names": {source: source for source in SERVICE_DEFINITIONS}}
        retrieved = {"source_features": {"forest_centre_stand": [{
            "source_id": "stand-1", "geometry": rectangle(0, 0, 24, 1),
            "attributes": {"volume": 200}, "values": {"volume": 200}}], "forest_centre_gridcell": grid},
            "coverage": [{"service_id": source, "status": "AVAILABLE"} for source in SERVICE_DEFINITIONS],
            "protected_areas_status": "AVAILABLE", "grid_sampler": GridCellSampler(grid)}
        classified = classify_source_features(inputs, retrieved)
        coverage = next(row for row in classified["coverage"] if row["service_id"] == "forest_centre_gridcell")
        self.assertFalse(any(key.startswith("indicator_diagnostic") for key in coverage))
        row = classified["result_rows"][0]
        self.assertNotIn("indicator_diagnostics", row)
        self.assertNotIn("indicator_status", row)
        self.assertAlmostEqual(row["indicator_coverage"]["grid_total_volume_m3_ha"]["unknown_area_ha"], 0.0024)
        self.assertIsNone(classified["result_rows"][0]["indicators"]["grid_total_volume_m3_ha"])
        self.assertEqual(classified["result_rows"][0]["indicators"]["total_volume_m3_ha"], 200)

    def test_retrieval_progress_stays_monotonic_before_classification_for_all_sources(self):
        class RecordingFeedback(QgsProcessingFeedback):
            def __init__(self):
                super().__init__()
                self.progress_values = []

            def setProgress(self, value):
                self.progress_values.append(value)
                super().setProgress(value)

        layer = grid_layer([])
        inputs = retrieval_inputs(layer, rectangle(0, 0, 16, 16))
        metadata = inputs["source_metadata"]["forest_centre_gridcell"]
        inputs.update({"sawlog_price_eur_m3": 75.25, "service_ids": tuple(SERVICE_DEFINITIONS),
                       "source_display_names": {source: source for source in SERVICE_DEFINITIONS},
                       "layers": {source: grid_layer([]) for source in SERVICE_DEFINITIONS},
                       "source_metadata": {source: dict(metadata) for source in SERVICE_DEFINITIONS}})
        feedback = RecordingFeedback()
        retrieve_sources(inputs, feedback)
        self.assertTrue(all(10 <= value <= 70 for value in feedback.progress_values))
        self.assertEqual(feedback.progress_values, sorted(feedback.progress_values))
        self.assertEqual(feedback.progress_values[-1], 70)


if __name__ == "__main__":
    unittest.main()
