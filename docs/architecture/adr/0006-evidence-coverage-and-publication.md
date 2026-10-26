# Preserve unknown evidence and coordinate one paired publication

Status: accepted  
Recorded: 2026-10-26

An empty iterator can hide a failed request, and a schema-ready source can still contain missing metric values. Required-source, request, geometry and classification-interpretation failures therefore stop the run; successful empty retrieval remains distinct from failure, and missing numeric values retain metric-specific unknown/partial coverage rather than becoming zero. Retain exact sufficient statistics for aggregation, snapshots and provenance, then publish one coordinated GeoPackage/workbook pair. This preserves traceability at the cost of larger metadata and explicit partial-result interpretation. See [source failure handling](../data-sources.md#wfs-retrieval-success), [coverage and rounding](../indicators.md), and [publication source](../../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow_steps/publishing.py).

Volumes publish as whole m³/ha and areas as 0.01 ha using half-up rounding after aggregation; exact coverage statistics remain available. If either output write fails, remove partial files and report failure; the paired cleanup is not crash-atomic. These outputs prepare evidence, so a successful no-hit or rounded zero must not be presented as proof of complete inventory or legal permission. [Reporting precision](../calculations.md#comparing-indicators-and-reporting-precision).
