# Savonia - Responsible Forest Planning

The QGIS plugin prepares classified forest polygons and indicator inputs for a
separate value-table model. It is Antti Kajanus's unfinished personal learning
prototype, not backed or approved by Savonia. See [project context](../docs/project-context.md).

## Runtime and installation

The experimental plugin targets **QGIS 4.2.3 and newer 4.x releases**; the
installation range is authoritative in
[metadata.txt](savonia_responsible_forest_planning_tool/metadata.txt).
QGIS 4.2.3 is the verification baseline. Analysis requires an internet connection
to the configured WFS services.

1. Download `savonia_responsible_forest_planning_tool-<version>.zip` from
   [GitHub Releases](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/releases).
   Alternatively, keep the complete checkout, including `docs/help/`, and run
   `./qgis_plugin/package.ps1` in Windows PowerShell from the repository root.
2. In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**
   and select the downloaded ZIP or the locally built ZIP under `qgis_plugin/dist/`.
3. Enable **Savonia - Responsible Forest Planning** and open Help to check the manual.

The build preserves the metadata version and replaces its existing ZIP.
It includes both manuals, licences and notices. Copying only the source package
folder omits the repository manuals. Release maintainers should use
`package.ps1 -BumpMinor` for an intentional version increment. See the
[development guide](../docs/architecture/development.md) for setup, reload,
debugging, tests and packaging details.

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
- [Calculations](../docs/architecture/calculations.md): classification, fields, formulas and coverage.
- [Source-layer requirements](../docs/architecture/source-layer-requirements.md): exact input contract.
- [Remaining verification](../docs/architecture/open-questions.md): unresolved acceptance and source checks.
- [Licences and acknowledgements](../OPEN_SOURCE_ACKNOWLEDGEMENTS.md).

Report bugs and enhancement requests through
[GitHub Issues](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues).
