# Indicator and output specification

The reporting domain and tiers are defined in [classification](classification.md). This document owns required user-facing results. [Indicator calculations](../architecture/indicator-calculations.md) own formulas and sufficient statistics; [output schema](../architecture/output-schema.md) owns stored field IDs and layout; [indicator design](../architecture/indicators.md) owns evidence and accuracy limits.

The [worked output examples](../examples/classified-forest-polygons.md) illustrate
these rules using two supplied result features, including partial coverage,
known zeros, unavailable growth and programme provenance.

## IO-01 Indicator catalogue

Provide these indicators on result polygons and in separate tier/class workbook summaries, in this order:

| Group | Indicator and unit | Required meaning |
| --- | --- | --- |
| Result land | Land area (ha) | Actual classified piece area, independent of metric coverage |
| Stand trees | Total volume (m³/ha) | Stand estimate, kept separate from grid total |
| Stand trees | Sawtimber volume (m³/ha) | Stand sawlog estimate |
| Stand trees | Growth (%/year) | Relative stand volume growth using stand stock; exact period/basis remains a documented source limitation |
| Stand trees | Tree basal area (m²/ha), when available | Trunk cross-sectional area at breast height per hectare, distinct from hectares of land |
| Grid volumes | Total, pine, spruce and deciduous volume (m³/ha) | Independent source estimates weighted by actual intersected valid area |
| Grid ages | Under 20, 20–80 inclusive and over 80 (%) | Area shares by overall grid-cell mean age over valid-age hectares |
| Grid land | Peatland area (ha) | Source-classified peat soil within analyzed forest |
| Grid land | Source-classified natural-mire area (ha) | Source drainage classification within analyzed forest |
| Sawlog price | Sawlog stumpage price (€/m³) | User-supplied unit price where valid positive stand sawlog volume is represented; otherwise blank |
| Sawlog value | Calculated sawlog value (€) | Full-precision represented stand sawlog m³ times the supplied unit price; known zero gives zero euros, missing evidence remains blank |

Use deciduous volume as adopted in [ADR-0011](../architecture/adr/0011-deciduous-volume-instead-of-birch.md). Birch-specific volume is out of scope and absent from result fields, summaries, coverage, metadata and UI. Deciduous volume describes all source-classified deciduous trees and must not be presented as birch-only volume.

## IO-02 Weighting and aggregation

- Weight grid values by their actual positive-area intersections with each result piece; boundary cells contribute only their overlap. Map visibility, cell centres and full touched-cell area do not determine their weights. Real sub-1 m² indicator intersections contribute under the technical geometry tolerance; the classification hit threshold does not apply.
- Use each metric's own valid area and source. Keep grid and stand total volume separate; never blend, add or silently substitute them. Missing species values are independent of available total volume and must not be inferred by subtraction.
- Summaries combine full-precision metric statistics before final rounding. Do not average already rounded polygon fields or weight a partially covered metric by the entire piece area.
- Weight stand metrics by actual result-piece area. Growth remains an area-weighted mean of stand growth rates using stand volume, rather than a ratio mixing stand growth with grid stock.
- Weight sawlog prices by represented sawlog cubic metres from unrounded stand sawlog volume and piece hectares. With one supplied unit price, every nonempty eligible group has that price; groups without eligible sawlogs have a null price. Price eligibility uses original values even when a tiny positive displayed volume rounds to zero.
- Calculate sawlog euro amounts from unrounded represented sawlog volume times the supplied €/m³. Complete group values sum exact piece amounts, then round to cents; they are totals rather than weighted mean prices. Retained stand overlaps can duplicate monetary contributions. Pulpwood valuation, external price feeds, whole-forest value and scenario income forecasts remain outside scope.
- Use original grid mean ages for age-band membership. The shares describe area with valid age, rather than stand counts or individual-tree age distribution. Disclose age coverage over the full reporting domain.
- Soil and drainage classifications are independent. Peatland and natural-mire hectares describe source-classified conditions at source date, rather than certification of present ecological condition.

