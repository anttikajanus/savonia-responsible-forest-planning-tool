"""Pure forest indicator mapping and weighted-summary helpers."""

import math


# Shared presentation order for result fields, forms and workbook columns/rows.
# IDs remain stable; source names belong in translated presentation labels.
METRIC_GROUPS = (
    ("stand", ("total_volume_m3_ha", "sawtimber_volume_m3_ha", "growth_percent", "basal_area_m2_ha")),
    ("grid_volume", ("grid_total_volume_m3_ha", "pine_volume_m3_ha", "spruce_volume_m3_ha", "deciduous_volume_m3_ha")),
    ("grid_age", ("share_under_20", "share_20_80", "share_over_80")),
    ("grid_area", ("peatland_area_ha", "natural_mire_area_ha")),
    ("unavailable", ("stumpage_price_eur_m3",)),
)
METRIC_FIELDS = tuple(metric for _group, metrics in METRIC_GROUPS for metric in metrics)
STAND_SCHEMA_FIELD_CANDIDATES = frozenset((
    "standid", "area", "basalarea", "proportionpine", "proportionspruce", "proportionother",
    "meanage", "volume", "sawlogvolume", "pulpwoodvolume", "volumegrowth",
))
METRIC_FIELD_MAPS = {
    # The Metsäkeskus 2.1.3 workbook and saved WFS XSD define volume and
    # sawlogvolume in m3/ha, so no stand-area scaling is needed.
    "total_volume_m3_ha": "volume",
    "sawtimber_volume_m3_ha": "sawlogvolume",
    "basal_area_m2_ha": "basalarea",
}
PROPORTION_METRIC_FIELD_MAPS = {
    "pine_volume_m3_ha": {"volume": "volume", "proportion": "proportionpine"},
    "spruce_volume_m3_ha": {"volume": "volume", "proportion": "proportionspruce"},
}
DERIVED_METRIC_FIELD_MAPS = {
    # Dividing annual growth by standing volume gives a per-year rate; multiplying
    # by 100 reports that rate as an annual percentage.
    "growth_percent": {"numerator": "volumegrowth", "denominator": "volume"},
}
AGE_BAND_METRIC_FIELD_MAPS = {
    "share_under_20": {"field": "meanage", "upper": 20, "upper_inclusive": False},
    "share_20_80": {"field": "meanage", "lower": 20, "upper": 80,
                    "lower_inclusive": True, "upper_inclusive": True},
    "share_over_80": {"field": "meanage", "lower": 80, "lower_inclusive": False},
}


def mapped_metric_ids(available_fields):
    """Return metrics whose configured source fields all exist, case-insensitively."""
    available = {str(field).lower() for field in available_fields}
    required_fields = {
        **{metric: (field,) for metric, field in METRIC_FIELD_MAPS.items()},
        **{
            metric: tuple(fields.values())
            for metric, fields in PROPORTION_METRIC_FIELD_MAPS.items()
        },
        **{
            metric: tuple(fields.values())
            for metric, fields in DERIVED_METRIC_FIELD_MAPS.items()
        },
        **{
            metric: (fields["field"],)
            for metric, fields in AGE_BAND_METRIC_FIELD_MAPS.items()
        },
    }
    return sorted(
        metric for metric, fields in required_fields.items()
        if all(field.lower() in available for field in fields)
    )


def _numeric_source_values(field_names, source_status, source_value):
    """Read available numeric source fields and return values or a stable status."""
    if source_status != "AVAILABLE":
        return None, "UNKNOWN_SOURCE_" + str(source_status or "MISSING")
    if not field_names or any(not field_name for field_name in field_names):
        return None, "UNKNOWN_FIELD_OR_VALUE"
    raw_values = [source_value(field_name) for field_name in field_names]
    if any(value is None for value in raw_values):
        return None, "UNKNOWN_FIELD_OR_VALUE"
    try:
        numeric_values = [float(value) for value in raw_values]
    except (TypeError, ValueError):
        return None, "UNKNOWN_NON_NUMERIC"
    if any(not math.isfinite(value) for value in numeric_values):
        return None, "UNKNOWN_NON_FINITE"
    return numeric_values, ""


