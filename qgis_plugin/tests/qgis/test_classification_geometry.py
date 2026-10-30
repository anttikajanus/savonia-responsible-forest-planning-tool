"""CL-01/02/03 geometry, promotion and piece-local provenance contracts."""

import unittest


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsApplication, QgsGeometry


from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.workflow_steps.spatial_classification import classify_source_features


def rectangle(x, y, width, height):
    """Create projected local fixtures near Finnish national grid coordinates."""
    x, y = x + 350000, y + 6900000
    return QgsGeometry.fromWkt("POLYGON (({0} {1},{2} {1},{2} {3},{0} {3},{0} {1}))".format(
        x, y, x + width, y + height))


def record(source, identifier, geometry, values=None):
    return {"service_id": source, "source_id": identifier, "geometry": geometry,
            "values": values or {}, "attributes": dict(values or {})}


def classify(stands, evidence, language):
    source_features = {source: [] for source in SERVICE_DEFINITIONS}
    source_features["forest_centre_stand"] = stands
    for item in evidence:
        source_features[item["service_id"]].append(item)
    return classify_source_features({"sawlog_price_eur_m3": 75.25, "language": language, "source_display_names": {
        source: source for source in SERVICE_DEFINITIONS}}, {
            "source_features": source_features, "protected_areas_status": "AVAILABLE",
            "coverage": [{"service_id": source, "status": "AVAILABLE"} for source in SERVICE_DEFINITIONS],
        })["result_rows"]


