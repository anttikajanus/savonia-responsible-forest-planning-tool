"""Sawlog-only price applicability and full-precision group weighting."""
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, os.environ.get("RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])))
from savonia_responsible_forest_planning_tool.analysis.classification import assemble_classified_piece
from savonia_responsible_forest_planning_tool.analysis.grid_indicators import summarize_indicator_rows

class SawlogPricingTest(unittest.TestCase):
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
