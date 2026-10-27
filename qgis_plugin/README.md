# Savonia - Responsible Forest Planning

The QGIS plugin prepares classified forest polygons and indicator inputs for a
separate value-table model. It is Antti Kajanus's unfinished personal learning
prototype, not backed or approved by Savonia. See [project context](../docs/project-context.md).

## Plugin installation

Install the packaged release ZIP directly in QGIS. QGIS supplies the runtime
dependencies; no separate Python packages or helper plugins are required.

### Requirements

The experimental plugin targets **QGIS 4.2.3 and newer 4.x releases**; the
installation range is authoritative in
[metadata.txt](savonia_responsible_forest_planning_tool/metadata.txt).
QGIS 4.2.3 is the verification baseline; newer releases require their own runtime
checks. Analysis requires an internet connection to the configured Metsäkeskus
and SYKE WFS services. The packaged manuals work offline.

### Install in QGIS

1. Download `savonia_responsible_forest_planning_tool-<version>.zip` from
   the release's **Assets** on
   [GitHub Releases](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/releases).
   Choose the named plugin ZIP; GitHub's **Source code (zip)** and
   **Source code (tar.gz)** downloads are repository archives for development.
   Keep the plugin ZIP compressed for the next step.
2. In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**
   and select the downloaded plugin ZIP, then click **Install Plugin**.
3. Under **Installed** in Plugin Manager, check that
   **Savonia - Responsible Forest Planning** is enabled
   (**Savonia - Vastuullinen metsäsuunnittelu** in Finnish).
4. Open the wizard from the plugin's QGIS toolbar button, then choose **Help**
   to check that the installed manual opens. **About** shows the installed version.

Continue with [First run](../README.md#first-run) to set up the source layers
and run an analysis. The [Language](#language) section explains how QGIS selects
Finnish or English.

### Build a plugin ZIP from source

If a release ZIP is unavailable or you need to package a checkout, follow
[packaging instructions](../docs/architecture/development.md#check-packaging-separately).
Keep the complete repository, including `docs/help/`, when building so both
manuals are included. Install the resulting ZIP through the same QGIS steps above.

For a development environment, follow the
[development setup](../docs/architecture/development.md#recommended-setup-a-dedicated-development-profile),
which also covers reload, debugging and tests.

## Requirements and SYKE setup

Use **Set up forest planning layers** in the wizard toolbar or plugin menu.
The plugin accepts a blank `sykeuserid`; SYKE requires an application-specific
identifier for sustained or intensive use. Setup can save one later. See
[access and identifier handling](../docs/architecture/data-sources.md#access-and-evidence-maintenance)
for provider instructions and how saved projects retain service URLs.

## Language

The plugin follows QGIS's application language: Finnish uses Finnish; other or
unavailable languages use English. Change QGIS's language and restart as prompted.
See the [Finnish](../docs/help/manual_fi.html) and
[English](../docs/help/manual_en.html) manuals for the workflow, outputs,
interpretation limits and Help/About controls.

## Technical references

- [Architecture index](../docs/architecture/README.md): execution, evidence and adopted decisions.
- [Geometry and classification](../docs/architecture/calculations.md): geometry mechanics, tolerances and classification field mapping.
- [Indicator calculations](../docs/architecture/indicator-calculations.md): formulas and aggregation.
- [Output schema](../docs/architecture/output-schema.md): fields, coverage and output layout.
- [Source-layer requirements](../docs/architecture/source-layer-requirements.md): exact input contract.
- [Remaining verification](../docs/architecture/open-questions.md): unresolved acceptance and source checks.
- [Licences and acknowledgements](../OPEN_SOURCE_ACKNOWLEDGEMENTS.md).

Report bugs and enhancement requests through
[GitHub Issues](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues).
