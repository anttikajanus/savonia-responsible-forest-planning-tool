# Classify stand pieces using six cumulative sensitivity tiers

Status: accepted  
Recorded: 2026-10-26

Keep AOI-clipped stands as parent units, split at relevant sensitivity boundaries, and store all six tier classifications on one result layer. All out, BAU and Light share protected-area and Section 10 criteria; Balance adds programme and groundwater footprints, Protection adds other valuable habitat, and Superprotection includes remaining analyzed forest when required evidence is available. Compared with cell-based outputs or separate scenario geometries, this preserves stand identity and comparable reporting domains while allowing finer indicator sampling. [Calculation rules](../calculations.md#classification).

A criterion overlap must exceed 1 m²; Section 10 codes 1 and 5 promote all pieces of the AOI-clipped parent stand, while other criteria affect overlapping pieces. This is a conservative planning assumption, with no added proximity buffers and no claim of whole-stand legal protection. The 1e-8 m² fragment tolerance is a separate numerical rule; pairwise stand overlaps up to and including 1 m² are retained without trimming. Grid boundaries never split classification geometry. [Geometry policy](../calculations.md#area-and-geometry).

MY zoning, recreation, potential protected sites, peatland sensitivity and water buffers remain excluded; finer indicator evidence does not activate them. Reconsideration requires an explicit scope decision using the [deferred-source questions](../deferred-sources.md).

## Current contract

The decision above retains its recorded context. [CL-01/CL-02](../../specs/classification.md) own current thresholds and tier membership; [geometry](../calculations.md#area-and-geometry) owns numerical tolerances.
