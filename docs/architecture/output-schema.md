# Result fields and output schema

This reference owns stored field IDs, field order, coverage serialization and
output layout. [IO-01 and IO-04–IO-06](../specs/indicators-and-outputs.md) own required
results and presentation; [indicator calculations](indicator-calculations.md)
own formulas/statistics; [publication boundaries](overview.md#geometry-evidence-and-publication-boundaries)
own writer coordination and failure cleanup.

## Per-polygon fields

The QGIS attribute table, grouped attribute form, Excel summary columns and
metric-coverage rows follow the order below. Source-dependent display labels
start with **Kuvio / Stand** or **Hila / Grid**, followed by the attribute.
Machine field IDs remain stable for expressions and integrations. Identity and
tier classifications precede these values; coverage and provenance follow them.
The GeoPackage saves the localized aliases and form groups for reopening.

### Result land area / Tuloksen maapinta-ala

**Pinta-ala (ha)** is the ground area of the actual result polygon, after clipping
and splitting: 1 ha = 10,000 m². **Puuston pohjapinta-ala (m²/ha)** is the sum of
tree-trunk cross-sectional areas at breast height per hectare of land. For
example, 20 m²/ha describes tree density; it does not mean a polygon has 20 m² of
land. Basal area comes from stand `basalarea`; land area comes from geometry.
The same explanation appears in Finnish and English in the result/stand form
tabs and the workbook's calculation notes.

| Field | Display meaning | Source and calculation |
| --- | --- | --- |
| `area_ha` | Tulospolygonin maapinta-ala / Result polygon land area (ha) | Actual result-polygon EPSG:3067 area / 10,000, independent of metric coverage. |

### Stand tree indicators / Kuvio: puustotunnukset

| Field | Display meaning | Source and calculation |
| --- | --- | --- |
| `total_volume_m3_ha` | Kuvio kokonaistilavuus / Stand total volume (m³/ha) | Stand `volume`; weighted by actual result-piece hectares in summaries. |
| `sawtimber_volume_m3_ha` | Kuvio tukkipuun määrä / Stand sawtimber volume (m³/ha) | Stand `sawlogvolume`; result-piece-area weighted in summaries. |
| `growth_percent` | Kuvio puuston kasvuprosentti / Stand growth (%/year) | [Stand growth rate](indicator-calculations.md#exact-intersections-and-volume-means) from `volumegrowth` and `volume`. |
| `basal_area_m2_ha` | Kuvio puuston pohjapinta-ala / Stand tree basal area (m²/ha) | Optional stand `basalarea`; result-piece-area weighted. Measures trunk cross-sectional area per hectare of land. |

### Grid volumes / Hila: puuston tilavuudet

| Field | Display meaning | Source and calculation |
| --- | --- | --- |
| `grid_total_volume_m3_ha` | Hila kokonaistilavuus / Grid total volume (m³/ha) | Grid `VOLUME`; mean weighted by valid intersected hectares. |
| `pine_volume_m3_ha` | Hila männyn tilavuus / Grid pine volume (m³/ha) | Grid `VOLUMEPINE`; its own valid intersected-area mean, replacing stand proportions. |
| `spruce_volume_m3_ha` | Hila kuusen tilavuus / Grid spruce volume (m³/ha) | Grid `VOLUMESPRUCE`; its own valid intersected-area mean. |
| `deciduous_volume_m3_ha` | Hila lehtipuun tilavuus / Grid deciduous volume (m³/ha) | Grid `VOLUMEDECIDUOUS`; all source-classified deciduous trees, with its own valid-area mean. |

### Grid age shares / Hila: ikäosuudet

| Field | Display meaning | Source and calculation |
| --- | --- | --- |
| `share_under_20` | Hila keski-ikä alle 20 vuotta: pinta-alaosuus / Grid mean age under 20: area share (%) | `100 × matching hectares with AGE < 20 / valid-age hectares`. |
| `share_20_80` | Hila keski-ikä 20–80 vuotta: pinta-alaosuus / Grid mean age 20–80: area share (%) | `100 × matching hectares with 20 ≤ AGE ≤ 80 / valid-age hectares`; both endpoints included. |
| `share_over_80` | Hila keski-ikä yli 80 vuotta: pinta-alaosuus / Grid mean age over 80: area share (%) | `100 × matching hectares with AGE > 80 / valid-age hectares`. |

### Grid land areas / Hila: maa-alat

| Field | Display meaning | Source and calculation |
| --- | --- | --- |
| `peatland_area_ha` | Hila turvemaiden pinta-ala / Grid peatland area (ha) | Intersected hectares matching the [peat-soil input mapping](source-layer-requirements.md#accepted-indicator-categories), as a total only with complete known soil classification. |
| `natural_mire_area_ha` | Hila lähteen luonnontilaisten soiden pinta-ala / Grid source-classified natural mire area (ha) | Intersected hectares matching the [natural-mire input mapping](source-layer-requirements.md#accepted-indicator-categories), as a total only with complete known drainage classification. |

### Unavailable indicators / Tunnusluvut, jotka eivät ole käytettävissä

This field has no implemented source and remains at the end of the indicators.

| Field | Display meaning | Source and calculation |
| --- | --- | --- |
| `stumpage_price_eur_m3` | Keskimääräinen kantohinta / Average stumpage price (€/m³) | Null, `OUT_OF_SCOPE`; no price source or weighting. |

## Metric coverage

`indicator_coverage` records each metric's `source_id`, `status`, `valid_area_ha`,
`unknown_area_ha` and sufficient statistics: `represented_volume_m3` for volume,
`weighted_sum` for stand rates/basal area and `matching_area_ha` for age/area
metrics. Age entries retain `coverage_percent_exact` and rounded
`coverage_percent`. The localized metric-coverage worksheet exposes tier/class,
metric, source, status, valid/unknown hectares and observed partial quantities.
Price is `OUT_OF_SCOPE`; its numeric field stays blank. Availability is recorded
in statuses and notes rather than appended to attribute names.

## Outputs and coverage

The GeoPackage contains one spatial result layer, AOI-clipped snapshots of the
returned WFS features, a `source_coverage` table, and a `run_metadata` table.
The result layer retains tier classes, criterion/source IDs, indicator values
and statuses, area, Section 10 promotion state, programme attributes, and
programme/protected overlap state. The workbook has Finnish or English
summaries, source/metric coverage details, and limitations.

The remaining result fields explain how the calculations were obtained:

| Result field | Dataset or input | Derivation |
| --- | --- | --- |
| `source_stand_id` | Stand: `standid` or provider feature ID | Retains the source identifier; the provider feature ID is the fallback when `standid` is absent or null. |
| `indicator_status` | Indicator inputs and validation | JSON metric statuses: `AVAILABLE`, `PARTIAL`, `UNKNOWN_FIELD_OR_VALUE` and `OUT_OF_SCOPE` for price; detailed invalid-value reasons are retained separately. |
| `tier_rule_ids` | Tier rules and matched source criteria | JSON object per tier listing matched criterion names, source IDs and any unknown source dependencies. An unmatched Superprotection piece with available evidence records `remaining_analyzed_forest`. |
| `source_ids` | Recognized Protected, Habitat, Programme and Groundwater criteria | JSON object grouping matched source IDs by criterion. Section 10 source IDs are carried to all pieces of a promoted stand. |
| `section10_stand_promoted` | Stand + Habitat: normalized Section 10 criterion and geometry | `true` if any recognized Section 10 habitat overlaps the AOI-clipped original stand under the [CL-01 hit rule](../specs/classification.md#cl-01-reporting-domain-and-geometry); applied to every result piece from that stand. `false` when Habitat is available with no hit; `null` when Habitat is unavailable. |
| `programme_info` | Matched Programme polygons and original attributes | JSON list retaining available `LsoAlueTunnus`, `Luokka`, `Subtype`, `Nimi`, `MuutosPvm`, and `Lisatieto` values. No values are estimated. |
| `programme_protected_overlap` | Result piece matched to Programme + recognized active Protected geometries | `YES` if the programme-matched result piece overlaps a recognized protected polygon under the [CL-01 hit rule](../specs/classification.md#cl-01-reporting-domain-and-geometry); otherwise `NO` when Protected is available, or `UNKNOWN` when it is unavailable. `null` when the piece has no programme match. |

These fields are assembled by
[`analysis/workflow_steps/spatial_classification.py`](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/spatial_classification.py)
and serialized by
[`adapters/classified_result.py`](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/classified_result.py).

Source availability and intentional exclusions are recorded separately from
metric availability. Failed required-source retrieval/interpretation follows
[WF-07](../specs/workflow.md#wf-07-failure-cancellation-and-observability);
successful counts and overlaps remain observations, not geographic completeness.
