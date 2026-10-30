"""Stand-age screening survives the real WFS/Processing/publication path."""

import json
import unittest

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsVectorLayer

from savonia_responsible_forest_planning_tool.i18n import tr
from test_grid_publication import workbook_rows
from workflow_fixture import WorkflowFixtureMixin, coordinates, fixture_sources, source_record


class StandAgeProtectionTests(WorkflowFixtureMixin, unittest.TestCase):
    def test_threshold_unknowns_and_summaries_in_both_languages(self):
        fields = fixture_sources()
        stands = [source_record({**fields["forest_centre_stand"], "standid": identifier, "MeanAge": age},
                                x=350000 + index * 100)
                  for index, (identifier, age) in enumerate((("at-80", 80), ("over-80", 80.01), ("unknown", None)))]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([], stands,
                    [coordinates(350000, 6900000, 300, 100)]) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "age-" + language)
                layer = QgsVectorLayer(result["RESULT"], "age results", "ogr")
                self.assertTrue(layer.isValid())
                features = {feature["source_stand_id"]: feature for feature in layer.getFeatures()}
                self.assertEqual(set(features), {"at-80", "over-80", "unknown"})
                for identifier, check, protection, superprotection in (
                        ("at-80", "NO_MATCH", "ECONOMIC", "SENSITIVE"),
                        ("over-80", "MATCH", "SENSITIVE", "SENSITIVE"),
                        ("unknown", "UNKNOWN", "UNKNOWN", "UNKNOWN")):
                    feature = features[identifier]
                    self.assertEqual(feature["check_potential_protected_age"], check)
                    self.assertEqual(feature["check_protected"], "NO_MATCH")
                    self.assertEqual(feature["class_protection"], protection)
                    self.assertEqual(feature["class_superprotection"], superprotection)
                    for tier in ("all_out", "bau", "light", "balance"):
                        self.assertEqual(feature["class_" + tier], "ECONOMIC")
                rules = json.loads(features["over-80"]["tier_rule_ids"])
                self.assertEqual(rules["protection"]["criteria"], ["potential_protected_age"])
                self.assertEqual(rules["protection"]["source_ids"], ["over-80"])
                self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("check_potential_protected_age")),
                                 tr(language, "check_potential_protected_age"))
                sheets = workbook_rows(result["EXCEL"])
                summary = sheets[tr(language, "sheet_summary")]
                for class_code in ("SENSITIVE", "ECONOMIC", "UNKNOWN"):
                    row = next(row for row in summary if row[:2] == [tr(language, "tier_protection"),
                                                                 tr(language, "class_" + class_code.lower())])
                    self.assertEqual(float(row[2]), 1)
                notes = str(sheets[tr(language, "sheet_notes")])
                self.assertIn("MEANAGE > 80", notes)
                self.assertIn("classification_semantics", notes)


if __name__ == "__main__":
    unittest.main()
