"""Grid and stand indicators from exact intersected hectares; no QGIS dependencies.

The geometry edge supplies non-overlapping, positive-area intersections. All
coverage areas and numerators are unrounded sufficient statistics. Only age
percentages are rounded, after division, for presentation/storage.
"""

import math
from decimal import Decimal, ROUND_HALF_UP
from numbers import Number


GRID_SOURCE_ID = "forest_centre_gridcell"
STAND_SOURCE_ID = "forest_centre_stand"
AREA_TOLERANCE_HA = 1e-12  # Existing geometry storage tolerance: 1e-8 m2.
GRID_VOLUME_FIELDS = {
    "grid_total_volume_m3_ha": "volume",
    "pine_volume_m3_ha": "volumepine",
    "spruce_volume_m3_ha": "volumespruce",
    "deciduous_volume_m3_ha": "volumedeciduous",
}
AGE_METRICS = ("share_under_20", "share_20_80", "share_over_80")
# Official Metsakeskus grid dictionary, Koodisto rows 27–56. Zero is unknown.
SOIL_CODES = frozenset((10, 11, 12, 20, 21, 22, 23, 24, 30, 31, 32, 40, 50,
                        60, 61, 62, 63, 64, 65, 66, 67, 70, 80))
PEAT_CODES = frozenset(range(60, 68))
DRAINAGE_CODES = frozenset((1, 2, 3, 6, 7, 8, 9))
AREA_METRICS = ("peatland_area_ha", "natural_mire_area_ha")
STAND_VOLUME_FIELDS = {"total_volume_m3_ha": "volume", "sawtimber_volume_m3_ha": "sawlogvolume"}


