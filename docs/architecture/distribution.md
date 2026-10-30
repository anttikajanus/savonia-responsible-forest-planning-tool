# Distribution, notices and attribution

This page describes the prototype's package inventory, licensing and data
attribution. Full ownership and host/transitive licence
compatibility audits remain outside that inventory check.
[ADR-0009](adr/0009-project-licence-and-portable-attribution.md).

## Project material and package inventory

Project material uses MIT with Antti Kajanus as developer/copyright holder, as recorded in the [root licence](../../LICENSE) and [packaged licence](../../qgis_plugin/savonia_responsible_forest_planning_tool/LICENSE). The project is an independent unfinished personal prototype; naming the source use case does not establish Savonia ownership, endorsement or acceptance.

The package includes project source, bilingual offline manuals, `LICENSE`,
`THIRD_PARTY_NOTICES`, `COMPONENT_INVENTORY.txt` and the original
`licenses/CC-BY-4.0.txt`. Root-only acknowledgements do not reach ZIP users.
The reviewed package contains no vendored libraries, datasets or binaries;
QGIS supplies host dependencies. Packaging commands and version switches belong
in the [development guide](development.md#check-packaging-separately).

The [component inventory](../../qgis_plugin/savonia_responsible_forest_planning_tool/COMPONENT_INVENTORY.txt) is a concise offline record of shipped project material and the original CC legal text, separating them from host dependencies and runtime data. Keep it as the package-content reference used by About, the manuals and package checks. Use the installed `metadata.txt` for the project version and `THIRD_PARTY_NOTICES` for detailed bilingual source credits and terms; do not duplicate those details or list unused components. Preserve applicable original notices for every future distributed component and update the inventory. Project MIT terms do not relabel host or data terms.

## GitHub builds and releases

The [GitHub Actions workflow](../../.github/workflows/build-and-release.yml)
tests and packages pull requests and pushes to `main`. Separate build and QGIS
quality jobs check the source and extracted installation ZIP; a main release
depends on both succeeding. QGIS integration uses a versioned official Windows
installer, verifies its published checksum and runtime version, and runs
offscreen without live analysis services. These checks leave desktop acceptance
separate. Exact tooling versions and cache options belong to the workflow;
[development](development.md#automatic-github-builds-and-releases) owns commands,
recovery and required merge-check setup.

Releases use the next minor version in the metadata's major, with metadata as
a floor and patch reset to zero. Version allocation is serialized and tied to
the tested source commit. The release commit changes metadata, has that source
as its parent, and is published only through a matching version tag; `main`
retains its development version. Tag, ZIP name and installed metadata agree.
This supports protected branches without automated pushes to `main`.
[Version preparation](../../scripts/prepare_release.py).

Only the release job receives repository write permission. It creates a draft,
uploads the tested ZIP, then publishes. Failures stop publication and tags are
never force-pushed. Retrying the same source reuses its version, can finish an
incomplete draft and leaves an already published release intact. Repository
policy must permit the token's tag/release writes.

Install the named plugin ZIP from [GitHub Releases](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/releases);
GitHub source archives do not provide the bundled installation layout.
[Hosted checks](#hosted-checks) and
[remaining questions](../open-questions.md#acceptance-and-distribution) are separate
from the workflow design.

### Hosted checks

Inspect [GitHub Actions](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/actions/workflows/build-and-release.yml)
for the source commit's build, integration, cache and release results. The logs
and release artifacts provide execution details without a separate dated summary
in repository documentation. CI success does not establish downloaded-ZIP desktop
behavior, live-provider completeness, newer-QGIS compatibility or merge blocking.

## Host software

[Open-source acknowledgements](../../OPEN_SOURCE_ACKNOWLEDGEMENTS.md) maintains the component table and primary upstream references. The host components use the following terms:

| Component | Upstream terms / inventory limit |
| --- | --- |
| QGIS / PyQGIS | GPL-2.0-or-later, with QGIS's published Qt linking exception. [QGIS licence](https://qgis.org/license/). |
| PyQt | GPLv3 or Riverbank commercial terms; Qt's LGPL offering does not make PyQt LGPL. [Riverbank licensing](https://riverbankcomputing.com/software/pyqt/intro). |
| Qt Core/GUI/Widgets/Test | Module/file-dependent LGPLv3, GPL alternatives or commercial terms; use the installed build's actual notices. [Qt licensing](https://doc.qt.io/qt-6/licensing.html). |
| CPython / standard library | PSF-2.0 with historical/incorporated-software notices. [Python licence history](https://docs.python.org/3/license.html). |
| GDAL/OGR | Primarily MIT-style, with file/dependency exceptions. [GDAL licence](https://gdal.org/en/stable/license.html). |
| GEOS | Upstream LGPL statement and supplied LGPL 2.1 text; do not infer every file's expression. [GEOS](https://libgeos.org/#license), [COPYING](https://github.com/libgeos/geos/blob/main/COPYING). |
| PROJ | MIT with upstream copyright notices. [PROJ](https://proj.org/en/stable/about.html#license). |
| SQLite | Deliverable library code is public domain; build scripts may differ. [SQLite](https://www.sqlite.org/copyright.html). |

These are supplied by QGIS rather than copied into the plugin ZIP. The table does not establish distribution compatibility or replace the exact version's full notices. Public QGIS repository publication has additional licence, documentation and real support-link requirements; this prototype has not been approved for that publication. [QGIS publishing rules](https://plugins.qgis.org/docs/publish).

## Analysis-data attribution

MML `PalstanSijaintitiedot` and `KiinteistotunnuksenSijaintitiedot` are online map context and are excluded from analysis
exports. The package notices and bilingual manuals credit Maanmittauslaitos
and link its [open interface terms and data licence](https://www.maanmittauslaitos.fi/kartat-ja-paikkatieto/asiantuntevalle-kayttajalle/maanmittauslaitoksen-avoimen-rajapinnan).
Preserve the provider credit on shared maps. No parcel data are bundled.

The implemented [data attribution registry](../../qgis_plugin/savonia_responsible_forest_planning_tool/data_attribution.py) records the following provider-specific credits for the actual configured products:

| Dataset | Credit retained with results | Evidence |
| --- | --- | --- |
| Metsävarakuviot, Erityisen tärkeät elinympäristöt, Metsävarahila | Suomen metsäkeskus; dataset identity and modifications, CC BY 4.0 | [Metsäkeskus's own open-data terms](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/avoimen-metsa-ja-luontotiedon-tuotteet). Other producers retain their own terms. |
| All three conservation/wilderness types | `Lähde: Metsähallitus`, CC BY 4.0; Syke is the distributor | [Dataset metadata](https://ckan.ymparisto.fi/dataset/luonnonsuojelu-ja-eramaa-alueet). |
| Conservation programme areas | `Lähde: Syke`, CC BY 4.0 | [Dataset metadata](https://ckan.ymparisto.fi/dataset/luonnonsuojeluohjelma-alueet). |
| `VHS2022_Pohjavesi` | `Lähde: Syke, Lupa- ja valvontavirasto (rantaviiva-aineisto: MML)`, CC BY 4.0 | [Water Framework Directive dataset metadata](https://ckan.ymparisto.fi/dataset/vesipuitedirektiivin-mukaiset-vesimuodostumat). Retain this complete line rather than substitute generic groundwater terms. |

Syke's [general terms](https://www.syke.fi/fi/ymparistotieto/kayttolupa-ja-vastuut) defer dataset-specific credit/exceptions to metadata. The above source lines come from the reviewed products' records. Preserve original provider/dataset names in both presentation languages; translate explanatory modification text and navigation.

AOI-clipped snapshots redistribute source geometry/attributes and derived results use those sources. The project therefore adds `data_attribution` to the common run record: dataset, exact credit, licence ID/link, metadata/terms link, and clipping/transformation/derivation notice. The GeoPackage `run_metadata` table and workbook notes serialize that record without a third output format. Retain endpoint/type/retrieval/measurement/update provenance separately. Shared isolated layers/tables need their relevant notices carried alongside the excerpt. This portable-metadata design follows the retention/modification provisions in [CC BY 4.0 sections 3–4](https://creativecommons.org/licenses/by/4.0/legalcode.en); About-only credits cannot travel with independent exports. [Publication implementation](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/publishing.py).

The original English CC BY 4.0 legal code is shipped offline in
`licenses/CC-BY-4.0.txt` and embedded verbatim in `THIRD_PARTY_NOTICES`.
Packaging checks verify original notices separately from translated summaries.

## OpenStreetMap context and remaining limits

MML Ortokuva and Maastokartta WMTS tiles also provide display context only.
They are not bundled or included in analysis exports. Both manuals and
`THIRD_PARTY_NOTICES` carry MML source credits and provider licence/terms links;
preserve attribution on shared maps. Connection and verification limits are in
[data sources](data-sources.md#mml-basemap-context).

Setup uses standard raster tiles from `tile.openstreetmap.org`; OSM is not copied to analysis GeoPackage/XLSX outputs. The reviewed [OSM attribution guidance](https://www.openstreetmap.org/copyright) and [tile policy](https://operations.osmfoundation.org/policies/tiles/) require map-visible attribution and impose tile-client conditions such as caching, identification and no bulk/prefetch download. Keep `© OpenStreetMap contributors` with shared maps/screenshots and a route to the copyright/ODbL information. The About/root credits alone do not provide visible canvas attribution.

Project setup does not explicitly arrange that map-visible credit. This remains a follow-up, not a completed compliance claim. QGIS server attribution metadata setters do not establish canvas display. Tile-client behavior and transitive host dependencies also require distribution review. See [remaining work](../open-questions.md#acceptance-and-distribution).

The maintainer supplied the public [GitHub repository](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool) and [GitHub Issues tracker](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues). Metadata, About and manuals use these destinations; the component inventory records the repository origin. The documentation/homepage link opens the repository's [docs/help directory](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/tree/main/docs/help).
