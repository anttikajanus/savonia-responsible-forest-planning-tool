# Open-source licences and acknowledgements

Savonia - Responsible Forest Planning is Antti Kajanus's unfinished personal
learning prototype, based on limited understanding and personal assumptions.
Neither it nor its results are official, backed, endorsed, finalized, or approved
by Savonia in any form.

This prototype builds on the work of the open-source GIS and Python
communities. We thank the maintainers and contributors of the projects below.

Last reviewed: **2026-10-26**.

## Scope

This document covers the software used by the QGIS plugin and its tests, plus
the configured map and analysis data sources. The source inventory found Python
standard-library imports and QGIS/PyQt imports, with no vendored third-party
libraries. QGIS and its supporting libraries are supplied by the user's QGIS
installation. The plugin declares QGIS **4.2.3**; supporting library versions
depend on that installation.

This is an acknowledgements and licence-reference document. The upstream
licence texts and copyright notices remain authoritative. The maintainer has
selected the [MIT License](LICENSE) for project material, with Antti Kajanus as
copyright holder; third-party software and data retain their own terms. The
[distribution reference](docs/architecture/distribution.md) records the package
inventory, dataset-specific credits and remaining verification limits.

## Direct software dependencies

| Project and credit | Use in this project | Upstream licence and references |
| --- | --- | --- |
| **QGIS / PyQGIS** — QGIS contributors | Plugin host, Processing, spatial layers, geometry operations, coordinate transforms and exports through `qgis.core` and `qgis.gui`. | GNU General Public License, version 2 or later (`GPL-2.0-or-later`), with the Qt linking exception described by QGIS. [QGIS source and licence declaration](https://github.com/qgis/QGIS#free-and-open-source) · [Licence text and exception](https://qgis.org/license/) |
| **PyQt** — Riverbank Computing | Python bindings accessed through `qgis.PyQt` for the interface, events and tests. | GNU General Public License version 3 or a commercial licence. PyQt is not available under the LGPL. The applicable edition is supplied by the QGIS installation. [Riverbank licensing information](https://riverbankcomputing.com/software/pyqt/intro) |
| **Qt** — The Qt Company and contributors | Core, GUI and Widgets through QGIS/PyQt; Qt Test in integration tests. | These modules offer LGPL version 3, GPL alternatives and commercial licensing. Use the licence and notices accompanying the installed Qt build. [Qt licensing](https://doc.qt.io/qt-6/licensing.html) · [Qt Core](https://doc.qt.io/qt-6/qtcore-index.html#licenses-and-attributions) · [Qt GUI](https://doc.qt.io/qt-6/qtgui-index.html#licenses-and-attributions) · [Qt Widgets](https://doc.qt.io/qt-6/qtwidgets-index.html#licenses) · [Qt Test](https://doc.qt.io/qt-6/qttest-index.html#licenses-and-attributions) |
| **Python / CPython** — Python Software Foundation and contributors | Runtime and standard library, including XML, ZIP/XLSX writing, HTTP requests, logging, numeric operations and `unittest`. | Python Software Foundation License Version 2 (`PSF-2.0`), together with historical and incorporated-component notices supplied with Python. [Python licence and acknowledgements](https://docs.python.org/3/license.html) |

The workbook exporter uses Python's `zipfile` and `xml.etree.ElementTree`;
there is no separate Excel-writing library dependency in the inspected source.
See [the exporter](qgis_plugin/savonia_responsible_forest_planning_tool/adapters/excel_writer.py).

## Supporting GIS libraries

The following projects support the operations exposed by QGIS. They are
acknowledged as part of the GIS runtime, rather than as Python packages imported
directly by this plugin. This list is not a complete inventory of every library
in a QGIS distribution; retain the notices supplied with that distribution.

| Project and credit | Role in the GIS runtime | Upstream licence and notices |
| --- | --- | --- |
| **GDAL / OGR** — GDAL contributors | Raster/vector data providers and format support, including GeoPackage access. | Primarily MIT-style; additional component notices apply. [GDAL licence](https://gdal.org/en/stable/license.html) |
| **GEOS** — GEOS contributors | Geometry processing used by QGIS. | GNU Lesser General Public License; upstream supplies the version 2.1 text. [GEOS licence statement](https://libgeos.org/#license) · [Licence text](https://github.com/libgeos/geos/blob/main/COPYING) |
| **PROJ** — PROJ contributors | Coordinate reference systems and coordinate transformations. | MIT (`MIT`), with the notices in its copyright file. [PROJ copyright and licence](https://proj.org/en/stable/about.html#license) |
| **SQLite** — SQLite authors | Database engine underlying GeoPackage storage. | Public domain dedication. [SQLite copyright statement](https://sqlite.org/copyright.html) |

## Data sources and map attribution

Data licences apply separately from software licences. The configured sources
are recorded in [the service definitions](qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py)
and [project setup](qgis_plugin/savonia_responsible_forest_planning_tool/adapters/project_setup.py).

| Source | Use | Licence and attribution reference |
| --- | --- | --- |
| **Finnish Forest Centre / Suomen metsäkeskus** | Forest stands, habitats and forest grid cells from the configured WFS services. | The Forest Centre's own open forest and nature data uses [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Identify the provider and dataset, retain the source date and indicate modifications. Other producers' datasets retain their own terms. [Provider's licensing and attribution guidance](https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/avoimen-metsa-ja-luontotiedon-tuotteet) |
| **Finnish Environment Institute / Suomen ympäristökeskus (Syke)** | State-owned and private-land protected areas, wilderness areas, nature conservation programme areas and groundwater polygons. | Syke's open-data terms use [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Name the licensor and dataset and preserve any additional credits or exceptions in that dataset's metadata. [Syke terms and attribution guidance](https://www.syke.fi/fi/ymparistotieto/kayttolupa-ja-vastuut) |
| **OpenStreetMap contributors** | Basemap context from `tile.openstreetmap.org`; not a classification input. | OpenStreetMap data uses the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Display **© OpenStreetMap contributors** and identify the licence as described in the [OpenStreetMap copyright and attribution guidance](https://www.openstreetmap.org/copyright). The tile service also has a [usage policy](https://operations.osmfoundation.org/policies/tiles/). |

Carry the applicable dataset credits, licence links, source dates and change
descriptions into shared results. For OpenStreetMap maps and images, follow the
display rules in the attribution guidance; this root document alone does not
provide attribution on a map. Dataset-specific metadata determines the final
credit wording for analysis data.

## Keeping acknowledgements current

- Update this inventory when adding dependencies, copied code, icons, fonts or
  data sources, and verify the licence for the version actually used.
- When redistributing third-party software or assets, include the applicable
  full licence texts, copyright notices and any required source materials with
  the distributed files. Preserve the notices supplied by upstream projects.
- The current packaging scripts archive only
  `qgis_plugin/savonia_responsible_forest_planning_tool/`. This root document is
  not included automatically in the plugin ZIP. Include any required notices
  inside the package when preparing a distribution.

For the source inventory, upstream evidence and verification limits, see
[distribution and attribution reference](docs/architecture/distribution.md).
