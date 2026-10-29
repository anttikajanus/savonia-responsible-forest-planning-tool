# Issue tracker: Local Markdown

Read this guide when a task or skill asks you to create, fetch, publish or update
an issue or working spec. Agent work lives as local Markdown in ignored
`.scratch/`; create the feature directory when needed. Public documentation must
remain usable without these files.
[GitHub Issues](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues)
is the public reporting channel described in the repository README; a skill's
generic tracker instruction maps to the local files below unless the user names
an external destination. The [documentation map](README.md) identifies maintained
requirements and technical owners; follow the [specification handoff](specifications.md)
when planning changes and completing implementation.

## Conventions

### Local development artifacts

Reserve `.scratch/` for working tickets, specs and their Markdown discussion,
review and verification records. Put disposable code, debugging scripts, logs,
screenshots, extracted packages, simulations and local tooling in ignored
`.local/<feature-slug>/`. The shared check runner uses `.local/checks/`; see the
[development guide](../architecture/development.md#local-check-runner).
Keep reusable scripts needed by the repository in versioned `scripts/`.
Record verification summaries in the working Markdown records and reference
supporting artifacts in `.local/` when useful.

### Working records

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Record triage readiness as `Status:` using the [triage labels](triage-labels.md).
  Track ticket progress separately with `Execution: open`, `claimed` or `resolved`;
  completion of a ticket does not establish completed feature acceptance.
- Working specs use `Status: implemented` when their implementation work is
  complete. Keep outstanding verification and documentation handoff explicit.
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

For a feature proposal, create `.scratch/<feature-slug>/spec.md`. For a task,
create `.scratch/<feature-slug>/issues/<NN>-<slug>.md`. Include the question or
scope, expected outcome, relevant maintained requirement IDs, dependencies and
verification needed. Readiness must reflect unanswered blocking questions.

## When a skill says "fetch the relevant ticket"

Read the referenced file. If given only a number, locate it within the named
feature; inspect its working spec, dependency tickets and linked maintained
requirements before changing it. Preserve comments and dated verification history.

## Wayfinding operations

Apply this section when a workflow explicitly uses a map with dependent child
tickets. Ordinary small tasks need only the spec/ticket conventions above.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. `Type:` records `research`/`prototype`/`grilling`/`task`; `Status:` records triage and `Execution:` records progress.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every listed ticket has `Execution: resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Execution: claimed` and save before work on that ticket.
- **Resolve**: append the answer and verification under `## Answer`, set
  `Execution: resolved`, then add a brief answer and link to the map's Decisions-so-far.
