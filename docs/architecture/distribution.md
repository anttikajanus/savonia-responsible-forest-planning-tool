# Distribution, notices and attribution

This page describes the prototype's package inventory, licensing and data
attribution, checked on 26 October 2026. Full ownership and host/transitive licence
compatibility audits remain outside that inventory check.
[ADR-0009](adr/0009-project-licence-and-portable-attribution.md).

## Project material and package inventory

Project material uses MIT with Antti Kajanus as developer/copyright holder, as recorded in the [root licence](../../LICENSE) and [packaged licence](../../qgis_plugin/savonia_responsible_forest_planning_tool/LICENSE). The project is an independent unfinished personal prototype; naming the source use case does not establish Savonia ownership, endorsement or acceptance.

The [packaging script](../../qgis_plugin/package.ps1) builds the current metadata version by default; `-BumpMinor` explicitly increments the minor version and resets the patch to zero before building. It archives the plugin package directory and bundles canonical manuals from repository `docs/help/` into package `docs/help/`, adjusting their local legal-resource links. Ship `LICENSE`, `THIRD_PARTY_NOTICES`, `COMPONENT_INVENTORY.txt` and `licenses/CC-BY-4.0.txt` inside the package; root-only acknowledgements do not reach ZIP users. Inventory inspection found project Python/metadata/documentation and the original CC legal text, with no vendored libraries, copied-code notices, fonts, custom icon files, binaries, tiles or datasets. QGIS provides theme/standard icons. The [XLSX writer](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/excel_writer.py) uses standard-library ZIP/XML, not an external spreadsheet library. These are findings about the reviewed package, not an assertion covering future additions.

The [component inventory](../../qgis_plugin/savonia_responsible_forest_planning_tool/COMPONENT_INVENTORY.txt) is a concise offline record of shipped project material and the original CC legal text, separating them from host dependencies and runtime data. Keep it as the package-content reference used by About, the manuals and package checks. Use the installed `metadata.txt` for the project version and `THIRD_PARTY_NOTICES` for detailed bilingual source credits and terms; do not duplicate those details or list unused components. Preserve applicable original notices for every future distributed component and update the inventory. Project MIT terms do not relabel host or data terms.

## GitHub builds and releases

The [GitHub Actions workflow](../../.github/workflows/build-and-release.yml)
tests and packages pull requests targeting `main` and pushes to `main` on
Windows. The `Test and build installable ZIP` job uses Python 3.12 for tooling
and pure plugin tests, including Finnish/English help and disposable packaging
checks, then tests the extracted installation ZIP. The build ZIP is retained as
a workflow artifact.