def indicator_values(source_values, area_ha, mappings, source_status, derived_mappings=None,
                     age_band_mappings=None, proportion_mappings=None):
    """Map verified source fields to output metrics without inventing defaults.

    ``mappings`` maps output metric IDs to source field names. A value is
    available only when the source is AVAILABLE and the mapped field has a
    numeric, non-null value. ``derived_mappings`` maps an output metric to a
    numerator and denominator field; it is used for ratios whose units are
    documented by the source schema. ``age_band_mappings`` maps an output
    metric to an age field and optional inclusive/exclusive bounds; matches
    contribute 100%, while non-matches contribute 0%. The returned status
    identifies missing evidence.
    """
    values = {}
    statuses = {}

    def source_value(field_name):
        if field_name in source_values:
            return source_values[field_name]
        normalized = str(field_name).lower()
        for name, value in source_values.items():
            if str(name).lower() == normalized:
                return value
        return None

    for metric, source_field in mappings.items():
        numeric_values, status = _numeric_source_values(
            (source_field,) if source_field else (), source_status, source_value,
        )
        values[metric] = numeric_values[0] if numeric_values is not None else None
        statuses[metric] = status or "AVAILABLE"
    for metric, fields in (derived_mappings or {}).items():
        numbers, status = _numeric_source_values(
            (fields.get("numerator"), fields.get("denominator")),
            source_status,
            source_value,
        )
        if status:
            values[metric] = None
            statuses[metric] = status
            continue
        numerator, denominator = numbers
        if denominator <= 0:
            values[metric] = None
            statuses[metric] = "UNKNOWN_NON_POSITIVE_DENOMINATOR"
            continue
        values[metric] = numerator / denominator * 100.0
        statuses[metric] = "AVAILABLE"
    for metric, fields in (proportion_mappings or {}).items():
        numbers, status = _numeric_source_values(
            (fields.get("volume"), fields.get("proportion")),
            source_status,
            source_value,
        )
        if status:
            values[metric] = None
            statuses[metric] = status
            continue
        volume, proportion = numbers
        if proportion < 0 or proportion > 100:
            values[metric] = None
            statuses[metric] = "UNKNOWN_PROPORTION_OUT_OF_RANGE"
            continue
        values[metric] = volume * proportion / 100.0
        statuses[metric] = "AVAILABLE"
    for metric, band in (age_band_mappings or {}).items():
        numbers, status = _numeric_source_values(
            (band.get("field"),), source_status, source_value,
        )
        if status:
            values[metric] = None
            statuses[metric] = status
            continue
        age = numbers[0]
        lower = band.get("lower")
        upper = band.get("upper")
        in_band = (
            (lower is None or age > lower or (band.get("lower_inclusive", False) and age == lower))
            and (upper is None or age < upper or (band.get("upper_inclusive", False) and age == upper))
        )
        values[metric] = 100.0 if in_band else 0.0
        statuses[metric] = "AVAILABLE"
    values["area_ha"] = float(area_ha) if area_ha is not None else None
    statuses["area_ha"] = "AVAILABLE" if area_ha is not None else "UNKNOWN_GEOMETRY"
    return values, statuses


def weighted_summary(rows, class_value):
    """Aggregate a class from sufficient statistics when coverage is supplied.

    Coverage-aware rows use each metric's valid hectares and full-precision
    numerators. Legacy rows without coverage retain their earlier area-weighted
    behavior, including the legacy price-weighting result.
    """
    selected = [row for row in rows if row.get("class") == class_value]
    if not selected or any("indicator_coverage" in row for row in selected):
        from .grid_indicators import summarize_indicator_rows
        return summarize_indicator_rows(selected)
    area = sum(float(row.get("area_ha") or 0.0) for row in selected)
    result = {"area_ha": area, "feature_count": len(selected)}
    metrics = (
        "total_volume_m3_ha", "pine_volume_m3_ha", "spruce_volume_m3_ha",
        "sawtimber_volume_m3_ha", "growth_percent",
        "share_under_20", "share_20_80", "share_over_80", "basal_area_m2_ha",
    )
    for metric in metrics:
        valid = [row for row in selected if row.get(metric) is not None and row.get("area_ha") is not None]
        denom = sum(float(row["area_ha"]) for row in valid)
        result[metric] = (
            sum(float(row[metric]) * float(row["area_ha"]) for row in valid) / denom
            if denom > 0 else None
        )
    price_rows = [row for row in selected if row.get("stumpage_price_eur_m3") is not None]
    volume_rows = [row for row in price_rows if row.get("total_volume_m3_ha") is not None and row.get("area_ha") is not None]
    weighted_volume = sum(float(r["total_volume_m3_ha"]) * float(r["area_ha"]) for r in volume_rows)
    if weighted_volume > 0:
        result["stumpage_price_eur_m3"] = sum(
            float(r["stumpage_price_eur_m3"]) * float(r["total_volume_m3_ha"]) * float(r["area_ha"])
            for r in volume_rows
        ) / weighted_volume
        result["stumpage_price_weighting"] = "volume_weighted"
    else:
        denom = sum(float(r.get("area_ha") or 0.0) for r in price_rows)
        result["stumpage_price_eur_m3"] = (
            sum(float(r["stumpage_price_eur_m3"]) * float(r.get("area_ha") or 0.0) for r in price_rows) / denom
            if denom > 0 else None
        )
        result["stumpage_price_weighting"] = "area_weighted_fallback" if denom > 0 else "unavailable"
    return result
