# Example classified forest polygon outputs

These two attribute records were supplied for documentation on 2026-10-27.
They are historical captures from before the 29 October 2026 price and result
inspection changes. New outputs use the current schema linked below. In
particular, the captures contain removed independent status/diagnostic fields
and an excluded price placeholder; no migration of these files is provided.
They illustrate individual features of `classified_forest_polygons` in the
GeoPackage, rather than workbook summary rows. A result feature is a classified
piece of a source stand; it need not represent the whole original stand.

The complete pasted records are available as text:

- [Feature 64, source stand 40962774](feature-64-stand-40962774.txt)
- [Feature 60, source stand 40962772](feature-60-stand-40962772.txt)

The source records use Finnish decimal commas and `epätosi` for false. Tables
below use decimal points and retain the supplied displayed precision. `NULL`
means no numeric value. JSON coverage statistics retain their original precision.
The supplied records do not include geometry, run metadata or source snapshots;
they illustrate interpretation, without establishing reproducibility or provider
accuracy. Neither the prototype nor these results are official or approved by
Savonia.

For authoritative definitions, use the [output schema](../architecture/output-schema.md),
[classification rules](../specs/classification.md), and
[indicator calculations](../architecture/indicator-calculations.md).

## Classification comparison

| Field | Feature 64 | Feature 60 |
| --- | --- | --- |
| `source_stand_id` | `40962774` | `40962772` |
| `class_all_out` | `ECONOMIC` | `ECONOMIC` |
| `class_bau` | `ECONOMIC` | `ECONOMIC` |
| `class_light` | `ECONOMIC` | `ECONOMIC` |
| `class_balance` | `SENSITIVE` | `ECONOMIC` |
| `class_protection` | `SENSITIVE` | `ECONOMIC` |
| `class_superprotection` | `SENSITIVE` | `SENSITIVE` |
| `section10_stand_promoted` | `false` | `false` |
| `source_ids` | `{"programme": ["SSO110426"]}` | `{}` |
| `programme_protected_overlap` | `NO` | `NULL` |

### Feature 64: programme match from Balance onward

The recorded trigger is conservation programme `SSO110426`. Programme areas
enter the cumulative criteria at Balance, so this piece is economic in All out,
BAU and Light, then sensitive in Balance, Protection and Superprotection.
For each of those three sensitive tiers, `tier_rule_ids` records:

```json
{
  "criteria": ["programme"],
  "source_ids": ["SSO110426"],
  "unknown_sources": []
}
```

The other three tiers have empty `criteria`, `source_ids` and `unknown_sources`
lists. The retained programme context is:

| `programme_info` attribute | Supplied value |
| --- | --- |
| `LsoAlueTunnus` | `SSO110426` |
| `Luokka` | `SSO` |
| `Subtype` | `Soidensuojeluohjelma` |
| `Nimi` | `Olvassuon-Oravisuon-Näätäsuon alue` |
| `MuutosPvm` | `Tue Sep 1 00:00:00 1998 GMT` |
| `Lisatieto` | `Ei rantaviivan tai nkrk:n mukainen` |

`programme_protected_overlap: NO` records no qualifying overlap of this
programme-matched piece with recognized active protected-area evidence. Programme
membership and established protection are separate concepts. The retained
`MuutosPvm` is a source attribute, not the analysis date.

### Feature 60: remaining forest in Superprotection

This piece has no recorded sensitivity match in All out through Protection.
Superprotection includes the remaining analyzed forest when required evidence
is available, so its `tier_rule_ids.superprotection` entry is:

```json
{
  "criteria": ["remaining_analyzed_forest"],
  "source_ids": [],
  "unknown_sources": []
}
```

All other tier entries have empty lists. Here `source_ids: {}` means no matched
classification source IDs; it does not mean the analysis used no source data.
`programme_info: []` and `programme_protected_overlap: NULL` indicate that there
is no programme match to assess for overlap. This differs from Feature 64's `NO`.

Both records have `section10_stand_promoted: false`. Neither classification
establishes legal harvesting permission or a harvesting prohibition.

## Indicator values and statuses

The statuses below describe the supplied metric coverage. An `AVAILABLE`
value has complete valid metric coverage under the calculation contract; it
does not certify measurement accuracy. A `PARTIAL` density or age share describes
only the hectares with valid evidence for that metric.

| Field (unit) | Feature 64 value | Status | Feature 60 value | Status |
| --- | --- | --- | --- | --- |
| `area_ha` (ha) | 1.87 | `AVAILABLE` | 2.23 | `AVAILABLE` |
| `total_volume_m3_ha` (m³/ha, stand) | 0 | `AVAILABLE` | 251 | `AVAILABLE` |
| `sawtimber_volume_m3_ha` (m³/ha, stand) | 0 | `AVAILABLE` | 81 | `AVAILABLE` |
| `growth_percent` (%/year, stand) | `NULL` | `UNKNOWN_FIELD_OR_VALUE` | 2.45 | `AVAILABLE` |
| `basal_area_m2_ha` (m²/ha, stand) | 0.00 | `AVAILABLE` | 30.89 | `AVAILABLE` |
| `grid_total_volume_m3_ha` (m³/ha) | 12 | `PARTIAL` | 220 | `AVAILABLE` |
| `pine_volume_m3_ha` (m³/ha, grid) | 10 | `PARTIAL` | 67 | `AVAILABLE` |
| `spruce_volume_m3_ha` (m³/ha, grid) | 1 | `PARTIAL` | 42 | `AVAILABLE` |
| `deciduous_volume_m3_ha` (m³/ha, grid) | 0 | `PARTIAL` | 112 | `PARTIAL` |
| `share_under_20` (%, grid age area) | 86 | `PARTIAL` | 0 | `AVAILABLE` |
| `share_20_80` (%, grid age area) | 14 | `PARTIAL` | 88 | `AVAILABLE` |
| `share_over_80` (%, grid age area) | 0 | `PARTIAL` | 12 | `AVAILABLE` |
| `peatland_area_ha` (ha, grid) | 1.87 | `AVAILABLE` | 0.03 | `AVAILABLE` |
| `natural_mire_area_ha` (ha, grid) | 1.76 | `AVAILABLE` | 0.00 | `AVAILABLE` |
| `stumpage_price_eur_m3` (€/m³) | `NULL` | `OUT_OF_SCOPE` | `NULL` | `OUT_OF_SCOPE` |

