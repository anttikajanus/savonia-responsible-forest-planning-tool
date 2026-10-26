# Project specifications

These are the maintained user stories and functional specifications for **Savonia - Responsible Forest Planning** / **Savonia - Vastuullinen metsäsuunnittelu**. They describe this personal prototype's current behavior.

This is Antti Kajanus's unfinished personal learning project. Neither the prototype nor its results are official, finalized, backed, endorsed or approved by Savonia. Requirements here record prototype decisions, not buyer acceptance or a claim of procurement compliance. [Project context](../project-context.md) preserves the external use case and procurement distinctions.

## Read the specifications

| Document | Owns |
| --- | --- |
| [User stories](user-stories.md) | User goals, stable story IDs and links to acceptance requirements |
| [Workflow](workflow.md) | Installation expectations, project setup, area selection, wizard, Processing, failure behavior and local development references |
| [Classification](classification.md) | Reporting domain, sensitivity tiers, spatial behavior and interpretation limits |
| [Indicators and outputs](indicators-and-outputs.md) | Required indicators, missing values, presentation, result files and map review |
| [Help and language](help-and-language.md) | Finnish/English behavior, offline help, About, identity, accessibility and attribution |

Requirement IDs such as `WF-03` are stable within these documents. The stories link to their acceptance requirements; the detailed criteria live in those requirements rather than being repeated per story.

## Product purpose and scope

Municipal forest planners and GIS analysts select an area, combine online forest and environmental evidence, and obtain classified forest polygons and descriptive indicators for six cumulative sensitivity tiers. Auditors can inspect the evidence, coverage and provenance of each run. Users of a separate value-table model receive spatial inputs for subsequent scenario comparison.

The current scope includes:

- A QGIS plugin with a persistent wizard and an equivalent Processing workflow.
- Eight configured online WFS source layers, explicit area selection and validation.
- One stand-based polygon result with six tier classifications, independent stand/grid indicators, source snapshots and coverage.
- A paired GeoPackage and Excel workbook, with Finnish or English presentation and offline instructions.

Scenario impact models, legal determinations and forestry prescriptions are outside this product. [ADR-0011](../architecture/adr/0011-deciduous-volume-instead-of-birch.md) adopts deciduous volume instead of the original bid/project requirement for birch-specific volume; birch support is explicitly out of scope. Average stumpage price remains blank and out of scope. Whole-AOI/open-mire reporting, local/offline source workflows, additional sensitivity criteria and source alternatives remain deferred. See [classification exclusions](classification.md#cl-04-exclusions-and-interpretation) and [indicator gaps](indicators-and-outputs.md#io-03-unavailable-and-partial-values).

## Maintaining specifications

Update affected specifications and [technical references](../architecture/README.md)
alongside implementation changes. Record and resolve discrepancies between code
and documentation. Follow the [specification workflow](../agents/specifications.md);
the [documentation map](../agents/README.md#documentation-ownership) identifies
the owner of each kind of information.

## Implementation and acceptance status

The behavior described here is implemented unless a requirement identifies a gap
or work in progress. Acceptance remains separate from implementation; see the
[development guide](../architecture/development.md) for verification instructions.

Interactive Finnish/English desktop, browser and disconnected-help checks remain open where recorded. Provider value/coverage evidence, map-visible OpenStreetMap attribution and release checks also remain open. The maintained [verification and deferred-work register](../architecture/open-questions.md) owns these follow-ups.
