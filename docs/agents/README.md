# Agent guidance and documentation map

[AGENTS.md](../../AGENTS.md) routes tasks to the required guides in this
directory. Use the map below to choose where to read and maintain project
information; follow only the branches relevant to the task.

## Documentation ownership

| Need | Owner | How to use it |
| --- | --- | --- |
| Project introduction and setup | [Repository README](../../README.md) | Keep the overview concise; link to detailed instructions and contracts. |
| External use case and procurement context | [Project context](../project-context.md) | Distinguish source requirements from this personal prototype's adopted behavior. |
| Domain terminology | [Root glossary](../../GLOSSARY.md) | One shared vocabulary; follow [domain guidance](domain.md) when changing terms or ADRs. |
| Current user goals and functional requirements | [Specification index](../specs/README.md) | Start with the affected stories and requirement IDs; use [specification maintenance](specifications.md) for changes. |
| Technical design, fields, formulas and adopted decisions | [Architecture index](../architecture/README.md) | Read the relevant contract and ADRs; link to the owning reference instead of copying its details. |
| Commands for development, tests and packaging | [Development guide](../architecture/development.md) | Use the documented runtime/commands; keep test outcomes in verification records. |
| Planner instructions | [English manual](../help/manual_en.html) and [Finnish manual](../help/manual_fi.html) | Maintain equivalent user instructions; [QGIS guidance](qgis.md) owns localization and package checks. |
| Local working proposals, issues and verification records | Ignored `.scratch/<feature-slug>/` | Follow the [local tracker](issue-tracker.md) and [triage mapping](triage-labels.md). Publish current behavior and remaining gaps in maintained documentation. |
| Research evidence | [Research directory](../research/README.md) | Follow [research guidance](research.md); promote adopted requirements, decisions and unresolved questions to their maintained owners. |
| External source material | [Reference index](../references/README.md) | Procurement PDFs are versioned under `procurement/629864/`; provider evidence has a separate cache. |
| Provider capabilities, schemas and PDF/XLSX documents | [Service metadata](../references/service-metadata/README.md) | Read cached files first. The manifest and instructions are versioned; downloads and retrieval metadata are ignored. |
| Remaining acceptance and provider checks | [Open questions](../architecture/open-questions.md) | Preserve explicit gaps and evidence dates; implementation completion does not close acceptance. |

## Reading and handoff

1. Use the relevant [root task pointer](../../AGENTS.md#read-the-guidance-for-your-task),
   then read the affected maintained owner above. If a requested local work item
   exists under `.scratch/`, consult it after identifying current behavior.
2. Keep one authoritative description for each detail. Cross-link functional
   requirements, technical contracts, manuals and evidence rather than repeating
   their full contents in every document.
3. Finish a change when the affected owners agree with the implementation,
   verification is recorded, and remaining gaps are explicit. For wording or
   navigation edits, check links and meaning without creating new product stories.

When code and documentation disagree, inspect the implementation and verification
evidence, then record and resolve the discrepancy under the
[specification workflow](specifications.md). Check implementation and acceptance
status separately.
