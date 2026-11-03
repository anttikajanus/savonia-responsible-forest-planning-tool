# Indicator design and reporting

This page adds indicator rationale, provider evidence and interpretation limits.
For the complete published indicator list and required meanings, see
[IO-01](../specs/indicators-and-outputs.md#io-01-indicator-catalogue); the
[output schema](output-schema.md) defines each stored field, the
[calculation reference](indicator-calculations.md) owns formulas and
aggregation, and [source-layer requirements](source-layer-requirements.md)
own accepted input values. This page does not repeat those catalog, field or
calculation definitions. The adopted hybrid design is recorded in
[ADR-0005](adr/0005-independent-stand-and-grid-indicators.md); evidence
retention and precision are recorded in
[ADR-0006](adr/0006-evidence-coverage-and-publication.md).

## Reporting domain and source allocation

Stand geometry preserves the forest-management unit, while independent grid evidence supports finer indicator sampling without introducing new sensitivity boundaries. This choice reports analyzed forest rather than every land type inside the AOI. The exact stand/grid allocation is in the [field dictionary](output-schema.md#per-polygon-fields) and [source contract](source-layer-requirements.md).

[ADR-0005's analysis-unit rationale](adr/0005-independent-stand-and-grid-indicators.md#analysis-unit-rationale)
explains why missing grid attributes are neither reconstructed through provider
methods nor inferred by distributing stand values to grid cells.

The checked grid schema lacks separate birch, sawlog and annual-growth fields.
The [provider grid dictionary](https://www.metsakeskus.fi/sites/default/files/document/hila-koodisto-ja-tietokantakuvaus.xlsx)
supports that source limitation. The current indicator selection is in
[IO-01](../specs/indicators-and-outputs.md#io-01-indicator-catalogue); the scope
decision and procurement distinction are recorded in [ADR-0011](adr/0011-deciduous-volume-instead-of-birch.md).

## Area-weighted evidence

Grid indicators allocate each cell's estimate uniformly within its intersected
area. This does not measure sub-cell variation or establish better accuracy;
the [calculation reference](indicator-calculations.md#exact-intersections-and-volume-means)
owns the weighting formula and examples.

Metric coverage describes which part of the reporting area supports each estimate. Different species coverage and independent stand/grid estimates can explain apparent disagreement between reported values. A successful source request alone cannot establish complete inventory coverage. Use the [comparison guidance](indicator-calculations.md#comparing-indicators-and-reporting-precision) and [summary example](indicator-calculations.md#tierclass-summaries-and-metric-coverage) when interpreting partial values.

## Sawlog price assumption

The sawlog price is an explicit user assumption, not a provider price estimate.
The saved Metsäkeskus 2.1.3 model workbook's MV GeoServer rows 34–35 define
sawlog and pulpwood densities in m³/ha. The chosen price applies to sawlogs;
it is not an all-timber average or whole-forest valuation. The calculation
reference owns eligibility, weighting and the separately published calculated
amount. See [ADR-0014](adr/0014-user-supplied-sawlog-price.md),
[ADR-0016](adr/0016-calculated-sawlog-value.md), the [price contract](indicator-calculations.md#sawlog-stumpage-price),
and the [value contract](indicator-calculations.md#calculated-sawlog-value).

## Growth percentage

The [growth formula](indicator-calculations.md#exact-intersections-and-volume-means) uses stand increment and stock. The saved [Metsäkeskus 2.1.3 workbook](../references/service-metadata/metsakeskus/tiedosto-tietomallikaavio-mv_ey_2-1-3-metsakeskuksen-tietomallin-uudistus.xlsx), **MV GeoServer** A33:B33 and A36:B36, defines m³/ha and m³/ha/year, supporting a percentage-per-year interpretation. [Saved stand XSD](../references/service-metadata/metsakeskus/stands/describe-feature-type.xsd).

The ratio is compatible with the standing-volume increment relationship in [iForest equation 1](https://iforest.sisef.org/contents/?id=ifor0635-005), but the provider definitions do not establish current versus periodic, gross versus net increment or the exact denominator date. Avoid stricter CAI/PAI labels. Other period formulas require observations not supplied by these fields; see the forestry discussion in [FRM 503, printed pp. 17–18](https://funaab.edu.ng/funaab-ocw/opencourseware/Forest%20Management%20Techniques.pdf).

## Ages, soil and drainage

Grid mean age supports area shares of inventory-cell mean ages; it does not
describe stand counts or individual-tree age distributions. The [calculation
reference](indicator-calculations.md#grid-ages-and-categorical-area-totals)
owns weighting and unknown-coverage behavior; the [source contract](source-layer-requirements.md#accepted-indicator-categories)
owns accepted codes.

Soil and drainage describe independent source classifications. Source-classified natural mire is not all undrained land or a certification of current ecological condition. The provider code definitions remain the evidence for interpreting these categories. [Soil code list](https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/metsarek/codeschemes/maalaji-v_1_0/codes), [drainage code list](https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/metsarek/codeschemes/kuivatustilanne-v_1_0/codes).

These area indicators cover analyzed forest; open mires outside stands require a separate scope/source choice. They do not add sensitivity criteria. Alternative raster and naturalness evidence remains in [deferred sources](deferred-sources.md).

## Reporting precision and accuracy

[IO-04](../specs/indicators-and-outputs.md#io-04-labels-order-and-precision) owns visible rounding increments; the [calculation contract](indicator-calculations.md#comparing-indicators-and-reporting-precision) owns retained precision and publication mechanics. Published numeric values are rounded after aggregation. [Publication precision adapter](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/result_precision.py).

Reporting precision is a project choice, not a forestry standard or measurement-accuracy claim. Metsäkeskus's [17 March 2026 quality statement, pp. 6–7](https://www.metsakeskus.fi/sites/default/files/document/metsavaratiedon-laatuseloste.pdf) distinguishes stand-volume quality descriptions from individual interpretation-unit accuracy; stand targets cannot be transferred to arbitrary clipped cells or species estimates. Its forest-use-notification [0.1 ha form convention](https://www.metsakeskus.fi/sites/default/files/document/taytto-ohje-metsankayttoilmoitus.pdf) concerns a different reporting purpose and does not prescribe this tool's 0.01 ha choice.
