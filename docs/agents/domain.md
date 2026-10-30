# Domain documentation

Read this guide when exploring domain concepts, changing terminology, or proposing
an architectural decision. The repository uses one context and one
[root glossary](../../GLOSSARY.md). The [documentation map](README.md) owns the
directory/ownership overview.

## Read the relevant owners

1. Read the glossary entries for the concepts involved. Use their terms in code,
   issues, hypotheses and tests, including the distinctions between scenarios,
   sensitivity tiers, classification and descriptive indicators.
2. For behavior questions, read the affected stories and requirements through the
   [specification index](../specs/README.md).
3. For design questions, read the relevant technical contract and adopted ADRs
   through the [architecture index](../architecture/README.md).
4. If a requested local `.scratch/` work item exists, use it for proposal details
   and verification records. Reconcile changes through
   [specification maintenance](specifications.md).

If a required owner or definition is missing, record the specific gap in the
working note and continue work that does not depend on it. Add a definition when
its meaning is resolved by the task, rather than creating speculative context
maps or parallel glossaries.

## Maintain terms and decisions

- Preserve the glossary's preferred terms and its explicit distinctions. Record
  a new or changed meaning in the glossary and update affected references together.
- Use `mattpocock-skills:domain-modeling` when building or sharpening the domain
  model, editing glossary entries or recording an ADR.
- Record consequential adopted choices as sequentially numbered ADRs under
  `docs/architecture/adr/`, then add them to the architecture index. Detailed
  contracts stay in the relevant technical reference.
- Identify any existing ADR that a proposal would change and explain why it
  should be reconsidered. For example, replacing provider-field readiness with
  a saved-schema decision changes
  [ADR-0003](../architecture/adr/0003-provider-field-source-contracts.md).
- Keep acceptance limits explicit. An adopted decision is
  separate from proof that its implementation or provider assumptions are verified.
