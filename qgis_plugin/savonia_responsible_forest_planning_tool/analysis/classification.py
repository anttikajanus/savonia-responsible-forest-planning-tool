"""Pure forest evidence interpretation and sensitivity-tier rules."""

import math
from numbers import Number

from .grid_indicators import calculate_grid_indicators, calculate_stand_indicators
from .source_readiness import PROTECTED_SOURCE_IDS

TIERS = (
    ("all_out", "All out"),
    ("bau", "BAU"),
    ("light", "Light"),
    ("balance", "Balance"),
    ("protection", "Protection"),
    ("superprotection", "Superprotection"),
)
CLASS_FIELDS = tuple("class_" + tier for tier, _label in TIERS)
CLASS_CODES = ("SENSITIVE", "ECONOMIC", "UNKNOWN")
CRITERION_FIELDS = (
    ("check_protected", "active_protected", "syke_protected_areas"),
    ("check_section10", "section10", "forest_centre_habitat"),
    ("check_programme", "programme_area", "syke_nature_conservation_programme_areas"),
    ("check_groundwater", "groundwater_area", "syke_groundwater_areas"),
    ("check_other_habitat", "other_valuable_habitat", "forest_centre_habitat"),
    ("check_potential_protected_age", "potential_protected_age", "forest_centre_stand"),
    ("check_riparian_buffer", "riparian_buffer", "syke_rantaviiva_water_buffers"),
)
SOURCE_STATES = ("AVAILABLE", "NOT_AVAILABLE", "OUT_OF_SCOPE")

# Accept broad and subtype codes because SYKE layers can return either form
# (for example, KPU for a national park).
PROTECTED_CATEGORIES = frozenset((
    "VSA", "YSA", "EMA", "MRA", "LTA", "ERA",
    "ESA", "HYL", "KPU", "KPM", "LHA", "LPU", "MHA", "SSA", "VMA",
    "ELD", "ERM", "UTL",
))
PROGRAMME_CLASS_CODES = frozenset(("AMO", "HSO", "LHO", "LVO", "MAO", "PMO", "KLO", "RSO", "SSO"))


def _status(value):
    return " ".join(str(value or "").strip().lower().split())


def potential_protection_by_age(stand_attributes, source_status):
    """Return a stand-wide age match, or None when MEANAGE is unusable."""
    values = {str(field).lower(): value for field, value in stand_attributes.items()}
    value = values.get("meanage")
    if source_status != "AVAILABLE" or isinstance(value, bool) or not isinstance(value, Number):
        return None
    try:
        age = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return age > 80 if math.isfinite(age) and age >= 0 else None


