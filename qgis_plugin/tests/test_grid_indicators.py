"""Pure numerical regressions at the agreed indicator calculation seam."""

from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    str(Path(__file__).resolve().parents[1]),
))

from savonia_responsible_forest_planning_tool.analysis.grid_indicators import (
    calculate_grid_indicators, summarize_indicator_rows,
)
from savonia_responsible_forest_planning_tool.analysis.classification import assemble_classified_piece
from savonia_responsible_forest_planning_tool.analysis.domain import weighted_summary


class GridIndicatorsTest(unittest.TestCase):
    def test_boundary_cells_weight_density_by_intersected_hectares(self):
        result = calculate_grid_indicators(0.0256, [
            {"area_ha": 0.0064, "values": {"volume": 100, "volumepine": 100,
             "volumespruce": 100, "volumedeciduous": 100}},
            {"area_ha": 0.0192, "values": {"volume": 300, "volumepine": 300,
             "volumespruce": 300, "volumedeciduous": 300}},
        ])
        for metric in ("grid_total_volume_m3_ha", "pine_volume_m3_ha",
                       "spruce_volume_m3_ha", "deciduous_volume_m3_ha"):
            with self.subTest(metric=metric):
                self.assertAlmostEqual(result["indicators"][metric], 250)
                coverage = result["indicator_coverage"][metric]
                self.assertAlmostEqual(coverage["represented_volume_m3"], 6.4)
                self.assertAlmostEqual(coverage["valid_area_ha"], 0.0256)
                self.assertEqual(coverage["status"], "AVAILABLE")

    def test_age_shares_use_valid_area_and_keep_unrounded_band_statistics(self):
        result = calculate_grid_indicators(2, [
            {"area_ha": 0.25, "values": {"age": 19.9}},
            {"area_ha": 1, "values": {"age": 80.1}},
        ])
        self.assertEqual([result["indicators"][metric] for metric in
                          ("share_under_20", "share_20_80", "share_over_80")], [20, 0, 80])
        coverage = result["indicator_coverage"]["share_under_20"]
        self.assertEqual(coverage["valid_area_ha"], 1.25)
        self.assertEqual(coverage["unknown_area_ha"], 0.75)
        self.assertEqual(coverage["matching_area_ha"], 0.25)
        self.assertEqual(coverage["coverage_percent_exact"], 62.5)
        self.assertEqual(coverage["coverage_percent"], 63)
        self.assertEqual(coverage["status"], "PARTIAL")
        endpoints = calculate_grid_indicators(2, [
            {"area_ha": 1, "values": {"age": 20}},
            {"area_ha": 1, "values": {"age": 80}},
        ])
        self.assertEqual(endpoints["indicators"]["share_20_80"], 100)
        half = calculate_grid_indicators(8, [
            {"area_ha": 5, "values": {"age": 10}},
            {"area_ha": 3, "values": {"age": 30}},
        ])
        self.assertEqual(half["indicators"]["share_under_20"], 63)
        self.assertIsInstance(half["indicators"]["share_under_20"], int)
        small_half = calculate_grid_indicators(0.00016, [
            {"area_ha": 0.0001, "values": {"age": 10}},
            {"area_ha": 0.00006, "values": {"age": 50}},
        ])
        self.assertEqual(small_half["indicators"]["share_under_20"], 63)

    def test_peat_and_mire_sum_fragments_but_partial_totals_stay_unknown(self):
        result = calculate_grid_indicators(0.00645, [
            {"area_ha": 0.0064, "values": {"soiltype": 60, "drainagestate": 6}},
            {"area_ha": 0.00005, "values": {"soiltype": 67, "drainagestate": 6}},
            {"area_ha": 0, "values": {"soiltype": 60, "drainagestate": 6}},
        ])
        for metric in ("peatland_area_ha", "natural_mire_area_ha"):
            self.assertAlmostEqual(result["indicators"][metric], 0.00645)
        partial = calculate_grid_indicators(1, [
            {"area_ha": 0.25, "values": {"soiltype": 61, "drainagestate": 6}},
            {"area_ha": 0.75, "values": {"soiltype": 999, "drainagestate": 1.5}},
        ])
        for metric in ("peatland_area_ha", "natural_mire_area_ha"):
            self.assertIsNone(partial["indicators"][metric])
            self.assertEqual(partial["indicator_coverage"][metric]["status"], "PARTIAL")
            self.assertEqual(partial["indicator_coverage"][metric]["matching_area_ha"], 0.25)
        known_zero = calculate_grid_indicators(1, [
            {"area_ha": 1, "values": {"soiltype": 11, "drainagestate": 7}},
        ])
        self.assertEqual(known_zero["indicators"]["peatland_area_ha"], 0)
        self.assertEqual(known_zero["indicators"]["natural_mire_area_ha"], 0)
        contradiction = calculate_grid_indicators(1, [
            {"source_id": "cell-conflict", "area_ha": 1,
             "values": {"soiltype": 11, "drainagestate": 6}},
        ])
        self.assertEqual(contradiction["indicators"]["peatland_area_ha"], 0)
        self.assertEqual(contradiction["indicators"]["natural_mire_area_ha"], 1)
        self.assertNotIn("diagnostics", contradiction)

    def test_zero_is_valid_but_invalid_and_missing_values_remain_independent(self):
        result = calculate_grid_indicators(1, [
            {"source_id": "zero-cell", "area_ha": 1, "values": {
                "volume": 0, "volumepine": None, "volumespruce": -1,
                "volumedeciduous": float("nan"), "age": True, "soiltype": 0,
                "drainagestate": "6"}},
        ])
        self.assertEqual(result["indicators"]["grid_total_volume_m3_ha"], 0)
        self.assertEqual(result["indicator_coverage"]["grid_total_volume_m3_ha"]["status"], "AVAILABLE")
        for metric in ("pine_volume_m3_ha", "spruce_volume_m3_ha", "deciduous_volume_m3_ha",
                       "share_under_20", "peatland_area_ha", "natural_mire_area_ha"):
            self.assertIsNone(result["indicators"][metric])
            self.assertEqual(result["indicator_coverage"][metric]["status"], "UNKNOWN_FIELD_OR_VALUE")
        self.assertNotIn("diagnostics", result)
        self.assertNotIn("indicator_status", result)
        empty = calculate_grid_indicators(1, [])
        self.assertTrue(all(value is None for value in empty["indicators"].values()))
        for invalid in (True, "2", -1, float("inf"), float("nan")):
            with self.subTest(invalid=invalid):
                unavailable = calculate_grid_indicators(1, [
                    {"area_ha": 1, "values": {"volume": invalid, "age": invalid}},
                ])
                self.assertIsNone(unavailable["indicators"]["grid_total_volume_m3_ha"])
                self.assertIsNone(unavailable["indicators"]["share_under_20"])

    def test_classified_piece_keeps_independent_stand_values_and_grid_evidence(self):
        row = assemble_classified_piece("stand-1", {
            "VOLUME": 200, "sawlogvolume": 100, "volumegrowth": 10,
            "basalarea": 20, "meanage": 50, "proportionpine": 100,
        }, 0.0256, {}, {"forest_centre_stand": "AVAILABLE"}, grid_intersections=[
            {"area_ha": 0.0064, "values": {"volume": 100, "age": 10}},
            {"area_ha": 0.0192, "values": {"volume": 300, "age": 90}},
        ])
        values = row["indicators"]
        self.assertAlmostEqual(values["grid_total_volume_m3_ha"], 250)
        self.assertEqual(values["total_volume_m3_ha"], 200)
        self.assertEqual(values["sawtimber_volume_m3_ha"], 100)
        self.assertEqual(values["growth_percent"], 5)
        self.assertEqual(values["basal_area_m2_ha"], 20)
        self.assertEqual(values["share_under_20"], 25)
        self.assertIsNone(values["pine_volume_m3_ha"])
        self.assertNotIn("birch_volume_m3_ha", values)
        self.assertIsNone(values["stumpage_price_eur_m3"])
        self.assertNotIn("indicator_status", row)
        self.assertNotIn("birch_volume_m3_ha", row["indicator_coverage"])
        self.assertEqual(row["indicator_coverage"]["stumpage_price_eur_m3"]["status"], "UNKNOWN_FIELD_OR_VALUE")
        self.assertEqual(row["indicator_coverage"]["total_volume_m3_ha"]["source_id"], "forest_centre_stand")
        self.assertEqual(row["indicator_coverage"]["grid_total_volume_m3_ha"]["source_id"], "forest_centre_gridcell")
        without_grid = assemble_classified_piece("stand-1", {"volume": 200}, 1, {},
                                                {"forest_centre_stand": "AVAILABLE"})
        self.assertEqual(without_grid["indicators"]["total_volume_m3_ha"], 200)
        self.assertIsNone(without_grid["indicators"]["grid_total_volume_m3_ha"])
        self.assertEqual(without_grid["classes"], row["classes"])

    def test_summary_combines_statistics_not_piece_means_or_rounded_age_shares(self):
        rows = [assemble_classified_piece("stand-1", {"volume": 100, "volumegrowth": 10}, 1,
                                         {}, {"forest_centre_stand": "AVAILABLE"}, [
            {"area_ha": 0.25, "values": {"volume": 100, "age": 10,
                                         "soiltype": 60, "drainagestate": 6}},
        ]), assemble_classified_piece("stand-2", {"volume": 300, "volumegrowth": 3}, 1,
                                      {}, {"forest_centre_stand": "AVAILABLE"}, [
            {"area_ha": 1, "values": {"volume": 300, "age": 90,
                                      "soiltype": 11, "drainagestate": 1}},
        ])]
        summary = summarize_indicator_rows(rows)
        self.assertNotIn("indicator_status", summary)
        self.assertNotIn("diagnostics", summary)
        self.assertEqual(summary["grid_total_volume_m3_ha"], 260)
        self.assertEqual(summary["total_volume_m3_ha"], 200)
        self.assertEqual(summary["growth_percent"], 5.5)
        self.assertEqual(summary["share_under_20"], 20)
        self.assertEqual(summary["share_over_80"], 80)
        self.assertEqual(summary["area_ha"], 2)
        self.assertEqual(summary["feature_count"], 2)
        self.assertEqual(summary["indicator_coverage"]["grid_total_volume_m3_ha"]["unknown_area_ha"], 0.75)
        self.assertEqual(summary["indicator_coverage"]["share_under_20"]["coverage_percent"], 63)
        self.assertIsNone(summary["peatland_area_ha"])
        self.assertEqual(summary["indicator_coverage"]["peatland_area_ha"]["matching_area_ha"], 0.25)
        flat_rows = [{"class": "ECONOMIC", "area_ha": row["area_ha"],
                      **row["indicators"], "indicator_coverage": row["indicator_coverage"]} for row in rows]
        self.assertEqual(weighted_summary(flat_rows, "ECONOMIC"), summary)
        empty = summarize_indicator_rows([])
        self.assertEqual(empty["area_ha"], 0)
        self.assertIsNone(empty["grid_total_volume_m3_ha"])
        self.assertIsNone(empty["share_under_20"])
        self.assertIsNone(empty["peatland_area_ha"])

    def test_all_documented_categorical_codes_preserve_known_zero_and_matches(self):
        for soil in (10, 11, 12, 20, 21, 22, 23, 24, 30, 31, 32, 40, 50,
                     60, 61, 62, 63, 64, 65, 66, 67, 70, 80):
            with self.subTest(soil=soil):
                result = calculate_grid_indicators(1, [{"area_ha": 1, "values": {"soiltype": soil}}])
                self.assertEqual(result["indicators"]["peatland_area_ha"], 1 if 60 <= soil <= 67 else 0)
                self.assertEqual(result["indicator_coverage"]["peatland_area_ha"]["status"], "AVAILABLE")
        for drainage in (1, 2, 3, 6, 7, 8, 9):
            with self.subTest(drainage=drainage):
                result = calculate_grid_indicators(1, [{"area_ha": 1, "values": {"drainagestate": drainage}}])
                self.assertEqual(result["indicators"]["natural_mire_area_ha"], 1 if drainage == 6 else 0)

    def test_age_summary_recomputes_before_rounding_and_empty_class_stays_unknown(self):
        rows = []
        for matching in (0.0049, 0.005):
            rows.append({"area_ha": 1, **calculate_grid_indicators(1, [
                {"area_ha": matching, "values": {"age": 10}},
                {"area_ha": 1 - matching, "values": {"age": 50}},
            ])})
        self.assertEqual([row["indicators"]["share_under_20"] for row in rows], [0, 1])
        summary = summarize_indicator_rows(rows)
        self.assertEqual(summary["share_under_20"], 0)
        self.assertAlmostEqual(summary["indicator_coverage"]["share_under_20"]["matching_area_ha"], 0.0099)
        empty_class = weighted_summary([], "SENSITIVE")
        self.assertEqual(empty_class["area_ha"], 0)
        self.assertIsNone(empty_class["share_under_20"])
        self.assertEqual(empty_class["indicator_coverage"]["share_under_20"]["status"], "UNKNOWN_FIELD_OR_VALUE")

    def test_area_invariants_stop_invalid_or_double_counted_results(self):
        for area, parts in ((-1, []), (float("nan"), []), (1, [{"area_ha": -1}]),
                            (1, [{"area_ha": 0.6}, {"area_ha": 0.6}])):
            with self.subTest(area=area, parts=parts), self.assertRaises(ValueError):
                calculate_grid_indicators(area, parts)
        tolerated = calculate_grid_indicators(1, [
            {"area_ha": 1.0000000000005, "values": {"volume": 100}},
        ])
        self.assertEqual(tolerated["indicator_coverage"]["grid_total_volume_m3_ha"]["unknown_area_ha"], 0)

    def test_summary_requires_coverage_for_every_piece(self):
        current = assemble_classified_piece("stand", {"volume": 100}, 1, {},
                                            {"forest_centre_stand": "AVAILABLE"})
        without_coverage = {"class": "ECONOMIC", "area_ha": 1,
                            "total_volume_m3_ha": 300, "stumpage_price_eur_m3": 50}
        for rows in ([without_coverage], [current, without_coverage]):
            with self.subTest(rows=rows), self.assertRaisesRegex(KeyError, "indicator_coverage"):
                summarize_indicator_rows(rows)
        with self.assertRaisesRegex(KeyError, "indicator_coverage"):
            weighted_summary([without_coverage], "ECONOMIC")


if __name__ == "__main__":
    unittest.main()
