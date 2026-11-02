---
name: spec-first-development
description: Use the project's spec-first workflow when planning or implementing a feature or user-visible behavior change.
---

# Spec-first development

Use this workflow for feature work and user-visible behavior changes. Repository guidance remains authoritative for local requirements, documentation ownership, tracker conventions, and QGIS checks.

## Plan the behavior

1. Read affected maintained specs, relevant architecture, and `GLOSSARY.md` when present. Read any existing `.scratch/<feature>/` work record before creating another.
2. For open design questions, use `mattpocock-skills:grill-me` to sharpen the plan. Use `mattpocock-skills:grill-with-docs` when the discussion also needs domain terms or decisions recorded in the glossary or an ADR. Follow [domain guidance](../../../docs/agents/domain.md) for those records.
3. Use `mattpocock-skills:to-spec` to synthesize the agreed conversation and codebase findings into `.scratch/<feature>/spec.md`. It writes the spec; it does not create the implementation ticket graph. Follow [specification guidance](../../../docs/agents/specifications.md).
4. After the spec is prepared, use `mattpocock-skills:to-tickets` to propose tracer-bullet tickets and their blocking edges. Get the user's agreement on the breakdown, then create one file per approved ticket under `.scratch/<feature>/issues/` and link each ticket and its dependencies from the spec. Follow [local tracker conventions](../../../docs/agents/issue-tracker.md). A multi-ticket spec must have its complete graph before `implement-spec` handoff; use one focused ticket and `implement` when a graph adds no value.
5. Identify the highest useful public test seam in the spec. Explain what it verifies and what it leaves unverified. Get the user's agreement on the proposed seam before writing tests.
6. Start implementation only when the working spec and its planned ticket files are ready and blocking decisions are resolved. Mark readiness with the project's [triage labels](../../../docs/agents/triage-labels.md).

For wording, navigation, or link changes that preserve behavior, edit the existing documentation owner directly instead of creating a feature spec. For bug fixes, use an existing spec or working ticket when available; create a focused working record if the expected behavior is otherwise unclear.

## Implement and verify

1. For a spec with a ticket graph, use `mattpocock-skills:implement-spec`. For a single ticket or scoped task, use `mattpocock-skills:implement`.
2. At implementation time, load and follow `mattpocock-skills:tdd` where available. Work in red-green vertical slices at the agreed public seams; keep tests focused on observable behavior.
3. Follow task-specific repository guidance, including [QGIS workflow and verification](../../../docs/agents/qgis.md) for changes under `qgis_plugin/`.
4. Reconcile implemented behavior into maintained specs and architecture as required by [specification guidance](../../../docs/agents/specifications.md). Keep implementation status distinct from acceptance and verification status.

The upstream skills are reusable dependencies and stay outside this repository. When an upstream skill is unavailable, follow the repository guidance linked above and state that limitation in the task summary.
