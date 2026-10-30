# Remaining verification and deferred work

These are outstanding evidence gaps, acceptance checks and deferred choices.
This register owns current outstanding status and dated evidence. Automated
procedures belong to [development](development.md), interactive procedures to the
[manual acceptance guide](../testing/manual-acceptance.md), and current behavior to
[specs](../specs/README.md). Adopted choices are indexed in the
[ADRs](README.md#architecture-decision-records).

## Automated regression verification

Latest recorded local evidence: 29 October 2026, Windows/QGIS 4.2.3, plugin
version 1.0.0. The complete check runner passed 25 tooling tests, 43 unit/resource
tests, Pylint and 126 integration/offscreen tests against source and the
extracted current-version ZIP. Packaged Python files and both manuals matched
the reviewed source.

The checks cover shared workflow and publication, metric coverage and unrounded
sawlog-value aggregation, selected-source capture, provider failures/paging,
worker ownership, repeated setup, bilingual presentation and plugin lifecycle.
Polygon-query checks cover backend predicates, holes/multipart AOIs, reduced
transfers with identical clipped evidence, all pages, existing subsets, changed
AOIs/cache reuse, source-CRS/axis handling, returned invalid-polygon repair and
the large-filter fallback.
Result-fragment checks cover standalone, multipart and split polygons, the
inclusive 0.01 m² reporting threshold, retained small real polygons, bilingual
feedback, metadata, unchanged snapshots and workbook counts. A geometry replay
of the supplied export removed all 15 zero-displayed rows while retaining the
21 other original row identities; this is not a live-provider rerun.
Use the [development guide](development.md#regression-seams) for test boundaries
and commands; detailed execution/debugging history belongs in local working
verification records.

A live eight-WFS-source setup check on 28 October 2026 verified the revised
initialization path, but excluded MML, OSM and desktop rendering. It does not
establish a guaranteed setup time or resolve slow metadata waits.

These fixtures and bounded observations do not establish live-provider
completeness, interactive desktop/browser/Excel acceptance or compatibility
with newer QGIS releases. Hosted evidence is recorded separately below.

## Provider evidence

### Reference material integrity

Offline review on 30 October 2026 checked all 25 entries in the versioned
[reference manifest](../references/service-metadata/manifest.json). The 24
present files passed the downloader's format validation and matched the byte
counts and SHA-256 values in local retrieval metadata. The WFS/model references
were captured on 26 October; the two MML parcel models on 28 October. No
references were refreshed during this review.

`mml/wmts/get-capabilities.xml` is absent. Its link in the
[reference instructions](../references/service-metadata/README.md#maanmittauslaitos)
identifies a download destination, not bundled evidence. Populate it using the
documented `MML_API_KEY` and `--only mml/wmts/` options when an authorized key is
available, then record the actual retrieval outcome. The missing authenticated
material does not invalidate the other 24 references or establish a plugin
failure. Integrity checks establish the identity of cached artifacts, not their
current accuracy, feature values or geographic completeness.

### Live values and service behavior

| Item | Current limit and next evidence needed |
| --- | --- |
| Analysis polygon queries | Added 29 October 2026. A small live Metsäkeskus grid comparison through shared retrieval inspected 274 candidates instead of 484 and retained the same 210 clipped features with identical attributes/geometries. These single bounded reads are not a performance guarantee. Verify representative AOIs on all eight sources, provider handling of malformed polygons before local repair, and deployment-specific GET limits; large filters currently retain bbox retrieval. |
| Setup responsiveness | Setup remains synchronous. A live eight-source WFS setup check passed on 28 October 2026, but the reported minute-long desktop stall has not been reproduced end to end. Use the manual checklist's MT-08 to investigate waits separately from map rendering. |
| MML property context | Added 28 October 2026 using the provider's API-key technical description and cached 2020 parcel and identifier-point models. Local authenticated OAPIF fixtures verify connection, retrieval and schema/geometry handling. A real MML key was not supplied: verify both current live collections/schemas, paging, representative formatted identifiers and network errors with an authorized key. |
| Representative classification values | Saved XSDs are not feature samples. Check sanitized habitat codes, active/inactive protected statuses/categories, programme identifiers/classes and null formats across all three protected sources. Current code rejects unrecognized values; a policy accepting inactive records would require an explicit change. |
| Groundwater | Capabilities and the exact VHS2022 XSD were downloaded on 26 October 2026; regenerate them with the reference downloader. Check representative identifiers/nulls and service-specific field meanings; the general groundwater PDF alone does not establish those semantics. |
| Wilderness evidence | Its dedicated XSD and protected-sites capabilities were downloaded on 26 October 2026. Representative statuses/categories and completeness remain unverified. |
| Inventory coverage and dates | Check stand/grid identifiers, measurement/update semantics, null prevalence and selected-product freshness. Successful empty retrieval permits a no-hit in the current application but does not establish authoritative geographic coverage or absence of unmapped habitats. |
| Growth meaning | Units support relative annual volume growth, but current/periodic, gross/net and denominator timing remain unspecified. Keep the transparent derived indicator until provider semantics support stricter wording. |

Evidence locations and primary sources are in [data sources](data-sources.md) and [indicators](indicators.md); saved XML/XSD/model artifacts remain under [references](../references/service-metadata/README.md).

## Scope and source alternatives

Local GeoPackage/raster adapters, open-mire/whole-AOI reporting, potential protection screening, urban-forest/MY interpretation, peat sensitivity and water buffers remain deferred. Candidate sources and unanswered thresholds/denominators are recorded in [deferred sources](deferred-sources.md).

No reviewed repository evidence establishes Savonia acceptance of the prototype's tier rules, interpretations or deliverables. Tender requirements and implementation choices have different authority. [Project context](../project-context.md).

### Section 10 stand-wide promotion validation

Added 27 October 2026; planning-rule acceptance remains pending. Validate with
the intended planners whether a qualifying mapped Section 10 habitat overlap
should make the entire AOI-clipped parent stand sensitive, including result
pieces outside the mapped habitat, or whether sensitivity should follow only
the mapped habitat footprint. The current stand-wide assumption is owned by
[CL-01](../specs/classification.md#cl-01-reporting-domain-and-geometry) and
[ADR-0004](adr/0004-stand-based-sensitivity-classification.md).

Use a concrete example: a 10 ha stand containing a 0.2 ha qualifying habitat
overlap currently becomes 10 ha of sensitive forest in every tier containing
Section 10. Check that planners understand and accept this extension as a
planning assumption; it does not establish that all 10 ha are legally a
Section 10 habitat. Also validate that the explanation of
`section10_stand_promoted = true` communicates the stand-wide rule, rather than
claiming that each result piece overlaps the mapped habitat. The
[field contract](output-schema.md#classification-reasons-and-context) owns its
stored meaning.

Record the reviewer, date, rationale and accepted spatial extent. Automated
tests of the implemented rule do not establish its suitability or acceptance.
This note leaves current behavior unchanged; a different accepted extent
requires a specification change and reconsideration of ADR-0004.

## Known implementation gaps

### Raw XSD metadata parser

Still open after source inspection on 30 October 2026:
[`describe_feature_type()`](../../qgis_plugin/savonia_responsible_forest_planning_tool/adapters/sources.py)
walks all XML elements into saved properties, including feature declarations
outside the selected type's property sequence. Provider-field readiness bypasses
this defect, but discovery provenance can contain misleading properties.

Completion requires parsing the selected feature type's actual property
definitions, with representative multi-type/imported-schema fixtures and
retained provider-field readiness behavior. Cached XSD availability and passing
readiness tests do not establish that this parser is correct.

## Resolved specification scope

### US-005 map review

On 30 October 2026, the project owner confirmed that the existing filtered views
and layer-tree tier-group controls satisfy the intended map-review interaction.
US-005 is implemented under [IO-06](../specs/indicators-and-outputs.md#io-06-map-review-and-run-retention).
The earlier dedicated-selector and automatic full-layer requirements are retired;
they are no longer implementation follow-up. Bilingual/package visual
[checks](#interactive-acceptance) remain part of personal testing; this scope
confirmation does not establish Savonia acceptance.

## Acceptance and distribution

### Interactive acceptance

Use the [personal manual checklist](../testing/manual-acceptance.md) for desktop,
language, Excel, browser and offline-help checks. Its
[open-question mapping](../testing/manual-acceptance.md#use-the-checklist-with-open-questions)
connects relevant checks to investigation topics.

As requested by the sole maintainer on 30 October 2026, individual manual-test
results and completion records are not tracked here. Keep substantive defects,
provider questions and planning decisions in their sections above; the checklist
remains the reusable guidance for manual testing. Removing test paperwork adds
no runtime or provider verification evidence.

### Release and distribution verification

- Hosted CI and release evidence: the [29 October 2026 run](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/actions/runs/40818055010)
  passed source and packaged QGIS integration, artifact transfer and release
  publication. It supersedes the failed source-integration evidence from
  [27 October](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/actions/runs/40484712894).
  Installer-cache changes passed local hit/miss/corruption checks on 29 October
  but still need hosted verification and timing. Optional merge blocking needs
  administrator activation of the checked-in ruleset, separately from CI and
  release gating. See [required merge checks](development.md#required-merge-checks).
- Automatic release preparation, tagging and publication have hosted evidence;
  installing a downloaded release ZIP and interactive desktop acceptance remain
  separate. See the [release contract](distribution.md#github-builds-and-releases).
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](distribution.md).
