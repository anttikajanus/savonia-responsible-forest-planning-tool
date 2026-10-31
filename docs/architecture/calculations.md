<a id="classification-and-indicator-semantics"></a>

# Geometry and classification contracts

This reference owns geometry mechanics, numerical tolerances and classification
evaluation. Observable planning rules belong to
[CL-01–CL-04](../specs/classification.md); accepted inputs belong to
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
[ADR-0013](adr/0013-nonfatal-stand-overlaps.md) supersedes the previous limit.
Identical
repeated grid IDs/records are deduplicated; conflicting records of one ID or
overlaps between distinct cells stop publication. Shared edges are allowed.
Apply the direct-hit threshold in
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry).
A shared boundary or point has no hit area. Protected areas, programme
areas, and other valuable habitats mark only the overlapping output piece(s).
Section 10 uses the same overlap threshold, then promotes every output piece
from the original stand. The hit threshold avoids tiny edge discrepancies
between source datasets. The separate `1e-8` m² output-geometry
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
output recipients can interpret the GeoPackage from one reference. Unrecognized
returned protected, habitat and programme classification inputs stop the run;
invalid individual stand ages follow the explicit unknown policy below.

The cumulative criteria are evaluated independently for each output piece. A
recognized positive match makes the tier `SENSITIVE`, even if another required
source is unavailable. Without a positive match, all sources required by that
tier must be `AVAILABLE` before a no-hit can be `ECONOMIC`; otherwise the result
is `UNKNOWN`. A successful source request with no AOI-clipped features is still
marked `AVAILABLE`, so an empty response currently permits a no-hit
classification. Feature counts describe returned data and do not establish
complete service coverage.

These dependency rules describe the pure classification policy. The application
workflow requires all eleven sources and stops before publication on a required
source or fatal interpretation failure; it does not publish a partial-source run
using these `UNKNOWN` rules. Missing numeric indicator evidence can still produce
partial or unknown metrics in a successful run. Missing/invalid individual stand
ages can produce unknown classifications under CL-03 without a source failure.

The criterion membership is defined in
[CL-02](../specs/classification.md#cl-02-six-cumulative-tiers). The
[tier-to-field table](output-schema.md#classification-fields-and-values) maps
those tiers to machine fields. Required source groups for a no-hit decision are:

| Tiers | Required source groups |
| --- | --- |
| All out, BAU, Light | Protected + Habitat |
| Balance | Protected + Habitat + Programme + Groundwater + Ranta10 water buffers + valid stand soil code |
| Protection, Superprotection | Protected + Habitat + Programme + Groundwater + Ranta10 water buffers + valid stand mean age and soil code |

Protected combines the three required protected-area products in the
[source inventory](data-sources.md#required-sources). Habitat, Programme and
Groundwater refer to their semantic source groups, not display-layer names.
Excluded criteria follow [CL-04](../specs/classification.md#cl-04-exclusions-and-interpretation).

The stand-age criterion consumes case-insensitive stand `MEANAGE` in years.
Finite nonnegative numeric values are valid; booleans and numeric text are not.
The unrounded value must be strictly greater than 80. Every piece of that
parent stand inherits the match and stand ID under `potential_protected_age`,
without a geometry split or overlap threshold. Missing/invalid individual
ages leave this criterion unknown even when Stand is available. Without any
positive trigger, Protection and Superprotection are `UNKNOWN`, identifying
`forest_centre_stand` in `unknown_sources`; a positive trigger still wins.
This rule uses no grid age substitute or age extrapolation.

The stand peatland screen consumes `SOILTYPE` from `forest_centre_stand`.
Finite integral numeric codes 60–69 inclusive match; other valid integral
codes do not. Recognized codes outside that range are no-match; missing,
nonnumeric, boolean, fractional, nonfinite and unrecognized individual values
are unknown. The required provider field is
checked at readiness. A match promotes every piece of a parent stand in
Balance, Protection and Superprotection, with that stand ID in
`potential_protected_peatland` provenance. An age match can independently promote
Protection and Superprotection. With no positive trigger and a required stand
check unknown, the affected tier remains unknown. No grid soil substitute is
used.

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

## Previous calculation-reference sections

These links preserve the previous section anchors and lead to their current owners.

- <a id="analysis-workflow"></a>[Analysis workflow](overview.md#one-execution-path).
- <a id="datasets-used-by-the-calculations"></a>[Datasets used by the calculations](data-sources.md#required-sources).
- <a id="indicators-and-summaries"></a>[Indicators and summaries](indicator-calculations.md).
- <a id="per-polygon-fields"></a>[Per-polygon fields](output-schema.md#per-polygon-fields).
- <a id="result-land-area--tuloksen-maapinta-ala"></a>[Result land area / Tuloksen maapinta-ala](output-schema.md#result-land-area--tuloksen-maapinta-ala).
- <a id="stand-tree-indicators--kuvio-puustotunnukset"></a>[Stand tree indicators / Kuvio: puustotunnukset](output-schema.md#stand-tree-indicators--kuvio-puustotunnukset).
- <a id="grid-volumes--hila-puuston-tilavuudet"></a>[Grid volumes / Hila: puuston tilavuudet](output-schema.md#grid-volumes--hila-puuston-tilavuudet).
- <a id="grid-age-shares--hila-ikäosuudet"></a>[Grid age shares / Hila: ikäosuudet](output-schema.md#grid-age-shares--hila-ikäosuudet).
- <a id="grid-land-areas--hila-maa-alat"></a>[Grid land areas / Hila: maa-alat](output-schema.md#grid-land-areas--hila-maa-alat).
- <a id="unavailable-indicators--tunnusluvut-jotka-eivät-ole-käytettävissä"></a>[Unavailable indicators / Tunnusluvut, jotka eivät ole käytettävissä](output-schema.md#unavailable-indicators--tunnusluvut-jotka-eivät-ole-käytettävissä).
- <a id="comparing-indicators-and-reporting-precision"></a>[Comparing indicators and reporting precision](indicator-calculations.md#comparing-indicators-and-reporting-precision).
- <a id="exact-intersections-and-volume-means"></a>[Exact intersections and volume means](indicator-calculations.md#exact-intersections-and-volume-means).
- <a id="grid-ages-and-categorical-area-totals"></a>[Grid ages and categorical area totals](indicator-calculations.md#grid-ages-and-categorical-area-totals).
- <a id="tierclass-summaries-and-metric-coverage"></a>[Tier/class summaries and metric coverage](indicator-calculations.md#tierclass-summaries-and-metric-coverage).
- <a id="outputs-and-coverage"></a>[Outputs and coverage](output-schema.md#outputs-and-coverage).
- <a id="remaining-source-verification"></a>[Remaining source verification](../open-questions.md#provider-evidence).
