<a id="classification-and-indicator-semantics"></a>

# Geometry and classification contracts

This reference owns geometry mechanics, numerical tolerances and classification
evaluation. Observable planning rules belong to the
[classification requirements](../specs/classification.md); accepted inputs belong to
[source-layer requirements](source-layer-requirements.md).

For related contracts, use [indicator calculations](indicator-calculations.md),
[output schema](output-schema.md), [execution path](overview.md#one-execution-path)
and [provider evidence](data-sources.md). Decision rationale is in
[ADR-0004](adr/0004-stand-based-sensitivity-classification.md).

## Area and geometry

The workflow accepts one polygon layer as the analysis area (AOI), using all
features or only selected features. Empty or invalid AOI geometry stops the
run. AOI and source geometries are transformed to EPSG:3067. Source polygons
are clipped to the AOI and the stand result polygons are split by the
boundaries of recognized sensitivity criteria. Invalid source polygon geometries
are repaired with QGIS `makeValid()` when that produces valid polygon components;
repairs are counted and reported with a capped sample of source IDs, using
provider feature IDs when a stable source ID is absent. Original sources are
never edited. AOI intersections are normalized to valid multipolygons; line
and point remnants from boundary-only contacts are excluded. Null, empty, unrepairable, or failed transformed
and clipped geometries stop the run. Area in hectares is planar EPSG:3067 geometry area divided by 10,000. The adopted Ranta10 criterion is the explicit buffer exception: line rivers and polygon rivers/lakes are buffered by 30 m in EPSG:3067 before final AOI clipping. Polygon buffers include the source water polygon; line buffers extend on both sides. The footprints are combined across all three source products, unioned and clipped to the AOI, so overlapping buffered ground is counted once. Only positive-area clipped polygon evidence is retained; boundary-only contact contributes no match.

Ordinary source candidates that do not overlap the AOI are counted and excluded. Ranta10 candidates use the expanded retrieval extent; only after buffering are they clipped to the AOI, so water source geometry outside the AOI can contribute to its derived evidence. Overlapping AOI features are
dissolved. Stand overlaps follow the warning policy in
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry).
Every stand overlap above `1e-8` m² is retained without trimming, with no maximum
accepted overlap. It may contribute to both stands' areas and indicators. Flag
every derived piece of either parent, regardless of the individual piece's
location. Technical logs retain pair evidence and an aggregate completion warning
discloses possible duplicate contributions. Pairwise areas must not be summed
as unique ground area.
[ADR-0013](adr/0013-nonfatal-stand-overlaps.md) records the adopted overlap policy.
Identical
repeated grid IDs/records are deduplicated; conflicting records of one ID or
overlaps between distinct cells stop publication. Shared edges are allowed.
Mapped area criteria match only when their overlap with a result piece is
strictly greater than 1 m² in EPSG:3067. Equal or smaller overlaps and shared
edges/points do not match. Section 10 applies the same hit threshold before its
stand-wide promotion. Other mapped criteria affect the overlapping output
pieces. The threshold avoids tiny edge discrepancies between source datasets.
The separate `1e-8` m² output-geometry
tolerance only discards negligible fragments when retaining split polygons; it
does not determine whether a criterion hit occurs. Clipped numerical fragments
at or below this tolerance are excluded.

After criterion overlays, disconnected polygon components are considered
individually, including stands with no matching criteria. Before sampling grid
evidence, exclude final result polygons whose unrounded planar area is at most
`0.01` m². Measure after translating EPSG:3067 coordinates near the origin,
as for indicator reporting areas. This reporting filter is independent of both
the overlay tolerance and the criterion-hit threshold. It does not filter grid
intersections or source snapshots, and it does not use rounded hectare fields.
Retained rows alone supply classifications, indicators and workbook summaries.
Technical logs retain excluded parent IDs and areas, with aggregate count and
area in bilingual feedback and durable run metadata. An all-excluded run fails
before publication under the existing no-stands policy.

## Classification

