# Savonia - Responsible Forest Planning

The QGIS plugin prepares classified forest polygons and indicator inputs for a
separate value-table model. It is Antti Kajanus's unfinished personal learning
prototype, not backed or approved by Savonia. See [project context](../docs/project-context.md).

## Plugin installation

Requires **QGIS 3.44 or newer 3.x/4.x** and an internet connection for source
setup and analysis. QGIS supplies the runtime dependencies; no additional Python
packages or helper plugins are required. See
[metadata.txt](savonia_responsible_forest_planning_tool/metadata.txt) for the
installation range and the [development guide](../docs/architecture/development.md#shared-qgis-test-environment)
for tested runtimes.

1. Download `savonia_responsible_forest_planning_tool-<version>.zip` from
   [GitHub Releases](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/releases).
   Use the plugin ZIP under **Assets**, rather than a **Source code** archive,
   and leave it compressed.
2. In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**
   and install the downloaded ZIP.
3. Under **Installed** in Plugin Manager, check that
   **Savonia - Responsible Forest Planning** is enabled
   (**Savonia - Vastuullinen metsäsuunnittelu** in Finnish).
4. Open the wizard from the plugin toolbar. **Help** opens the installed manual;
   **About** shows the installed version.

## First run

Follow the [first-run guide](../README.md#first-run) to prepare the required MML
API key, supply a SYKE identifier when needed, set up the source layers and run
an analysis with a positive sawlog stumpage price. Each successful run writes a
GeoPackage and an Excel workbook.

## Language

The plugin follows QGIS's language: Finnish for Finnish QGIS, English otherwise.
The [Finnish](../docs/help/manual_fi.html) and [English](../docs/help/manual_en.html)
manuals cover the workflow, outputs and interpretation limits, and are available
offline through **Help**.

## Development and references

- [Build a plugin ZIP](../docs/architecture/development.md#check-packaging-separately).
- [Development guide](../docs/architecture/development.md): setup, reload, debugging and tests.
- [Architecture index](../docs/architecture/README.md): source contracts, calculations and output schemas.
- [Known limitations and remaining verification](../docs/open-questions.md).
- [Licences and acknowledgements](../OPEN_SOURCE_ACKNOWLEDGEMENTS.md).

Report bugs and enhancement requests through
[GitHub Issues](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues).
