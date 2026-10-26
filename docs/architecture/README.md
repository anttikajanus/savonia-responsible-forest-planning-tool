# Architecture

These documents describe the implemented architecture and adopted design decisions of **Savonia - Responsible Forest Planning**. User stories and functional requirements live in [specifications](../specs/README.md); outstanding validation and release work is listed in [open questions](open-questions.md).

The [agent guidance and documentation map](../agents/README.md) identifies the
other documentation owners and task instructions. For provider metadata and
documents, inspect the [local reference cache](../references/README.md) before
fetching another copy; its source manifest is versioned and downloads are ignored.

## Technical documentation

Start with the [technical architecture diagram and explanation](overview.md#system-diagram). The diagram is available as an [SVG](technical-architecture.svg) and an editable [Draw.io file](technical-architecture.drawio).

| Document | Purpose |
| --- | --- |
| [Overview](overview.md) | Execution path, module ownership, threading, outputs and failure boundaries |
| [Data sources](data-sources.md) | Required products, schema evidence, interpretation and provider references |
| [Source-layer requirements](source-layer-requirements.md) | Required/optional fields, aliases, identifiers and source-layer behavior |
| [Calculations](calculations.md) | Exact classification, geometry, field, aggregation and publication contracts |
| [Indicators](indicators.md) | Indicator rationale, provider evidence, accuracy and source limitations |
| [Operations](operations.md) | Logging, runtime, testing and bilingual help design |
| [Development](development.md) | Setup, reload, debugging, test and packaging commands |
| [Distribution](distribution.md) | Software inventory, licensing decisions and exported data attribution |
| [Deferred sources](deferred-sources.md) | Candidate datasets and policy questions outside the implemented scope |
| [Open questions](open-questions.md) | Remaining verification and release work |

[Project context](../project-context.md) explains the external use case and procurement scope. [GLOSSARY.md](../../GLOSSARY.md) defines domain terminology.

## Architecture decision records

ADRs explain adopted design choices and their reasons. Detailed contracts are
in the technical references above.

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
