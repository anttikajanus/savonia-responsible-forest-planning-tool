"""Six-tier policy contracts exercised without QGIS."""

import copy
import itertools
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    str(Path(__file__).resolve().parents[1]),
))

from savonia_responsible_forest_planning_tool.analysis.classification import assemble_classified_piece, classify_tiers, interpret_sources


class ClassificationTests(unittest.TestCase):
    tiers = ("all_out", "bau", "light", "balance", "protection", "superprotection")
    sources = ("syke_protected_areas", "forest_centre_habitat",
               "syke_nature_conservation_programme_areas", "syke_groundwater_areas", "forest_centre_stand")

    def test_all_trigger_combinations_have_cumulative_classes_and_exact_rules(self):
        # Expected membership comes from CL-02, independently of implementation constants.
        triggers = (("active_protected", "protected", 0), ("section10", "section10", 0),
                    ("programme_area", "programme", 3), ("groundwater_area", "groundwater", 3),
                    ("other_valuable_habitat", "other_habitat", 4),
                    ("potential_protected_age", "potential_protected_age", 4))
        states = dict.fromkeys(self.sources, "AVAILABLE")
        for enabled in itertools.product((False, True), repeat=6):
            evidence = {field: value for (field, _, _), value in zip(triggers, enabled)}
            evidence["source_ids"] = {criterion: ["b-" + criterion, "a-" + criterion,
                                                   "a-" + criterion, None]
                                      for _, criterion, _ in triggers}
            before = copy.deepcopy(evidence)
            classes, rules = classify_tiers(evidence, states)
            row = assemble_classified_piece("stand", {"MEANAGE": 81 if enabled[-1] else 80}, 1, {
                **evidence, "source_ids": {},
            }, states)
            with self.subTest(enabled=enabled):
                for (_, criterion, _), value in zip(triggers, enabled):
                    self.assertEqual(row["check_" + criterion], "MATCH" if value else "NO_MATCH")
                for index, tier in enumerate(self.tiers):
                    matches = [criterion for (_, criterion, first), value in zip(triggers, enabled)
                               if value and first <= index]
                    expected = "SENSITIVE" if matches or index == 5 else "ECONOMIC"
                    self.assertEqual(classes[tier], expected)
                    self.assertEqual(rules[tier]["criteria"], matches or (
                        ["remaining_analyzed_forest"] if index == 5 else []))
                    self.assertEqual(rules[tier]["source_ids"], sorted(
                        identifier for criterion in matches
                        for identifier in ("a-" + criterion, "b-" + criterion)))
                self.assertEqual(evidence, before)

    def test_missing_dependencies_affect_only_dependent_tiers_and_positive_matches_win(self):
        for source, first_tier in zip(self.sources, (0, 0, 3, 3, 4)):
            for state in (None, "NOT_AVAILABLE", "OUT_OF_SCOPE"):
                states = dict.fromkeys(self.sources, "AVAILABLE")
                if state is None:
                    del states[source]
                else:
                    states[source] = state
                with self.subTest(source=source, state=state):
                    classes, rules = classify_tiers({"potential_protected_age": False}, states)
                    for index, tier in enumerate(self.tiers):
                        self.assertEqual(classes[tier], "UNKNOWN" if index >= first_tier else "ECONOMIC")
                        if index >= first_tier:
                            self.assertEqual(rules[tier]["unknown_sources"], [source])
                    classes, rules = classify_tiers({"section10": True,
                        "source_ids": {"section10": ["habitat-1"]}}, states)
                    self.assertEqual(set(classes.values()), {"SENSITIVE"})
                    self.assertTrue(all(rule["source_ids"] == ["habitat-1"] for rule in rules.values()))

    def test_piece_exposes_criterion_matches_without_redundant_indicator_payloads(self):
        states = dict.fromkeys(self.sources, "AVAILABLE")
        states["forest_centre_stand"] = "AVAILABLE"
        row = assemble_classified_piece("stand-1", {}, 1, {
            "section10": True, "section10_stand_promoted": True,
            "programme_area": True, "groundwater_area": True,
        }, states)
        self.assertEqual({key: row[key] for key in (
            "check_protected", "check_section10", "check_programme",
            "check_groundwater", "check_other_habitat")}, {
            "check_protected": "NO_MATCH", "check_section10": "MATCH",
            "check_programme": "MATCH", "check_groundwater": "MATCH",
            "check_other_habitat": "NO_MATCH",
        })
        self.assertNotIn("indicator_status", row)
        self.assertNotIn("indicator_diagnostics", row)
        self.assertEqual(row["indicator_coverage"]["grid_total_volume_m3_ha"]["status"],
                         "UNKNOWN_FIELD_OR_VALUE")
        unknown = assemble_classified_piece("stand-2", {}, 1, {}, {})
        self.assertEqual(unknown["check_section10"], "UNKNOWN")
        self.assertEqual(unknown["check_protected"], "UNKNOWN")
        self.assertEqual(unknown["check_programme"], "UNKNOWN")
        self.assertEqual(unknown["check_groundwater"], "UNKNOWN")
        self.assertEqual(unknown["check_other_habitat"], "UNKNOWN")
        positive = assemble_classified_piece("stand-3", {}, 1, {"section10": True}, {})
        self.assertEqual(positive["check_section10"], "MATCH")

    def test_stand_age_threshold_and_provenance_are_independent_of_grid_age(self):
        states = dict.fromkeys(self.sources, "AVAILABLE")
        for field in ("MEANAGE", "MeanAge", "meanage"):
            for age, match in ((0, False), (79.99, False), (80, False), (80.001, True), (120, True)):
                with self.subTest(field=field, age=age):
                    evidence = {"source_ids": {"protected": []}}
                    original = copy.deepcopy(evidence)
                    row = assemble_classified_piece("parent", {field: age}, 0.25, evidence, states,
                        grid_intersections=[{"area_ha": 0.25, "values": {"age": 150 if age <= 80 else 10}}])
                    self.assertEqual(row["check_potential_protected_age"], "MATCH" if match else "NO_MATCH")
                    self.assertEqual(row["check_protected"], "NO_MATCH")
                    self.assertEqual(row["classes"]["protection"], "SENSITIVE" if match else "ECONOMIC")
                    self.assertEqual(row["classes"]["superprotection"], "SENSITIVE")
                    for tier in ("all_out", "bau", "light", "balance"):
                        self.assertEqual(row["classes"][tier], "ECONOMIC")
                    for tier in ("protection", "superprotection"):
                        self.assertEqual("potential_protected_age" in row["rules"][tier]["criteria"], match)
                        self.assertEqual(row["rules"][tier]["source_ids"], ["parent"] if match else [])
                    self.assertEqual(evidence, original)

    def test_unknown_stand_age_never_becomes_no_match_or_superprotection_catch_all(self):
        states = dict.fromkeys(self.sources, "AVAILABLE")
        for age in (None, "81", "invalid", True, False, -1, float("nan"), float("inf"), float("-inf"), 81j):
            for evidence in ({}, {"other_valuable_habitat": True}):
                with self.subTest(age=age, evidence=evidence):
                    row = assemble_classified_piece("parent", {"MEANAGE": age}, 1, evidence, states)
                    self.assertEqual(row["check_potential_protected_age"], "UNKNOWN")
                    for tier in ("protection", "superprotection"):
                        self.assertEqual(row["classes"][tier], "SENSITIVE" if evidence else "UNKNOWN")
                        if not evidence:
                            self.assertEqual(row["rules"][tier]["unknown_sources"], ["forest_centre_stand"])
                    self.assertEqual(row["classes"]["balance"], "ECONOMIC")
        missing = assemble_classified_piece("parent", {}, 1, {}, states)
        self.assertEqual(missing["check_potential_protected_age"], "UNKNOWN")
        unavailable = assemble_classified_piece("parent", {"MEANAGE": 100}, 1, {},
            {**states, "forest_centre_stand": "NOT_AVAILABLE"})
        self.assertEqual(unavailable["check_potential_protected_age"], "UNKNOWN")

    def test_unrecognized_classification_records_are_diagnostic_not_no_hits(self):
        cases = (
            ("syke_protected_areas_private_land", {"olotila": "Poistunut", "tyyppilyhenne": "YSA"},
             "UNRECOGNIZED_PROTECTED_VALUES"),
            ("forest_centre_habitat", {"habitattype": "999"}, "UNRECOGNIZED_HABITAT_VALUES"),
            ("syke_nature_conservation_programme_areas", {"luokka": "AMO", "lsoaluetunnus": " "},
             "UNRECOGNIZED_PROGRAMME_VALUES"),
            ("syke_nature_conservation_programme_areas", {"luokka": "invalid", "lsoaluetunnus": "P1"},
             "UNRECOGNIZED_PROGRAMME_VALUES"),
        )
        for source, values, reason in cases:
            feature = {"service_id": source, "source_id": "bad-1", "values": values,
                       "attributes": values.copy(), "geometry": object()}
            with self.subTest(source=source, values=values):
                _, _, diagnostics = interpret_sources({source: [feature]}, {})
                self.assertEqual(diagnostics[source]["reason_code"], reason)
                self.assertIn("bad-1", repr(diagnostics[source]))


if __name__ == "__main__":
    unittest.main()
