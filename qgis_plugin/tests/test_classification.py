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

from savonia_responsible_forest_planning_tool.analysis.classification import classify_tiers, interpret_sources


class ClassificationTests(unittest.TestCase):
    tiers = ("all_out", "bau", "light", "balance", "protection", "superprotection")
    sources = ("syke_protected_areas", "forest_centre_habitat",
               "syke_nature_conservation_programme_areas", "syke_groundwater_areas")

    def test_all_trigger_combinations_have_cumulative_classes_and_exact_rules(self):
        # Expected membership comes from CL-02, independently of implementation constants.
        triggers = (("active_protected", "protected", 0), ("section10", "section10", 0),
                    ("programme_area", "programme", 3), ("groundwater_area", "groundwater", 3),
                    ("other_valuable_habitat", "other_habitat", 4))
        states = dict.fromkeys(self.sources, "AVAILABLE")
        for enabled in itertools.product((False, True), repeat=5):
            evidence = {field: value for (field, _, _), value in zip(triggers, enabled)}
            evidence["source_ids"] = {criterion: ["b-" + criterion, "a-" + criterion,
                                                   "a-" + criterion, None]
                                      for _, criterion, _ in triggers}
            before = copy.deepcopy(evidence)
            classes, rules = classify_tiers(evidence, states)
            with self.subTest(enabled=enabled):
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
        for source, first_tier in zip(self.sources, (0, 0, 3, 3)):
            for state in (None, "NOT_AVAILABLE", "OUT_OF_SCOPE"):
                states = dict.fromkeys(self.sources, "AVAILABLE")
                if state is None:
                    del states[source]
                else:
                    states[source] = state
                with self.subTest(source=source, state=state):
                    classes, rules = classify_tiers({}, states)
                    for index, tier in enumerate(self.tiers):
                        self.assertEqual(classes[tier], "UNKNOWN" if index >= first_tier else "ECONOMIC")
                        if index >= first_tier:
                            self.assertEqual(rules[tier]["unknown_sources"], [source])
                    classes, rules = classify_tiers({"section10": True,
                        "source_ids": {"section10": ["habitat-1"]}}, states)
                    self.assertEqual(set(classes.values()), {"SENSITIVE"})
                    self.assertTrue(all(rule["source_ids"] == ["habitat-1"] for rule in rules.values()))

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