The [output schema](output-schema.md#classification-fields-and-values) owns the
six stored tier fields, class-code meanings and reason-code dictionary so that
output recipients can interpret the GeoPackage from one reference. Normalized
input values belong to the
[source contract](source-layer-requirements.md#accepted-classification-values).

### Sensitivity criteria by tier

The matrix summarizes which criteria affect each tier.
[CL-02](../specs/classification.md#cl-02-six-cumulative-tiers) owns tier
membership; [CL-03](../specs/classification.md#cl-03-classes-and-evidence-policy)
owns class and evidence behavior. Stored fields and reason codes are defined in
the [output schema](output-schema.md#classification-fields-and-values).

| Criterion | All out | BAU | Light | Balance | Protection | Superprotection |
| --- | --- | --- | --- | --- | --- | --- |
| Recognized active protected area | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Section 10 habitat | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Nature conservation programme area | — | — | — | ✓ | ✓ | ✓ |
| Groundwater area | — | — | — | ✓ | ✓ | ✓ |
| Ranta10 riparian buffer | — | — | — | ✓ | ✓ | ✓ |
| Parent-stand peatland screen | — | — | — | ✓ | ✓ | ✓ |
| Other valuable habitat | — | — | — | — | ✓ | ✓ |
| Parent-stand age screen | — | — | — | — | ✓ | ✓ |
| Remaining analyzed forest | — | — | — | — | — | ✓ |

`✓` indicates that a criterion can affect the tier's class.

In every tier, a positive match to any included criterion makes the result `SENSITIVE`. Without a positive match, the piece is `ECONOMIC` only when all evidence required for that tier's no-hit decision is available; otherwise it is `UNKNOWN`.

### Class result and evidence

Evaluation is independent for each output piece, and a positive match takes
precedence over unavailable evidence. The pure policy's no-hit and unknown
behavior is defined in [CL-03](../specs/classification.md#cl-03-classes-and-evidence-policy).
The workflow's source-readiness, failure, and publication behavior is defined in
[WF-03](../specs/workflow.md#wf-03-source-readiness-and-retrieval) and
[WF-07](../specs/workflow.md#wf-07-failure-cancellation-and-observability).
Indicator missingness is defined in
[IO-03](../specs/indicators-and-outputs.md#io-03-unavailable-and-partial-values).

The required evidence for a no-hit decision is defined in
[CL-03](../specs/classification.md#cl-03-classes-and-evidence-policy).
The implementation evaluates that policy using the normalized source inputs
defined by [source-layer requirements](source-layer-requirements.md#accepted-classification-values).

<a id="no-hit-evidence"></a>
See the [required evidence table in CL-03](../specs/classification.md#cl-03-classes-and-evidence-policy).

### Stand age screen

The stand-age criterion consumes case-insensitive stand `MEANAGE` in years.
The cutoff and tier membership are owned by
[CL-02](../specs/classification.md#cl-02-six-cumulative-tiers); missing-value
behavior is owned by [CL-03](../specs/classification.md#cl-03-classes-and-evidence-policy).
Provider value acceptance is owned by the
[source contract](source-layer-requirements.md#accepted-classification-values).
Stand criteria inherit the parent stand's interpretation; see
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry) for
their spatial effect.

### Stand peatland screen

The stand peatland screen consumes `SOILTYPE` from `forest_centre_stand`.
The matching codes and tier membership are owned by
[CL-02](../specs/classification.md#cl-02-six-cumulative-tiers); missing-value
behavior is owned by [CL-03](../specs/classification.md#cl-03-classes-and-evidence-policy).
Provider value acceptance is owned by the
[source contract](source-layer-requirements.md#accepted-classification-values).
Stand criteria inherit the parent stand's interpretation; see
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry) for
their spatial effect.

The [input contract](source-layer-requirements.md#accepted-classification-values)
owns accepted statuses, categories, habitat codes and programme identifiers.
Classification consumes their normalized criteria. Optional subtype and original
programme context remain available for the
[output fields](output-schema.md#outputs-and-coverage).

Section 10 stand promotion follows
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry); it is a
planning assumption, distinct from a legal determination. Provider definitions
and their limits remain in [source evidence](data-sources.md#interpretation-and-geographic-limits).

Provenance is local to each result piece: matching one piece must not alter
sibling source identifiers. Section 10 stand-wide promotion is the explicit
exception. Output identifiers are sorted and unique.
