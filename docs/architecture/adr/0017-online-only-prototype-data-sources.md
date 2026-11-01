# Limit prototype analysis data sources to online services

Status: accepted  
Recorded: 2026-11-01

Support only online services as analysis data sources in this prototype.
Loading local datasets as replacement or additional analysis evidence is outside
the prototype scope. This keeps the scope manageable: the prototype explores a
subset of the intended product and does not aim to fulfill all of its required
functionality. The current source policy is defined in
[WF-03](../../specs/workflow.md#wf-03-source-readiness-and-retrieval).

The full product should support local datasets alongside online sources. Local
support would let users edit and correct datasets to improve their accuracy and
use data supplied by customer organizations. Deferring this capability means
prototype analyses depend on the configured online evidence and cannot use those
local corrections or organization-provided datasets as analysis sources.

This boundary concerns analysis evidence, not locally supplied analysis-area
boundaries, locally written results and source snapshots, or packaged offline
help. Local dataset support remains deferred work for the full product; this
decision does not define its formats or integration design, or establish buyer
acceptance of the prototype's reduced scope.
[Project context](../../project-context.md),
[deferred scope](../../open-questions.md#scope-and-source-alternatives).
