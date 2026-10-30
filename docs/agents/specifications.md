# Maintaining project specifications

Read this guide when planning a feature, changing user-visible behavior, completing
implementation or reconciling documentation. The [documentation map](README.md)
identifies the authoritative owners; this guide owns the handoff between them.

## Ownership

Use the affected maintained requirements as the starting point for current
behavior, technical references for exact contracts, and `.scratch/` for the
local proposal and useful debugging notes. `.scratch/` is ignored by Git and may be
absent in a fresh checkout. Keep final user goals and observable behavior in
`docs/specs/`; link technical details to their architecture owner. Maintained
documentation must contain the information needed without local work records.

The repository README provides the introduction, concise behavior summary and
setup entry points. Detailed examples, formulas and acceptance criteria belong
with the appropriate maintained owner, reached by links from that summary.

### Architecture scope

When writing or reviewing `docs/architecture/`, document the decisions and
contracts a maintainer needs to understand or safely change the system:

- Explain responsibilities, dependency and thread boundaries, data flow,
  deployment, consequential trade-offs and failure guarantees.
- Keep exact fields, units, formulas, accepted provider values and numerical
  tolerances where they define interoperability or the meaning of results.
  Link to their owner instead of repeating them in an overview or ADR.
- Leave renderer colors, fonts, line widths, widget geometry, internal naming,
  helper call sequences and routine test inventories in code/tests. Describe
  a runtime workaround only when it explains a consequential constraint; link
  to its implementation for the mechanics.
- Keep user interactions in specs/manuals and repeatable commands in the
  development guide. Keep useful debugging detail local; maintained documentation
  needs current limitations, outstanding gaps and the next check.

Before retaining a paragraph, identify the decision, boundary, guarantee or
external contract it explains. If it only restates discoverable implementation,
remove it. Review affected architecture after implementation; add detail only
when that architectural meaning or contract changed. Accepted ADRs retain
their recorded context and explicit supersession links.

## Planning

1. Read the affected current specs and relevant architecture before writing the proposal. Use the existing story and requirement IDs when describing a change.
2. Create or update `.scratch/<feature-slug>/spec.md` with the proposed behavior, acceptance criteria, failure policy and exclusions. After grilling, finish this working spec before implementation.
3. Link the current specs the work is expected to change. Keep undecided ideas, abandoned alternatives and implementation tickets in `.scratch/` until their outcome is resolved. A proposal does not establish current product behavior.

After grilling, the working spec must be ready before implementation begins.
For a wording, navigation or link correction that preserves behavior, edit the
existing owner directly; use an existing work record when available instead of
creating a new feature spec or user story solely for that correction.

## Completing implementation

Before reporting the feature complete:

1. Reconcile the working spec with the final implementation and verification evidence. Distinguish implemented behavior, remaining acceptance checks and deferred scope.
2. Update every affected functional document in `docs/specs/` in the same change. Include changed inputs, outputs, user interactions, failure/unknown behavior and interpretation limits. Update requirements in place so each document describes current behavior directly.
3. Update `docs/specs/user-stories.md` for added, changed or retired user goals. Preserve stable story/requirement IDs; allocate new IDs for new goals. For a retired goal, retain its ID with its disposition or replacement link rather than reusing the ID.
4. Review technical references and consequential ADRs in `docs/architecture/` against the [architecture scope](#architecture-scope), updating changed decisions and contracts rather than narrating implementation. Update domain terms in `GLOSSARY.md` and affected manuals/entry-point links. For an internal refactor, update architecture when needed and record that the functional specs were reviewed and behavior is unchanged.
5. Add links from the local working spec to the maintained specs/technical references that describe its outcome. Keep working records in `.scratch/` and publish final behavior, decisions and remaining evidence gaps in their maintained owners. Public documentation must not link to individual `.scratch/` files or depend on scripts stored there.
6. Check local links, requirement/story references and consistency between specs, architecture and actual behavior. Record any unresolved discrepancy explicitly, with its current behavior and follow-up. Keep outstanding checks clear; documentation promotion does not complete acceptance tests.

The documentation handoff is complete when the affected maintained docs reflect the final behavior, the working spec links to them, and remaining verification/deferred items have an explicit home. Use `Status: implemented` for implementation progress under [triage guidance](triage-labels.md); keep that status separate from documentation handoff and acceptance completion. Report any unfinished handoff rather than treating the feature as fully complete.

## Scope verification to the change

- For behavior changes, verify the affected acceptance criteria and follow the
  required [QGIS checks](qgis.md) before claiming plugin behavior is verified.
- For documentation-only corrections, check local paths/anchors, requirement IDs,
  ownership links and agreement with the existing contracts. Record that product
  behavior is unchanged. Packaged manual/resource changes also need their relevant
  help and package checks under QGIS guidance.
- Summarize checks performed and remaining concerns in the task response.
  Verification reports, date-stamped evidence summaries and test-history
  documentation are not required. Keep substantive unresolved questions in
  [open questions](../open-questions.md). Source measurement/update
  dates and machine-generated retrieval provenance retain their product meaning.
- Manual testing follows the [personal checklist](../testing/manual-acceptance.md).
  Its lightweight workflow governs manual checks. Local notes may help debugging; keep
  substantive defects and unanswered questions in their maintained owners.

## Writing a maintained spec

Use the existing functional topic when possible. Add a focused document and an index link only when it covers a distinct user-facing area. Include purpose/scope, user goals or story links, inputs/outputs, observable rules, failure/missing-data behavior, acceptance criteria and explicit gaps. Link exact field tables, formulas and consequential design decisions to their architecture owner under the scope above; routine implementation detail stays in code/tests.

Resolve a conflict by inspecting the implementation, accepted decisions and verification evidence. Keep proposal readiness, implementation status and acceptance evidence separate. Record the disposition of each code/spec mismatch before claiming conformance.
