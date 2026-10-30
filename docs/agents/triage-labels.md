# Triage labels and execution state

Use these five readiness labels in a working issue's `Status:` field. The skill
role names map directly to the same local strings; “AFK-ready” maps to
`ready-for-agent`. File locations and ticket operations are owned by the
[local tracker guide](issue-tracker.md).

| Label | Meaning |
| --- | --- |
| `needs-triage` | The issue needs evaluation before its next action is chosen. |
| `needs-info` | Missing information blocks implementation. |
| `ready-for-agent` | Scope, dependencies and acceptance criteria are sufficient for agent implementation. |
| `ready-for-human` | The next required action needs a human. |
| `wontfix` | The proposed work will not be pursued. |

## Completion is a separate dimension

Ticket progress uses `Execution: open`, `claimed` or `resolved` under the tracker
conventions. Keep readiness in `Status:`; a resolved ticket can retain the
readiness label under which it was executed.

For working specs, set `Status: implemented` when implementation work is complete. This records implementation progress; review or verification may still remain. Before reporting the feature fully complete, also finish the [documentation handoff](specifications.md#completing-implementation) to `docs/specs/` and `docs/architecture/`, recording any outstanding acceptance checks separately.

An accepted ADR, implemented spec and passing automated check each establish a
different fact. Keep substantive acceptance questions and provider-verification
gaps in the [maintained register](../architecture/open-questions.md). Verification
reporting follows [specification guidance](specifications.md#scope-verification-to-the-change).
Manual checks follow the
[personal checklist](../testing/manual-acceptance.md).
