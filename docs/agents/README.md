# Agent guidance and documentation map

[AGENTS.md](../../AGENTS.md) routes tasks to the required guides in this
directory. Use the map below to choose where to read and maintain project
information; follow only the branches relevant to the task.

## Optional agent setup

This repository includes a project-scoped [spec-first development workflow](../../.agents/skills/spec-first-development/SKILL.md). It connects upstream skills to the local spec, tracker, and documentation conventions. Keep reusable upstream skill files outside this repository; the workflow still applies if an upstream skill is unavailable.

For agent-assisted development, install the `mattpocock/skills` collection as an
external plugin using the [upstream installation instructions](https://github.com/mattpocock/skills#installation-30-second-setup)
for your agent. Keep upstream skill files outside this repository. The repository's
[spec-first development workflow](../../.agents/skills/spec-first-development/SKILL.md)
connects those reusable skills to this project's local spec, tracker and documentation
rules. The plugin setup is optional for developing and running the project; follow
the repository workflow even when an upstream skill is unavailable.

When a skill asks for project-specific setup, use the [local issue tracker](issue-tracker.md),
[triage labels](triage-labels.md) and documentation ownership map below for the
tracker, labels and document destinations.

## Documentation ownership

| Need | Owner | How to use it |
| --- | --- | --- |
| Project introduction and setup | [Repository README](../../README.md) | Keep the overview concise; link to detailed instructions and contracts. |
| External use case and procurement context | [Project context](../project-context.md) | Distinguish source requirements from this personal prototype's adopted behavior. |
| Domain terminology | [Root glossary](../../GLOSSARY.md) | One shared vocabulary; follow [domain guidance](domain.md) when changing terms or ADRs. |
| Current user goals and functional requirements | [Specification index](../specs/README.md) | Start with the affected stories and requirement IDs; use [specification maintenance](specifications.md) for changes. |
| Technical boundaries, contracts and adopted decisions | [Architecture index](../architecture/README.md) | Read the relevant contract and ADRs; apply [architecture scope](specifications.md#architecture-scope) when writing or reviewing them. |
| Commands for development, tests and packaging | [Development guide](../architecture/development.md) | Use the documented runtime/commands; summarize checks in the task response. |
| Personal manual testing | [Manual checklist](../testing/manual-acceptance.md) | Use its steps and expected results when checking the installed plugin; follow its lightweight workflow. |
| Planner instructions | [English manual](../help/manual_en.html) and [Finnish manual](../help/manual_fi.html) | Maintain equivalent user instructions; [QGIS guidance](qgis.md) owns localization and package checks. |
| Local working proposals, issues and verification records | Ignored `.scratch/<feature-slug>/` | Follow the [local tracker](issue-tracker.md) and [triage mapping](triage-labels.md). Publish current behavior and remaining gaps in maintained documentation. |
| Local scripts, debugging and generated artifacts | Ignored `.local/` | Use the [script index](../../scripts/README.md) for reusable repository scripts; follow the [local artifact guidance](issue-tracker.md#local-development-artifacts) for local files. The [development guide](../architecture/development.md#local-check-runner) owns check-runner commands. |
| Research evidence | [Research guidance](research.md) | Save findings under ignored `docs/research/`; promote adopted requirements, decisions and unresolved questions to their maintained owners. |
| External source material | [Reference index](../references/README.md) | Procurement PDFs are versioned under `procurement/629864/`; provider evidence has a separate cache. |
| Provider capabilities, schemas and PDF/XLSX documents | [Service metadata](../references/service-metadata/README.md) | Read cached files first. The manifest and instructions are versioned; downloads and retrieval metadata are ignored. |
| Project-wide gaps, provider questions, pending acceptance and deferred choices | [Open questions](../open-questions.md) | Keep unresolved questions and limitations explicit; implementation completion does not close acceptance. |

## Reading and handoff

Keep inspection bounded: locate headings or filenames first, then read the
relevant section or line range. Reuse guidance already loaded in the current
context. Scope `rg` to relevant paths and file types; use `rg -l` for filenames or
`rg -n -m 10 --max-columns 200 --max-columns-preview` for bounded content matches.
Search SVGs and other assets containing embedded images only when relevant, using
filename-only results or bounded content previews.

1. Use the relevant [root task pointer](../../AGENTS.md#read-the-guidance-for-your-task),
   then read the affected maintained owner above. If a requested local work item
   exists under `.scratch/`, consult it after identifying current behavior.
2. Keep one authoritative description for each detail. Cross-link functional
   requirements, technical contracts, manuals and evidence rather than repeating
   their full contents in every document.
3. Finish a change when the affected owners agree with the implementation,
   verification scope is clear, and remaining gaps are explicit. For wording or
   navigation edits, check links and meaning without creating new product stories.

When code and documentation disagree, inspect the implementation and verification
evidence, then record and resolve the discrepancy under the
[specification workflow](specifications.md). Check implementation and acceptance
status separately.
