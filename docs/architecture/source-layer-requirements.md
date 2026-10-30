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
| Forest Centre stands | `volume`, `sawlogvolume`, `volumegrowth`, `meanage` | Stand total volume, sawtimber and growth are stand-derived. `basalarea`, when present, maps to basal area (m²/ha), separately from geometry-derived land area. `standid` is used as source identifier when present; otherwise the provider feature ID is used. Stand `meanage` supplies the potential-protection criterion; age shares use grid `AGE`, and species volumes use direct grid fields. |
| Forest Centre grid cells | `GRIDCELLID`, `VOLUME`, `VOLUMEPINE`, `VOLUMESPRUCE`, `VOLUMEDECIDUOUS`, `AGE`, `SOILTYPE`, `DRAINAGESTATE` | Stable `GRIDCELLID` identifies cells. `TREEDATADATE` (measurement date) and `UPDATETIME` (database update) are retained independently when present. Grid total, pine, spruce, deciduous volume, age shares, peatland and source-classified natural-mire area use this source. |
| Forest Centre habitats | `habitattype` | `habitatid` is used as a source identifier when present; otherwise the provider feature ID is used. Accepted values are defined [below](#accepted-classification-values). |
| Protected areas | State-owned, private-land, and wilderness WFS layers are required. Each must expose `olotila` and either `tyyppilyhenne` or `kohdetyyppi`. | `kohdeid` or `lsaluetunnus` is used as a source identifier when present; otherwise the provider feature ID is used. Status/category checks are defined [below](#accepted-classification-values). Natura layers are separate feature types and do not satisfy this source requirement. |
| Nature conservation programme areas | `lsoaluetunnus` and `luokka` | `subtype`, `nimi`, `muutospvm`, and `lisatieto` are retained when present. Identifier/class checks are defined [below](#accepted-classification-values). |
| SYKE groundwater areas | No required attributes; valid polygon geometry is required. | All returned polygon footprints are used as the groundwater criterion, without filtering `alueluokka` or `subtype`. The provider feature ID is retained if no recognized source identifier is available. |

## Configured layer behavior

Managed WFS sources use WFS 2.0.0 with paging and view/AOI-bounded requests,
without a total feature cap. Setup discovers metadata and provider fields
without downloading sample features or counting records. Analysis retrieves
each source once for the AOI and clips it exactly; the grid is reused locally
across result polygons. Ordinary WFS reads combine the bounding rectangle with
`Intersects` predicates against the actual AOI in the source CRS, combining
individual polygon parts with `Or` for multipart AOIs. This retains
holes and multipart geometry, original fields, existing provider subsets and
authentication. The expression belongs to the feature request, leaving project
layer connections unchanged. Oversized serialized polygon filters use the
bounded rectangle alone; no total feature cap or inward simplification is used.
The selected strategy is retained in source coverage. Rendering visibility never controls analysis readiness
or retrieval. Setup remains synchronous, so metadata waits can delay the UI.
See the [connection adapter](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py)
for provider URI options.

Repeated setup reuses managed layer identities and refreshes connection options
and credentials while preserving user layers, filters, existing CRS and visibility
choices. Failed provider/schema checks leave setup incomplete. Stable service
IDs identify sources independently of translated labels and layer-tree position.
Reference grouping, rendering and scale visibility are presentation behavior;
[WF-02](../specs/workflow.md#wf-02-project-setup) and the
[manuals](../help/manual_en.html) describe the user-facing organization.

The MML parcel polygons and property-identifier points are display context,
outside the analysis registry and exports. Setup requires a saved MML key before
project mutation and validates provider geometry/CRS; identifier points also
require `kiinteistotunnuksenEsitysmuoto`. Connections authenticate discovery and
feature requests using the key as the HTTP Basic username with an empty
password. QGIS handles map reprojection; these layers supply no analysis area or
distance calculations. [Access and source evidence](data-sources.md#mml-parcel-map-context).

## Basemap stack

MML orthophoto/topographic WMTS and OpenStreetMap XYZ are display-only adapters,
separate from the eight required analysis sources. Repeated setup refreshes
credentials and reuses layer identities while preserving user visibility choices.
Invalid basemap providers produce localized setup diagnostics; they neither
satisfy analysis readiness nor substitute for failed evidence sources.
The [workflow spec](../specs/workflow.md#wf-02-project-setup) owns initial
visibility and ordering; [data sources](data-sources.md#mml-basemap-context)
owns the connection and access evidence.

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

When selected-feature-only mode is enabled and the layer-based analysis area is also a configured source layer, both the wizard and Processing copy the selected features' geometries and attributes into a local snapshot instead of requesting those same features again from WFS. The same captured selection supplies both the AOI and source snapshot, so later selection or service changes cannot alter that run. The copied geometries are still transformed and intersected with the analysis area before use. Other sources use the AOI spatial-filter policy above and are also intersected exactly with the analysis area. Explicit provider-FID selections retain their ID filter without replacing it with a polygon expression. Unchecking selected-feature-only mode uses the full analysis-area layer and retrieves matching source features through the provider.

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
| Stand `MEANAGE` | Finite nonnegative numeric mean age in years; strictly over 80 triggers potential protection. Null/missing, text, booleans, negative and nonfinite values leave this check unknown; they do not stop publication. A missing required field remains fatal at schema validation. |

Uninterpretable protected, habitat and programme classification inputs stop publication under
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
