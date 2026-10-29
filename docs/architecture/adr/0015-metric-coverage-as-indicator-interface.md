# Keep metric coverage as the indicator evidence interface

Status: accepted  
Recorded: 2026-10-29

Independent indicator status and per-value diagnostic payloads duplicate or
complicate result inspection. Remove those interfaces while retaining metric
coverage, its own status members and exact sufficient statistics. Coverage is
needed for independent partial-data weighting and the workbook coverage sheet;
removing it would require a wider aggregation redesign. This narrows the
presentation of evidence while preserving the unknown-value and paired-output
decisions in [ADR-0006](0006-evidence-coverage-and-publication.md).

Readable ordinary criterion fields complement retained classification reasons.
Numeric null/partial behavior, bounded area corrections and fatal invariants
remain intact. Operational errors, source geometry/retrieval records and stand
overlap diagnostics remain separate concerns. See the
[output schema](../output-schema.md#metric-coverage).
