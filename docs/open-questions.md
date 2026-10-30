# Remaining verification and deferred work

This project-wide register tracks unresolved implementation gaps, provider
questions, acceptance checks and deferred choices. Automated procedures belong to
[development](architecture/development.md), interactive procedures to the
[manual acceptance guide](testing/manual-acceptance.md), and current behavior to
[specs](specs/README.md). Adopted choices are indexed in the
[ADRs](architecture/README.md#architecture-decision-records).

## Provider evidence

### Reference material integrity

`mml/wmts/get-capabilities.xml` is absent from the local cache. Its entry in the
[reference manifest](references/service-metadata/manifest.json) and link in the
[reference instructions](references/service-metadata/README.md#maanmittauslaitos)
identify a download destination, not bundled evidence. Populate it using the
documented `MML_API_KEY` and `--only mml/wmts/` options when an authorized key is
available. The missing authenticated material does not establish a plugin failure.
Cache integrity does not verify
current provider values or geographic completeness.

### Live values and service behavior

| Item | Current limit and next evidence needed |
| --- | --- |
| Analysis polygon queries | Verify representative AOIs on all eight sources, provider handling of malformed polygons before local repair, and deployment-specific GET limits; large filters currently retain bbox retrieval. Bounded sample comparisons do not establish completeness or a performance guarantee. |
| Setup responsiveness | Setup remains synchronous; the reported minute-long desktop stall has not been reproduced end to end. Use the manual checklist's MT-08 to investigate waits separately from map rendering. |
| MML property context | Cached parcel and identifier-point models do not establish current live schemas. Verify both live collections/schemas, paging, representative formatted identifiers and network errors with an authorized key. |
| Representative classification values | Saved XSDs are not feature samples. Check sanitized habitat codes, active/inactive protected statuses/categories, programme identifiers/classes and null formats across all three protected sources. Current code rejects unrecognized values; a policy accepting inactive records would require an explicit change. |
| Groundwater | The cache includes capabilities and the exact VHS2022 XSD. Check representative identifiers/nulls and service-specific field meanings; the general groundwater PDF alone does not establish those semantics. |
| Wilderness evidence | The cache includes its dedicated XSD and protected-sites capabilities. Representative statuses/categories and completeness remain unverified. |
| Inventory coverage and dates | Check stand/grid identifiers, measurement/update semantics, null prevalence and selected-product freshness. Successful empty retrieval permits a no-hit in the current application but does not establish authoritative geographic coverage or absence of unmapped habitats. |
| Growth meaning | Units support relative annual volume growth, but current/periodic, gross/net and denominator timing remain unspecified. Keep the transparent derived indicator until provider semantics support stricter wording. |

Evidence locations and primary sources are in [data sources](architecture/data-sources.md) and [indicators](architecture/indicators.md); saved XML/XSD/model artifacts remain under [references](references/service-metadata/README.md).

## Scope and source alternatives

Local GeoPackage/raster adapters, open-mire/whole-AOI reporting, potential protection screening, urban-forest/MY interpretation, peat sensitivity and water buffers remain deferred. Candidate sources and unanswered thresholds/denominators are recorded in [deferred sources](architecture/deferred-sources.md).

No reviewed repository evidence establishes Savonia acceptance of the prototype's tier rules, interpretations or deliverables. Tender requirements and implementation choices have different authority. [Project context](project-context.md).

### Section 10 stand-wide promotion validation

Planning-rule acceptance remains pending. Validate with
the intended planners whether a qualifying mapped Section 10 habitat overlap
should make the entire AOI-clipped parent stand sensitive, including result
pieces outside the mapped habitat, or whether sensitivity should follow only
the mapped habitat footprint. The current stand-wide assumption is owned by
[CL-01](specs/classification.md#cl-01-reporting-domain-and-geometry) and
[ADR-0004](architecture/adr/0004-stand-based-sensitivity-classification.md).

Use a concrete example: a 10 ha stand containing a 0.2 ha qualifying habitat
overlap currently becomes 10 ha of sensitive forest in every tier containing
Section 10. Check that planners understand and accept this extension as a
planning assumption; it does not establish that all 10 ha are legally a
Section 10 habitat. Also validate that the explanation of
`section10_stand_promoted = true` communicates the stand-wide rule, rather than
claiming that each result piece overlaps the mapped habitat. The
[field contract](architecture/output-schema.md#classification-reasons-and-context) owns its
stored meaning.

Agree the rationale and intended spatial extent. Automated tests of the
implemented rule do not establish its suitability or acceptance.
This note leaves current behavior unchanged; a different accepted extent
requires a specification change and reconsideration of ADR-0004.

## Known implementation gaps

### Raw XSD metadata parser

[`describe_feature_type()`](../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py)
walks all XML elements into saved properties, including feature declarations
outside the selected type's property sequence. Provider-field readiness bypasses
this defect, but discovery provenance can contain misleading properties.

Completion requires parsing the selected feature type's actual property
definitions, with representative multi-type/imported-schema fixtures and
retained provider-field readiness behavior. Cached XSD availability and passing
readiness tests do not establish that this parser is correct.

## Acceptance and distribution

### Interactive acceptance

Use the [personal manual checklist](testing/manual-acceptance.md) for desktop,
language, Excel, browser and offline-help checks. Its
[open-question mapping](testing/manual-acceptance.md#use-the-checklist-with-open-questions)
connects relevant checks to investigation topics.

Verification histories and individual test-completion records are not maintained
here. Keep substantive defects, provider questions and planning decisions in this
register.

### Release and distribution verification

- Optional merge blocking needs administrator activation of the checked-in
  ruleset. See [required merge checks](architecture/development.md#required-merge-checks).
- Compatibility with newer QGIS 4.x releases remains unverified; recorded
  runtime evidence covers QGIS 4.2.3. Repeat the source and packaged checks on
  each newer targeted release before recording compatibility.
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](architecture/distribution.md).