def whole_percent(value):
    """Round a final percentage to a whole integer, with exact halves up."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _percentage(numerator, denominator):
    # Preserve exact decimal halves even for small hectare fragments: binary
    # 100 * .0001 / .00016 is just below 62.5 and would round the wrong way.
    return float(Decimal(str(numerator)) * 100 / Decimal(str(denominator)))


def _number(value):
    """Accept real finite nonnegative numbers, never booleans or numeric text."""
    if isinstance(value, bool) or not isinstance(value, Number):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def _area(value):
    result = _number(value)
    if result is None:
        raise ValueError("INVALID_INDICATOR_AREA")
    return result


def calculate_stand_indicators(area_ha, values, source_status="AVAILABLE", sawlog_price_eur_m3=None):
    """Retain stand density/rate semantics weighted by actual result-piece area.

    Growth is 100 * annual stand volume growth / standing stand volume; it never
    uses the grid estimate. Field lookup remains case-insensitive for raw stand
    attributes supplied by existing callers.
    """
    area_ha = _area(area_ha)
    values = {str(field).lower(): value for field, value in values.items()}
    coverage = {}
    indicators = {}
    for metric, field in {**STAND_VOLUME_FIELDS, "basal_area_m2_ha": "basalarea",
                          "growth_percent": "volumegrowth"}.items():
        value = _number(values.get(field)) if source_status == "AVAILABLE" else None
        if metric == "growth_percent":
            volume = _number(values.get("volume"))
            value = 100 * value / volume if value is not None and volume is not None and volume > 0 else None
        valid_area = area_ha if value is not None else 0.0
        statistic = "represented_volume_m3" if metric in STAND_VOLUME_FIELDS else "weighted_sum"
        coverage[metric] = _coverage(area_ha, valid_area, STAND_SOURCE_ID,
                                     **{statistic: area_ha * value if value is not None else 0.0})
        indicators[metric] = value if valid_area else None
    sawlogs = _number(values.get("sawlogvolume")) if source_status == "AVAILABLE" else None
    price = _number(sawlog_price_eur_m3)
    eligible = sawlogs is not None and sawlogs > 0 and price is not None and price > 0
    represented = area_ha * sawlogs if eligible else 0.0
    coverage["stumpage_price_eur_m3"] = _coverage(
        area_ha, area_ha if eligible else 0.0, STAND_SOURCE_ID,
        represented_volume_m3=represented,
        weighted_sum=represented * price if eligible else 0.0,
    )
    indicators["stumpage_price_eur_m3"] = price if eligible and area_ha > 0 else None
    return _result(coverage, indicators)


def _code(value, recognized):
    number = _number(value)
    return int(number) if number is not None and number.is_integer() and number in recognized else None


def _coverage(area_ha, valid_area_ha, source_id, **statistics):
    unknown = area_ha - valid_area_ha
    if unknown < -AREA_TOLERANCE_HA:
        raise ValueError("INDICATOR_AREA_EXCEEDS_REPORTING_AREA")
    if abs(unknown) <= AREA_TOLERANCE_HA:
        unknown = 0.0
    status = ("UNKNOWN_FIELD_OR_VALUE" if valid_area_ha <= 0 else
              "PARTIAL" if unknown > 0 else "AVAILABLE")
    return {"source_id": source_id, "status": status,
            "valid_area_ha": valid_area_ha, "unknown_area_ha": unknown,
            **statistics}


def _result(coverage, indicators):
    return {"indicators": indicators,
            "indicator_coverage": coverage}


def calculate_grid_indicators(area_ha, intersections):
    """Calculate grid indicators over a reporting polygon of ``area_ha`` hectares.

    Intersections contain ``area_ha``, normalized lowercase ``values`` and an
    optional cell ``source_id`` for provenance. Source field values are not
    coerced from text. Geometry validity/overlap detection belongs to the edge;
    invalid areas or excessive coverage raise ``ValueError`` before publication.
    """
    area_ha = _area(area_ha)
    intersections = list(intersections)
    parts = [(_area(part["area_ha"]), part.get("values", {}), part.get("source_id"))
             for part in intersections]
    _coverage(area_ha, math.fsum(area for area, _, _ in parts), GRID_SOURCE_ID)
    coverage = {}
    indicators = {}
    for metric, field in GRID_VOLUME_FIELDS.items():
        valid = [(area, _number(values.get(field))) for area, values, _ in parts
                 if area > AREA_TOLERANCE_HA and _number(values.get(field)) is not None]
        valid_area = math.fsum(area for area, _ in valid)
        represented = math.fsum(area * value for area, value in valid)
        coverage[metric] = _coverage(area_ha, valid_area, GRID_SOURCE_ID,
                                     represented_volume_m3=represented)
        indicators[metric] = represented / valid_area if valid_area else None
    valid_age = [(area, _number(values.get("age"))) for area, values, _ in parts
                 if area > AREA_TOLERANCE_HA and _number(values.get("age")) is not None]
    valid_age_area = math.fsum(area for area, _ in valid_age)
    bands = (
        math.fsum(area for area, age in valid_age if age < 20),
        math.fsum(area for area, age in valid_age if 20 <= age <= 80),
        math.fsum(area for area, age in valid_age if age > 80),
    )
    age_coverage = _percentage(valid_age_area, area_ha) if area_ha else None
    for metric, matching in zip(AGE_METRICS, bands):
        coverage[metric] = _coverage(
            area_ha, valid_age_area, GRID_SOURCE_ID, matching_area_ha=matching,
            coverage_percent_exact=age_coverage,
            coverage_percent=whole_percent(age_coverage) if age_coverage is not None else None,
        )
        indicators[metric] = whole_percent(_percentage(matching, valid_age_area)) if valid_age_area else None
    for metric, field, codes, matching_codes in (
        ("peatland_area_ha", "soiltype", SOIL_CODES, PEAT_CODES),
        ("natural_mire_area_ha", "drainagestate", DRAINAGE_CODES, {6}),
    ):
        known = [(area, _code(values.get(field), codes)) for area, values, _ in parts
                 if area > AREA_TOLERANCE_HA and _code(values.get(field), codes) is not None]
        valid_area = math.fsum(area for area, _ in known)
        matching = math.fsum(area for area, code in known if code in matching_codes)
        coverage[metric] = _coverage(area_ha, valid_area, GRID_SOURCE_ID, matching_area_ha=matching)
        indicators[metric] = matching if coverage[metric]["status"] == "AVAILABLE" else None
    return _result(coverage, indicators)


def summarize_indicator_rows(rows):
    """Return flat group metrics recomputed from each piece's sufficient statistics.

    Accept classified rows or flat workbook rows, each with ``area_ha`` and
    ``indicator_coverage``. Missing metric statistics remain unknown; displayed
    polygon means and rounded age percentages are never used as group weights.
    """
    rows = list(rows)
    area_ha = math.fsum(_area(row["area_ha"]) for row in rows)
    source_by_metric = {
        **{metric: GRID_SOURCE_ID for metric in (*GRID_VOLUME_FIELDS, *AGE_METRICS, *AREA_METRICS)},
        **{metric: STAND_SOURCE_ID for metric in (*STAND_VOLUME_FIELDS, "basal_area_m2_ha", "growth_percent")},
    }
    coverage = {}
    indicators = {}
    for metric, source_id in source_by_metric.items():
        parts = [row["indicator_coverage"].get(metric, {}) for row in rows]
        valid_area = math.fsum(_area(part.get("valid_area_ha", 0.0)) for part in parts)
        statistic = ("matching_area_ha" if metric in (*AGE_METRICS, *AREA_METRICS) else
                     "weighted_sum" if metric in ("basal_area_m2_ha", "growth_percent") else
                     "represented_volume_m3")
        numerator = math.fsum(_area(part.get(statistic, 0.0)) for part in parts)
        coverage[metric] = _coverage(area_ha, valid_area, source_id, **{statistic: numerator})
        if metric in AGE_METRICS:
            percent = _percentage(valid_area, area_ha) if area_ha else None
            coverage[metric].update({"coverage_percent_exact": percent,
                                    "coverage_percent": whole_percent(percent) if percent is not None else None})
            indicators[metric] = whole_percent(_percentage(numerator, valid_area)) if valid_area else None
        elif metric in AREA_METRICS:
            indicators[metric] = numerator if coverage[metric]["status"] == "AVAILABLE" else None
        else:
            indicators[metric] = numerator / valid_area if valid_area else None
    price_parts = [row["indicator_coverage"].get("stumpage_price_eur_m3", {}) for row in rows]
    price_area = math.fsum(_area(part.get("valid_area_ha", 0.0)) for part in price_parts)
    price_volume = math.fsum(_area(part.get("represented_volume_m3", 0.0)) for part in price_parts)
    price_sum = math.fsum(_area(part.get("weighted_sum", 0.0)) for part in price_parts)
    coverage["stumpage_price_eur_m3"] = _coverage(
        area_ha, price_area, STAND_SOURCE_ID,
        represented_volume_m3=price_volume, weighted_sum=price_sum,
    )
    indicators["stumpage_price_eur_m3"] = price_sum / price_volume if price_volume else None
    return {"area_ha": area_ha, "feature_count": len(rows), **indicators,
            "indicator_coverage": coverage}
