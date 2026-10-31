# Project specifications

These are the maintained user stories and functional specifications for **Savonia - Responsible Forest Planning** / **Savonia - Vastuullinen metsäsuunnittelu**. They describe this personal prototype's current behavior.

This is Antti Kajanus's unfinished personal learning project. Neither the prototype nor its results are official, finalized, backed, endorsed or approved by Savonia. Requirements here record prototype decisions, not buyer acceptance or a claim of procurement compliance. [Project context](../project-context.md) preserves the external use case and procurement distinctions.

## Read the specifications

| Document | Owns |
| --- | --- |
| [User stories](user-stories.md) | User goals, stable story IDs and links to acceptance requirements |
| [Workflow](workflow.md) | Installation expectations, project setup, area selection, wizard, Processing, failure behavior; WF-08/09 separately cover maintainer references and isolated checks |
| [Classification](classification.md) | Reporting domain, sensitivity tiers, spatial behavior and interpretation limits |
| [Indicators and outputs](indicators-and-outputs.md) | Required indicators, missing values, presentation, result files and map review |
| [Help and language](help-and-language.md) | Finnish/English behavior, offline help, About, identity, accessibility and attribution |

Requirement IDs such as `WF-03` are stable within these documents. The stories link to their acceptance requirements; the detailed criteria live in those requirements rather than being repeated per story.

## Product purpose and scope

Municipal forest planners and GIS analysts select an area, combine online forest and environmental evidence, and obtain classified forest polygons and descriptive indicators for six cumulative sensitivity tiers. Auditors can inspect the evidence, coverage and provenance of each run. Users of a separate value-table model receive spatial inputs for subsequent scenario comparison.

The current scope includes:

- A QGIS plugin with a persistent wizard and an equivalent Processing workflow.
- Eleven configured online WFS source layers, explicit area selection and validation, including the Ranta10 line-river, polygon-river and lake products.
- One stand-based polygon result with six tier classifications, independent stand/grid indicators, source snapshots, combined riparian-buffer evidence and coverage.
- A paired GeoPackage and Excel workbook, with Finnish or English presentation and offline instructions.

Scope boundaries are maintained in
[classification exclusions](classification.md#cl-04-exclusions-and-interpretation)
and the [indicator catalogue](indicators-and-outputs.md#io-01-indicator-catalogue).
The latter links adopted scope decisions; the
[register](../open-questions.md) separates implementation gaps,
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
[development guide](../architecture/development.md) for automated checks and the
[manual checklist](../testing/manual-acceptance.md) for interactive steps,
expected results and personal checking.

The [verification and deferred-work register](../open-questions.md)
owns current implementation gaps, provider checks and acceptance/release status.
Stories with outstanding functionality carry an explicit partial/deferred marker.

Use these links to distinguish completed changes from remaining work:

| Area | Requirement and current status | Checks / remaining work |
| --- | --- | --- |
| Stand overlaps, required price and run readiness | Implemented: [CL-01](classification.md#cl-01-reporting-domain-and-geometry), [WF-04–06](workflow.md#wf-04-analysis-area-and-destination) | [Automated checks](../architecture/development.md#automated-regression-verification); personal [desktop checklist](../testing/manual-acceptance.md#inputs-and-execution). |
| Calculated sawlog value | Implemented: [IO-01–04](indicators-and-outputs.md#io-01-indicator-catalogue) | [Automated checks](../architecture/development.md#automated-regression-verification); [QGIS/Excel interpretation checks](../testing/manual-acceptance.md#numerical-interpretation-and-exceptional-evidence). |
| Polygon source queries and negligible result fragments | Implemented: [WF-03](workflow.md#wf-03-source-readiness-and-retrieval), [CL-01](classification.md#cl-01-reporting-domain-and-geometry) | [Automated checks](../architecture/development.md#automated-regression-verification) and bounded [provider evidence](../open-questions.md#provider-evidence). |
| US-005 map review | Implemented: [IO-06](indicators-and-outputs.md#io-06-map-review-and-run-retention) | Current scope confirmed by the project owner; visual [desktop checks](../open-questions.md#interactive-acceptance) remain separate. |
| Maintainer reference material | Implemented tooling: [WF-08](workflow.md#wf-08-local-development-reference-material) | [Cache integrity and missing authenticated material](../open-questions.md#reference-material-integrity); cached schemas do not verify feature values. |