def interpret_sources(source_features, source_states):
    """Interpret normalized source records without importing QGIS or translating text.

    Source feature geometries are carried through as opaque values for the
    spatial workflow. The returned diagnostics contain stable reason codes
    and data for the QGIS edge to localize.
    """
    criteria = []
    states = dict(source_states)
    diagnostics = {}
    # An unfamiliar code is not evidence of absence; surface it for review
    # rather than silently increasing the area classified as non-sensitive.

    for protected_id in PROTECTED_SOURCE_IDS:
        protected_counts = {}
        protected_unknown = []
        for feature in source_features.get(protected_id, ()):
            values = feature["values"]
            status = _status(values.get("olotila"))
            category = str(values.get("tyyppilyhenne") or "").strip().upper()
            key = category or "UNKNOWN"
            protected_counts[key] = protected_counts.get(key, 0) + 1
            if status == "voimassa" and category in PROTECTED_CATEGORIES:
                criteria.append({
                    "criterion": "protected", "geometry": feature["geometry"],
                    "service_id": feature["service_id"],
                    "source_id": feature["source_id"], "attributes": feature["attributes"],
                })
            else:
                protected_unknown.append({
                    "source_id": feature["source_id"],
                    "status": values.get("olotila"),
                    "category": values.get("tyyppilyhenne"),
                })
        diagnostics[protected_id] = {"observed_category_counts": protected_counts}
        if protected_unknown:
            diagnostics[protected_id].update({
                "reason_code": "UNRECOGNIZED_PROTECTED_VALUES",
                "unrecognized_records": protected_unknown[:100],
            })

    habitat_id = "forest_centre_habitat"
    habitat_types = {"1": "section10", "3": "other_habitat", "5": "section10"}
    habitat_counts = {}
    habitat_unknown = []
    for feature in source_features.get(habitat_id, ()):
        attrs = feature["attributes"]
        value = feature["values"].get("habitattype")
        code = str(value).strip() if value is not None else ""
        key = code or "UNKNOWN"
        habitat_counts[key] = habitat_counts.get(key, 0) + 1
        criterion = habitat_types.get(code)
        if criterion is None:
            habitat_unknown.append(feature["source_id"])
            continue
        criteria.append({
            "criterion": criterion, "geometry": feature["geometry"],
            "service_id": feature["service_id"],
            "source_id": feature["source_id"], "attributes": attrs,
        })
    diagnostics[habitat_id] = {
        "observed_habitat_type_counts": habitat_counts,
        "unrecognized_feature_ids": habitat_unknown[:100],
    }
    if habitat_unknown:
        diagnostics[habitat_id]["reason_code"] = "UNRECOGNIZED_HABITAT_VALUES"

    programme_id = "syke_nature_conservation_programme_areas"
    programme_counts = {}
    programme_unknown = []
    for feature in source_features.get(programme_id, ()):
        attrs = feature["attributes"]
        values = feature["values"]
        programme_class = str(values.get("luokka") or "").strip().upper()
        key = programme_class or "UNKNOWN"
        programme_counts[key] = programme_counts.get(key, 0) + 1
        source_identifier = str(values.get("lsoaluetunnus") or "").strip()
        if not source_identifier or programme_class not in PROGRAMME_CLASS_CODES:
            programme_unknown.append(feature["source_id"])
        if programme_class not in PROGRAMME_CLASS_CODES:
            continue
        criteria.append({
            "criterion": "programme", "geometry": feature["geometry"],
            "service_id": feature["service_id"],
            "source_id": feature["source_id"], "attributes": attrs,
        })
    diagnostics[programme_id] = {
        "observed_programme_class_counts": programme_counts,
        "unrecognized_feature_ids": programme_unknown[:100],
    }
    if programme_unknown:
        diagnostics[programme_id]["reason_code"] = "UNRECOGNIZED_PROGRAMME_VALUES"

    groundwater_id = "syke_groundwater_areas"
    for feature in source_features.get(groundwater_id, ()):
        criteria.append({
            "criterion": "groundwater", "geometry": feature["geometry"],
            "service_id": feature["service_id"],
            "source_id": feature["source_id"], "attributes": feature["attributes"],
        })
    diagnostics[groundwater_id] = {
        "observed_feature_count": len(source_features.get(groundwater_id, ())),
    }

    return criteria, states, diagnostics


