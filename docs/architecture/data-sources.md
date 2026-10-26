# Data sources and evidence contract

This page defines the prototype's configured sources and evidence limits.
Provider observations were recorded on 23–26 October 2026; individual checks
retain their evidence dates below. [ADR-0003](adr/0003-provider-field-source-contracts.md)
explains why provider fields, rather than saved XSD contents, determine readiness.

## Required sources

Eight WFS layers are required. The three protected-area layers form one interpretation group but remain separate required inputs. The exact registry is [sources.py](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py); field requirements, accepted aliases, identifier fallbacks, display scales and selected-feature snapshot handling are maintained in [source-layer requirements](source-layer-requirements.md).

| Product | Endpoint | Feature type / selection | Contribution |
| --- | --- | --- | --- |
| Metsäkeskus stands | `https://avoin.metsakeskus.fi/rajapinnat/v2/stand/ows` | `v2:stand` | Parent geometry, stand volume, sawlog volume, growth, optional basal area |
| Metsäkeskus habitats | `https://avoin.metsakeskus.fi/rajapinnat/v2/habitat/ows` | `v2:habitat` | Section 10 and other valuable habitat criteria |
| Metsäkeskus inventory grid | `https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows` | `v2:gridcell` | Independent volume, age, soil and drainage indicators |
| SYKE state-owned protected areas | `https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs` | `PS.ProtectedSitesValtionOmistamaLuonnonsuojelualue` | Active protected-area criterion |
| SYKE private-land protected areas | Same protected-sites endpoint | `PS.ProtectedSitesYksityistenMaillaOlevaLuonnonsuojelualue` | Active protected-area criterion |
| SYKE wilderness | Same protected-sites endpoint | `PS.ProtectedSitesEramaaAlue` | Active protected-area criterion |
| SYKE conservation programmes | `https://paikkatiedot.ymparisto.fi/geoserver/syke_luonnonsuojeluohjelma_alueet/wfs` | `syke_luonnonsuojeluohjelma_alueet:Luonnonsuojeluohjelmaalueet` | Programme criterion, distinct from established protection |
| SYKE groundwater | `https://paikkatiedot.ymparisto.fi/geoserver/syke_vhspohjavesi/wfs` | `syke_vhspohjavesi:VHS2022_Pohjavesi` | All returned polygon footprints; Balance and higher |

