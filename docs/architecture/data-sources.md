# Data sources and evidence contract

This page defines the prototype's configured sources and evidence limits.
Provider observations were recorded on 23–26 October 2026; individual checks
retain their evidence dates below. [ADR-0003](adr/0003-provider-field-source-contracts.md)
explains why provider fields, rather than saved XSD contents, determine readiness.

## Required sources

Eight WFS layers are required. The three protected-area layers form one interpretation group but remain separate required inputs. The exact registry is [sources.py](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py); field requirements, accepted aliases, identifier fallbacks and selected-feature snapshot handling are maintained in [source-layer requirements](source-layer-requirements.md).

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

Ranta10 is disabled and not retrieved. MML WMTS basemaps and OpenStreetMap are display context and do not enter classifications or exported analysis snapshots. MY, potential protected sites, recreation, water buffers and peatland sensitivity sources are excluded; [deferred sources](deferred-sources.md) records alternatives without activating them.

## MML basemap context

Setup uses the [open MML WMTS capabilities endpoint](https://avoin-karttakuva.maanmittauslaitos.fi/avoin/wmts/1.0.0/WMTSCapabilities.xml)
with products `ortokuva` (`image/jpeg`) and `maastokartta` (`image/png`), style
`default`, matrix set `ETRS-TM35FIN` and CRS `EPSG:3067`. QGIS's `wms` raster
provider discovers capabilities and reads tiles. The saved parcel-service MML
key is supplied as `username` with an empty `password`, authenticating both
capabilities and tile requests without adding secrets to service URLs. Saved
projects retain the username; repeating setup refreshes changed credentials.
The project CRS is unchanged.

The [official WMTS technical description](https://www.maanmittauslaitos.fi/en/maps-and-spatial-data/datasets-and-interfaces/map-interface-services/map-image-service-wms-wmts-1)
and [API-key instructions](https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje)
were checked on 28 October 2026. An unauthenticated capabilities request returned
HTTP 401; authenticated live capabilities/tiles remain unverified here.
The [reference cache](../references/service-metadata/README.md) supports an
optional `MML_API_KEY` for this download. These are display-only rasters outside
the eight-source analysis registry and exports. Preserve MML attribution in
shared maps under the provider's open-data licence and interface terms.
The [source-layer contract](source-layer-requirements.md#basemap-stack)
owns reuse and failure behavior; the workflow spec owns map presentation.

## MML parcel map context

Project setup also adds `PalstanSijaintitiedot` and
`KiinteistotunnuksenSijaintitiedot` through QGIS's `oapif` provider
from `https://avoin-paikkatieto.maanmittauslaitos.fi/kiinteisto-avoin/simple-features/v3/`.
This is map context outside the eight analysis sources. The
[MML API-key product description](https://www.maanmittauslaitos.fi/kiinteistotietojen-kyselypalvelu-ogc-api/avoimet-tuotteet-api-avain)
documents the collections and CRS84 default, with EPSG:3067 also supported.
The [parcel model](../references/service-metadata/mml/parcels/palstan-sijaintitiedot.pdf)
defines polygon location. The cached
[identifier-location model](../references/service-metadata/mml/parcels/kiinteistotunnuksen-sijaintitiedot.pdf)
defines identifier points (`GM_Point`) and `kiinteistotunnuksenEsitysmuoto`.
These are older model evidence, not live service schema checks. Reviewed 28 October 2026; live
credentialed/schema and desktop verification remain in the
[verification register](open-questions.md#provider-evidence).

The mandatory MML key is stored in QGIS settings, separately from SYKE access.
Blank/cancelled input stops setup before project mutation. Connections use the
key as the HTTP Basic username with an empty password so authentication reaches
both discovery and feature requests, including linked URLs. Saved projects
retain that username; review connections before sharing them. Plugin errors
redact credentials. See [MML authentication instructions](https://www.maanmittauslaitos.fi/rajapinnat/api-avaimen-ohje)
and the [setup instructions](../../qgis_plugin/README.md#requirements-and-syke-setup)
for key replacement. The [source-layer contract](source-layer-requirements.md#configured-layer-behavior)
owns validation and reuse.

## Readiness and normalization

WFS setup discovers schemas without downloading sample features or counting
records. Managed connections use explicit WFS 2.0, view/AOI-bounded reads and
paged responses with no total feature cap. Repeated setup upgrades older
connection options; the [source-layer contract](source-layer-requirements.md#configured-layer-behavior)
owns initialization and preservation guarantees.

The [source-layer contract](source-layer-requirements.md) owns field readiness, alias priority, source identity and normalization. Setup and analysis use the same provider-field contract; schema readiness remains distinct from valid feature values and complete metric coverage. [Contract implementation](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/source_readiness.py), [QGIS-facing checks](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/source_layers.py).

Saved XSD metadata is provenance rather than a readiness authority. Its known
parser limitation is tracked separately in the
[gap register](open-questions.md#known-implementation-gaps).
[ADR-0003](adr/0003-provider-field-source-contracts.md).

## Provider evidence

Use the [reference instructions](../references/service-metadata/README.md) to populate or
explicitly refresh local evidence. The versioned manifest owns request URLs and
filenames; local retrieval metadata records capture times and checksums.
Capabilities/XSD files establish advertised types, CRS and property definitions
at capture time; they contain no representative feature records. Keep dated
observations separate from subsequent refreshes of these mutable local artifacts.

| Evidence | Established fact | Limit |
| --- | --- | --- |
| Saved stand XSD + Metsäkeskus 2.1.3 **MV GeoServer** workbook sheet | `standid`, `meanage`, `volume`, `sawlogvolume`, `volumegrowth` exist in the reduced WFS model; age is years, stock/sawlogs m³/ha and annual growth m³/ha/year. | Optional nullable decimal fields do not establish populated or valid values. The wider GeoPackage model is not proof of WFS fields. |
| Saved habitat XSD + **EY GeoServer** sheet | `habitattype` is the controlling property; workbook links it to the official `elinymparistokuvion_tyyppi-v_1_0` code set. | Schema does not establish current code frequencies or inventory completeness. |
| Protected-sites capabilities and all three XSDs, refreshed 26 October | Separate state/private/wilderness types advertise EPSG:3067; schemas include `olotila`, `tyyppilyhenne`, `kohdetyyppi`. | Not a sample of active/inactive values or proof of geographic completeness. |
| Saved programme capabilities/XSD | Exact typename, EPSG:3067, `lsoaluetunnus`, `luokka` and optional nullable `subtype`. | Current class/subtype distribution and completeness are not verified by XSD. |
| Grid schema and three-cell bounded request checked 25 October | Direct total/pine/spruce/deciduous fields, age, soil/drainage; sample showed a null spruce value and different measurement/update dates. | Raw samples were not saved. Three cells do not estimate regional/national coverage or null prevalence. |
| Groundwater capabilities/XSD downloaded 26 October and general provider dictionary | Exact `syke_vhspohjavesi:VHS2022_Pohjavesi` type advertises EPSG:3067 and its schema is retained; fields include `pvaluetunnus`, `pvalueeutunnus`, `pvalueluokka`, nullable `muutospvm` (`xsd:dateTime`) and `geom` (`gml:MultiSurfacePropertyType`). | No representative feature values were retrieved. The general dictionary does not independently define this service's complete field semantics. |

The local [2.1.3 workbook](../references/service-metadata/metsakeskus/tiedosto-tietomallikaavio-mv_ey_2-1-3-metsakeskuksen-tietomallin-uudistus.xlsx), [provider model update page](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/tietojen-yllapito/tietomallin-uudistus), and [GeoPackage guide](https://www.metsakeskus.fi/sites/default/files/document/tiedosto-geopackage-sisaltoohjeet-tietomalli-2-0.pdf) establish modeled units and code relationships. WFS is a narrower product; stand `PROPORTIONPINE`/`PROPORTIONSPRUCE`/`PROPORTIONOTHER` definitions did not establish volume proportions. Current species metrics use direct grid volumes instead.

The grid evidence came from the [DescribeFeatureType request](https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows?service=WFS&version=2.0.0&request=DescribeFeatureType&typeNames=v2:gridcell), [grid dictionary](https://www.metsakeskus.fi/sites/default/files/document/hila-koodisto-ja-tietokantakuvaus.xlsx), and a [three-cell request](https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=v2:gridcell&count=3&outputFormat=application/json&srsName=EPSG:3067&bbox=350000,6900000,352000,6902000,EPSG:3067). The sample recorded measurement 13 June 2025 and database update 9 April 2026. `TREEDATADATE`, `UPDATETIME` and retrieval time have separate meanings; a later update/retrieval is not evidence of a newer forest observation. The [December 2025 grid product description](https://www.metsakeskus.fi/sites/default/files/document/tietotuotekuvaus-hila-aineisto.pdf) describes 16 m estimates; planned product changes must be verified against the actual delivered data.

## Interpretation and geographic limits

The provider defines habitat code 1 as an ML10 habitat, code 3 as other valuable habitat, and code 5 as an ML10 habitat requiring ML20 corrective measures, following the workbook code reference and [provider guide](https://www.metsakeskus.fi/sites/default/files/document/tiedosto-geopackage-sisaltoohjeet-tietomalli-2-0.pdf). The adopted [accepted-value mapping](source-layer-requirements.md#accepted-classification-values) is separate from these provider definitions. Mapped habitat inventories are incomplete; no mapped hit does not establish absence of a habitat. [Provider data quality](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/tietojen-yllapito/tiedon-laatu).

Stand-wide promotion is the prototype's conservative spatial assumption. The [Forest Act](https://www.finlex.fi/fi/lainsaadanto/saadoskokoelma/1996/1093), [2026 amendment](https://www.finlex.fi/fi/lainsaadanto/saadoskokoelma/2026/448), and [Metsäkeskus interpretation guidance](https://www.metsakeskus.fi/sites/default/files/document/metsalain-10-pykalan-kohteiden-tulkintasuositus.pdf) provide background; operational/legal use needs current authoritative guidance and site evidence.

The [protected-area metadata](https://ckan.ymparisto.fi/dataset/luonnonsuojelu-ja-eramaa-alueet) describes updates, overlapping records and exclusion of Åland; it does not independently verify the plugin's entire accepted-status mapping.

Provider metadata describes indicative boundaries, overlap, exclusions and historical records retained despite later protection/programme changes. Programme membership therefore remains separate from established protection; outputs retain programme attributes and observed protected overlap. [Programme metadata](https://ckan.ymparisto.fi/fi/dataset/luonnonsuojeluohjelma-alueet), [attribute dictionary](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/LuonnonsuojeluOhjelmaAlueet.pdf).

The general [groundwater metadata](https://ckan.ymparisto.fi/dataset/pohjavesialueet) and [attribute reference](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/Pohjavesialueet.pdf) distinguish groundwater/recharge areas and modern 1/2/E classifications, but these are not a provider mapping to prototype sensitivity tiers. Those documents' CRS and update descriptions are not independent checks of the configured VHS2022 service. Its dataset-specific credit is documented in [distribution](distribution.md#analysis-data-attribution).

## WFS retrieval success

Only WFS 2.0 is supported, with managed sources configured as WFS 2.0.0.
[ADR-0010](adr/0010-wfs-2-only.md) records why WFS 1.x compatibility, downgrade
fallback and legacy exception handling are outside the planned scope.

A single AOI-bounded read retrieves each source; selected-feature snapshots
bypass that provider read. Accepting retrieval requires both iterator completion
and a provider-error check. QGIS can deliver request errors asynchronously, so
the adapter must collect pending errors in the provider's owning thread before
reporting coverage. This keeps failed requests distinct from successful empty
responses without a second query. HTTP failures and HTTP-200 OWS exception
responses stop publication.

The [retrieval adapter](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/source_loading.py)
and its [workflow regressions](../../qgis_plugin/tests/qgis/test_workflow_contracts.py)
own the QGIS-specific cache and event handling. Verification covers the QGIS
4.2.3 WFS boundary; it is not a guarantee for arbitrary providers.

Successful empty retrieval is `AVAILABLE` but is not certification of complete geographic coverage. Source request/iteration failures stop the run. Metric nulls are handled independently as documented in [indicators](indicators.md).

## Access and evidence maintenance

For sustained/load-generating SYKE use, obtain the provider-issued application identifier and pass it as `sykeuserid`; keep it outside committed source, fixtures and logs. The plugin saves it in QGIS settings and includes it in SYKE WFS layer URLs. Saving a project intentionally persists those URLs, including the identifier, in `.qgs` or `.qgz` so the layers retain their service connection details. Review layer URLs before sharing or committing a project. This persistence is separate from error-message redaction in [sources.py](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py). See [SYKE service guidance](https://www.syke.fi/fi/ymparistotieto/avoimet-rajapinnat/paikkatietorajapinnat), [request parameter guidance](https://wwwi4.ymparisto.fi/i4/fin/eowiki/kysymys_wcs.html), and the [plugin setup instructions](../../qgis_plugin/README.md#requirements-and-syke-setup).

Future evidence checks should record exact endpoint/type, request date, CRS, required properties and representative sanitized status/code/null formats. Keep schema evidence distinct from feature values, field readiness distinct from metric coverage, and provider facts distinct from application choices. [Outstanding checks](open-questions.md).
