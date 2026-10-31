# Indicator calculations and aggregation

This reference owns intersection weights, metric statistics and aggregation.
[IO-01–IO-04](../specs/indicators-and-outputs.md) own observable indicator behavior;
[output schema](output-schema.md) owns field layout and coverage serialization;
[indicator design](indicators.md) owns evidence and accuracy limits.

The reporting domain is analyzed forest represented by classified polygons.
Each tier partitions that same domain. Grid boundaries supply independent
evidence without introducing classification boundaries.

## Comparing indicators and reporting precision

Both total-volume estimates retain separate columns, source IDs and statistics.
They are not blended, added together or substituted when one is unavailable.
Species means use their own valid-area denominators. When species coverage differs,
adding pine, spruce and deciduous means need not reproduce the grid total, even
when the represented cubic metres nearly agree. A stand total is a separate source
estimate and need not agree with either. Inspect each metric's coverage before
comparing values; never replace missing species values with zero to force agreement.
Stand growth always uses stand volume, never grid volume. Stand `meanage` remains
required by the retained schema contract, but age shares use overall grid `AGE`.

The rounding increments and visible precision are specified in
[IO-04](../specs/indicators-and-outputs.md#io-04-labels-order-and-precision).
Apply half-up rounding to exported numeric volume/area fields after aggregation,
not just their display labels. Other decimal fields use the viewer's locale;
GeoPackage field presentation persists on reopen. Calculation inputs, coverage
JSON and coverage-sheet statistics retain full precision. See the
[precision assessment](indicators.md#reporting-precision-and-accuracy) for limits.

## Exact intersections and volume means

For a result piece `P` and grid cell `G_i`, use EPSG:3067:

```text
A(P) = area(P) / 10000                      # reporting hectares
a_i(P) = area(P ∩ G_i) / 10000              # intersected hectares
valid_area_m = Σ a_i(P) with a valid value for metric m
represented_volume_m3 = Σ a_i(P) × value_im
mean_m = represented_volume_m3 / valid_area_m
unknown_area_m = A(P) - valid_area_m
```

Retain intersections whose areas exceed the
[geometry tolerance](calculations.md#area-and-geometry). A genuine
0.5 m² fragment contributes; edge/point contact does not. The classification hit threshold does not apply to indicators. Do not use nominal 256 m² cells,
cell centres, full touched-cell areas, source area attributes or unweighted means.
Per-hectare values remain unchanged densities within cells: multiply by intersected
hectares once. This allocates the source estimate uniformly within the cell; it
does not measure sub-cell variation or establish better accuracy.

For example, 64 m² at 100 m³/ha and 192 m² at 300 m³/ha represent 6.4 m³ over
0.0256 ha: **250 m³/ha**. Stand volume 200 on the same polygon remains
**Kuvio kokonaistilavuus = 200**, independently of **Hila kokonaistilavuus = 250**.

Volume and age validity follows
[IO-03](../specs/indicators-and-outputs.md#io-03-unavailable-and-partial-values).
Missing species values are independent of total volume and are not inferred by
subtraction. No valid area gives null and `UNKNOWN_FIELD_OR_VALUE`. Some valid
area gives its mean with `PARTIAL` status and unknown hectares disclosed. Complete
valid coverage gives `AVAILABLE`. These statuses belong to metric coverage.
Tiny unknown-area differences within tolerance are clamped to zero;
larger negative unknown areas are invariant failures that stop publication.

For stand density values, valid area is the actual result-piece area and the
numerator is `stand_value × piece_area_ha`; missing values have zero valid area.
Do not use original uncut stand area or grid-covered area as the stand weight.
Growth is `100 × stand.volumegrowth / stand.volume`, requiring positive
stand volume and a valid increment. Zero growth with positive volume is valid. Provider definitions do not settle the estimate's exact period,
gross/net basis or timing; see [growth design and evidence](indicators.md#growth-percentage).

## Sawlog stumpage price

Require a finite positive user-supplied price `p` (€/m³) before retrieval or
output mutation. Use the original stand `sawlogvolume` (m³/ha) for eligibility,
not its rounded exported field. For a result piece of `A` hectares with valid
positive sawlog density `v`, publish `p`, retain represented sawlogs `A × v`
in m³ and the price accumulator `p × A × v`. Invalid, missing, negative,
non-finite or known-zero sawlog volume gives null price. The required source
schema remains fatal if absent.

For a tier/class group, divide summed price accumulators by summed eligible
represented sawlog m³. A nonempty eligible group has the supplied price;
without eligible volume it is null. Coverage retains valid/unknown hectares
and exact weighting statistics. Run metadata and calculation notes identify
the input as a user assumption and the stand sawlog field as its applicability
source. This prices sawlogs only, without pulpwood derivation or whole-forest valuation.
[ADR-0014](adr/0014-user-supplied-sawlog-price.md) records the scope decision.

## Calculated sawlog value

`sawlog_value_eur = original_piece_area_ha × stand.sawlogvolume × supplied_price_eur_m3`.
Both area and density are unrounded. The supplied price is per cubic metre,
not per square metre. For 1.4772514669427148 ha at 342.71 m³/ha and 10 €/m³,
represented stock is 506.26885023593775 m³ and the amount is
5062.688502359378 €, published as **5062.69 €**. Multiplying the rounded
1.48 ha and 343 m³/ha would give a different, incorrect amount.

Known nonnegative stand sawlog density and valid price give a known value;
zero density gives zero euros, even though its unit-price result is null.
Missing, invalid, negative or non-finite sawlog values give null value.
Coverage retains independent valid/unknown hectares, represented sawlog m³
and `weighted_sum` as the unrounded known euro subtotal. Complete tier/class
totals sum those amounts before half-up rounding to cents. With unknown area,
the total remains null and coverage exposes the known subtotal; an empty group
also has null value. A total is never derived from rounded polygon amounts.

This sawlog-only amount retains duplicate contributions from overlapping
stands. It is not a whole-forest value or an income/harvest forecast.
[ADR-0016](adr/0016-calculated-sawlog-value.md) extends the previous price-only scope.

## Grid ages and categorical area totals

Age shares use **grid-cell mean age**, not stand counts or individual-tree age
distributions. Divide matching-band hectares by valid-age hectares, and disclose
valid/unknown age hectares and coverage of the full reporting area. No valid ages
gives three null/blank shares. Use original unrounded age to select a band.

Apply [IO-04](../specs/indicators-and-outputs.md#io-04-labels-order-and-precision)
after deriving shares from full-precision areas. Display ages in years without
decimals; never aggregate rounded shares.

Accepted soil/drainage codes and matching categories are defined in the
[input contract](source-layer-requirements.md#accepted-indicator-categories).
Recognized nonmatching codes contribute known zero. Soil and drainage have
independent coverage; neither classification overrides the other.

Complete classification coverage permits matching-hectare totals, including a
known zero. Any unknown hectares leave the requested total null/blank with
partial/unknown status; observed matching hectares remain a **lower bound**.
A 64 m² match contributes 0.0064 ha; a 0.5 m² match contributes 0.00005 ha.
These source-date classifications do not certify ecological condition. The
grid indicators are separate from the adopted parent-stand `SOILTYPE` sensitivity
screen in [CL-02](../specs/classification.md#cl-02-six-cumulative-tiers).

## Tier/class summaries and metric coverage

Every summary input row must contain the current `indicator_coverage` record.
A missing record is an internal schema error and stops the run. Missing individual
metric statistics within that record remain unknown under the current coverage
policy.

Combine full-precision sufficient statistics separately per tier/class:

- Density mean: summed represented m³ / summed metric-valid hectares,
  independently for grid total, stand total, pine, spruce, deciduous and sawtimber.
- Growth and basal area: summed area-weighted stand values / their valid
  result-piece hectares. Growth remains a mean of stand rates, not a new ratio
  of group growth and volume.
- Age share: 100 × summed band hectares / summed valid-age hectares, rounded
  after division. Age coverage uses full group reporting area.
- Peat/mire total: summed matching hectares only when the entire group reporting
  area has known classification; otherwise disclose lower bound and unknown area.
- Sawlog value: sum exact known euro amounts when the entire group has known
  sawlog stock; otherwise keep the total null and disclose the known subtotal.
- Area: summed actual result-piece hectares regardless of metric coverage.
  Feature count counts pieces. Empty groups have zero area/count and null
  density/age values.

Two 1 ha pieces with grid-valid areas 0.25 ha at 100 and 1 ha at 300 give
**260 m³/ha**, with 1.25 valid ha and 0.75 unknown ha. Stand values 100 and 300
over the complete pieces give **200 m³/ha** over 2 valid ha. Full-piece weighting
of partial grid means would be wrong. If the first grid age is under 20 and the
second over 80, shares are **20%, 0%, 80%**, with exact age coverage 62.5%,
presented as **63%**.

The [coverage schema](output-schema.md#metric-coverage) records these sufficient
statistics in both outputs. Availability belongs in statuses and notes rather
than appended to attribute names.
