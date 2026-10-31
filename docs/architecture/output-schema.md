# Result fields and output schema

This is a field reference for the classifications and calculated values in the
GeoPackage layer `classified_forest_polygons`. Each row represents a piece of a
source forest stand within the analysis area (AOI), with MultiPolygon geometry
in EPSG:3067. A split stand has several rows with the same `source_stand_id`.

Field IDs and stored codes are language-neutral; display labels follow the
run's Finnish or English presentation language. Calculation methods are in
[indicator calculations](indicator-calculations.md) and
[geometry and classification](calculations.md). Supporting metadata is
summarized at the end.

For two supplied polygon records with field values, classification reasons and
coverage interpretation, see the [worked output examples](../examples/classified-forest-polygons.md).

## Classification fields and values

Each row carries six text fields classifying the **same land** under different
tiers. Select one tier for area reporting; adding areas across tiers counts
the land repeatedly. The tier key is also used inside `tier_rule_ids`.
Criteria accumulate from one tier to the next.

| Result field | Tier / JSON tier key | Sensitivity represented by this tier |
| --- | --- | --- |
| `class_all_out` | All out / `all_out` | Recognized active protected areas and mapped Section 10 habitats. |
| `class_bau` | BAU / `bau` | Same criteria as All out; retained as a separate tier. |
| `class_light` | Light / `light` | Same criteria as All out and BAU. |
| `class_balance` | Balance / `balance` | Light criteria plus nature conservation programme areas, groundwater areas, Ranta10 riparian buffers and parent stands with peatland soil type (`SOILTYPE` 60–69). |
| `class_protection` | Protection / `protection` | Balance criteria plus other valuable habitats and potential protected areas based on stand age or peatland soil code. |
| `class_superprotection` | Superprotection / `superprotection` | Protection criteria plus all remaining analyzed forest with available required evidence. |

Protected areas include state-owned protected areas, private-land protected
areas and wilderness areas. All out, BAU and Light currently carry identical
classifications. Tier names describe planning classifications; they are not
modeled harvest or financial outcomes.

### Class codes

Each `class_*` field stores one of these exact values:

| Stored value | Meaning | Interpretation |
| --- | --- | --- |
| `SENSITIVE` | The piece meets at least one sensitivity criterion included in this tier, or Superprotection's remaining-forest rule applies. | Inspect `tier_rule_ids` for the reason. Sensitivity is a prototype planning classification; it does not itself establish a legal harvesting prohibition. |
| `ECONOMIC` | No included sensitivity criterion matched, and all source groups required for that tier's no-hit decision were available. | The piece falls in the economic-forest class under this tier's evidence and rules. This code does not establish profitability, harvesting permission or absence of unmapped constraints. |
| `UNKNOWN` | No positive criterion matched and evidence required to establish a no-hit decision was unavailable. | A data-quality state: classification cannot be resolved from the available evidence. It is neither a forest type nor a numeric zero. |

The current application publishes results only when required sources are
available. Missing or invalid individual stand ages can still leave Protection
and Superprotection `UNKNOWN` when no other positive criterion matches.
Indicator availability is recorded independently.

### Classification reasons and context

`tier_rule_ids` records the reason for each tier's classification. Its `criteria`
lists use these codes; several reasons can apply to one piece.

| Reason code | Meaning |
| --- | --- |
| `protected` | Match to a recognized active protected-area polygon. |
| `section10` | A mapped Forest Act Section 10 habitat triggered promotion of the parent stand. |
| `programme` | Match to a recognized nature conservation programme polygon. Programme membership is distinct from established protection. |
| `groundwater` | Match to a groundwater-area footprint. |
| `riparian_buffer` | Match to the combined Ranta10 30 m buffer footprint. |
| `other_habitat` | Match to another valuable habitat. |
| `potential_protected_age` | Parent stand matches the potential-protection criterion based on forest age. This is distinct from established legal protection. |
| `potential_protected_peatland` | Parent stand has a SOILTYPE code from 60 through 69, inclusive; a planning screen distinct from established legal protection. |
| `remaining_analyzed_forest` | Superprotection's rule for analyzed forest with no more specific sensitivity match and available required evidence. This is a policy reason and has no matched source-feature identifier. |

