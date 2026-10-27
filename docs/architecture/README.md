# Architecture

These documents describe the implemented architecture and adopted design decisions of **Savonia - Responsible Forest Planning**. User stories and functional requirements live in [specifications](../specs/README.md); outstanding validation and release work is listed in [open questions](open-questions.md).

The [agent guidance and documentation map](../agents/README.md) identifies the
other documentation owners and task instructions. For provider metadata and
documents, inspect the [local reference cache](../references/README.md) before
fetching another copy; its source manifest is versioned and downloads are ignored.

## Technical documentation

Start with the [technical architecture diagram and explanation](overview.md#system-diagram). The diagram is available as an [SVG](technical-architecture.svg) and an editable [Draw.io file](technical-architecture.drawio).

### Current technical contracts

| Need | Owner |
| --- | --- |
| Execution path, module ownership and threading | [Overview](overview.md) |
| Provider fields, aliases, accepted input values and source identity | [Source-layer requirements](source-layer-requirements.md) |
| Geometry operations, numerical tolerances and tier-to-field mapping | [Geometry and classification](calculations.md) |
| Intersection weights, metric statistics and aggregation examples | [Indicator calculations](indicator-calculations.md) |
| Stored fields, field order, coverage JSON and output tables | [Output schema](output-schema.md) |

### Evidence and interpretation

| Need | Owner |
| --- | --- |
| Configured products/endpoints, dated checks and provider references | [Data sources](data-sources.md) |
| Indicator evidence, rationale, accuracy and source limitations | [Indicator design](indicators.md) |
| Candidate datasets and unadopted policy questions | [Deferred sources](deferred-sources.md) |

### Operations, development and verification

| Need | Owner |
| --- | --- |
| Logging configuration and runtime language/help mechanisms | [Operations](operations.md) |
| Repeatable setup, reload, debugging, test and packaging procedures | [Development](development.md) |
| Release mechanics, software inventory, licensing and exported attribution | [Distribution](distribution.md) |
| Current implementation gaps, provider evidence gaps and pending acceptance | [Open questions](open-questions.md) |

[Project context](../project-context.md) explains the external use case and procurement scope. [GLOSSARY.md](../../GLOSSARY.md) defines domain terminology.

## Architecture decision records

ADRs record adopted choices, alternatives and consequences at the recorded date.
Their original decision context is retained, including historical constants;
they are not another current configuration reference. The technical contracts
above and linked functional requirements establish current behavior. If a
consequential choice changes, record its replacement and explicit supersession
rather than silently rewriting the original decision. Accepted status does not
establish implementation or provider/desktop acceptance.

| ADR | Decision |
| --- | --- |
| [0001](adr/0001-spatial-input-preparation-boundary.md) | Prepare spatial evidence for a separate value-table model |
| [0002](adr/0002-shared-processing-workflow.md) | Share one workflow between the wizard and Processing |
| [0003](adr/0003-provider-field-source-contracts.md) | Validate provider fields against semantic contracts |
| [0004](adr/0004-stand-based-sensitivity-classification.md) | Keep stand-based pieces and cumulative sensitivity tiers |
| [0005](adr/0005-independent-stand-and-grid-indicators.md) | Combine stand geometry with independent grid indicators |
| [0006](adr/0006-evidence-coverage-and-publication.md) | Preserve unknown evidence and coordinate paired outputs |
| [0007](adr/0007-separate-operational-log-channels.md) | Separate technical diagnostics and business-action records |
| [0008](adr/0008-qgis-language-and-offline-help.md) | Follow QGIS language and ship offline help |
| [0009](adr/0009-project-licence-and-portable-attribution.md) | Package MIT project notices and portable dataset attribution |
| [0010](adr/0010-wfs-2-only.md) | Support only WFS 2.0; exclude legacy WFS 1.x compatibility |
| [0011](adr/0011-deciduous-volume-instead-of-birch.md) | Use deciduous volume instead of supporting birch-specific volume |
| [0012](adr/0012-local-reference-downloads.md) | Download provider references locally and keep the cache out of Git |
