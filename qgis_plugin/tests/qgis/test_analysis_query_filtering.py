"""Real WFS requests must reduce candidates without changing clipped evidence."""

import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsCoordinateTransformContext, QgsDataSourceUri, QgsGeometry,
                       QgsPointXY, QgsProcessingException, QgsProcessingFeedback, QgsVectorLayer)

from savonia_responsible_forest_planning_tool.adapters.sources import qgis_wfs_uri
from savonia_responsible_forest_planning_tool.analysis.workflow_steps import source_loading
from test_grid_sampling import retrieval_inputs, rectangle
from wfs_fixture import LocalWfs, request_has_bbox
from workflow_fixture import fixture_sources, source_record


GRID = "forest_centre_gridcell"


def spatial_records(record, query):
    """Interpret the spatial predicates emitted by QGIS, before fixture paging."""
    polygon = QgsGeometry.fromWkt(
        "POLYGON ((" + ",".join(pair.replace(",", " ") for pair in record["coordinates"].split()) + "))")
    if "bbox" in query:
        bounds = [float(value) for value in query["bbox"].split(",")[:4]]
        if not polygon.intersects(rectangle(bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1])):
            return False
    if "filter" in query:
        root = ET.fromstring(query["filter"])
        for predicate in root.findall(".//{*}Intersects"):
            shape = predicate.find("{*}Polygon")
            if shape is None:
                shape = predicate.find("{*}MultiSurface")
            if shape is None:
                shape = predicate.find("{*}MultiPolygon")
            assert shape is not None, query
            polygons = [shape] if shape.tag.endswith("}Polygon") else shape.findall(".//{*}Polygon")
            parts = []
            for part in polygons:
                rings = []
                for ring in part.findall(".//{*}LinearRing"):
                    values = [float(x) for x in ring.find("{*}posList").text.split()]
                    rings.append([QgsPointXY(x, y) for x, y in zip(values[::2], values[1::2])])
                parts.append(rings)
            geometry = QgsGeometry.fromMultiPolygonXY(parts)
            if not polygon.intersects(geometry):
                return False
        for bounds in root.findall(".//{*}BBOX"):
            lower = [float(x) for x in bounds.find(".//{*}lowerCorner").text.split()]
            upper = [float(x) for x in bounds.find(".//{*}upperCorner").text.split()]
            if not polygon.intersects(rectangle(lower[0], lower[1], upper[0] - lower[0], upper[1] - lower[1])):
                return False
        for predicate in root.findall(".//{*}PropertyIsGreaterThan"):
            field = predicate.find("{*}ValueReference").text.split(":")[-1]
            if float(record["attributes"][field]) <= float(predicate.find("{*}Literal").text):
                return False
    return True


