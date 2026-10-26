# Source layer requirements

These requirements belong to **Savonia - Responsible Forest Planning**, Antti
Kajanus's unfinished personal learning prototype based on limited understanding
and personal assumptions. Neither the prototype nor its results are official,
backed, endorsed, finalized, or approved by Savonia in any form.

This reference owns required/optional fields, normalization, source identifiers
and source-layer behavior. [Data sources](data-sources.md) records provider
evidence and interpretation limits; [calculations](calculations.md) owns exact
geometry, classification and indicator rules.

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
| Forest Centre grid cells | `GRIDCELLID`, `VOLUME`, `VOLUMEPINE`, `VOLUMESPRUCE`, `VOLUMEDECIDUOUS`, `AGE`, `SOILTYPE`, `DRAINAGESTATE` | Stable `GRIDCELLID` identifies cells. `TREEDATADATE` (measurement date) and `UPDATETIME` (database update) are retained independently when present. Grid total, pine, spruce, deciduous volume, age shares, peatland and source-classified natural-mire area use this source. Price is OUT_OF_SCOPE. |
| Forest Centre habitats | `habitattype` | `habitatid` is used as a source identifier when present; otherwise the provider feature ID is used. Habitat values are interpreted separately: 1 and 5 trigger Section 10, and 3 triggers other valuable habitat. Unknown values stop the run. |
| Protected areas | State-owned, private-land, and wilderness WFS layers are required. Each must expose `olotila` and either `tyyppilyhenne` or `kohdetyyppi`. Active records use status `Voimassa`; recognized category/subtype codes include `VSA`, `YSA`, `EMA`, `MRA`, `LTA`, `ERA`, `ESA`, `HYL`, `KPU`, `KPM`, `LHA`, `LPU`, `MHA`, `SSA`, `VMA`, `ELD`, `ERM`, and `UTL`. | `kohdeid` or `lsaluetunnus` is used as a source identifier when present; otherwise the provider feature ID is used. Status and category values are interpreted separately; unrecognized values stop the run. Natura layers are separate feature types and do not satisfy this source requirement. |
| Nature conservation programme areas | `lsoaluetunnus` and `luokka` | `subtype`, `nimi`, `muutospvm`, and `lisatieto` are retained when present. Recognized classes are `AMO`, `HSO`, `LHO`, `LVO`, `MAO`, `PMO`, `KLO`, `RSO` and `SSO`. A missing/empty identifier or unrecognized class stops the run. |
| SYKE groundwater areas | No required attributes; valid polygon geometry is required. | All returned polygon footprints are used as the groundwater criterion, without filtering `alueluokka` or `subtype`. The provider feature ID is retained if no recognized source identifier is available. |

Project setup applies scale-based visibility to the Forest Centre stands and habitats reference layers: they are hidden when the map is zoomed farther out than 1:500,000. This keeps detailed WFS rendering focused around municipality-level views. The limit affects map rendering only; analysis still requests features within the AOI bounding box and intersects them with the AOI.

The grid source is `forest_centre_gridcell`, endpoint
`https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows`, advertised feature type
`v2:gridcell`. Setup verifies that type, retains discovery metadata, and puts
exactly one managed grid at the bottom of References below all other references.
Setup/relabeling reuses that layer and preserves the relative order of other
references. Grid rendering is restricted to **1:300 or closer** (visible at 1:200
and 1:300; hidden at 1:500). QGIS 4.2.3 uses a tiny comparison margin to include
the boundary scale. Rendering never controls source availability or calculations.
Processing requires an explicit polygon-layer `GRIDCELLS` parameter; the wizard
looks up the configured source by its stable service ID and captures worker-owned
inputs before analysis.

One AOI-bounded grid retrieval is clipped exactly and reused with a local spatial
index across the classified result polygons. Provider names, original attributes,
cell IDs, endpoint/type, retrieval time and any measurement/update dates remain
traceable in snapshots and metadata. A refreshed service is not a newer measurement.

The required attribute groups are the minimum field contract for each semantic source. A group with alternatives means at least one listed field must exist. If any required field is missing from any required source, project setup reports the project as not ready and analysis stops before publishing outputs. This field check does not certify that feature values are complete, numeric, or recognized; geometry validity, provider request success, and interpreted value checks remain separate workflow validations. Null feature values differ from missing schema fields. Grid numeric values must be finite nonnegative numbers; booleans, text, nulls and negative values are unavailable. Zero remains valid. Metric-specific unknown areas are disclosed without a stand fallback. Successful empty responses and partial value coverage can complete classification with unknown/partial grid metrics; request/iteration failures cannot.

Only WFS 2.0 is supported; managed sources are configured as WFS 2.0.0.
[ADR-0010](adr/0010-wfs-2-only.md) excludes WFS 1.x endpoints, protocol downgrade
fallback and legacy exception handling from the planned scope. The workflow
checks provider errors after delivering queued errors to the provider in its
owning thread, so HTTP
failures and HTTP-200 OWS `ExceptionReport` responses stop publication. QGIS 4.2
does not recognize the legacy WFS 1.0 `ServiceExceptionReport` response as an
exception; custom legacy services may therefore appear to return an empty
collection. Such services are unsupported under this source contract.
Use the managed configuration for these failure semantics.
See [WFS failure detection](data-sources.md).

Overlapping AOI features are dissolved. Identical duplicate grid records with the
same ID are deduplicated; conflicting same-ID records, positive-area overlaps
between distinct cells, or overlaps greater than 1 m² between distinct AOI-clipped
stands stop the run with source identifiers. Pairwise stand overlaps up to and
including 1 m² are accepted without trimming and may contribute to both stands'
areas and indicators. Shared edges are allowed. Indicator intersections retain
positive areas above the `1e-8` m² geometry tolerance, including genuine 0.5 m²
fragments; the sensitivity-trigger threshold greater than 1 m² does not apply.
Clipped numerical fragments at or below the storage tolerance are skipped before
snapshot/index construction rather than treated as invalid partitions.

Invalid non-empty polygon geometries returned by a source are repaired with QGIS `makeValid()` in the analysis copy. Only polygonal components are retained. AOI intersections are also normalized to valid multipolygons before they are saved; line and point remnants from boundary-only contacts are excluded. Repaired feature counts and a capped sample of source IDs are reported, using provider feature IDs when a stable source ID is absent; source layers are never edited. Analysis stops if repair fails or polygonal intersection components cannot be normalized to a valid geometry.

When selected-feature-only mode is enabled and the layer-based analysis area is also a configured source layer, the wizard copies the selected features' geometries and attributes into a worker-safe local snapshot instead of requesting those same features again from WFS. The copied geometries are still transformed and intersected with the analysis area before use. Other sources are retrieved using the analysis-area bounding box and are also intersected exactly with the analysis area. Unchecking selected-feature-only mode uses the full analysis-area layer and retrieves matching source features through the provider.

The field contract is provider-neutral. An adapter for a future local or custom source should pass its provider's field names and the corresponding semantic source ID to the shared readiness check. The current analysis workflow still configures its online WFS sources through project setup; this document does not itself add local/custom source selection.
