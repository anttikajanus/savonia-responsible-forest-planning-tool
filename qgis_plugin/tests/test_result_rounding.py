"""Reporting rounding preserves unknowns and uses consistent half-up ties."""

import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    str(Path(__file__).resolve().parents[1]),
))

from savonia_responsible_forest_planning_tool.adapters.result_precision import RESULT_DECIMALS, published_value


class ResultRoundingTests(unittest.TestCase):
    def test_half_up_zero_and_unknown_for_every_published_volume_and_area(self):
        for metric, decimals in RESULT_DECIMALS.items():
            with self.subTest(metric=metric):
                self.assertIsNone(published_value(metric, None))
                self.assertEqual(published_value(metric, 0), 0)
                self.assertEqual(published_value(metric, 12.5 if decimals == 0 else 12.325),
                                 13 if decimals == 0 else 12.33)
        self.assertEqual(published_value("growth_percent", 3.167832565546266), 3.167832565546266)
        self.assertEqual(published_value("share_under_20", 63), 63)


if __name__ == "__main__":
    unittest.main()