Metsäkeskus and SYKE list their services in the [Metsäkeskus interface directory](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/aineistot-paikkatieto-ohjelmille/rajapinnat) and [SYKE service directory](https://www.syke.fi/fi/ymparistotieto/avoimet-rajapinnat/paikkatietorajapinnat). WMS is map context; analysis uses vector WFS. `inspire_ps` contains multiple feature families: a Natura type does not satisfy the required protected/wilderness contract. Compare the provider's [Natura dictionary](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/Natura.pdf) with the [protected/wilderness dictionary](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/Luonnonsuojelujaeramaaalueet.pdf).

Ranta10 is disabled and not retrieved. OpenStreetMap is display context and does not enter classifications or exported analysis snapshots. MY, potential protected sites, recreation, water buffers and peatland sensitivity sources are excluded; [deferred sources](deferred-sources.md) records alternatives without activating them.

## Readiness and normalization

The [source-layer contract](source-layer-requirements.md) owns field readiness, alias priority, source identity and normalization. Setup and analysis use the same provider-field contract; schema readiness remains distinct from valid feature values and complete metric coverage. [Contract implementation](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/source_readiness.py), [QGIS-facing checks](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/source_layers.py).

Saved XSD metadata is provenance rather than a readiness authority. Its parser includes global feature declarations among properties, so it cannot define the required provider fields. That metadata defect remains separate from provider-field readiness. [ADR-0003](adr/0003-provider-field-source-contracts.md), [OGC DescribeFeatureType response semantics](https://docs.ogc.org/is/09-025r2/09-025r2.html#_describe_feature_type_operation), [QGIS provider API](https://api.qgis.org/api/4.2/classQgsVectorDataProvider.html).

## Provider evidence

Recreate the ignored [local reference artifacts](../references/README.md) with
`python scripts/download_references.py`. The versioned
[download manifest](../references/manifest.json) owns request URLs and filenames;
`retrievals.json` records UTC retrieval times, byte counts and SHA-256 hashes for
completed downloads. Cached files are reused unless invalid or explicitly
refreshed. Failed requests preserve existing copies and produce a nonzero exit
status after other entries are attempted. The script downloads service metadata
and documentation, without feature records or recursive imported-XSD retrieval.
Capabilities/XSD files establish advertised types, CRS and property definitions
at capture time; they contain no representative feature records. Keep dated
observations separate from subsequent refreshes of these mutable local artifacts.

| Evidence | Established fact | Limit |
| --- | --- | --- |
| Saved stand XSD + Metsäkeskus 2.1.3 **MV GeoServer** workbook sheet | `standid`, `meanage`, `volume`, `sawlogvolume`, `volumegrowth` exist in the reduced WFS model; age is years, stock/sawlogs m³/ha and annual growth m³/ha/year. | Optional nullable decimal fields do not establish populated or valid values. The wider GeoPackage model is not proof of WFS fields. |
| Saved habitat XSD + **EY GeoServer** sheet | `habitattype` is the controlling property; workbook links it to the official habitat-type code set. | Schema does not establish current code frequencies or inventory completeness. |
| Protected-sites capabilities and all three XSDs, refreshed 26 October | Separate state/private/wilderness types advertise EPSG:3067; schemas include `olotila`, `tyyppilyhenne`, `kohdetyyppi`. | Not a sample of active/inactive values or proof of geographic completeness. |
| Saved programme capabilities/XSD | Exact typename, EPSG:3067, `lsoaluetunnus`, `luokka` and optional nullable `subtype`. | Current class/subtype distribution and completeness are not verified by XSD. |
| Grid schema and three-cell bounded request checked 25 October | Direct total/pine/spruce/deciduous fields, age, soil/drainage; sample showed a null spruce value and different measurement/update dates. | Raw samples were not saved. Three cells do not estimate regional/national coverage or null prevalence. |
| Groundwater capabilities/XSD downloaded 26 October and general provider dictionary | Exact `syke_vhspohjavesi:VHS2022_Pohjavesi` type advertises EPSG:3067 and its schema is retained; fields include `pvaluetunnus`, `pvalueeutunnus`, `pvalueluokka`, nullable `muutospvm` (`xsd:dateTime`) and `geom` (`gml:MultiSurfacePropertyType`). | No representative feature values were retrieved. The general dictionary does not independently define this service's complete field semantics. |

The local [2.1.3 workbook](../references/metsakeskus/tiedosto-tietomallikaavio-mv_ey_2-1-3-metsakeskuksen-tietomallin-uudistus.xlsx), [provider model update page](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/tietojen-yllapito/tietomallin-uudistus), and [GeoPackage guide](https://www.metsakeskus.fi/sites/default/files/document/tiedosto-geopackage-sisaltoohjeet-tietomalli-2-0.pdf) establish modeled units and code relationships. WFS is a narrower product; stand `PROPORTIONPINE`/`PROPORTIONSPRUCE`/`PROPORTIONOTHER` definitions did not establish volume proportions. Current species metrics use direct grid volumes instead.

The grid evidence came from the [DescribeFeatureType request](https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows?service=WFS&version=2.0.0&request=DescribeFeatureType&typeNames=v2:gridcell), [grid dictionary](https://www.metsakeskus.fi/sites/default/files/document/hila-koodisto-ja-tietokantakuvaus.xlsx), and a [three-cell request](https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=v2:gridcell&count=3&outputFormat=application/json&srsName=EPSG:3067&bbox=350000,6900000,352000,6902000,EPSG:3067). The sample recorded measurement 13 June 2025 and database update 9 April 2026. `TREEDATADATE`, `UPDATETIME` and retrieval time have separate meanings; a later update/retrieval is not evidence of a newer forest observation. The [December 2025 grid product description](https://www.metsakeskus.fi/sites/default/files/document/tietotuotekuvaus-hila-aineisto.pdf) describes 16 m estimates; planned product changes must be verified against the actual delivered data.

## Interpretation and geographic limits

Habitat types 1 and 5 trigger Section 10 and type 3 triggers other valuable habitat, following the workbook code reference and [provider guide](https://www.metsakeskus.fi/sites/default/files/document/tiedosto-geopackage-sisaltoohjeet-tietomalli-2-0.pdf). Other returned codes are fatal interpretation errors. Mapped habitat inventories are incomplete; no mapped hit does not establish absence of a habitat. [Provider data quality](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/tietojen-yllapito/tiedon-laatu).

Stand-wide promotion is the prototype's conservative spatial assumption. The [Forest Act](https://www.finlex.fi/fi/lainsaadanto/saadoskokoelma/1996/1093), [2026 amendment](https://www.finlex.fi/fi/lainsaadanto/saadoskokoelma/2026/448), and [Metsäkeskus interpretation guidance](https://www.metsakeskus.fi/sites/default/files/document/metsalain-10-pykalan-kohteiden-tulkintasuositus.pdf) provide background; operational/legal use needs current authoritative guidance and site evidence.

Protected records require normalized status `voimassa` and a category recognized by the [current interpreter](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/classification.py). Every other returned status/category stops the run, including apparently inactive values. The [protected-area metadata](https://ckan.ymparisto.fi/dataset/luonnonsuojelu-ja-eramaa-alueet) describes updates, overlapping records and exclusion of Åland; it does not independently verify the plugin's entire accepted-status mapping.

The [programme contract](source-layer-requirements.md) requires interpretable identifiers/classes and permits absent subtype. Provider metadata describes indicative boundaries, overlap, exclusions and historical records retained despite later protection/programme changes. Programme membership therefore remains separate from established protection; outputs retain programme attributes and observed protected overlap. [Programme metadata](https://ckan.ymparisto.fi/fi/dataset/luonnonsuojeluohjelma-alueet), [attribute dictionary](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/LuonnonsuojeluOhjelmaAlueet.pdf).

Groundwater uses all returned polygon footprints without `alueluokka` or `subtype` filtering. The general [groundwater metadata](https://ckan.ymparisto.fi/dataset/pohjavesialueet) and [attribute reference](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/Pohjavesialueet.pdf) distinguish groundwater/recharge areas and modern 1/2/E classifications, but these are not a provider mapping to prototype sensitivity tiers. Those documents' CRS and update descriptions are not independent checks of the configured VHS2022 service. Its dataset-specific credit is documented in [distribution](distribution.md#analysis-data-attribution).

## WFS retrieval success

Only WFS 2.0 is supported, with managed sources configured as WFS 2.0.0.
[ADR-0010](adr/0010-wfs-2-only.md) records why WFS 1.x compatibility, downgrade
fallback and legacy exception handling are outside the planned scope.

An exhausted iterator alone cannot establish successful retrieval. In the QGIS 4.2.3 HTTP-503 fixture, provider errors became visible only after queued provider `MetaCall` events were delivered. Before reusing a provider, drain earlier queued errors and clear the error list; after consuming/closing its iterator, dispatch only that provider's queued `MetaCall` events in its owning thread and inspect errors before accepting coverage. The current implementation is in [source_loading.py](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/source_loading.py).

This is a version-specific application policy supported by the local regression and QGIS's signal path, not a guarantee for arbitrary providers. It avoids a duplicate query, global event processing or relying on unrelated panel messages. [QGIS WFS provider](https://github.com/qgis/QGIS/blob/release-4_2/src/providers/wfs/qgswfsprovider.cpp), [shared data](https://github.com/qgis/QGIS/blob/release-4_2/src/providers/wfs/qgswfsshareddata.cpp), [Qt targeted event dispatch](https://doc.qt.io/qt-6/qcoreapplication.html#sendPostedEvents).

Managed sources use WFS 2.0.0. HTTP failures and HTTP-200 OWS `ExceptionReport` responses stop publication. QGIS 4.2's parser does not similarly recognize WFS 1.0 `ServiceExceptionReport`; provider error draining cannot fix that compatibility limit. Preserve successful-empty, 503, OWS-exception and unrelated-provider regression cases. [QGIS GML parser](https://github.com/qgis/QGIS/blob/release-4_2/src/core/qgsgml.cpp), [WFS downloader](https://github.com/qgis/QGIS/blob/release-4_2/src/providers/wfs/qgswfsfeaturedownloaderimpl.cpp), [OGC WFS 2 exception reporting](https://docs.ogc.org/is/09-025r2/09-025r2.html#_exception_reporting).

Successful empty retrieval is `AVAILABLE` but is not certification of complete geographic coverage. Source request/iteration failures stop the run. Metric nulls are handled independently as documented in [indicators](indicators.md).

## Access and evidence maintenance

For sustained/load-generating SYKE use, obtain the provider-issued application identifier and pass it as `sykeuserid`; keep it outside committed source, fixtures and logs. The plugin saves it in QGIS settings and includes it in SYKE WFS layer URLs. Saving a project intentionally persists those URLs, including the identifier, in `.qgs` or `.qgz` so the layers retain their service connection details. Review layer URLs before sharing or committing a project. This persistence is separate from error-message redaction in [sources.py](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py). See [SYKE service guidance](https://www.syke.fi/fi/ymparistotieto/avoimet-rajapinnat/paikkatietorajapinnat), [request parameter guidance](https://wwwi4.ymparisto.fi/i4/fin/eowiki/kysymys_wcs.html), and the [plugin setup instructions](../../qgis_plugin/README.md#requirements-and-syke-setup).

Future evidence checks should record exact endpoint/type, request date, CRS, required properties and representative sanitized status/code/null formats. Keep schema evidence distinct from feature values, field readiness distinct from metric coverage, and provider facts distinct from application choices. [Outstanding checks](open-questions.md).
