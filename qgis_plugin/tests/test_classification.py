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

    def available_states(self):
        return {**dict.fromkeys(self.sources, "AVAILABLE"),
                "syke_rantaviiva_water_buffers": "AVAILABLE"}

    def test_all_trigger_combinations_have_cumulative_classes_and_exact_rules(self):
        # Expected membership comes from CL-02, independently of implementation constants.
        triggers = (("active_protected", "protected", 0), ("section10", "section10", 0),
                    ("programme_area", "programme", 3), ("groundwater_area", "groundwater", 3),
                    ("other_valuable_habitat", "other_habitat", 4),
                    ("potential_protected_age_100", "potential_protected_age_100", 2),
                    ("potential_protected_age_90", "potential_protected_age_90", 3),
                    ("potential_protected_age", "potential_protected_age", 4),
                    ("potential_protected_peatland", "potential_protected_peatland", 3),
                    ("parent_peatland_watercourse", "parent_peatland_watercourse", 2),
                    ("natural_state_mire", "natural_state_mire", 1))
        states = self.available_states()
        tier_criteria = {
            "all_out": {"protected", "section10"},
            "bau": {"protected", "section10", "natural_state_mire"},
            "light": {"protected", "section10", "potential_protected_age_100",
                      "natural_state_mire", "parent_peatland_watercourse"},
            "balance": {"protected", "section10", "programme", "groundwater", "riparian_buffer",
                        "potential_protected_age_90", "potential_protected_peatland", "natural_state_mire",
                        "parent_peatland_watercourse"},
            "protection": {"protected", "section10", "programme", "groundwater", "riparian_buffer",
                           "other_habitat", "potential_protected_age", "potential_protected_peatland",
                           "natural_state_mire", "parent_peatland_watercourse"},
            "superprotection": {"protected", "section10", "programme", "groundwater", "riparian_buffer",
                                "other_habitat", "potential_protected_age", "potential_protected_peatland",
                                "natural_state_mire", "parent_peatland_watercourse"},
        }
        for enabled in itertools.product((False, True), repeat=len(triggers)):
            # Threshold booleans from one age value must be ordered: reaching
            # 100 implies also reaching 90 and 80; reaching 90 implies 80.
            if (enabled[5] and not enabled[6]) or (enabled[6] and not enabled[7]):
                continue
            evidence = {field: value for (field, _, _), value in zip(triggers, enabled)}
            # This matrix exercises tier membership for each explicit trigger
            # combination; omitted evidence has its own UNKNOWN regression.
            evidence["natural_state_mire"] = evidence.get("natural_state_mire", False)
            evidence["source_ids"] = {criterion: ["b-" + criterion, "a-" + criterion,
                                                   "a-" + criterion, None]
                                      for _, criterion, _ in triggers}
            before = copy.deepcopy(evidence)
            classes, rules = classify_tiers(evidence, states)
            with self.subTest(enabled=enabled):
                for index, tier in enumerate(self.tiers):
                    matches = [criterion for (_, criterion, _), value in zip(triggers, enabled)
                               if value and criterion in tier_criteria[tier]]
                    expected = "SENSITIVE" if matches or index == 5 else "ECONOMIC"
                    self.assertEqual(classes[tier], expected)
                    self.assertEqual(rules[tier]["criteria"], matches or (
                        ["remaining_analyzed_forest"] if index == 5 else []))
                    self.assertEqual(rules[tier]["source_ids"], sorted(
                        identifier for criterion in matches
                        for identifier in ("a-" + criterion, "b-" + criterion)))
                self.assertEqual(evidence, before)

    def test_missing_dependencies_affect_only_dependent_tiers_and_positive_matches_win(self):
        for source, first_tier in zip(self.sources, (0, 0, 3, 3, 1)):
            for state in (None, "NOT_AVAILABLE", "OUT_OF_SCOPE"):
                states = self.available_states()
                if state is None:
                    del states[source]
                else:
                    states[source] = state
                with self.subTest(source=source, state=state):
                    classes, rules = classify_tiers({
                        "potential_protected_age": False, "potential_protected_age_90": False,
                        "potential_protected_age_100": False,
                        "potential_protected_peatland": False,
                        "parent_peatland_watercourse": False,
                        "natural_state_mire": False,
                    }, states)
                    for index, tier in enumerate(self.tiers):
                        self.assertEqual(classes[tier], "UNKNOWN" if index >= first_tier else "ECONOMIC")
                        if index >= first_tier:
                            self.assertEqual(rules[tier]["unknown_sources"], [source])
                    classes, rules = classify_tiers({"section10": True,
                        "source_ids": {"section10": ["habitat-1"]}}, states)
                    self.assertEqual(set(classes.values()), {"SENSITIVE"})
                    self.assertTrue(all(rule["source_ids"] == ["habitat-1"] for rule in rules.values()))

    def test_omitted_natural_state_mire_evidence_is_unknown_for_applicable_tiers(self):
        classes, rules = classify_tiers({}, self.available_states())

        self.assertEqual(classes["all_out"], "ECONOMIC")
        for tier in self.tiers[1:]:
            with self.subTest(tier=tier):
                self.assertEqual(classes[tier], "UNKNOWN")
                self.assertEqual(rules[tier]["unknown_sources"], ["forest_centre_stand"])

    def test_piece_exposes_criterion_matches_without_redundant_indicator_payloads(self):
        states = self.available_states()
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

    def test_riparian_is_an_available_dependency_from_balance_and_coexists_with_other_reasons(self):
        states = self.available_states()
        missing = dict(states)
        del missing["syke_rantaviiva_water_buffers"]
        classes, rules = classify_tiers({
            "potential_protected_age": False, "potential_protected_age_90": False,
            "potential_protected_age_100": False, "potential_protected_peatland": False,
            "parent_peatland_watercourse": False,
            "natural_state_mire": False,
        }, missing)
        self.assertEqual([classes[tier] for tier in self.tiers], [
            "ECONOMIC", "ECONOMIC", "ECONOMIC", "UNKNOWN", "UNKNOWN", "UNKNOWN",
        ])
        for tier in self.tiers[3:]:
            self.assertIn("syke_rantaviiva_water_buffers", rules[tier]["unknown_sources"])

        row = assemble_classified_piece("stand", {}, 1, {
            "groundwater_area": True,
            "riparian_buffer": True,
            "source_ids": {
                "groundwater": ["groundwater-1"],
                "riparian_buffer": ["syke_rantaviiva_line_river:line-1"],
            },
        }, states)
        self.assertEqual(row["check_riparian_buffer"], "MATCH")
        self.assertEqual(row["classes"]["all_out"], "ECONOMIC")
        for tier in self.tiers[3:]:
            self.assertEqual(row["classes"][tier], "SENSITIVE")
            self.assertEqual(row["rules"][tier]["criteria"], ["groundwater", "riparian_buffer"])
            self.assertEqual(row["rules"][tier]["source_ids"], [
                "groundwater-1", "syke_rantaviiva_line_river:line-1",
            ])

    def test_stand_age_threshold_and_provenance_are_independent_of_grid_age(self):
        states = self.available_states()
        for field in ("MEANAGE", "MeanAge", "meanage"):
            for age, match in ((0, False), (79.99, False), (80, True), (80.001, True), (120, True)):
                with self.subTest(field=field, age=age):
                    evidence = {"source_ids": {"protected": []}}
                    original = copy.deepcopy(evidence)
                    row = assemble_classified_piece("parent", {field: age, "SOILTYPE": "10", "DRAINAGESTATE": "1"}, 0.25, evidence, states,
                        grid_intersections=[{"area_ha": 0.25, "values": {"age": 150 if age <= 80 else 10}}])
                    self.assertEqual(row["check_potential_protected_age"], "MATCH" if match else "NO_MATCH")
                    self.assertEqual(row["check_protected"], "NO_MATCH")
                    self.assertEqual(row["classes"]["protection"], "SENSITIVE" if match else "ECONOMIC")
                    self.assertEqual(row["classes"]["superprotection"], "SENSITIVE")
                    for tier in ("all_out", "bau"):
                        self.assertEqual(row["classes"][tier], "ECONOMIC")
                    self.assertEqual(row["classes"]["light"], "SENSITIVE" if age >= 100 else "ECONOMIC")
                    self.assertEqual(row["classes"]["balance"], "SENSITIVE" if age >= 90 else "ECONOMIC")
                    for tier in ("protection", "superprotection"):
                        self.assertEqual("potential_protected_age" in row["rules"][tier]["criteria"], match)
                        self.assertEqual(row["rules"][tier]["source_ids"], ["parent"] if match else [])
                    self.assertEqual(evidence, original)

    def test_unknown_stand_age_never_becomes_no_match_or_superprotection_catch_all(self):
        states = self.available_states()
        for age in (None, "81", "invalid", True, False, -1, float("nan"), float("inf"), float("-inf"), 81j):
            for evidence in ({}, {"other_valuable_habitat": True}):
                with self.subTest(age=age, evidence=evidence):
                    row = assemble_classified_piece("parent", {"MEANAGE": age, "SOILTYPE": "10", "DRAINAGESTATE": "1"}, 1, evidence, states)
                    self.assertEqual(row["check_potential_protected_age"], "UNKNOWN")
                    for tier in ("protection", "superprotection"):
                        self.assertEqual(row["classes"][tier], "SENSITIVE" if evidence else "UNKNOWN")
                        if not evidence:
                            self.assertEqual(row["rules"][tier]["unknown_sources"], ["forest_centre_stand"])
                    self.assertEqual(row["classes"]["light"], "UNKNOWN")
                    self.assertEqual(row["classes"]["balance"], "UNKNOWN")
        missing = assemble_classified_piece("parent", {"DRAINAGESTATE": "1"}, 1, {}, states)
        self.assertEqual(missing["check_potential_protected_age"], "UNKNOWN")
        unavailable = assemble_classified_piece("parent", {"MEANAGE": 100, "DRAINAGESTATE": "1"}, 1, {},
            {**states, "forest_centre_stand": "NOT_AVAILABLE"})
        self.assertEqual(unavailable["check_potential_protected_age"], "UNKNOWN")

    def test_stand_soil_codes_control_peatland_checks_independently_of_grid_soil(self):
        cases = [(code, "MATCH") for code in range(60, 70)] + [
            ("60", "MATCH"), (" 69.0 ", "MATCH"), (10, "NO_MATCH"), ("70", "NO_MATCH"),
            (59, "UNKNOWN"), (None, "UNKNOWN"), ("", "UNKNOWN"), ("invalid", "UNKNOWN"),
            (True, "UNKNOWN"), (False, "UNKNOWN"), (60.5, "UNKNOWN"), (999, "UNKNOWN"),
            (float("nan"), "UNKNOWN"), (float("inf"), "UNKNOWN"), (float("-inf"), "UNKNOWN"),
        ]
        for field in ("SOILTYPE", "SoilType", "soiltype"):
            for soil, check in cases:
                with self.subTest(field=field, soil=soil):
                    row = assemble_classified_piece("parent", {"MEANAGE": 79, field: soil, "DRAINAGESTATE": "1"},
                        1, {}, self.available_states(), grid_intersections=[{
                            "area_ha": 1, "values": {"soiltype": 10 if check == "MATCH" else 60},
                        }])
                    self.assertEqual(row["check_potential_protected_peatland"], check)
                    for tier in self.tiers[:2]:
                        self.assertEqual(row["classes"][tier], "ECONOMIC")
                    self.assertEqual(row["classes"]["light"],
                                     "UNKNOWN" if check == "UNKNOWN" else "ECONOMIC")
                    expected = {"MATCH": "SENSITIVE", "NO_MATCH": "ECONOMIC", "UNKNOWN": "UNKNOWN"}[check]
                    for tier in self.tiers[3:]:
                        self.assertEqual(row["classes"][tier],
                                         "SENSITIVE" if tier == "superprotection" and check == "NO_MATCH" else expected)
                        self.assertEqual(row["rules"][tier]["source_ids"], ["parent"] if check == "MATCH" else [])
                        self.assertEqual(row["rules"][tier]["unknown_sources"],
                                         ["forest_centre_stand"] if check == "UNKNOWN" else [])

    def test_age_and_peatland_matches_win_over_the_other_unknown_stand_check(self):
        for attributes, criterion, balance in (
                ({"SOILTYPE": "60"}, "potential_protected_peatland", "SENSITIVE"),
                ({"MEANAGE": 81}, "potential_protected_age", "UNKNOWN")):
            with self.subTest(attributes=attributes):
                row = assemble_classified_piece("parent", attributes, 1, {}, self.available_states())
                self.assertEqual(row["classes"]["balance"], balance)
                for tier in ("protection", "superprotection"):
                    self.assertEqual(row["classes"][tier], "SENSITIVE")
                    self.assertEqual(row["rules"][tier]["criteria"], [criterion])
                    self.assertEqual(row["rules"][tier]["source_ids"], ["parent"])

    def test_parent_peatland_watercourse_screen_affects_light_through_superprotection(self):
        for drainage in (7, 8, 9):
            for piece_number in (1, 2):
                with self.subTest(drainage=drainage, piece_number=piece_number):
                    row = assemble_classified_piece("parent", {
                        "MEANAGE": 40, "SOILTYPE": "60", "DRAINAGESTATE": drainage,
                    }, 0.5, {}, self.available_states())
                    self.assertEqual(row["check_parent_peatland_watercourse"], "MATCH")
                    for tier in ("all_out", "bau"):
                        self.assertEqual(row["classes"][tier], "ECONOMIC")
                        self.assertNotIn("parent_peatland_watercourse", row["rules"][tier]["criteria"])
                    for tier in ("light", "balance", "protection", "superprotection"):
                        self.assertEqual(row["classes"][tier], "SENSITIVE")
                        self.assertIn("parent_peatland_watercourse", row["rules"][tier]["criteria"])
                        self.assertEqual(row["rules"][tier]["source_ids"], ["parent"])

    def test_parent_peatland_watercourse_screen_rejects_nonmatching_and_unknown_values(self):
        states = self.available_states()
        for attributes in (
                {"SOILTYPE": 61, "DRAINAGESTATE": 7},
                {"SOILTYPE": 60, "DRAINAGESTATE": 6},
                {"SOILTYPE": 10, "DRAINAGESTATE": 8},
                {"SOILTYPE": 60, "DRAINAGESTATE": 1}):
            with self.subTest(attributes=attributes):
                row = assemble_classified_piece("parent", {"MEANAGE": 40, **attributes}, 1, {}, states)
                self.assertEqual(row["check_parent_peatland_watercourse"], "NO_MATCH")
                for tier in ("all_out", "bau", "light", "balance", "protection"):
                    self.assertNotIn("parent_peatland_watercourse", row["rules"][tier]["criteria"])

        for attributes in (
                {"SOILTYPE": 60, "DRAINAGESTATE": None},
                {"SOILTYPE": None, "DRAINAGESTATE": 7},
                {"SOILTYPE": 60, "DRAINAGESTATE": 12},
                {"SOILTYPE": 999, "DRAINAGESTATE": 7}):
            with self.subTest(attributes=attributes):
                row = assemble_classified_piece("parent", {"MEANAGE": 40, **attributes}, 1, {}, states)
                self.assertEqual(row["check_parent_peatland_watercourse"], "UNKNOWN")

        positive = assemble_classified_piece("parent", {
            "MEANAGE": 40, "SOILTYPE": 60, "DRAINAGESTATE": None,
        }, 1, {"section10": True}, states)
        self.assertEqual(positive["check_parent_peatland_watercourse"], "UNKNOWN")
        self.assertEqual(set(positive["classes"].values()), {"SENSITIVE"})

    def test_stand_natural_state_mire_codes_and_unknowns(self):
        states = self.available_states()
        cases = [(6, "MATCH"), ("6.0", "MATCH")] + [
            (code, "NO_MATCH") for code in (1, 2, 3, 7, 8, 9)
        ] + [
            (None, "UNKNOWN"), ("", "UNKNOWN"), ("bad", "UNKNOWN"),
            (True, "UNKNOWN"), (False, "UNKNOWN"), (6.5, "UNKNOWN"),
            (12, "UNKNOWN"), (float("nan"), "UNKNOWN"), (float("inf"), "UNKNOWN"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                row = assemble_classified_piece("parent", {
                    "MEANAGE": 40, "SOILTYPE": "10", "DRAINAGESTATE": value,
                }, 1, {}, states)
                self.assertEqual(row["check_natural_state_mire"], expected)
                self.assertEqual(row["classes"]["all_out"], "ECONOMIC")
                self.assertEqual(row["classes"]["bau"],
                                 "SENSITIVE" if expected == "MATCH" else
                                 "UNKNOWN" if expected == "UNKNOWN" else "ECONOMIC")
                for tier in ("light", "balance", "protection"):
                    self.assertEqual(row["classes"][tier],
                                     "SENSITIVE" if expected == "MATCH" else
                                     "UNKNOWN" if expected == "UNKNOWN" else "ECONOMIC")
                self.assertEqual(row["classes"]["superprotection"],
                                 "SENSITIVE" if expected in ("MATCH", "NO_MATCH") else "UNKNOWN")
                self.assertEqual(row["rules"]["bau"]["source_ids"], ["parent"] if expected == "MATCH" else [])

    def test_natural_state_mire_positive_wins_over_unknowns_and_preserves_all_out(self):
        row = assemble_classified_piece("parent", {
            "MEANAGE": None, "SOILTYPE": "bad", "DRAINAGESTATE": "6",
        }, 1, {}, self.available_states())
        self.assertEqual(row["check_natural_state_mire"], "MATCH")
        self.assertEqual(row["classes"]["all_out"], "ECONOMIC")
        for tier in ("bau", "light", "balance", "protection", "superprotection"):
            self.assertEqual(row["classes"][tier], "SENSITIVE")
            self.assertIn("natural_state_mire", row["rules"][tier]["criteria"])
            self.assertEqual(row["rules"][tier]["source_ids"], ["parent"])

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
