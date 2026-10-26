# Validate semantic source contracts against actual provider fields

Status: accepted  
Recorded: 2026-10-26

Saved XSDs can include unrelated optional properties and global feature declarations, so comparing every element against layer fields can reject valid inputs. Setup and analysis share a semantic-source contract checked against `layer.dataProvider().fields()`, resolve required aliases case-insensitively in declared priority order, and use that same mapping to normalize feature values. Saved schema JSON is provenance only; joins, virtual fields, extra field order and stale schema metadata cannot satisfy or invalidate the provider contract. The trade-off is that readiness establishes required names, not field types, valid values or geographic completeness; those require separate validation.

For protected categories, `tyyppilyhenne` precedes `kohdetyyppi`; a null chosen value does not cause a per-record alias fallback. The contract is provider-neutral, while current source selection remains managed WFS. See [source requirements](../source-layer-requirements.md), [implementation](../../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/source_readiness.py), and [data-source evidence](../data-sources.md).
