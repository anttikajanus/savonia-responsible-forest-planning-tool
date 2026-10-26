"""Pure source schema readiness and interpretation regressions (no QGIS)."""

from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])))

from savonia_responsible_forest_planning_tool.analysis.classification import (
    classify_tiers, interpret_sources,
)
from savonia_responsible_forest_planning_tool.analysis.source_readiness import (
    PROTECTED_SOURCE_IDS, assess_source_schema, normalize_source_attributes,
)


def record(service_id, attributes, source_id="feature-1"):
    readiness = assess_source_schema(service_id, attributes)
    assert readiness["status"] == "AVAILABLE", readiness
    return {
        "service_id": service_id, "source_id": source_id, "geometry": object(),
        "attributes": attributes,
        "values": normalize_source_attributes(attributes, readiness["field_map"]),
    }


class SourceFieldsTest(unittest.TestCase):
    def test_protected_sources_resolve_their_own_aliases(self):
        attributes = (
            {"extra": "kept", "TYYPPILYHENNE": "VSA", "OLOTILA": "Voimassa"},
            {"KohdeTyyppi": "YSA", "Olotila": "Voimassa"},
            {"olotila": "Voimassa", "kohdetyyppi": "EMA"},
        )
        records = {
            source: [record(source, attrs, "same-id")]
            for source, attrs in zip(PROTECTED_SOURCE_IDS, attributes)
        }
        criteria, _, diagnostics = interpret_sources(records, {})
        self.assertEqual({item["service_id"] for item in criteria}, set(PROTECTED_SOURCE_IDS))
        self.assertTrue(all(item["criterion"] == "protected" for item in criteria))
        for source, attrs, category in zip(PROTECTED_SOURCE_IDS, attributes, ("VSA", "YSA", "EMA")):
            self.assertEqual(diagnostics[source], {"observed_category_counts": {category: 1}})
            self.assertEqual(records[source][0]["attributes"], attrs)
        self.assertEqual(criteria[0]["attributes"]["extra"], "kept")

    def test_alias_priority_is_not_field_order_or_value_fallback(self):
        source = PROTECTED_SOURCE_IDS[1]
        for attributes in (
            {"kohdetyyppi": "YSA", "olotila": "Voimassa", "tyyppilyhenne": None},
            {"tyyppilyhenne": None, "olotila": "Voimassa", "kohdetyyppi": "YSA"},
        ):
            with self.subTest(attributes=attributes):
                criteria, _, diagnostics = interpret_sources({source: [record(source, attributes)]}, {})
                self.assertEqual(criteria, [])
                self.assertEqual(diagnostics[source]["reason_code"], "UNRECOGNIZED_PROTECTED_VALUES")
                self.assertIsNone(diagnostics[source]["unrecognized_records"][0]["category"])

    def test_habitat_and_programme_casing_and_original_attributes(self):
        habitat = "forest_centre_habitat"
        programme = "syke_nature_conservation_programme_areas"
        sources = {
            habitat: [record(habitat, {"HabitatType": "5"})],
            programme: [record(programme, {"LsoAlueTunnus": "P1", "Luokka": "AMO", "Subtype": "original"})],
        }
        criteria, _, diagnostics = interpret_sources(sources, {})
        self.assertEqual([item["criterion"] for item in criteria], ["section10", "programme"])
        self.assertEqual(criteria[1]["attributes"]["Subtype"], "original")
        self.assertFalse(any(row.get("reason_code") for row in diagnostics.values()))

    def test_missing_fields_and_unknown_sources_fail_readiness(self):
        for fields in ([], None, ["extra", "olotila"]):
            with self.subTest(fields=fields):
                result = assess_source_schema(PROTECTED_SOURCE_IDS[0], fields)
                self.assertEqual(result["reason_code"], "REQUIRED_FIELDS_MISSING")
                self.assertIn("tyyppilyhenne or kohdetyyppi", result["missing_fields"])
        self.assertEqual(assess_source_schema("unknown", ["olotila"])["reason_code"], "SOURCE_CONTRACT_MISSING")

    def test_empty_groundwater_schema_is_ready(self):
        result = assess_source_schema("syke_groundwater_areas", [])
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(normalize_source_attributes({"alueluokka": "any"}, result["field_map"]), {})

    def test_unknown_values_belong_to_actual_source(self):
        source = PROTECTED_SOURCE_IDS[1]
        item = record(source, {"olotila": "unrecognized", "kohdetyyppi": "YSA"})
        criteria, _, diagnostics = interpret_sources({source: [item]}, {})
        self.assertEqual(criteria, [])
        self.assertEqual(diagnostics[source]["reason_code"], "UNRECOGNIZED_PROTECTED_VALUES")
        self.assertNotIn("reason_code", diagnostics[PROTECTED_SOURCE_IDS[0]])
        classes, _ = classify_tiers({}, {})
        self.assertEqual(set(classes.values()), {"UNKNOWN"})


if __name__ == "__main__":
    unittest.main()
