# Open questions and remaining verification

This register contains unresolved implementation gaps, provider questions,
planning assumptions and acceptance/release checks. Settled behavior and scope
belong in [specs](specs/README.md) and [architecture](architecture/README.md).
Automated procedures belong to [development](architecture/development.md), and
interactive procedures to the [manual checklist](testing/manual-acceptance.md).

## Provider evidence

### Reference material integrity

The authenticated `mml/wmts/get-capabilities.xml` reference is still missing.
Capture it when an authorized key is available, following the
[reference instructions](references/service-metadata/README.md#provider-credentials).
Keep this material-availability check separate from live feature values and
coverage verification.

### Live values and service behavior

| Item | Current limit and next evidence needed |
| --- | --- |
| Analysis polygon queries | Verify the original multipart parcel selection interactively, representative AOIs on all eleven sources, provider handling of malformed polygons before local repair, and deployment-specific GET limits. Bounded samples do not establish completeness or a performance guarantee. |
| Setup responsiveness | Investigate the reported minute-long setup stall end to end. Use the manual checklist's MT-08 to separate source initialization waits from map rendering. |
| MML property context | Verify both live collections/schemas, paging, representative formatted identifiers and network errors with an authorized key. Cached models alone do not establish live behavior. |
| Representative classification values | Check sanitized habitat codes, active/inactive protected statuses/categories, programme identifiers/classes and null formats. Verify representative values and completeness across all three protected sources, including wilderness. Saved XSDs do not settle these questions. |
| Groundwater | Confirm representative identifiers/nulls and service-specific field meanings for VHS2022. The general groundwater PDF does not establish those semantics. |
| Ranta10 water sources | Verify live access, source subsets/authentication, complete paging, expanded bbox/polygon filtering, nearby outside-AOI river retention, update dates and request failures for all three products. Geographic completeness remains unverified. |
| Inventory coverage and dates | Check stand/grid identifiers, measurement/update semantics, null prevalence and product freshness. Establish geographic coverage; an empty response alone does not show that habitats or inventory are absent. |
| Growth meaning | Clarify current versus periodic growth, gross versus net growth, and denominator timing before adopting a stricter description of the derived indicator. |

Evidence locations and primary sources are in [data sources](architecture/data-sources.md) and [indicators](architecture/indicators.md); saved XML/XSD/model artifacts remain under [references](references/service-metadata/README.md).

## Analysis validation

### Large-area memory use

Measure peak memory on representative AOIs and establish practical guidance for
run size. The [current working set](architecture/overview.md#aoi-wide-working-set)
can exhaust memory and potentially crash QGIS, but no safe-area threshold or
reproduced out-of-memory crash has been established.

### Section 10 stand-wide promotion validation

Validate with intended planners whether a qualifying mapped habitat should make
the entire AOI-clipped parent stand sensitive or only the mapped habitat
footprint. For example, a 10 ha stand containing a 0.2 ha qualifying habitat
currently becomes 10 ha of sensitive forest in tiers containing Section 10.
Agree the rationale and spatial extent; correct implementation alone does not
establish suitability or planner acceptance.

Check that the explanation of `section10_stand_promoted = true` communicates
the stand-wide planning assumption without implying every piece overlaps the
habitat or all 10 ha are legally Section 10 habitat. Current behavior and field
meaning remain owned by [CL-01](specs/classification.md#cl-01-reporting-domain-and-geometry)
and the [output contract](architecture/output-schema.md#classification-reasons-and-context).

## Known implementation gaps

### Raw XSD metadata parser

[`describe_feature_type()`](../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py)
walks all XML elements into saved properties, including feature declarations
outside the selected type's property sequence. Provider-field readiness bypasses
this defect, but discovery provenance can contain misleading properties.

Completion requires parsing the selected feature type's actual property
definitions, with representative multi-type/imported-schema fixtures and
retained provider-field readiness behavior.

## Acceptance and distribution

### Interactive acceptance

Complete desktop, Finnish/English, Excel, browser and offline-help checks using
the [personal manual checklist](testing/manual-acceptance.md). Include Water-group
ordering, symbols and scale restoration; wizard/Processing parity; reopened
output presentation; and retained snapshot-group behavior. The checklist's
[open-question mapping](testing/manual-acceptance.md#use-the-checklist-with-open-questions)
connects the relevant cases to investigation topics.

### Release and distribution verification

- Optional merge blocking needs administrator activation of the checked-in
  ruleset. See [required merge checks](architecture/development.md#required-merge-checks).
- Compatibility with releases beyond the QGIS 3.44.0 and 4.2.3 verification
  baselines remains unverified, including intervening 4.0/4.2 releases admitted
  by the continuous metadata range. Repeat source and packaged checks for each
  additional target. Finnish/English desktop acceptance on both baselines
  remains separate from offscreen automated coverage.
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](architecture/distribution.md).
