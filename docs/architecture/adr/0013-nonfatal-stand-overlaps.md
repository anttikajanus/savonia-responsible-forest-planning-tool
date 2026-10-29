# Retain overlapping stands with traceable warnings

Status: accepted  
Recorded: 2026-10-29  
Supersedes: the stand-overlap acceptance limit in [ADR-0004](0004-stand-based-sensitivity-classification.md)

Planners need results from supplied stand attributes even where provider stand
polygons overlap. Retain every AOI-clipped parent geometry and its contributions,
regardless of overlap size, rather than rejecting larger overlaps or trimming
one stand using an arbitrary precedence. This deliberately permits duplicate
area and timber contributions in summaries; neither the outputs nor pairwise
overlap areas represent unique overlapping ground area.

Flag all pieces of each affected parent, record each pair in technical logging,
and deliver a completion warning through the shared workflow after publication.
The warning makes the trade-off visible while retaining source identity. An
overlap outside the AOI has no effect. This decision makes no claim about why
the provider geometries overlap. Grid conflicts, geometry invariants, the
sensitivity hit threshold and Section 10 promotion retain their separate policies.
See [geometry](../calculations.md#area-and-geometry) and
[CL-01](../../specs/classification.md#cl-01-reporting-domain-and-geometry).
