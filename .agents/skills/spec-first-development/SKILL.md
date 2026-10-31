---
name: spec-first-development
description: Use the project's spec-first workflow when planning or implementing a feature or user-visible behavior change.
---

# Spec-first development

Use this workflow for feature work and user-visible behavior changes. Repository guidance remains authoritative for local requirements, documentation ownership, tracker conventions, and QGIS checks.

## Plan the behavior

1. Read affected maintained specs, relevant architecture, and `GLOSSARY.md` when present. Read any existing `.scratch/<feature>/` work record before creating another.
2. Use `mattpocock-skills:to-spec` to turn the agreed conversation and codebase findings into a working spec. Follow [specification guidance](../../../docs/agents/specifications.md) and [local tracker conventions](../../../docs/agents/issue-tracker.md): the working spec belongs at `.scratch/<feature>/spec.md`, and implementation tickets belong in its `issues/` directory.
3. Identify the highest useful public test seam in the spec. Explain what it verifies and what it leaves unverified. Get the user's agreement on the proposed seam before writing tests.
4. Start implementation only when the working spec is ready and blocking decisions are resolved. Mark readiness with the project's [triage labels](../../../docs/agents/triage-labels.md).

For wording, navigation, or link changes that preserve behavior, edit the existing documentation owner directly instead of creating a feature spec. For bug fixes, use an existing spec or working ticket when available; create a focused working record if the expected behavior is otherwise unclear.

## Implement and verify

1. For a spec with a ticket graph, use `mattpocock-skills:implement-spec`. For a single ticket or scoped task, use `mattpocock-skills:implement`.
2. At implementation time, load and follow `mattpocock-skills:tdd` where available. Work in red-green vertical slices at the agreed public seams; keep tests focused on observable behavior.
3. Follow task-specific repository guidance, including [QGIS workflow and verification](../../../docs/agents/qgis.md) for changes under `qgis_plugin/`.
4. Reconcile implemented behavior into maintained specs and architecture as required by [specification guidance](../../../docs/agents/specifications.md). Keep implementation status distinct from acceptance and verification status.

The upstream skills are reusable dependencies and stay outside this repository. When an upstream skill is unavailable, follow the repository guidance linked above and state that limitation in the task summary.