Stand total volume and grid total volume are independent source estimates.
In Feature 64 the stand estimate is a known zero, while the grid estimate is
12 m³/ha over a partially covered area. Feature 60 likewise retains both
251 m³/ha (stand) and 220 m³/ha (grid). Do not blend or substitute these values.

Feature 64's growth is unavailable because the growth calculation requires
positive stand volume. Its zero stand volume does not yield a valid growth
percentage. Stumpage price has a different reason for being null in both
records: it is intentionally out of scope.

## Coverage calculations

The displayed polygon areas are rounded. The coverage records retain
**1.8679622677108971 ha** for Feature 64 and **2.234380610422013 ha** for
Feature 60. The following table rounds coverage to six decimals for reading;
the linked text records retain full precision.

| Feature | Metric | Valid ha | Unknown ha | Status |
| --- | --- | --- | --- | --- |
| 64 | Stand total, sawtimber, basal area | 1.867962 | 0 | `AVAILABLE` |
| 64 | Growth | 0 | 1.867962 | `UNKNOWN_FIELD_OR_VALUE` |
| 64 | Grid total, pine, all three age shares | 0.713697 | 1.154265 | `PARTIAL` |
| 64 | Spruce | 0.557240 | 1.310722 | `PARTIAL` |
| 64 | Deciduous | 0.585697 | 1.282265 | `PARTIAL` |
| 64 | Peatland and natural mire | 1.867962 | 0 | `AVAILABLE` |
| 60 | All in-scope metrics except deciduous | 2.234381 | 0 | `AVAILABLE` |
| 60 | Deciduous | 2.222204 | 0.012177 | `PARTIAL` |

For Feature 64, the grid total-volume calculation is:

```text
represented volume / valid area
= 8.51137540676717 m³ / 0.7136968610449103 ha
≈ 11.9258 m³/ha → reported as 12 m³/ha
```

Its age shares use the same 0.7136968610449103 valid hectares. Those hectares
cover **38.20724183682326%** of the polygon, reported as **38%** coverage.
The age shares are derived separately:

```text
under 20: 100 × 0.6145408445210397 / 0.7136968610449103 ≈ 86.1% → 86%
20–80:    100 × 0.09915601652387059 / 0.7136968610449103 ≈ 13.9% → 14%
over 80:  100 × 0 / 0.7136968610449103 = 0%
```

These percentages describe the valid-age area; age is unknown over about
1.154265 ha. They do not establish the age distribution of the entire polygon.
Soil and drainage evidence nevertheless cover the full piece, allowing complete
peatland and natural-mire totals. Metric coverage is independent, even within
one grid source.

Feature 64 also demonstrates a small positive estimate rounded to zero:

```text
deciduous: 0.28094497816807396 m³ / 0.5856968610449103 ha
≈ 0.4797 m³/ha → reported as 0 m³/ha, PARTIAL
```

That displayed zero differs from the stand total's known zero and from a missing
value. Its species metrics have different valid areas, so adding their rounded
means need not reproduce the grid total.

For Feature 60, grid total volume and age have complete coverage. The age shares
are 0%, 88% and 12% over the full polygon. Only deciduous volume has a numeric
evidence gap:

```text
deciduous: 248.01148288538676 m³ / 2.2222035197117065 ha
≈ 111.6061 m³/ha → reported as 112 m³/ha, PARTIAL
```

The unknown deciduous area is 0.012177090710306704 ha, about 0.55% of the piece.
Use `indicator_coverage` for each metric's valid and unknown hectares. Current
outputs retain those statistics without per-value diagnostic records.

Feature 60's natural-mire `matching_area_ha` is exactly zero with complete
drainage coverage. Its displayed 0.00 ha therefore represents a known zero in
the source classification, rather than an unavailable total or a rounded small
positive area.

## Reading the workbook alongside these features

The workbook groups result pieces separately by tier and class. Feature 64
contributes to economic groups in All out–Light and sensitive groups in
Balance–Superprotection. Feature 60 contributes to economic groups through
Protection and the sensitive Superprotection group. These tiers classify the
same land in different ways; adding their areas together repeats the land.

Summaries combine full-precision represented volumes, matching areas and valid
areas before rounding. The displayed polygon values above should not be
averaged directly to recreate workbook summaries. See the
[aggregation contract](../architecture/indicator-calculations.md#tierclass-summaries-and-metric-coverage)
for weighting and treatment of partial evidence.