The dependent `Pylint and QGIS 4.2.3 integration` job installs the official
`QGIS-OSGeo4W-4.2.3-2.msi`, checks its published SHA-256 before installation,
and verifies the runtime version. It installs the pinned development
requirements through QGIS's Python launcher, runs the existing Pylint policy
over plugin/scripts/tests, and runs the offscreen QGIS integration suite against
source and the downloaded build ZIP. Diagnostics and failed installation/test
commands fail the job. Installer logs are retained on failure when available.
The versioned installer and checksum are listed in the
[official QGIS downloads](https://qgis.org/downloads-list/).

Checkout, Python setup and artifact transfer use Node 24 actions; artifact
upload uses `actions/upload-artifact@v7` with its default ZIP archive behavior
and download uses `actions/download-artifact@v8`. Interactive desktop acceptance
remains a separate check. Required merge status checks are repository settings;
the [development guide](development.md#required-merge-checks) owns their setup
and the distinction between the checked-in ruleset and active enforcement.

After both main build and QGIS quality jobs succeed, a serialized release job
prepares the next minor version with [prepare_release.py](../../scripts/prepare_release.py).
It uses the highest semantic-version tag in the metadata's major, with source
metadata as a version floor, and resets patch to zero. With metadata `1.0.0`
and no previous tags, releases start at `1.1.0`, then `1.2.0`.
Other majors and prerelease tags do not participate. Pending release jobs use
GitHub's [concurrency queue](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
(`queue: max`) instead of replacing one another; the exact tested source commit
is checked out.

The release job writes that version into metadata, builds and tests the extracted
ZIP, then commits metadata on a detached release commit whose sole parent is the
triggering source commit. It pushes only the matching `vMAJOR.MINOR.0` tag.
The main branch retains its development version; installing the release ZIP or
building its tag uses the release version. The tag, ZIP filename and installed
metadata agree. This permits branch protection without automated pushes to main.

The built-in `GITHUB_TOKEN` has `contents: write` only in the release job.
Repository policy must permit that permission, creating release tags and
publishing releases. No additional token secret is needed. A draft is created
with generated notes, the ZIP is uploaded, and only then is the release published.
Build, test, Git or API failures stop the job; tags are never force-pushed.
Retrying the same source recognizes its release commit and restores its version;
an existing draft can recover its asset upload, and an already published release
is left intact. Manual dispatch on main supports recovery or the first build.

Download the named plugin ZIP under
[GitHub Releases](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/releases),
then use QGIS **Install from ZIP**. GitHub's automatically generated source
archives omit the bundled installation layout and are intended for source use.
Hosted execution remains pending in the [verification register](open-questions.md#acceptance-and-distribution).

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

The implemented [data attribution registry](../../qgis_plugin/savonia_responsible_forest_planning_tool/data_attribution.py) records the following provider-specific credits for the actual configured products:

| Dataset | Credit retained with results | Evidence |
| --- | --- | --- |
| Metsävarakuviot, Erityisen tärkeät elinympäristöt, Metsävarahila | Suomen metsäkeskus; dataset identity and modifications, CC BY 4.0 | [Metsäkeskus's own open-data terms](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/avoimen-metsa-ja-luontotiedon-tuotteet). Other producers retain their own terms. |
| All three conservation/wilderness types | `Lähde: Metsähallitus`, CC BY 4.0; Syke is the distributor | [Dataset metadata](https://ckan.ymparisto.fi/dataset/luonnonsuojelu-ja-eramaa-alueet). |
| Conservation programme areas | `Lähde: Syke`, CC BY 4.0 | [Dataset metadata](https://ckan.ymparisto.fi/dataset/luonnonsuojeluohjelma-alueet). |
| `VHS2022_Pohjavesi` | `Lähde: Syke, Lupa- ja valvontavirasto (rantaviiva-aineisto: MML)`, CC BY 4.0 | [Water Framework Directive dataset metadata](https://ckan.ymparisto.fi/dataset/vesipuitedirektiivin-mukaiset-vesimuodostumat). Retain this complete line rather than substitute generic groundwater terms. |

Syke's [general terms](https://www.syke.fi/fi/ymparistotieto/kayttolupa-ja-vastuut) defer dataset-specific credit/exceptions to metadata. The above source lines come from the reviewed products' records. Preserve original provider/dataset names in both presentation languages; translate explanatory modification text and navigation.

AOI-clipped snapshots redistribute source geometry/attributes and derived results use those sources. The project therefore adds `data_attribution` to the common run record: dataset, exact credit, licence ID/link, metadata/terms link, and clipping/transformation/derivation notice. The GeoPackage `run_metadata` table and workbook notes serialize that record without a third output format. Retain endpoint/type/retrieval/measurement/update provenance separately. Shared isolated layers/tables need their relevant notices carried alongside the excerpt. This portable-metadata design follows the retention/modification provisions in [CC BY 4.0 sections 3–4](https://creativecommons.org/licenses/by/4.0/legalcode.en); About-only credits cannot travel with independent exports. [Publication implementation](../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/publishing.py).

The original English [CC BY 4.0 plain-text legal code](https://creativecommons.org/licenses/by/4.0/legalcode.txt) is stored offline in `licenses/CC-BY-4.0.txt` and embedded verbatim in `THIRD_PARTY_NOTICES`. The recorded download was 18,657 bytes with SHA-256 `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411`. Its licence-text dedication does not change the datasets' CC BY licence. Packaging/content checks distinguish exact original notices from translated summaries.

## OpenStreetMap context and remaining limits

Setup uses standard raster tiles from `tile.openstreetmap.org`; OSM is not copied to analysis GeoPackage/XLSX outputs. The reviewed [OSM attribution guidance](https://www.openstreetmap.org/copyright) and [tile policy](https://operations.osmfoundation.org/policies/tiles/) require map-visible attribution and impose tile-client conditions such as caching, identification and no bulk/prefetch download. Keep `© OpenStreetMap contributors` with shared maps/screenshots and a route to the copyright/ODbL information. The About/root credits alone do not provide visible canvas attribution.

The `_ensure_osm()` setup does not explicitly arrange that map-visible credit. This remains a follow-up, not a completed compliance claim. QGIS server attribution metadata setters do not establish canvas display. Tile-client behavior and transitive host dependencies also require distribution review. See [remaining work](open-questions.md#acceptance-and-distribution).

The maintainer supplied the public [GitHub repository](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool) and [GitHub Issues tracker](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues). Metadata, About and manuals use these destinations; the component inventory records the repository origin. The documentation/homepage link opens the repository's [docs/help directory](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/tree/main/docs/help).
