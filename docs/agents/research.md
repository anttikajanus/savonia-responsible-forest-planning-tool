# Research

Read this guide for research tasks and use `mattpocock-skills:research`.
It complements the [documentation map](README.md): research notes hold findings
and sources; maintained specs and technical references hold adopted outcomes.

## Workflow

1. Read the affected maintained specification/technical reference and its open
   questions so the investigation answers an actual evidence gap.
2. For provider capabilities, schemas or PDF/XLSX documentation, inspect
   `docs/references/service-metadata/` first. Follow the [reference instructions](../references/service-metadata/README.md)
   to populate missing files. Use `--list` to inspect source URLs offline and
   `--only` to select a needed path prefix. Refresh explicitly when the question
   needs current evidence rather than the cached snapshot.
3. Follow the skill's primary-source and claim-level citation requirements.
   Distinguish a local observation from a provider claim or inference. Record
   exact endpoint/typename where relevant, source document dates, retrieval dates
   and what was actually checked. Cached metadata is evidence at capture time;
   an XSD or PDF alone does not verify feature values or geographic completeness.
4. Write one Markdown file per question under `docs/research/`, using a short
   lowercase kebab-case name, such as `forest-road-permits.md`. Link to each
   primary source next to the supported claim, including its public URL even
   when the inspected artifact is local.

Keep raw research notes in `docs/research/`; a working ticket can link to them
from `.scratch/`. This directory is currently ignored by Git, so promote enduring
findings to versioned owners before relying on them in a fresh checkout.

## Finalizing findings

When a research question is resolved, record adopted consequential choices as ADRs under `docs/architecture/adr/` and move enduring technical guidance and primary-source citations into the appropriate `docs/architecture/` reference. Record remaining questions in the [project-wide register](../open-questions.md), linking to their relevant specs, technical contracts and evidence. Capture adopted user-facing requirements in `docs/specs/` using the [specification workflow](specifications.md), keeping proposals in `.scratch/`. Put project context outside architecture when it is not technical. Distinguish proposals from implemented decisions; dated verification reports are not required.

Mark a fully superseded note `Disposition: ready to delete`, link its replacements,
and redirect incoming project-documentation links before removal. A note with
unique unresolved findings remains needed until those findings have a maintained
home. Keep downloaded source artifacts and retrieval metadata in ignored
`docs/references/service-metadata/`; maintain their public URLs and paths in its versioned
manifest. Use [reference instructions](../references/service-metadata/README.md) for cache and
application-identifier handling instead of copying downloads into Git or fixtures.
