# Source layer requirements

These requirements belong to **Savonia - Responsible Forest Planning**, Antti
Kajanus's unfinished personal learning prototype based on limited understanding
and personal assumptions. Neither the prototype nor its results are official,
backed, endorsed, finalized, or approved by Savonia in any form.

This reference owns required/optional fields, normalization, source identifiers
and source-layer behavior. Accepted feature values are separate from schema readiness. [Data sources](data-sources.md) records provider
evidence and interpretation limits; [calculations](calculations.md) owns exact
geometry and classification mechanics; [indicator calculations](indicator-calculations.md)
own metric statistics.

## Provider fields and readiness

The plugin checks required attributes against the fields supplied by each layer's data provider, excluding joined and virtual fields. Field matching and feature-attribute lookup are case-insensitive, so WFS names such as `SAWLOGVOLUME` match the calculation field `sawlogvolume`. Extra attributes and attribute order do not affect readiness. The plugin does not compare every field with a saved WFS schema or validate field types at this stage.

The readiness result also resolves the provider fields used to normalize
interpretation values during retrieval. Each protected-area source uses its own
mapping; if both accepted category fields exist, `tyyppilyhenne` takes precedence
over `kohdetyyppi`, independent of field order or feature values. A null or
unrecognized value in the chosen field does not fall back to another alias.
Classification receives normalized values with source identity, while original
attributes remain intact in the clipped snapshots and programme metadata.
Interpretation diagnostics identify the actual state-owned, private-land, or
wilderness source. Indicator coverage also uses current provider fields. Missing,
stale, malformed, or differently shaped saved schema metadata cannot select
interpretation fields or determine indicator availability; it is provenance only.

All eight configured WFS sources are required. Each must be a valid polygon
layer with a usable CRS and matching source identity. Required attributes are:

