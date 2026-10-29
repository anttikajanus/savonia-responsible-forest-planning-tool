"""Sawlog-only price applicability and full-precision group weighting."""
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, os.environ.get("RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])))
from savonia_responsible_forest_planning_tool.analysis.classification import assemble_classified_piece
from savonia_responsible_forest_planning_tool.analysis.grid_indicators import summarize_indicator_rows
from savonia_responsible_forest_planning_tool.adapters.result_precision import published_value

class SawlogPricingTest(unittest.TestCase):
    def test_calculated_value_uses_unrounded_represented_sawlogs(self):
        row = assemble_classified_piece("33456372", {"sawlogvolume": 342.71},
            1.4772514669427148, {}, {"forest_centre_stand": "AVAILABLE"},
            sawlog_price_eur_m3=10)
        self.assertAlmostEqual(row["indicators"]["sawlog_value_eur"], 5062.688502359378)
        self.assertEqual(row["indicators"]["stumpage_price_eur_m3"], 10)
        coverage = row["indicator_coverage"]["sawlog_value_eur"]
        self.assertAlmostEqual(coverage["represented_volume_m3"], 506.26885023593775)
        self.assertAlmostEqual(coverage["weighted_sum"], 5062.688502359378)
        self.assertEqual(coverage["status"], "AVAILABLE")

    def test_value_totals_sum_exact_amounts_and_keep_missing_evidence_explicit(self):
        rows = [assemble_classified_piece("stand", {"sawlogvolume": volume}, area, {},
            {"forest_centre_stand": "AVAILABLE"}, sawlog_price_eur_m3=10)
            for volume, area in ((100, 1), (300, 2), (None, 1), (0, 1))]
        self.assertEqual(summarize_indicator_rows(rows[:2])["sawlog_value_eur"], 7000)
        partial = summarize_indicator_rows(rows)
        self.assertIsNone(partial["sawlog_value_eur"])
        self.assertEqual(partial["indicator_coverage"]["sawlog_value_eur"], {
            "source_id": "forest_centre_stand", "status": "PARTIAL",
            "valid_area_ha": 4, "unknown_area_ha": 1,
            "represented_volume_m3": 700, "weighted_sum": 7000,
        })
        self.assertEqual(rows[-1]["indicators"]["sawlog_value_eur"], 0)
        self.assertEqual(summarize_indicator_rows(rows[-1:])["sawlog_value_eur"], 0)
        self.assertIsNone(summarize_indicator_rows([])["sawlog_value_eur"])
        for volume in (-1, None, float("nan"), float("inf"), "20", True):
            with self.subTest(volume=volume):
                missing = assemble_classified_piece("stand", {"sawlogvolume": volume}, 1, {},
                    {"forest_centre_stand": "AVAILABLE"}, sawlog_price_eur_m3=10)
                self.assertIsNone(missing["indicators"]["sawlog_value_eur"])

    def test_euro_cents_are_rounded_after_group_summation(self):
        row = assemble_classified_piece("tiny", {"sawlogvolume": 0.0006}, 1, {},
            {"forest_centre_stand": "AVAILABLE"}, sawlog_price_eur_m3=10)
        self.assertEqual(published_value("sawlog_value_eur", row["indicators"]["sawlog_value_eur"]), 0.01)
        summary = summarize_indicator_rows([row, row])
        self.assertAlmostEqual(summary["indicator_coverage"]["sawlog_value_eur"]["weighted_sum"], 0.012)
        self.assertEqual(published_value("sawlog_value_eur", summary["sawlog_value_eur"]), 0.01)

    def test_price_applies_only_to_positive_finite_source_sawlogs(self):
        for volume in (100, 0.000001, 0, -1, None, float("nan"), float("inf"), "20"):
            with self.subTest(volume=volume):
                row = assemble_classified_piece("stand", {"sawlogvolume": volume}, 2, {},
                    {"forest_centre_stand": "AVAILABLE"}, sawlog_price_eur_m3=75.25)
                expected = 75.25 if volume in (100, 0.000001) else None
                self.assertEqual(row["indicators"]["stumpage_price_eur_m3"], expected)
                coverage = row["indicator_coverage"]["stumpage_price_eur_m3"]
                self.assertEqual(coverage["valid_area_ha"], 2 if expected else 0)
                self.assertEqual(coverage["source_id"], "forest_centre_stand")

    def test_summary_weights_price_by_unrounded_represented_sawlog_volume(self):
        rows = [assemble_classified_piece("stand", {"sawlogvolume": volume}, area, {},
            {"forest_centre_stand": "AVAILABLE"}, sawlog_price_eur_m3=price)
            for volume, area, price in ((100, 1, 50), (300, 2, 80), (0, 1, 99), (None, 1, 99))]
        summary = summarize_indicator_rows(rows)
        self.assertAlmostEqual(summary["stumpage_price_eur_m3"], 53000 / 700)
        coverage = summary["indicator_coverage"]["stumpage_price_eur_m3"]
        self.assertEqual(coverage["represented_volume_m3"], 700)
        self.assertEqual(coverage["valid_area_ha"], 3)
        self.assertEqual(coverage["unknown_area_ha"], 2)
        self.assertEqual(coverage["status"], "PARTIAL")
        for members in ([], rows[2:]):
            self.assertIsNone(summarize_indicator_rows(members)["stumpage_price_eur_m3"])

if __name__ == "__main__":
    unittest.main()