def classify_tiers(evidence, source_states):
    """Return each tier class and matched source IDs.

    A recognized positive trigger is sufficient evidence for a sensitive
    classification, even if another source is missing. Without a trigger,
    missing sources leave the result UNKNOWN rather than implying no sensitivity.
    """
    source_ids = evidence.get("source_ids", {})
    triggers = {
        "protected": bool(evidence.get("active_protected")),
        "section10": bool(evidence.get("section10")),
        "programme": bool(evidence.get("programme_area")),
        "groundwater": bool(evidence.get("groundwater_area")),
        "riparian_buffer": bool(evidence.get("riparian_buffer")),
        "other_habitat": bool(evidence.get("other_valuable_habitat")),
        "potential_protected_age": evidence.get("potential_protected_age"),
    }
    tier_criteria = {
        "all_out": ("protected", "section10"),
        "bau": ("protected", "section10"),
        "light": ("protected", "section10"),
        "balance": ("protected", "section10", "programme", "groundwater", "riparian_buffer"),
        "protection": ("protected", "section10", "programme", "groundwater", "riparian_buffer", "other_habitat", "potential_protected_age"),
        "superprotection": ("protected", "section10", "programme", "groundwater", "riparian_buffer", "other_habitat", "potential_protected_age"),
    }
    dependencies = {
        "protected": ("syke_protected_areas",),
        "section10": ("forest_centre_habitat",),
        "programme": ("syke_nature_conservation_programme_areas",),
        "groundwater": ("syke_groundwater_areas",),
        "riparian_buffer": ("syke_rantaviiva_water_buffers",),
        "other_habitat": ("forest_centre_habitat",),
        "potential_protected_age": ("forest_centre_stand",),
    }
    classes = {}
    rules = {}
    for tier, _label in TIERS:
        criteria = tier_criteria[tier]
        matched = [criterion for criterion in criteria if triggers[criterion]]
        if matched:
            classes[tier] = "SENSITIVE"
            rules[tier] = {
                "criteria": matched,
                "source_ids": sorted({
                    str(identifier)
                    for criterion in matched
                    for identifier in source_ids.get(criterion, ())
                    if identifier is not None
                }),
            }
            continue

        required_sources = {
            source_id
            for criterion in criteria
            for source_id in dependencies[criterion]
        }
        unknown_values = {
            source_id for criterion in criteria if triggers[criterion] is None
            for source_id in dependencies[criterion]
        }
        unknown_sources = sorted(
            source_id for source_id in required_sources
            if source_states.get(source_id) != "AVAILABLE" or source_id in unknown_values
        )
        if unknown_sources:
            classes[tier] = "UNKNOWN"
            rules[tier] = {"criteria": [], "source_ids": [], "unknown_sources": unknown_sources}
        elif tier == "superprotection":
            # With complete source coverage, this tier treats analyzed forest
            # outside the more specific triggers as sensitive by definition.
            classes[tier] = "SENSITIVE"
            rules[tier] = {"criteria": ["remaining_analyzed_forest"], "source_ids": []}
        else:
            classes[tier] = "ECONOMIC"
            rules[tier] = {"criteria": [], "source_ids": []}
    return classes, rules


def assemble_classified_piece(stand_id, stand_attributes, area_ha, evidence, source_states,
                              grid_intersections=None, sawlog_price_eur_m3=None):
    """Turn normalized piece evidence into a complete, QGIS-independent result row."""
    age_match = potential_protection_by_age(
        stand_attributes, source_states.get("forest_centre_stand"),
    )
    evidence = {**evidence, "potential_protected_age": age_match,
                "source_ids": {**evidence.get("source_ids", {}),
                               "potential_protected_age": [stand_id] if age_match else []}}
    classes, rules = classify_tiers(evidence, source_states)
    for tier in rules:
        rules[tier]["unknown_sources"] = rules[tier].get("unknown_sources", [])

    stand = calculate_stand_indicators(
        area_ha, stand_attributes, source_states.get("forest_centre_stand", "NOT_AVAILABLE"),
        sawlog_price_eur_m3=sawlog_price_eur_m3,
    )
    grid = calculate_grid_indicators(area_ha, grid_intersections or ())
    values = {**stand["indicators"], **grid["indicators"], "area_ha": area_ha}

    normalized_source_ids = {
        key: sorted(set(identifiers))
        for key, identifiers in evidence.get("source_ids", {}).items()
    }
    return {
        "source_stand_id": stand_id,
        **{field: "MATCH" if evidence.get(evidence_key) else
           "NO_MATCH" if source_states.get(source_id) == "AVAILABLE"
           and evidence.get(evidence_key, False) is not None else "UNKNOWN"
           for field, evidence_key, source_id in CRITERION_FIELDS},
        "classes": classes,
        "rules": rules,
        "source_ids": normalized_source_ids,
        "indicators": values,
        "indicator_coverage": {**stand["indicator_coverage"], **grid["indicator_coverage"]},
        "area_ha": area_ha,
        "section10_stand_promoted": evidence.get("section10_stand_promoted"),
        "programme_info": list(evidence.get("programme_info", ())),
        "programme_protected_overlap": evidence.get("programme_protected_overlap"),
    }