| Source | Required attributes | Optional attributes and behavior |
| --- | --- | --- |
| Forest Centre stands | `volume`, `sawlogvolume`, `volumegrowth`, `meanage` | Stand total volume, sawtimber and growth are stand-derived. `basalarea`, when present, maps to basal area (m²/ha), separately from geometry-derived land area. `standid` is used as source identifier when present; otherwise the provider feature ID is used. The schema contract requires `meanage`; age shares use grid `AGE`, and species volumes use direct grid fields. |
| Forest Centre grid cells | `GRIDCELLID`, `VOLUME`, `VOLUMEPINE`, `VOLUMESPRUCE`, `VOLUMEDECIDUOUS`, `AGE`, `SOILTYPE`, `DRAINAGESTATE` | Stable `GRIDCELLID` identifies cells. `TREEDATADATE` (measurement date) and `UPDATETIME` (database update) are retained independently when present. Grid total, pine, spruce, deciduous volume, age shares, peatland and source-classified natural-mire area use this source. |
| Forest Centre habitats | `habitattype` | `habitatid` is used as a source identifier when present; otherwise the provider feature ID is used. Accepted values are defined [below](#accepted-classification-values). |
| Protected areas | State-owned, private-land, and wilderness WFS layers are required. Each must expose `olotila` and either `tyyppilyhenne` or `kohdetyyppi`. | `kohdeid` or `lsaluetunnus` is used as a source identifier when present; otherwise the provider feature ID is used. Status/category checks are defined [below](#accepted-classification-values). Natura layers are separate feature types and do not satisfy this source requirement. |
| Nature conservation programme areas | `lsoaluetunnus` and `luokka` | `subtype`, `nimi`, `muutospvm`, and `lisatieto` are retained when present. Identifier/class checks are defined [below](#accepted-classification-values). |
| SYKE groundwater areas | No required attributes; valid polygon geometry is required. | All returned polygon footprints are used as the groundwater criterion, without filtering `alueluokka` or `subtype`. The provider feature ID is retained if no recognized source identifier is available. |

## Configured layer behavior

Managed WFS connections use explicit `version=2.0.0`, `pagingEnabled=true`,
`pageSize=1000`, `restrictToRequestBBOX=1`, `skipInitialGetFeature=true` and
`forceInitialGetFeature=false`. Metadata discovery also requests WFS 2.0.0.
QGIS still reads capabilities and the feature schema, but skips its startup
sample-feature request. Schema-declared polygon geometry, CRS and provider
fields remain the readiness evidence; no feature count is requested by setup.
The discovered CRS becomes `srsname` unless an existing connection chose a CRS.
Page size limits individual responses; managed connections have no
`maxNumFeatures` total cap. Later map reads use view bounds; shared workflow
reads retain AOI bounds and exact clipping across every page. Worker-owned
providers inherit these options. Setup remains synchronous, so slow metadata
responses can still delay the UI.

Repeated setup updates older connection options in place with `setDataSource`
only when the URI changes. It disables any forced startup sample request and
removes old total feature caps while preserving layer ID, endpoint, filters,
authentication, existing CRS, tree position and visibility choices. Schema
discovery/readiness remains fresh; an unavailable service or invalid reopened
provider leaves setup incomplete under the existing failure policy.
The options are implemented by
[QGIS 4.2.3 WFS URI parsing](https://github.com/qgis/QGIS/blob/final-4_2_3/src/providers/wfs/qgswfsdatasourceuri.cpp)
and [provider initialization](https://github.com/qgis/QGIS/blob/final-4_2_3/src/providers/wfs/qgswfsprovider.cpp).

The display-only MML layers have managed service IDs `mml_parcels` (polygon
collection `PalstanSijaintitiedot`) and `mml_property_identifiers` (point collection
`KiinteistotunnuksenSijaintitiedot`). Setup requires a saved MML API key before
any project mutation. Both `oapif` layers must have the expected geometry and a
valid saved API key in the connection username with an empty password, so all
discovery and feature requests use HTTP Basic authentication. Neither landing
page nor linked URLs need an `api-key` query parameter. Both layers require a
valid CRS; the point layer also requires the exact provider field
`kiinteistotunnuksenEsitysmuoto`. Unavailable connections or invalid schemas
leave setup incomplete. Both are outside the eight-source analysis registry and
Processing inputs, readiness, classification and export snapshots.

References has four managed subgroups, in order: `properties` (Kiinteistörajat),
`forest` (Metsävara), `protected` (Suojelualueet), `water` (Vesistö). Names are
localized; IDs remain stable. Properties contains Kiinteistörajat followed by
Kiinteistötunnukset. Polygons have no fill, solid red (`#ff0000`) outlines
1 mm wide and no labeling. Points use `QgsNullSymbolRenderer` with red 20-point
Arial field labels placed over the points, with a white 2 mm text buffer
(rounded joins, full opacity, no interior fill). Boundaries render at **1:25,000 or closer** and identifiers at **1:10,000 or closer**,
including the boundary using the same `1e-6` denominator margin as the grid.
Setup reapplies presentation, reuses layer identity, reconnects invalid layers
or changed credentials, and restores managed group/child order. User layers and
visibility choices survive node moves.

Tree moves insert a cloned node before removing the original, including group
moves. QGIS 4.2 queues deletion of project layers when their last node disappears;
disabling the registry bridge does not suppress its tree-removal slots. Never
detach/remove first and reinsert later. Tests must process queued GUI events
before asserting registry membership and tree completeness. See the
[QGIS registry bridge implementation](https://github.com/qgis/QGIS/blob/release-4_2/src/core/layertree/qgslayertreeregistrybridge.cpp).

The provider uses its advertised/default CRS
(CRS84 by default); QGIS handles map reprojection. No parcel area or distance
calculations are performed. Requests are restricted to the view bounding box
with a page size of 1,000; provider schema probes may request a small unbounded
sample. The endpoint, collection and access evidence are in
[data sources](data-sources.md#mml-parcel-map-context).

Project setup applies scale-based visibility to the Forest Centre stands and habitats reference layers: they are visible at **1:7,763 or closer** and hidden farther out. Setup restores these limits on both new and reused managed layers. A `1e-6` denominator margin includes the exact boundary despite QGIS comparison tolerance; there is no closer-zoom cutoff. Saved projects retain the settings. The limit affects map rendering only; analysis still requests features within the AOI bounding box and intersects them with the AOI.

The grid source is `forest_centre_gridcell`; its endpoint/type is in the
[source inventory](data-sources.md#required-sources). Setup verifies that type,
retains discovery metadata, and puts
exactly one managed grid after habitats and stands inside Forest inventory.
Protected areas contains programmes, wilderness, state-owned and private-land
layers in that order; Water contains groundwater. All four protected layers use
the same fill RGBA `210,95,125,95` and outline `155,55,85,220`, 0.35 mm wide.
This matches groundwater's fill/outline alpha and width while retaining a
separate rose hue. Setup gives the grid a solid dark green (`#006400`, RGBA
`0,100,0,255`) outline, 0.25 mm wide, with no fill (`style=no`). Repeated setup
restores this symbol on existing layers; saved projects retain it. Grid rendering is restricted to **1:300 or closer** (visible at 1:200
and 1:300; hidden at 1:500). QGIS 4.2.3 uses a tiny comparison margin to include
the boundary scale. Rendering never controls source availability or calculations.
Processing requires an explicit polygon-layer `GRIDCELLS` parameter; the wizard
looks up the configured source by its stable service ID and captures worker-owned
inputs before analysis.

One AOI-bounded grid retrieval is clipped exactly and reused with a local spatial
index across the classified result polygons. Provider names, original attributes,
cell IDs, endpoint/type, retrieval time and any measurement/update dates remain
traceable in snapshots and metadata. A refreshed service is not a newer measurement.

## Basemap stack

Managed raster IDs use the `savonia/layer_id` property: `mml_ortokuva`,
`mml_maastokartta`, `osm_xyz`, in that tree order. Finnish labels are Ortokuva,
Maastokartta and OpenStreetMap; English labels are Orthophoto, Topographic map
and OpenStreetMap. The MML WMTS connection contract is in
[data sources](data-sources.md#mml-basemap-context).

Setup creates/reconnects invalid MML raster providers and refreshes changed
connection credentials in place. It restores managed tree order ahead of user
layers without replacing existing layer IDs or losing check states. When
Maastokartta is first added, setup enables the Basemaps group and checks only
Maastokartta among managed basemaps, including upgrades from OSM-only projects.
Later runs preserve user visibility choices. Newly recreated Ortokuva is hidden.
An invalid WMTS layer produces a localized `WMTS_LAYER_INVALID` setup diagnostic;
new invalid layers are not published. Existing invalid layers remain for retry.
OSM creation failures retain `XYZ_LAYER_INVALID` with a localized diagnostic.
Basemap errors do not change analysis readiness or substitute another source
as valid analysis evidence. The existing MML-key preflight remains in force.

## Validation boundaries

The required attribute groups are the minimum field contract for each semantic source. A group with alternatives means at least one listed field must exist. If any required field is missing from any required source, project setup reports the project as not ready and analysis stops before publishing outputs. This field check does not certify that feature values are complete, numeric, or recognized; geometry validity, provider request success, and interpreted value checks remain separate workflow validations. Null feature values differ from missing schema fields. Numeric validity and missing-value behavior follow
[IO-03](../specs/indicators-and-outputs.md#io-03-unavailable-and-partial-values);
[indicator calculations](indicator-calculations.md) define per-metric statistics.

Supported protocol and request-failure handling are defined in
[WFS retrieval success](data-sources.md#wfs-retrieval-success), with the product
boundary in [WF-03](../specs/workflow.md#wf-03-source-readiness-and-retrieval).
Geometry repair, clipping, duplicate records and overlap tolerances belong to the
[geometry contract](calculations.md#area-and-geometry); field readiness does not
certify any of those conditions.

When selected-feature-only mode is enabled and the layer-based analysis area is also a configured source layer, both the wizard and Processing copy the selected features' geometries and attributes into a local snapshot instead of requesting those same features again from WFS. Processing captures selected features once during validation and uses that same set to build the AOI and source snapshot; provider FIDs/cache contents must not determine a second read. Validation forwards wizard snapshots unchanged to retrieval. The copied geometries are still transformed and intersected with the analysis area before use. Other sources are retrieved using the analysis-area bounding box and are also intersected exactly with the analysis area. Unchecking selected-feature-only mode uses the full analysis-area layer and retrieves matching source features through the provider.

The field contract is provider-neutral. An adapter for a future local or custom source should pass its provider's field names and the corresponding semantic source ID to the shared readiness check. The current analysis workflow still configures its online WFS sources through project setup; this document does not itself add local/custom source selection.

## Accepted classification values

These are prototype input mappings, not claims about the legal status of a site.
Provider definitions and their evidence limits are in
[data sources](data-sources.md#interpretation-and-geographic-limits).

| Input | Accepted normalized meaning |
| --- | --- |
| Habitat `habitattype` | Codes 1 and 5 map to Section 10; code 3 maps to other valuable habitat. Other returned codes are uninterpretable. |
| Protected status/category | Normalized active status `voimassa` and category `VSA`, `YSA`, `EMA`, `MRA`, `LTA`, `ERA`, `ESA`, `HYL`, `KPU`, `KPM`, `LHA`, `LPU`, `MHA`, `SSA`, `VMA`, `ELD`, `ERM`, or `UTL`. Another status, including inactive values, or an unrecognized category is uninterpretable. |
| Programme class/identifier | Class `AMO`, `HSO`, `LHO`, `LVO`, `MAO`, `PMO`, `KLO`, `RSO` or `SSO`, and a nonempty `lsoaluetunnus`. Optional subtype may be absent/null. |
| Groundwater | Every returned polygon footprint; no class/subtype filter. |

Uninterpretable classification inputs stop publication under
[WF-07](../specs/workflow.md#wf-07-failure-cancellation-and-observability).
Tier membership belongs to [CL-02](../specs/classification.md#cl-02-six-cumulative-tiers).

## Accepted indicator categories

Recognized soil codes are 10, 11, 12, 20–24, 30–32, 40, 50, 60–67, 70 and 80;
peat codes are 60–67. Recognized drainage codes are 1, 2, 3, 6, 7, 8 and 9;
natural mire is 6. Codes must be numeric, finite, integral and recognized; null,
text, booleans, unrecognized codes (including 0) and fractions are unknown.
Numeric volume/age inputs follow
[IO-03](../specs/indicators-and-outputs.md#io-03-unavailable-and-partial-values).
Per-metric coverage and lower-bound calculations are in
[indicator calculations](indicator-calculations.md#grid-ages-and-categorical-area-totals).
