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
and clipped geometries stop the run. Area in hectares is planar
EPSG:3067 geometry area divided by 10,000. No buffers or proximity distances
are applied.

Source candidates that
do not overlap the AOI are counted and excluded. Overlapping AOI features are
dissolved. Stand overlaps follow the warning policy in
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry).
Every stand overlap above `1e-8` m² is retained without trimming, with no maximum
accepted overlap. It may contribute to both stands' areas and indicators. Flag
every derived piece of either parent, regardless of the individual piece's
location. Each unordered pair is logged once at DEBUG with run/source/stand IDs
and intersection m²; one WARNING reports pair count, affected-parent count and
a capped ID sample. Pairwise areas must not be summed as unique ground area.
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
does not determine whether a criterion hit occurs. Clipped numerical
fragments at or below this tolerance are skipped before snapshot/index
construction rather than treated as invalid partitions.

## Classification

The [output schema](output-schema.md#classification-fields-and-values) owns the
six stored tier fields, class-code meanings and reason-code dictionary so that
output recipients can interpret the GeoPackage from one reference. Unrecognized
returned classification inputs stop the run.

The cumulative criteria are evaluated independently for each output piece. A
recognized positive match makes the tier `SENSITIVE`, even if another required
source is unavailable. Without a positive match, all sources required by that
tier must be `AVAILABLE` before a no-hit can be `ECONOMIC`; otherwise the result
is `UNKNOWN`. A successful source request with no AOI-clipped features is still
marked `AVAILABLE`, so an empty response currently permits a no-hit
classification. Feature counts describe returned data and do not establish
complete service coverage.

These dependency rules describe the pure classification policy. The application
workflow requires all eight sources and stops before publication on a required
source or interpretation failure; it does not publish a partial-source run using
these `UNKNOWN` rules. Missing numeric indicator evidence can still produce
partial or unknown metrics in a successful run.

The criterion membership is defined in
[CL-02](../specs/classification.md#cl-02-six-cumulative-tiers). The
[tier-to-field table](output-schema.md#classification-fields-and-values) maps
those tiers to machine fields. Required source groups for a no-hit decision are:

| Tiers | Required source groups |
| --- | --- |
| All out, BAU, Light | Protected + Habitat |
| Balance, Protection, Superprotection | Protected + Habitat + Programme + Groundwater |

Protected combines the three required protected-area products in the
[source inventory](data-sources.md#required-sources). Habitat, Programme and
Groundwater refer to their semantic source groups, not display-layer names.
Excluded criteria follow [CL-04](../specs/classification.md#cl-04-exclusions-and-interpretation).

The [input contract](source-layer-requirements.md#accepted-classification-values)
owns accepted statuses, categories, habitat codes and programme identifiers.
Classification consumes their normalized criteria. The interpreter can build a
programme criterion for a recognized class without an identifier, but also reports
that record as uninterpretable; the workflow therefore stops before publication
under [WF-07](../specs/workflow.md#wf-07-failure-cancellation-and-observability).
Optional subtype and original programme context remain available for the
[output fields](output-schema.md#outputs-and-coverage).

Section 10 stand promotion follows
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry); it is a
planning assumption, distinct from a legal determination. Provider definitions
and their limits remain in [source evidence](data-sources.md#interpretation-and-geographic-limits).

Each split branch owns independent source-ID sets. Adding a matching record to
one branch cannot mutate the provenance of its siblings; normalized output IDs
remain sorted and unique. Spatial regressions exercise overlapping protected
records in both orders, alongside the stand-wide Section 10 exception.

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
- <a id="remaining-source-verification"></a>[Remaining source verification](open-questions.md#provider-evidence).