Acceptance: reproduce the [boundary-weighting example](../architecture/indicator-calculations.md#exact-intersections-and-volume-means) and [partial-coverage/age example](../architecture/indicator-calculations.md#tierclass-summaries-and-metric-coverage), retaining their metric-specific denominators and rounding only after aggregation.

## IO-03 Unavailable and partial values

- Numeric zero is valid. Null, boolean, text, negative and non-finite volume/age inputs are unavailable rather than zero. Missing required schema fields are fatal under [WF-07](workflow.md#wf-07-failure-cancellation-and-observability), unlike missing individual numeric values.
- For a density or age metric, complete valid coverage is available; some valid coverage permits a mean/share with partial status; no valid coverage gives null/blank with an explicit unavailable status. Preserve valid and unknown hectares independently for each metric.
- For peat/mire area totals, any unknown classification area leaves the requested total blank. Expose observed matching hectares as a lower bound, with valid/unknown area. Complete known coverage permits a genuine zero total.
- Apply the same completeness policy to calculated sawlog value: valid zero sawlog stock gives zero euros, while missing/invalid stock gives null. Partial group totals and empty groups stay blank; coverage retains the known euro subtotal and valid/unknown hectares. Do not treat missing stock as zero value.
- A successfully empty grid response may yield unavailable grid metrics while forest classification completes. There is no stand-value fallback for grid metrics.
- Unavailable and excluded indicator scope follows [IO-01](#io-01-indicator-catalogue).
- An empty tier/class has zero land area and feature count, with null density/age-share values. Missing metrics must remain distinguishable from known zero through both output formats.
- Retain `indicator_coverage`, including its own availability statuses and exact statistics. Independent `indicator_status` and per-indicator diagnostic interfaces are removed. Do not produce per-value, contradictory-soil/drainage or area-roundoff diagnostic records; preserve numerical corrections, fatal invariants, source/geometry diagnostics and operational logging.

## IO-04 Labels, order and precision

- Put identity and classification before indicators, and coverage/provenance after them. The riparian criterion check uses the translated label for stable field `check_riparian_buffer`; its `MATCH`, `NO_MATCH` and `UNKNOWN` values remain language-neutral. Use the catalogue order in QGIS attributes/forms, workbook summaries, metric coverage and calculation notes.
- Source-dependent labels start with **Kuvio / Stand** or **Hila / Grid**, followed by the attribute and explicit units. Availability belongs in statuses/notes.
- Sawlog price/value labels name the assortment and distinguish €/m³ from €. Their coverage and notes identify the user price assumption and stand-stock source.
- Provide localized field groups and explain ground area versus tree basal area in forms and workbook notes. Preserve aliases, grouping and presentation when reopening the GeoPackage.
- Publish volume densities as whole m³/ha and hectares to 0.01 ha, rounding exact halves up. These are exported numeric values as well as display choices. Other decimal results and numeric coverage statistics display two decimals; age shares/coverage and feature counts use whole numbers.
- Publish calculated sawlog euro amounts to cents, half up, after calculation or group summation. Retain exact unrounded euro subtotals in coverage.
- Preserve full precision for calculations, coverage statistics and aggregation inputs. Round summaries only after aggregation. Nulls stay blank. Explain that rounded shares may total 99% or 101% and small positive quantities can display as zero.
- Explain that reporting precision is not measurement accuracy, and independently covered species means need not sum to grid total. Stand and grid totals may also differ legitimately.

## IO-05 Files and publication

Every successful run produces `<basename>.gpkg` and `<basename>.xlsx` with the same basename. Reject existing outputs. A caught publication failure or cancellation attempts cleanup of both partial files under [WF-07](workflow.md#wf-07-failure-cancellation-and-observability).

The GeoPackage contains:

- Exactly one spatial analysis result dataset of classified forest polygons, each carrying all six tier classes, ordinary criterion checks (including riparian buffer), parent-overlap flag, indicators, metric coverage, source/rule identifiers and classification context.
- AOI-clipped source snapshots with original attributes and source identifiers, including grid cells and groundwater. Water inputs are represented by one derived `buffered_water_evidence` layer containing the combined Ranta10 buffer footprint; do not export raw Ranta10 source geometries as additional snapshot layers.
- Source coverage and run metadata, including parameters, the user-supplied sawlog price and its interpretation/source, run/language identity, source endpoint/type/provider/CRS, retrieval and available measurement/update dates, field provenance, limitations, attribution and prototype identity. Retain individual retrieval/availability rows for all three Ranta10 products, separate from derived-buffer coverage.
- Full-precision per-metric coverage/statistics sufficient to explain aggregation, independently of rounded displayed results.
- Run metadata records the result-fragment threshold, excluded polygon count/area and parents with no retained polygons under [CL-01](classification.md#cl-01-reporting-domain-and-geometry). These fragments contribute to neither result feature counts nor workbook summaries. Riparian provenance records the fixed 30 m distance and units, EPSG:3067 geometry policy, candidate query extent/filter strategy, source-qualified references and update dates, source retrieval and derived-buffer counts, union/clipping policy, and limitation that successful empty evidence does not prove full source coverage.

The valid Excel workbook contains four localized worksheets: tier/class summaries, source coverage, metric coverage and calculation notes/limitations. Report sensitive/economic and relevant unknown classes separately for each tier, with sources, statuses, valid/unknown hectares and observed partial quantities. Retain formulas/meaning, reporting domain, dates, exclusions, attribution and prototype notice. A workbook must reopen in standard XLSX readers; manual Microsoft Excel acceptance remains separately tracked.

Neither successful requests, feature counts nor mapped overlap alone establish complete service coverage. Both formats must communicate that limit. Do not create separate result datasets per tier or turn scenario inputs into modeled scenario impacts.

## IO-06 Map review and run retention

- After wizard success, retain each run beneath Results without removing configured sources or earlier runs.
- Include eighteen filtered project views (six tiers x three classes) and hidden-by-default clipped snapshots loaded from that run GeoPackage, including the single combined buffered-water evidence layer. Filtered views reference the same result dataset rather than creating extra outputs. Initially only the All out tier group is visible. Users switch tiers through layer-tree group visibility by turning the current tier group off and the desired group on.
- Check every class child view in all six tier groups. Check every snapshot child inside its initially unchecked parent group. Enabling a previously hidden group immediately reveals its checked children.
- Every view and snapshot must remain readable with the row count implied by its filter or captured source. Opening a later view or another run must not disrupt readers of an earlier view.
- Use sensitive red/orange, economic green and unknown grey for the class views. Tier and category labels follow the QGIS language. The complete classified dataset is available in the GeoPackage and can be added separately.
- Keep Results above References above Basemaps after setup and publication. Changing map scale or toggling source rendering must not change analysis values.

Acceptance covers reopened bilingual GeoPackage/workbook artifacts, field order/value alignment, independent metric coverage, partial/zero/null behavior, rounding after aggregation, persisted forms and repeated-run retention. Outstanding visual desktop checks remain in [open questions](../open-questions.md).
