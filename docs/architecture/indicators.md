# Indicator design and reporting

This page owns indicator rationale, provider evidence and interpretation limits. The adopted hybrid design is recorded in [ADR-0005](adr/0005-independent-stand-and-grid-indicators.md); evidence retention and precision are recorded in [ADR-0006](adr/0006-evidence-coverage-and-publication.md). The [calculation reference](calculations.md#indicators-and-summaries) owns exact field names, ordering, formulas, accepted values, worked examples and summary contracts.

## Reporting domain and source allocation

Stand geometry preserves the forest-management unit, while independent grid evidence supports finer indicator sampling without introducing new sensitivity boundaries. This choice reports analyzed forest rather than every land type inside the AOI. The exact stand/grid allocation is in the [field dictionary](calculations.md#per-polygon-fields) and [source contract](source-layer-requirements.md).

The checked grid schema lacks separate birch, sawlog and annual-growth fields. [ADR-0011](adr/0011-deciduous-volume-instead-of-birch.md) changes the original bid/project requirement to use grid deciduous volume instead of supporting birch-specific volume. The adopted indicator describes all source-classified deciduous trees and must not be labelled or interpreted as birch-only volume. Sawlogs and growth retain stand evidence. Price has no implemented source. These are deliberate prototype choices rather than a claim that every original procurement indicator is supplied. [Provider grid dictionary](https://www.metsakeskus.fi/sites/default/files/document/hila-koodisto-ja-tietokantakuvaus.xlsx), [procurement Annex 2](../bid/liite2_hankinnankohteenkuvaus.pdf).

## Area-weighted evidence

Exact intersection weighting allocates the source estimate uniformly within each intersected cell; it does not measure sub-cell variation or establish better accuracy. The [intersection formulas and worked example](calculations.md#exact-intersections-and-volume-means) define that allocation. [Pure indicator implementation](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/grid_indicators.py), [grid sampling](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/grid_sampling.py).

Metric coverage describes which part of the reporting area supports each estimate. Different species coverage and independent stand/grid estimates can explain apparent disagreement between reported values. A successful source request alone cannot establish complete inventory coverage. Use the [comparison guidance](calculations.md#comparing-indicators-and-reporting-precision) and [summary example](calculations.md#tierclass-summaries-and-metric-coverage) when interpreting partial values.

## Growth percentage

The [growth formula](calculations.md#stand-tree-indicators--kuvio-puustotunnukset) uses stand increment and stock. The saved [Metsäkeskus 2.1.3 workbook](../references/metsakeskus/tiedosto-tietomallikaavio-mv_ey_2-1-3-metsakeskuksen-tietomallin-uudistus.xlsx), **MV GeoServer** A33:B33 and A36:B36, defines m³/ha and m³/ha/year, supporting a percentage-per-year interpretation. [Saved stand XSD](../references/metsakeskus/stands/describe-feature-type.xsd).

Summaries use the area-weighted mean of valid per-stand percentages, using actual result-piece hectares. They do not divide total annual growth by total stock: that alternative weights by standing stock and describes a different statistic. For equal 1 ha pieces, stock/growth values 100/10 and 300/3 give stand rates 10% and 1%, an adopted mean of 5.5%; the alternative ratio is 3.25%.

The ratio is compatible with the standing-volume increment relationship in [iForest equation 1](https://iforest.sisef.org/contents/?id=ifor0635-005), but the provider definitions do not establish current versus periodic, gross versus net increment or the exact denominator date. Avoid stricter CAI/PAI labels. Other period formulas require observations not supplied by these fields; see the forestry discussion in [FRM 503, printed pp. 17–18](https://funaab.edu.ng/funaab-ocw/opencourseware/Forest%20Management%20Techniques.pdf).

## Ages, soil and drainage

Grid mean age supports area shares of inventory-cell mean ages; it does not describe stand counts or the ages of individual trees. The [age and categorical-area contract](calculations.md#grid-ages-and-categorical-area-totals) defines bands, accepted codes, unknown coverage and lower-bound reporting.

Soil and drainage describe independent source classifications. Source-classified natural mire is not all undrained land or a certification of current ecological condition. The provider code definitions remain the evidence for interpreting these categories. [Soil code list](https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/metsarek/codeschemes/maalaji-v_1_0/codes), [drainage code list](https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/metsarek/codeschemes/kuivatustilanne-v_1_0/codes).

These area indicators cover analyzed forest; open mires outside stands require a separate scope/source choice. They do not add sensitivity criteria. Alternative raster and naturalness evidence remains in [deferred sources](deferred-sources.md).

## Reporting precision and accuracy

The [publication contract](calculations.md#comparing-indicators-and-reporting-precision) owns rounding increments, retained precision and interpretation of rounded results. Published numeric values are rounded after aggregation. [Publication precision adapter](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/result_precision.py).

Reporting precision is a project choice, not a forestry standard or measurement-accuracy claim. Metsäkeskus's [17 March 2026 quality statement, pp. 6–7](https://www.metsakeskus.fi/sites/default/files/document/metsavaratiedon-laatuseloste.pdf) distinguishes stand-volume quality descriptions from individual interpretation-unit accuracy; stand targets cannot be transferred to arbitrary clipped cells or species estimates. Its forest-use-notification [0.1 ha form convention](https://www.metsakeskus.fi/sites/default/files/document/taytto-ohje-metsankayttoilmoitus.pdf) concerns a different reporting purpose and does not prescribe this tool's 0.01 ha choice.
