# Agent instructions

Use the [documentation map](docs/agents/README.md) to find the owner of each kind
of information. Current behavior belongs in `docs/specs/`, technical contracts
in `docs/architecture/`, and local working plans in ignored `.scratch/`.

## Read the guidance for your task

| Task | Required guidance |
| --- | --- |
| Explore domain terms or design decisions | [Domain documentation](docs/agents/domain.md) |
| Plan a feature, change behavior, complete implementation or reconcile documentation | [Specification workflow](docs/agents/specifications.md) |
| Create, fetch or update working issues/specs; map a skill's tracker instructions | [Local issue tracker](docs/agents/issue-tracker.md) and [triage labels](docs/agents/triage-labels.md) |
| Research a question | Use `mattpocock-skills:research` and follow [research guidance](docs/agents/research.md); save findings in `docs/research/` |
| Inspect provider schemas/documents or set up local references | Read the cached files first; follow [reference instructions](docs/references/README.md) to populate missing files or explicitly refresh them |
| Read, change, review, test, package or document code under `qgis_plugin/` | First read [QGIS guidance](docs/agents/qgis.md); its implementation workflow, testing and Finnish/English checks are required |
| Edit agent instructions or skills | Use `mattpocock-skills:writing-for-agents`; keep task conditions explicit and detailed rules with their owner |

## Planning and completion

After grilling, create or update `.scratch/<feature-slug>/spec.md` before
implementation; begin implementation only when that spec is ready. Reconcile
completed behavior into the maintained specs and architecture. Use the five
default [triage labels](docs/agents/triage-labels.md); `implemented` records spec
implementation separately from acceptance and verification.

## Diagrams

Use Draw.io for complex diagrams needing detailed layout or visual editing.
Use Mermaid for straightforward diagrams, such as flow diagrams.
