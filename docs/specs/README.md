# Project specifications

These are the maintained user stories and functional specifications for **Savonia - Responsible Forest Planning** / **Savonia - Vastuullinen metsäsuunnittelu**. They describe this personal prototype's current behavior.

This is Antti Kajanus's unfinished personal learning project. Neither the prototype nor its results are official, finalized, backed, endorsed or approved by Savonia. Requirements here record prototype decisions, not buyer acceptance or a claim of procurement compliance. [Project context](../project-context.md) preserves the external use case and procurement distinctions.

## Read the specifications

| Document | Owns |
| --- | --- |
| [User stories](user-stories.md) | User goals, stable story IDs and links to acceptance requirements |
| [Workflow](workflow.md) | Installation expectations, project setup, area selection, wizard, Processing, failure behavior; WF-08 separately covers maintainer reference tooling |
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

Scope boundaries are maintained in
[classification exclusions](classification.md#cl-04-exclusions-and-interpretation)
and the [indicator catalogue](indicators-and-outputs.md#io-01-indicator-catalogue).
The latter links adopted scope decisions; the
[register](../architecture/open-questions.md) separates implementation gaps,
deferred scope and evidence/acceptance checks.

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

The [verification and deferred-work register](../architecture/open-questions.md)
owns current implementation gaps, provider checks and acceptance/release status.
Stories with outstanding functionality carry an explicit partial/deferred marker.