class AnalysisQueryFilteringTest(unittest.TestCase):
    def layer(self, fixture, crs="EPSG:3067", subset=None):
        uri = QgsDataSourceUri(qgis_wfs_uri({
            "endpoint": fixture.endpoint, "feature_type": "fixture:" + GRID, "source_crs": crs,
        }))
        if subset:
            uri.setParam("filter", subset)
        layer = QgsVectorLayer(uri.uri(), "query grid", "WFS")
        self.assertTrue(layer.isValid())
        return layer

    def read(self, layer, aoi, language="en", **options):
        inputs = retrieval_inputs(layer, aoi)
        inputs.update(language=language, **options)
        return source_loading.retrieve_sources(inputs, QgsProcessingFeedback())

    def test_holes_disjoint_parts_and_boundary_cells_reduce_transfer_with_identical_evidence(self):
        fields = fixture_sources()[GRID]
        records = [source_record({**fields, "GRIDCELLID": str(index)}, x=x, y=y, width=10, height=10)
                   for index, (x, y) in enumerate(((350000, 6900000), (350025, 6900025),
                                                  (350070, 6900000), (350115, 6900000),
                                                  (350009, 6900045)))]
        aoi = QgsGeometry.fromWkt(
            "MULTIPOLYGON (((350000 6900000,350050 6900000,350050 6900050,350000 6900050,350000 6900000),"
            "(350020 6900020,350040 6900020,350040 6900040,350020 6900040,350020 6900020)),"
            "((350100 6900000,350120 6900000,350120 6900020,350100 6900020,350100 6900000)))")
        self.assertTrue(aoi.isGeosValid())
        for language in ("en", "fi"):
            with self.subTest(language=language), LocalWfs({GRID: fields}, records={GRID: records},
                    version="2.0.0", page_size=2, record_filter=spatial_records) as fixture:
                bounded = self.layer(fixture)
                with patch.object(source_loading, "MAX_ENCODED_POLYGON_FILTER_BYTES", 0):
                    baseline = self.read(bounded, aoi, language)
                baseline_count = sum(count for _, count in fixture.returned_counts)
                fixture.returned_counts.clear()
                fixture.requests.clear()
                layer = self.layer(fixture)
                result = self.read(layer, aoi, language)
                queries = [q for q in fixture.requests if q.get("request", "").lower() == "getfeature"]
                self.assertLess(sum(count for _, count in fixture.returned_counts), baseline_count)
                self.assertEqual([int(q.get("startindex", 0)) for q in queries], [0, 2])
                self.assertTrue(all(request_has_bbox(q) and "Intersects" in q["filter"] for q in queries))
                actual = {r["source_id"]: r for r in result["source_features"][GRID]}
                expected = {r["source_id"]: r for r in baseline["source_features"][GRID]}
                self.assertEqual(set(actual), {"0", "3", "4"})
                self.assertEqual(set(actual), set(expected))
                for identifier, record in actual.items():
                    self.assertTrue(record["geometry"].isGeosEqual(expected[identifier]["geometry"]))
                    self.assertEqual(record["attributes"], expected[identifier]["attributes"])
                self.assertEqual(result["coverage"][0]["spatial_filter"], "aoi_intersects")
                self.assertEqual(baseline["coverage"][0]["spatial_filter"], "bbox_filter_size")

    def test_existing_subset_repeated_and_changed_aoi_do_not_leak_cached_features(self):
        fields = fixture_sources()[GRID]
        records = [source_record({**fields, "GRIDCELLID": str(index), "VOLUME": volume},
                                 x=350000 + index * 20, width=10, height=10)
                   for index, volume in enumerate((100, 0, 300))]
        with LocalWfs({GRID: fields}, records={GRID: records}, version="2.0.0", record_filter=spatial_records) as fixture:
            layer = self.layer(fixture, subset='"VOLUME" > 0')
            original_uri = layer.source()
            for offset, expected in ((0, {"0"}), (0, {"0"}), (20, set()), (40, {"2"}), (0, {"0"})):
                with self.subTest(offset=offset):
                    result = self.read(layer, rectangle(350000 + offset, 6900000, 10, 10))
                    self.assertEqual({r["source_id"] for r in result["source_features"][GRID]}, expected)
            queries = [q for q in fixture.requests if q.get("request", "").lower() == "getfeature"]
            self.assertTrue(all("PropertyIsGreaterThan" in q["filter"] and "Intersects" in q["filter"] for q in queries))
            self.assertEqual(layer.source(), original_uri)

    def test_query_geometry_is_transformed_to_source_crs(self):
        fields = fixture_sources()[GRID]
        with LocalWfs({GRID: fields}, records={GRID: []}, version="2.0.0") as fixture:
            layer = self.layer(fixture, crs="EPSG:4326")
            aoi = rectangle(350000, 6900000, 100, 100)
            result = self.read(layer, aoi)
            query = next(q for q in fixture.requests if q.get("request", "").lower() == "getfeature")
            shape = ET.fromstring(query["filter"]).find(".//{*}Polygon")
            self.assertIn("4326", shape.get("srsName"))
            positions = [float(x) for x in shape.find(".//{*}posList").text.split()]
            expected = QgsGeometry(aoi)
            expected.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:3067"),
                                                     layer.crs(), QgsCoordinateTransformContext()))
            first = next(expected.vertices())
            # WFS 2 honours EPSG:4326's latitude/longitude axis order.
            self.assertAlmostEqual(positions[0], first.y())
            self.assertAlmostEqual(positions[1], first.x())
            self.assertEqual(result["coverage"][0]["status"], "AVAILABLE")

    def test_large_polygon_uses_bounded_fallback_and_captured_selection_needs_no_read(self):
        fields = fixture_sources()[GRID]
        with LocalWfs({GRID: fields}, version="2.0.0", record_filter=spatial_records) as fixture:
            layer = self.layer(fixture)
            aoi = rectangle(350000, 6900000, 100, 100).densifyByCount(100)
            result = self.read(layer, aoi)
            self.assertEqual(result["coverage"][0]["spatial_filter"], "bbox_filter_size")
            self.assertEqual(len(result["source_features"][GRID]), 1)
            queries = [q for q in fixture.requests if q.get("request", "").lower() == "getfeature"]
            self.assertTrue(all("bbox" in q and "filter" not in q for q in queries))
            # Finish the provider download before measuring snapshot-only reads.
            original, = list(layer.getFeatures())
            fixture.requests.clear()
            selected = self.read(layer, aoi, selected_source_feature_snapshots={GRID: (
                (original.id(), bytes(original.geometry().asWkb()), tuple(original.attributes())),
            )})
            self.assertEqual(selected["coverage"][0]["spatial_filter"], "selected_snapshot")
            self.assertEqual(len(selected["source_features"][GRID]), 1)
            self.assertFalse(any(q.get("request", "").lower() == "getfeature" for q in fixture.requests))
            selected = self.read(layer, aoi, selected_source_feature_ids={GRID: (original.id(),)})
            self.assertEqual(selected["coverage"][0]["spatial_filter"], "selected_fids")
            self.assertEqual(len(selected["source_features"][GRID]), 1)

    def test_returned_invalid_polygon_is_repaired_and_request_errors_remain_fatal(self):
        fields = fixture_sources()[GRID]
        bowtie = {"attributes": fields, "coordinates":
                  "350000,6900000 350010,6900010 350000,6900010 350010,6900000 350000,6900000"}
        with LocalWfs({GRID: fields}, records={GRID: [bowtie]}, version="2.0.0", record_filter=spatial_records) as fixture:
            result = self.read(self.layer(fixture), rectangle(349999, 6899999, 20, 20))
            self.assertEqual(result["coverage"][0]["geometry_repaired_feature_count"], 1)
            self.assertEqual(len(result["source_features"][GRID]), 1)
            fixture.service_exceptions.add(GRID)
            for language in ("en", "fi"):
                with self.subTest(language=language), self.assertRaises(QgsProcessingException):
                    self.read(self.layer(fixture), rectangle(349999, 6899999, 20, 20), language)


if __name__ == "__main__":
    unittest.main()
