# Remaining verification and deferred work

These are outstanding evidence gaps, acceptance checks and deferred choices.
This register owns current outstanding status and dated evidence; procedures
belong to [development](development.md), and current behavior belongs to
[specs](../specs/README.md). Adopted choices are indexed in the
[ADRs](README.md#architecture-decision-records).

## Automated regression verification

Latest recorded local evidence: 29 October 2026, Windows/QGIS 4.2.3, plugin
version 1.0.0. The complete check runner passed 25 tooling tests, 43 unit/resource
tests, Pylint and 118 integration/offscreen tests against source and the
extracted current-version ZIP. Packaged Python files and both manuals matched
the reviewed source.

The checks cover shared workflow and publication, metric coverage and unrounded
sawlog-value aggregation, selected-source capture, provider failures/paging,
worker ownership, repeated setup, bilingual presentation and plugin lifecycle.
Polygon-query checks cover backend predicates, holes/multipart AOIs, reduced
transfers with identical clipped evidence, all pages, existing subsets, changed
AOIs/cache reuse, source-CRS/axis handling, returned invalid-polygon repair and
the large-filter fallback.
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

| Item | Current limit and next evidence needed |
| --- | --- |
| Analysis polygon queries | Added 29 October 2026. A small live Metsäkeskus grid comparison through shared retrieval inspected 274 candidates instead of 484 and retained the same 210 clipped features with identical attributes/geometries. These single bounded reads are not a performance guarantee. Verify representative AOIs on all eight sources, provider handling of malformed polygons before local repair, and deployment-specific GET limits; large filters currently retain bbox retrieval. |
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

| Item | Current status and completion boundary |
| --- | --- |
| US-005 tier selector and full-layer presentation | Manual review on 26 October 2026 found these unimplemented. US-005 is partially implemented; existing map behavior is owned by [IO-06](../specs/indicators-and-outputs.md#io-06-map-review-and-run-retention). Implementing a dedicated selector/full-layer presentation is separate from visual acceptance of the existing filtered views. |
| Raw XSD metadata parser | `describe_feature_type()` still walks global XML elements into saved properties. Provider-field readiness bypasses this defect; provenance metadata may still be misleading. Correcting that parser is separate work. |

## Acceptance and distribution

### Interactive acceptance

As of 29 October 2026, Finnish/English desktop, browser, network-disconnected
help and Microsoft Excel acceptance remain pending. Automated/offscreen checks
do not close them. Record build/runtime, locale, date and outcome when executing
the linked procedures.

| Pending check | Acceptance boundary / procedure |
| --- | --- |
| Wizard lifecycle and input handling | Docked/floating layout, setup, reload/unload, remembered/cleared price and decimal-comma entry, readiness after selection/source/output changes, understandable completion warnings. [Package and wizard checks](development.md#check-packaging-separately). |
| Reference and basemap presentation | Repeated bilingual setup/language changes, layer grouping and scale visibility, retained choices/identities after save/reopen, readable map presentation. Use [WF-02](../specs/workflow.md#wf-02-project-setup), the manuals and [grid GUI acceptance](development.md#grid-indicator-manual-gui-acceptance). Visual acceptance of the 28 October changes remains open. |
| Live authenticated MML context | Both parcel collections and WMTS basemaps, valid/rejected/replaced keys, discovery and pan/zoom without extra credential prompts, persisted connections and service failures. Authenticated local fixtures passed; live access remains unverified. Unauthenticated WMTS capabilities returned HTTP 401 on 28 October. |
| WFS initialization and responsiveness | On fresh and existing projects, confirm setup avoids feature/count requests, map reads are view-bounded and analysis retrieves complete pages. Check reconnection preserves layer identity and user choices. Setup remains synchronous; the reported minute-long desktop stall has not been reproduced end to end. |
| Result and workbook interpretation | Inspect field labels/forms, nulls and coverage, source dates, tier/snapshot visibility and GeoPackage reopening. Verify €/m³ versus €, known zero versus unknown, and complete versus partial totals in QGIS and the four-sheet workbook in Microsoft Excel. [Result field checks](development.md#result-field-organization-checks). |
| Language and offline resources | Finnish/English and unsupported-language fallback, Help/About with dock closed, offline links/legal texts and browser failure recovery. [Help and credits verification](development.md#help-and-credits-verification). |
| Cancellation and failures | Required-source/geometry failures and cancellation leave actionable localized messages and no apparently complete partial output. [Grid GUI acceptance](development.md#grid-indicator-manual-gui-acceptance). |

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