Ordinary source-check attributes complement the structured reasons:

| Field | Meaning |
| --- | --- |
| `check_protected` | Recognized active protected-area match. |
| `check_section10` | Parent stand promoted by Section 10 evidence, including pieces outside its footprint. |
| `check_programme` | Conservation programme match. |
| `check_groundwater` | Groundwater footprint match. |
| `check_riparian_buffer` | Match to the combined Ranta10 30 m buffer footprint. |
| `check_other_habitat` | Other valuable habitat match. |
| `check_potential_protected_age` | Potential protected-area match based on parent stand age. |
| `check_potential_protected_peatland` | Potential protected-area match based on parent stand soil code. |

Each stores `MATCH`, `NO_MATCH` or `UNKNOWN`, with localized presentation.
Display labels describe the criterion without embedding formulas or thresholds.
Unavailable dependencies are unknown rather than no-match; stand-age and
stand-soil checks also remain unknown for missing or invalid individual values. Each check reports its own
criterion independently, even when another criterion determines a tier's class.
Superprotection's remaining-forest rule stays in `tier_rule_ids` rather than
another check field. Exact matching rules are defined in
[geometry and classification](calculations.md#classification); saved calculation
definitions are described under [Supporting metadata](#supporting-metadata).

Additional fields describe classification and parent geometry context:

| Field | Stored values and meaning |
| --- | --- |
| `section10_stand_promoted` | Nullable boolean. `true`: Section 10 habitat evidence promoted the whole parent stand, including result pieces outside the mapped habitat footprint. `false`: no qualifying mapped Section 10 hit with Habitat available. `null`: Habitat unavailable. |
| `stand_has_overlap` | Boolean. The AOI-clipped parent stand overlaps another stand beyond numerical tolerance anywhere inside the AOI. Every derived piece inherits the same value; this does not locate the physical overlap within each piece. |
| `programme_protected_overlap` | Text. `YES`: a programme-matched piece has a qualifying overlap with recognized active protected-area evidence. `NO`: no such overlap with Protected available. `UNKNOWN`: Protected unavailable. `null`: no programme match to assess. |

A false promotion flag does not exclude other sensitivity reasons or unmapped
habitats. Viewers may show boolean true/false as 1/0 or localized text. For
programme overlap, `NO` means assessed with no overlap, while null means no
programme match to assess. Unavailable-source states are not expected in a
successful current run.

<a id="per-polygon-fields"></a>

## Calculated fields

Indicator fields occur in the order below. Source-dependent display labels
start with **Kuvio / Stand** or **Hila / Grid**, followed by the attribute.
Age shares are integer fields; the other calculated values are decimal fields.
The GeoPackage retains localized aliases and form groups for reopening.

### Result land area / Tuloksen maapinta-ala

Land area describes the ground covered by the result piece. Tree basal area
describes trunk cross-sectional area per hectare and has a separate field below.

| Field | Display label | Meaning of stored value |
| --- | --- | --- |
| `area_ha` | Tulospolygonin maapinta-ala / Result polygon land area (ha) | Land area of this result piece in hectares, independent of indicator coverage. |

### Stand tree indicators / Kuvio: puustotunnukset

| Field | Display label | Meaning of stored value |
| --- | --- | --- |
| `total_volume_m3_ha` | Kuvio kokonaistilavuus / Stand total volume (m³/ha) | Stand-source estimate of total standing timber volume per hectare. |
| `sawtimber_volume_m3_ha` | Kuvio tukkipuun määrä / Stand sawtimber volume (m³/ha) | Stand-source estimate of sawtimber volume per hectare. |
| `growth_percent` | Kuvio puuston kasvuprosentti / Stand growth (%/year) | Relative annual stand volume growth, expressed as a percentage of standing volume. |
| `basal_area_m2_ha` | Kuvio puuston pohjapinta-ala / Stand tree basal area (m²/ha) | Tree-trunk cross-sectional area at breast height per hectare of land; nullable when unavailable. |

### Grid volumes / Hila: puuston tilavuudet

| Field | Display label | Meaning of stored value |
| --- | --- | --- |
| `grid_total_volume_m3_ha` | Hila kokonaistilavuus / Grid total volume (m³/ha) | Grid-source estimate of total standing timber volume per hectare with valid coverage. Separate from the stand-source estimate. |
| `pine_volume_m3_ha` | Hila männyn tilavuus / Grid pine volume (m³/ha) | Grid-source pine volume per hectare with valid pine coverage. |
| `spruce_volume_m3_ha` | Hila kuusen tilavuus / Grid spruce volume (m³/ha) | Grid-source spruce volume per hectare with valid spruce coverage. |
| `deciduous_volume_m3_ha` | Hila lehtipuun tilavuus / Grid deciduous volume (m³/ha) | Grid-source volume of all source-classified deciduous trees per hectare with valid deciduous coverage. |

### Grid age shares / Hila: ikäosuudet

| Field | Display label | Meaning of stored value |
| --- | --- | --- |
| `share_under_20` | Hila keski-ikä alle 20 vuotta: pinta-alaosuus / Grid mean age under 20: area share (%) | Percentage of valid-age land with grid-cell mean age under 20 years. |
| `share_20_80` | Hila keski-ikä 20–80 vuotta: pinta-alaosuus / Grid mean age 20–80: area share (%) | Percentage of valid-age land with grid-cell mean age from 20 to 80 years, including both endpoints. |
| `share_over_80` | Hila keski-ikä yli 80 vuotta: pinta-alaosuus / Grid mean age over 80: area share (%) | Percentage of valid-age land with grid-cell mean age over 80 years. |

### Grid land areas / Hila: maa-alat

| Field | Display label | Meaning of stored value |
| --- | --- | --- |
| `peatland_area_ha` | Hila turvemaiden pinta-ala / Grid peatland area (ha) | Hectares classified as peat soil within the result piece; null if soil coverage is incomplete. |
| `natural_mire_area_ha` | Hila lähteen luonnontilaisten soiden pinta-ala / Grid source-classified natural mire area (ha) | Hectares classified as natural mire in the grid drainage data; null if drainage coverage is incomplete. |

These categories describe the source classification at its source date, rather
than certification of present ecological condition. They are descriptive
indicators, separate from the sensitivity classifications.

<a id="unavailable-indicators--tunnusluvut-jotka-eivät-ole-käytettävissä"></a>

<a id="sawlog-price--tukkipuun-kantohinta"></a>

### Sawlog price and value / Tukkipuun hinta ja arvo

These fields occur at the end of the indicators, with unit price before value.

| Field | Display label | Meaning of stored value |
| --- | --- | --- |
| `stumpage_price_eur_m3` | Tukkipuun kantohinta / Sawlog stumpage price (€/m³) | Explicit user-supplied unit price when original stand sawlog volume is valid and positive; otherwise null. Group price is weighted by represented sawlog m³. |
| `sawlog_value_eur` | Tukkipuun laskennallinen arvo / Calculated sawlog value (€) | Original piece hectares × valid nonnegative stand sawlog m³/ha × supplied €/m³. Zero stock gives zero euros; unknown stock gives null. Complete groups sum exact amounts; partial and empty totals are null with known subtotals in coverage. |

### Stored precision

Volume density fields contain whole m³/ha values; hectare fields have 0.01 ha
precision. Age shares are whole percentages and can sum to 99% or 101% after
rounding. Growth and basal-area values display two decimals. Coverage JSON
retains full precision, so its hectares can differ from the rounded `area_ha`
field. Reporting precision does not establish measurement accuracy.
Calculated sawlog value is stored to cents using half-up rounding after
calculation or group summation. Its coverage euro subtotal remains unrounded.

## Metric coverage

### Availability codes and missing values

Availability codes are retained inside each metric's `indicator_coverage` entry.
There is no independent `indicator_status` result field. Published land area
comes directly from valid result geometry.

| Status | Meaning | Numeric result |
| --- | --- | --- |
| `AVAILABLE` | The metric has valid evidence over the whole result piece, within numerical tolerance. | A value, including a valid zero. This status does not certify measurement accuracy. |
| `PARTIAL` | Some hectares have valid evidence and some are unknown for this metric. | Volume means and age shares describe valid hectares only. Peatland/natural-mire and calculated sawlog-value totals remain null; their known quantities remain in coverage JSON. |
| `UNKNOWN_FIELD_OR_VALUE` | No valid area is available for the metric, for example because values are missing/invalid or no grid cells cover the piece. | Null, never an assumed zero. |
| `OUT_OF_SCOPE` | An intentionally excluded metric in the retained coverage vocabulary. | Null; sawlog price is now in scope. |

A null/blank numeric field means no reported value; consult its status to find
the reason. A numeric zero can be a known zero or a small positive estimate
rounded to zero. It must not be used as a replacement for null. Classification
`UNKNOWN` and metric `UNKNOWN_FIELD_OR_VALUE` describe different decisions: a
piece may have fully resolved classes and still have unavailable indicators.

### Coverage JSON

`indicator_coverage` is a JSON object keyed by metric field ID. Each metric has
its own source, availability, valid/unknown hectares and supporting quantities.

| Coverage member | Meaning / unit |
| --- | --- |
| `source_id` | Dataset identifier: `forest_centre_stand` for stand metrics, sawlog-price applicability and calculated sawlog value, or `forest_centre_gridcell` for grid metrics. Unlike `source_ids`, this identifies a dataset rather than matched feature records. |
| `status` | The metric availability code defined above. |
| `valid_area_ha` | Hectares with valid evidence for this particular metric. |
| `unknown_area_ha` | Reporting hectares without valid metric evidence; not assumed zero or allocated to a matching category. |
| `represented_volume_m3` | Timber volume represented over this metric's valid area, in m³. Present for volume metrics, the sawlog-price denominator and calculated sawlog value. |
| `weighted_sum` | Accumulator retained for growth, basal area, sawlog price or calculated sawlog value. Growth/basal area use hectares; price uses represented sawlog m³. For sawlog value this is the exact known euro subtotal, retained even when the complete total is null. |
| `matching_area_ha` | Valid hectares matching the age band, peat soil or natural-mire category. For partial area totals this is the observed lower bound. |
| `coverage_percent_exact` | Percentage of the result piece with valid age evidence, at full precision. |
| `coverage_percent` | The same age coverage rounded to a whole percent. This is coverage of the polygon, not its share in an age band. |

Each metric's coverage applies independently. A partial value describes its
valid area only. Stand and grid totals are separate estimates, and species
means need not add up to grid total volume. Age shares describe valid-age land
by grid-cell mean age, rather than individual-tree ages.

<a id="outputs-and-coverage"></a>

## Supporting metadata

These result fields provide traceability. Structured objects and lists are JSON
stored in text fields.

| Field | Meaning |
| --- | --- |
| `source_stand_id` | Parent stand identifier, using the provider feature ID when `standid` is absent/null. Distinct from the result row's GeoPackage feature ID. |
| `tier_rule_ids` | Object keyed by tier. Each entry contains `criteria` (reason codes), `source_ids` (supporting feature identifiers) and `unknown_sources` (unavailable dependencies for an unmatched decision). Empty lists mean no entries of that kind. |
| `source_ids` | Matched feature identifiers grouped by classification reason, independently of tier. `{}` means no matched classification identifiers, rather than no source data used. Section 10 identifiers apply to all promoted pieces; age-based matches identify the parent stand on every derived piece. |
| `programme_info` | List of retained programme records: `LsoAlueTunnus` (identifier), `Luokka` (class), `Subtype` (subtype), `Nimi` (name), `MuutosPvm` (source change date) and `Lisatieto` (additional information), where available. `[]` means no retained programme records. |
| `source_ids.riparian_buffer` | Source-qualified identifiers of only those Ranta10 features whose derived buffers contribute to the result piece. The service ID prefix prevents identifiers from different products colliding. |

The GeoPackage also contains one derived polygon layer named `buffered_water_evidence` when the AOI has positive-area buffered evidence. It can contain a combined multipart geometry and defines the used footprint. Its fields are `evidence_id` (`combined_riparian_buffer`), `source_refs` (source-qualified contributing feature identifiers), `source_update_dates`, `buffer_distance_m` (30), `source_retrieved_feature_count` (sum of original retrieved source features), `buffers_generated_count` (derived buffers), and `aoi_contributing_buffer_feature_count` (buffers that contribute positive area inside the AOI). Raw Ranta10 source geometries are not exported as separate snapshots. The three source retrieval rows remain separate in `source_coverage`; the derived evidence has its own coverage record.

`run_metadata.water_buffer_evidence` records the source IDs/references and update dates, 30 m distance and units, EPSG:3067 buffering before union/clipping, full polygon-buffer inclusion, two-sided line buffering, criterion threshold/comparison, counts and per-product retrieval provenance. An empty derived evidence layer is still available when all three retrievals succeeded empty.
There is no per-indicator diagnostic result field or corresponding metadata
summary. Coverage retains the evidence needed for null/partial interpretation;
geometry corrections and invariant checks still run. General source/geometry
records, operational errors and stand-overlap logs remain separate.

The file also contains AOI-clipped source snapshots, a `source_coverage` table
with retrieval/interpretation details and exclusions, and a `run_metadata`
table with run identity, parameters, source dates, limitations and attribution.
Calculation definitions are stored in its JSON members and included unchanged
in workbook calculation notes:

| Run metadata member | Meaning |
| --- | --- |
| `classification_semantics` | Criterion definitions. `potential_protected_age` records source `forest_centre_stand`, field `MEANAGE`, unit `years`, rule `MEANAGE > 80`, tiers `protection` and `superprotection`; `potential_protected_peatland` records the same source, field `SOILTYPE`, integral codes 60–69 inclusive, tiers `balance`, `protection` and `superprotection`. Both cover every parent-stand piece and retain missing/invalid-value policy and potential rather than legal interpretation. Accepted values and unknown handling follow the [classification input contract](source-layer-requirements.md#accepted-classification-values). |
| `indicator_semantics` | Indicator formulas, source groupings, units, weighting, rounding, completeness rules and interpretation of the supplied sawlog price and calculated sawlog value. Exact methods are defined in [indicator calculations](indicator-calculations.md). |

Its `result_geometry_filter` JSON object records `maximum_excluded_area_m2`
(`0.01`), `excluded_piece_count`, full-precision `excluded_area_m2` and
`excluded_stand_count` (parents with no retained result polygon) for final
polygons omitted under the [reporting-area filter](calculations.md#area-and-geometry).
These polygons do not contribute to `result_feature_count` or metric summaries;
clipped source snapshots can still contain them.
`skipped_stand_count` records the same excluded parent count.
Each retrieved source's coverage row retains `spatial_filter`: `aoi_intersects` for the
polygon request, `bbox_filter_size` for its size-budget fallback, `bbox` for
other rectangle reads, `selected_snapshot` for captured features, or
`selected_fids` for an explicit ID request. These describe the requested
retrieval strategy, not a provider coverage certification. Received/skipped
candidate counts may decrease with polygon filtering; retained snapshots still
contain the exact AOI-clipped evidence and original attributes.
Run parameters include the supplied sawlog price; durable metadata identifies
its user-supplied origin, applicability source and unit-price interpretation.
The application columns in both tables are text, with objects/lists stored as
JSON. Successful source counts do not establish geographic completeness;
source dates are distinct from the run timestamp. Retain attribution when
sharing outputs.
