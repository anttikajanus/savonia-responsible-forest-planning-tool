"""Stand-age screening survives the real WFS/Processing/publication path."""

import json
import unittest

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsProcessingException, QgsVectorLayer

from savonia_responsible_forest_planning_tool.i18n import tr
from test_grid_publication import workbook_rows
from workflow_fixture import WorkflowFixtureMixin, coordinates, fixture_sources, source_record


class StandAgeProtectionTests(WorkflowFixtureMixin, unittest.TestCase):
    def test_natural_state_mire_check_and_publication_in_both_languages(self):
        fields = fixture_sources()
        cases = (("match", "6", "MATCH"),
                 ("code-1", "1", "NO_MATCH"), ("code-2", "2", "NO_MATCH"),
                 ("code-3", "3", "NO_MATCH"), ("code-7", "7", "NO_MATCH"),
                 ("code-8", "8", "NO_MATCH"), ("code-9", "9", "NO_MATCH"),
                 ("null", None, "UNKNOWN"), ("fraction", "6.5", "UNKNOWN"),
                 ("unrecognized", "12", "UNKNOWN"), ("text", "bad", "UNKNOWN"))
        stands = [source_record({**fields["forest_centre_stand"], "standid": identifier,
                                 "DRAINAGESTATE": code}, x=350000 + index * 100)
                  for index, (identifier, code, _check) in enumerate(cases)]
        grid = [source_record(fields["forest_centre_gridcell"])]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario(
                    grid, stands, [coordinates(350000, 6900000, len(stands) * 100, 100)]) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "mire-" + language)
                layer = QgsVectorLayer(result["RESULT"], "mire results", "ogr")
                self.assertTrue(layer.isValid())
                features = {feature["source_stand_id"]: feature for feature in layer.getFeatures()}
                self.assertEqual(set(features), {identifier for identifier, _code, _check in cases})
                for identifier, _code, expected_check in cases:
                    feature = features[identifier]
                    self.assertEqual(feature["check_natural_state_mire"], expected_check)
                    self.assertEqual(feature["class_all_out"], "ECONOMIC")
                    self.assertEqual(feature["class_bau"],
                                     "SENSITIVE" if expected_check == "MATCH" else
                                     "UNKNOWN" if expected_check == "UNKNOWN" else "ECONOMIC")
                    self.assertEqual(feature["class_light"],
                                     "SENSITIVE" if expected_check == "MATCH" else
                                     "UNKNOWN" if expected_check == "UNKNOWN" else "ECONOMIC")
                    for tier in ("balance", "protection"):
                        self.assertEqual(feature["class_" + tier],
                                         "SENSITIVE" if expected_check == "MATCH" else
                                         "UNKNOWN" if expected_check == "UNKNOWN" else "ECONOMIC")
                    self.assertEqual(feature["class_superprotection"],
                                     "SENSITIVE" if expected_check in ("MATCH", "NO_MATCH") else "UNKNOWN")
                self.assertEqual(features["match"]["natural_mire_area_ha"], 1)
                matched_rules = json.loads(features["match"]["tier_rule_ids"])
                for tier in ("bau", "light", "balance", "protection", "superprotection"):
                    self.assertIn("natural_state_mire", matched_rules[tier]["criteria"])
                    self.assertEqual(matched_rules[tier]["source_ids"], ["match"])
                expected_alias = ("Luonnontilaisen suon tarkistus" if language == "fi"
                                  else "Natural-state mire check")
                field_index = layer.fields().indexFromName("check_natural_state_mire")
                self.assertEqual(layer.attributeAlias(field_index), expected_alias)
                metadata = QgsVectorLayer(result["RESULT"].split("|", 1)[0] + "|layername=run_metadata",
                                          "metadata", "ogr")
                semantics = json.loads(next(metadata.getFeatures())["classification_semantics"])
                self.assertEqual(semantics["natural_state_mire"], {
                    "source_id": "forest_centre_stand", "field": "DRAINAGESTATE", "unit": "drainage code",
                    "rule": "DRAINAGESTATE == 6", "tiers": ["bau", "light", "balance", "protection", "superprotection"],
                    "scope": "all pieces of the parent stand",
                    "unknown": "missing, boolean, malformed, nonfinite, fractional or unrecognized drainage code",
                    "interpretation": "source-classified natural-state mire sensitivity; not a legal protection determination",
                })
                notes = workbook_rows(result["EXCEL"])[tr(language, "sheet_notes")]
                workbook_semantics = json.loads("".join(row[2] for row in notes
                                                       if row[0] == "classification_semantics"))
                self.assertEqual(workbook_semantics, semantics)

    def test_missing_stand_drainage_field_fails_before_output(self):
        with self.scenario([], omit_stand_fields=("DRAINAGESTATE",)) as (_, layers, aoi):
            with self.assertRaises(QgsProcessingException):
                self.run_algorithm(layers, aoi, "en", "missing-drainage")
            import os
            self.assertFalse(os.path.exists(os.path.join(self.temp.name, "missing-drainage.gpkg")))
            self.assertFalse(os.path.exists(os.path.join(self.temp.name, "missing-drainage.xlsx")))

    def test_parent_stand_mire_check_is_inherited_by_split_result_pieces(self):
        fields = fixture_sources()
        stand = source_record({**fields["forest_centre_stand"], "standid": "mire-parent",
                               "DRAINAGESTATE": "6"})
        habitat = source_record({"HabitatId": "splitter", "HabitatType": "3"},
                                x=350050, width=50, height=100)
        with self.scenario([], [stand], [coordinates(350000, 6900000, 100, 100)],
                           additional_records={"forest_centre_habitat": [habitat]}) as (_, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "mire-parent-pieces")
            layer = QgsVectorLayer(result["RESULT"], "mire pieces", "ogr")
            features = list(layer.getFeatures())
            self.assertEqual(len(features), 2)
            self.assertEqual({feature["source_stand_id"] for feature in features}, {"mire-parent"})
            self.assertTrue(all(feature["check_natural_state_mire"] == "MATCH" for feature in features))

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
                        ("at-80", "MATCH", "SENSITIVE", "SENSITIVE"),
                        ("over-80", "MATCH", "SENSITIVE", "SENSITIVE"),
                        ("unknown", "UNKNOWN", "UNKNOWN", "UNKNOWN")):
                    feature = features[identifier]
                    self.assertEqual(feature["check_potential_protected_age"], check)
                    self.assertEqual(feature["check_protected"], "NO_MATCH")
                    self.assertEqual(feature["class_protection"], protection)
                    self.assertEqual(feature["class_superprotection"], superprotection)
                    for tier in ("all_out", "bau"):
                        self.assertEqual(feature["class_" + tier], "ECONOMIC")
                    for tier in ("light", "balance"):
                        self.assertEqual(feature["class_" + tier],
                                         "UNKNOWN" if identifier == "unknown" else "ECONOMIC")
                rules = json.loads(features["over-80"]["tier_rule_ids"])
                self.assertEqual(rules["protection"]["criteria"], ["potential_protected_age"])
                self.assertEqual(rules["protection"]["source_ids"], ["over-80"])
                expected_alias = ("Metsänikään perustuva mahdollinen suojelu (80 vuotta)"
                                  if language == "fi" else "Potential protected area based on forest age (80 years)")
                self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("check_potential_protected_age")),
                                 expected_alias)
                metadata = QgsVectorLayer(result["RESULT"].split("|", 1)[0] + "|layername=run_metadata", "metadata", "ogr")
                self.assertTrue(metadata.isValid())
                semantics = json.loads(next(metadata.getFeatures())["classification_semantics"])
                self.assertEqual(semantics["potential_protected_age"], {
                    "source_id": "forest_centre_stand", "field": "MEANAGE", "unit": "years",
                    "rule": "MEANAGE >= 80", "tiers": ["protection", "superprotection"],
                    "scope": "all pieces of the parent stand",
                    "unknown": "missing, nonnumeric, boolean, nonfinite or negative age",
                    "interpretation": "potential protection based on age; not legal protection",
                })
                sheets = workbook_rows(result["EXCEL"])
                summary = sheets[tr(language, "sheet_summary")]
                expected_area = {"SENSITIVE": 2, "ECONOMIC": 0, "UNKNOWN": 1}
                for class_code in ("SENSITIVE", "ECONOMIC", "UNKNOWN"):
                    row = next(row for row in summary if row[:2] == [tr(language, "tier_protection"),
                                                                 tr(language, "class_" + class_code.lower())])
                    self.assertEqual(float(row[2]), expected_area[class_code])
                notes = sheets[tr(language, "sheet_notes")]
                workbook_semantics = json.loads("".join(row[2] for row in notes
                                                       if row[0] == "classification_semantics"))
                self.assertEqual(workbook_semantics, semantics)


if __name__ == "__main__":
    unittest.main()
