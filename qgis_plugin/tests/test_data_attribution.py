"""Source credits must survive independently shared analysis outputs."""

from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])),
))

from savonia_responsible_forest_planning_tool.data_attribution import data_attribution


class DataAttributionTests(unittest.TestCase):
    def test_every_analysis_source_has_its_own_credit_and_modification_notice(self):
        ids = (
            "forest_centre_stand", "forest_centre_habitat", "forest_centre_gridcell",
            "syke_protected_areas_state_owned", "syke_protected_areas_private_land",
            "syke_protected_areas_wilderness", "syke_nature_conservation_programme_areas",
            "syke_groundwater_areas",
        )
        for notice in ("Aineisto leikattu; johdettuja tuloksia.", "Data clipped; derived results."):
            with self.subTest(notice=notice):
                credits = data_attribution(ids, notice)
                self.assertEqual(set(credits), set(ids))
                for item in credits.values():
                    self.assertEqual(item["license"], "CC-BY-4.0")
                    self.assertEqual(item["license_url"], "https://creativecommons.org/licenses/by/4.0/")
                    self.assertTrue(item["dataset"])
                    self.assertTrue(item["attribution"])
                    self.assertTrue(item["terms_url"].startswith("https://"))
                    self.assertEqual(item["modifications"], notice)
                self.assertIn("Metsähallitus", credits["syke_protected_areas_wilderness"]["attribution"])
                self.assertIn("Lupa- ja valvontavirasto", credits["syke_groundwater_areas"]["attribution"])
                self.assertIn("MML", credits["syke_groundwater_areas"]["attribution"])
                self.assertNotIn("osm_xyz", credits, "Basemap data is not an analysis export")

if __name__ == "__main__":
    unittest.main()
