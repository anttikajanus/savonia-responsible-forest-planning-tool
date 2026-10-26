"""Reporting precision applied only after analysis and aggregation."""

from decimal import Decimal, ROUND_HALF_UP

from ..analysis.grid_indicators import AREA_METRICS, GRID_VOLUME_FIELDS, STAND_VOLUME_FIELDS


RESULT_DECIMALS = {
    **dict.fromkeys((*GRID_VOLUME_FIELDS, *STAND_VOLUME_FIELDS), 0),
    **dict.fromkeys((*AREA_METRICS, "area_ha"), 2),
}


def published_value(metric, value):
    """Round result fields half up, preserving nulls and unrelated metrics."""
    decimals = RESULT_DECIMALS.get(metric)
    if value is None or decimals is None:
        return value
    rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return int(rounded) if decimals == 0 else float(rounded)
