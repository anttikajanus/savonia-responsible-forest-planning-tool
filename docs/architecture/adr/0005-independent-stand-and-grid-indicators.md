# Retain independent stand and grid indicators on stand-based results

Status: accepted  
Recorded: 2026-10-26

Grid WFS supplies spatially finer species, age, soil and drainage evidence but lacks stand sawlog and annual-growth fields. Retain stand total volume, sawtimber, derived growth and optional basal area, and add independent grid total/species volumes, age-area shares and peat/mire areas using exact polygon intersections. Neither total replaces or combines with the other, and each metric retains its own valid-area denominator. This avoids discarding useful stand information or inferring species from ambiguous stand proportions, while accepting that independent source means may disagree. [Indicator design](../indicators.md).

Use area-weighted means of per-stand growth percentages; dividing summed growth by summed stock would define a different indicator. Grid deciduous volume is broader than birch, and birch-specific volume is absent from outputs. Peat/mire indicators cover analyzed forest only and do not become sensitivity criteria. [Fields and summary rules](../indicator-calculations.md).

## Analysis-unit rationale

Clarified: 2026-11-01

Use forest stands (kuviot) as the basis of analysis rather than inventory grid
cells (hilat). A grid-based analysis was an alternative, but the selected
Suomen Metsäkeskus grid data does not provide all the values available in the
stand data, including sawlog volume and annual growth. Reproducing the provider's
complex calculations or methods to derive those missing values from grid data
would add unnecessary implementation and validation work to the prototype.

Distributing stand values to grid cells would not provide sufficiently accurate
cell-level estimates: a stand-level value does not describe how that attribute
varies within the stand. An area-based allocation would assume a uniform
within-stand distribution rather than establish it from evidence. The prototype
therefore does not derive missing grid attributes from stand estimates.

Retain the provider's stand attributes on stand-based results, splitting stands
only at the analysis-area and relevant sensitivity boundaries as decided in
[ADR-0004](0004-stand-based-sensitivity-classification.md). Grid data remains
useful as independent indicator evidence, weighted by its actual intersections
with each result piece; grid boundaries do not define the analysis units.
This preserves the existing stand/grid design and its
[allocation and accuracy limits](../indicators.md#area-weighted-evidence).
