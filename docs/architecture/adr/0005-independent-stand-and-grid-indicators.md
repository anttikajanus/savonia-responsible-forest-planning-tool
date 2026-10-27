# Retain independent stand and grid indicators on stand-based results

Status: accepted  
Recorded: 2026-10-26

Grid WFS supplies spatially finer species, age, soil and drainage evidence but lacks stand sawlog and annual-growth fields. Retain stand total volume, sawtimber, derived growth and optional basal area, and add independent grid total/species volumes, age-area shares and peat/mire areas using exact polygon intersections. Neither total replaces or combines with the other, and each metric retains its own valid-area denominator. This avoids discarding useful stand information or inferring species from ambiguous stand proportions, while accepting that independent source means may disagree. [Indicator design](../indicators.md).

Use area-weighted means of per-stand growth percentages; dividing summed growth by summed stock would define a different indicator. Grid deciduous volume is broader than birch, and birch-specific volume is absent from outputs. Peat/mire indicators cover analyzed forest only and do not become sensitivity criteria. [Fields and summary rules](../indicator-calculations.md).