class ClassificationGeometryTests(unittest.TestCase):
    def test_protected_strip_splits_only_matching_pieces_and_conserves_area(self):
        geometry = rectangle(0, 0, 100, 100)
        stand = record("forest_centre_stand", "stand-1", geometry, {"volume": 100, "meanage": 40})
        strip = record("syke_protected_areas_state_owned", "strip", rectangle(0, 0, 25, 100),
                       {"olotila": "Voimassa", "tyyppilyhenne": "VSA"})
        for language in ("en", "fi"):
            with self.subTest(language=language):
                rows = classify([stand], [strip], language)
                self.assertEqual(len(rows), 2)
                union = QgsGeometry.unaryUnion([row["geometry"] for row in rows])
                self.assertLess(union.symDifference(geometry).area(), 1e-6)
                self.assertAlmostEqual(sum(row["area_ha"] for row in rows), 1)
                for tier in ("all_out", "bau", "light", "balance", "protection"):
                    self.assertAlmostEqual(sum(row["area_ha"] for row in rows
                                               if row["classes"][tier] == "SENSITIVE"), 0.25)
                self.assertTrue(all(row["classes"]["superprotection"] == "SENSITIVE" for row in rows))

    def test_age_check_is_inherited_by_split_pieces_only_in_protection_tiers(self):
        stand = record("forest_centre_stand", "old-stand", rectangle(0, 0, 100, 100), {"MEANAGE": 80.01})
        protected = record("syke_protected_areas_state_owned", "protected-strip", rectangle(0, 0, 25, 100),
                           {"olotila": "Voimassa", "tyyppilyhenne": "VSA"})
        for language in ("en", "fi"):
            with self.subTest(language=language):
                rows = classify([stand], [protected], language)
                self.assertEqual(len(rows), 2)
                self.assertAlmostEqual(sum(row["area_ha"] for row in rows), 1)
                for row in rows:
                    self.assertEqual(row["check_potential_protected_age"], "MATCH")
                    self.assertEqual(row["source_ids"]["potential_protected_age"], ["old-stand"])
                    for tier in ("protection", "superprotection"):
                        self.assertEqual(row["classes"][tier], "SENSITIVE")
                        self.assertIn("potential_protected_age", row["rules"][tier]["criteria"])
                        self.assertIn("old-stand", row["rules"][tier]["source_ids"])
                outside, = [row for row in rows if row["check_protected"] == "NO_MATCH"]
                self.assertEqual(outside["rules"]["protection"]["source_ids"], ["old-stand"])
                self.assertEqual(outside["classes"]["balance"], "ECONOMIC")

    def test_criterion_threshold_excludes_small_overlaps_edges_and_points(self):
        stand = record("forest_centre_stand", "stand", rectangle(0, 0, 10, 10))
        cases = ((rectangle(0, 0, 0.5, 1), False), (rectangle(0, 0, 1, 1), False),
                 (rectangle(0, 0, 1.5, 1), True), (rectangle(10, 0, 1, 10), False),
                 (rectangle(10, 10, 1, 1), False))
        for language in ("en", "fi"):
            for source, values in (("syke_protected_areas_state_owned",
                                    {"olotila": "Voimassa", "tyyppilyhenne": "VSA"}),
                                   ("forest_centre_habitat", {"habitattype": "1"})):
                for geometry, hit in cases:
                    with self.subTest(language=language, source=source, area=geometry.area(), hit=hit):
                        rows = classify([stand], [record(source, "criterion", geometry, values)], language)
                        sensitive = sum(row["geometry"].area() for row in rows
                                        if row["classes"]["all_out"] == "SENSITIVE")
                        expected = (100 if source == "forest_centre_habitat" else 1.5) if hit else 0
                        self.assertAlmostEqual(sensitive, expected)
                        self.assertAlmostEqual(sum(row["geometry"].area() for row in rows), 100)
                        self.assertEqual(stand["geometry"].area(), 100)

    def test_section10_promotes_all_parent_pieces_but_not_neighbor(self):
        stands = [record("forest_centre_stand", "parent", rectangle(0, 0, 100, 100)),
                  record("forest_centre_stand", "neighbor", rectangle(100, 0, 100, 100))]
        habitat = record("forest_centre_habitat", "habitat", rectangle(0, 0, 25, 100), {"habitattype": "5"})
        split = record("syke_groundwater_areas", "groundwater", rectangle(50, 0, 25, 100))
        for language in ("en", "fi"):
            with self.subTest(language=language):
                rows = classify(stands, [habitat, split], language)
                parent = [row for row in rows if row["source_stand_id"] == "parent"]
                self.assertGreater(len(parent), 1)
                self.assertAlmostEqual(sum(row["area_ha"] for row in parent), 1)
                for row in parent:
                    self.assertTrue(row["section10_stand_promoted"])
                    self.assertEqual(row["check_section10"], "MATCH")
                    self.assertEqual(set(row["classes"].values()), {"SENSITIVE"})
                    self.assertEqual(row["source_ids"]["section10"], ["habitat"])
                    self.assertIn("section10", row["rules"]["all_out"]["criteria"])
                neighbor, = [row for row in rows if row["source_stand_id"] == "neighbor"]
                self.assertFalse(neighbor["section10_stand_promoted"])
                self.assertEqual(neighbor["check_section10"], "NO_MATCH")
                self.assertEqual(neighbor["classes"]["all_out"], "ECONOMIC")

    def test_overlapping_protected_records_keep_piece_local_ids_in_either_order(self):
        stand = record("forest_centre_stand", "stand", rectangle(0, 0, 100, 100))
        values = {"olotila": "Voimassa", "tyyppilyhenne": "VSA"}
        left = record("syke_protected_areas_state_owned", "left", rectangle(0, 0, 60, 100), values)
        right = record("syke_protected_areas_state_owned", "right", rectangle(40, 0, 60, 100), values)
        for language in ("en", "fi"):
            for evidence in ([left, right], [right, left]):
                with self.subTest(language=language, first=evidence[0]["source_id"]):
                    rows = classify([stand], evidence, language)
                    self.assertEqual(len(rows), 3)
                    for row in rows:
                        x = row["geometry"].centroid().asPoint().x() - 350000
                        expected = ["left"] if x < 40 else ["right"] if x > 60 else ["left", "right"]
                        self.assertEqual(row["source_ids"]["protected"], expected)
                        self.assertEqual(row["rules"]["all_out"]["source_ids"], expected)


if __name__ == "__main__":
    unittest.main()
