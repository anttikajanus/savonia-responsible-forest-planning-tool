# Retrieve the full analysis-area evidence before classification

Status: accepted  
Recorded: 2026-11-01

Keep the prototype's area-of-interest (AOI) workflow: retrieve all required
source evidence for the selected area before classifying stand pieces and
calculating their indicators. Retain the clipped source records, source
snapshots and grid-cell spatial index in memory for reuse across the run.
Geometry transformation, repair, clipping and water buffering already happen
during retrieval; this decision concerns the boundary before classification and
indicator calculation, not an absence of geometry calculations during download.

This keeps the prototype scope manageable and avoids repeated source requests
for each stand piece. The implementation follows this order in the
[workflow](../../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow.py),
retains source collections and memory-layer snapshots in
[retrieval](../../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/source_loading.py),
and builds an in-memory index in the
[grid sampler](../../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/grid_sampling.py).
Stand pieces are calculated sequentially against that retained evidence; they
are not separate fetch/calculate/release jobs. WFS paging and spatial filtering
reduce request sizes and irrelevant candidates but do not bound the total
retained working set. The wizard's background task does not change this design.

Large AOIs can bring enough inventory grid cells (hilat), other source features
and result geometry into memory to exhaust available memory and potentially
crash QGIS. The workflow has no application-level AOI-size, retained-feature or
memory-budget guard. This is a scalability risk inferred from the implementation,
not a reproduced crash or a measured safe-area threshold.

The full product should likely fetch and calculate in bounded work units based
on stands or other geometries, release source data as each unit completes, and
parallelize independent units with a bounded number of workers. Parallelism
alone can increase memory use; bounded fetching, retained data and output
buffering are needed to control the working set. A production design must
preserve neighboring evidence needed by buffers, avoid duplicate contributions
across work units, and retain consistent coverage, provenance and summaries.
That redesign is deferred, with no claim that the prototype supports arbitrarily
large areas. See the [current execution boundary](../overview.md#aoi-wide-working-set).
