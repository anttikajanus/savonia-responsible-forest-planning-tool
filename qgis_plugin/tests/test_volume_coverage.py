"""Species means with different valid areas are not additive total estimates."""

import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])))

from savonia_responsible_forest_planning_tool.analysis.classification import assemble_classified_piece
from savonia_responsible_forest_planning_tool.analysis.grid_indicators import summarize_indicator_rows


class VolumeCoverageTests(unittest.TestCase):
    def test_missing_species_is_unknown_and_uses_its_own_denominator(self):
        row = assemble_classified_piece("stand", {"volume": 175.83}, 2, {},
            {"forest_centre_stand": "AVAILABLE"}, [
                {"area_ha": 1, "values": {"volume": 100, "volumepine": 100,
                    "volumespruce": None, "volumedeciduous": 0}},
                {"area_ha": 1, "values": {"volume": 100, "volumepine": 0,
                    "volumespruce": 100, "volumedeciduous": 0}},
            ])
        summary = summarize_indicator_rows([row])
        self.assertEqual(summary["total_volume_m3_ha"], 175.83)
        self.assertEqual(summary["grid_total_volume_m3_ha"], 100)
        self.assertEqual(summary["pine_volume_m3_ha"], 50)
        self.assertEqual(summary["spruce_volume_m3_ha"], 100)
        self.assertEqual(summary["deciduous_volume_m3_ha"], 0)
        coverage = summary["indicator_coverage"]
        self.assertEqual(coverage["spruce_volume_m3_ha"]["status"], "PARTIAL")
        self.assertEqual(coverage["spruce_volume_m3_ha"]["valid_area_ha"], 1)
        self.assertEqual(coverage["spruce_volume_m3_ha"]["unknown_area_ha"], 1)
        species = ("pine_volume_m3_ha", "spruce_volume_m3_ha", "deciduous_volume_m3_ha")
        self.assertEqual(sum(summary[metric] for metric in species), 150)
        self.assertEqual(sum(coverage[metric]["represented_volume_m3"] for metric in species),
                         coverage["grid_total_volume_m3_ha"]["represented_volume_m3"])


if __name__ == "__main__":
    unittest.main()
