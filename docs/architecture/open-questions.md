# Remaining verification and deferred work

These are outstanding evidence gaps, acceptance checks and deferred choices.
This register owns current outstanding status and dated evidence; procedures
belong to [development](development.md), and current behavior belongs to
[specs](../specs/README.md). Adopted choices are indexed in the
[ADRs](README.md#architecture-decision-records).

## Automated regression verification

On 27 October 2026, plugin version 1.0.0 was verified on Windows with QGIS
4.2.3 (Python 3.12.15). The expanded suite adds 21 test methods across the eight
reviewed areas; parameterized cases cover both Finnish and English where
presentation is involved. [Test seams and procedures](development.md#regression-seams).

| Check | Outcome |
| --- | --- |
| Ordinary Python unit/resource/package suite | 36 passed against the checkout and the extracted ZIP, using Python without the QGIS launcher. |
| QGIS integration/offscreen suite | 80 passed against the checkout and the rebuilt, extracted ZIP, including load/Processing/unload and local WFS 2.0 paging. |
| Development tooling | 15 passed with Git on PATH. |
| Pylint | Full `qgis_plugin scripts` check passed. |
| Packaging and documentation | Current-version ZIP built; all 35 packaged Python files matched source; local documentation links/anchors and bilingual packaged manuals passed checks. |

Regressions exposed and now cover selected-source snapshot loss and repeated
provider reads, source-ID leakage across split pieces, Windows file handles
preventing style-failure cleanup, active-task callbacks after unload, and
GeoPackage readers disrupted by applying filters after opening class views.
Views now open with filters in their initial provider URI; tests verify exact
row counts and feature iteration rather than only layer validity.

These checks use generated local fixtures and do not establish live-provider
completeness, hosted QGIS CI, desktop/browser/Excel acceptance or compatibility
with newer QGIS releases. The outstanding interactive and provider checks below
remain open.

## Provider evidence

| Item | Current limit and next evidence needed |
| --- | --- |
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

As of the 26 October 2026 documentation reconciliation, desktop, browser and
network-disconnected acceptance remains pending. Automated/headless checks do
not close these items. Use the procedures below and record build/runtime,
locale, date and outcome when checking them:

On 27 October 2026, the component naming and prefix cleanup passed lint, 15 tooling
tests, and 33 pure plus 62 offscreen QGIS 4.2.3 tests against source and the extracted
plugin ZIP, including Finnish/English workflow, help and lifecycle checks.
Preferred/legacy test-root configuration and persisted project-property keys were
also checked. These checks leave the interactive acceptance items below pending.

| Pending check | Procedure |
| --- | --- |
| Wizard docked/floating layout, resize spacing, toolbar icon sizing, setup and reload/unload | [Package and wizard checks](development.md#check-packaging-separately) |
| Grid placement/scales, repeated setup/language refresh, cancellation and localized failures | [Grid GUI acceptance](development.md#grid-indicator-manual-gui-acceptance) |
| Field order/labels/forms, partial coverage, source dates and output inspection in QGIS and Microsoft Excel | [Result fields](development.md#result-field-organization-checks) and [grid GUI acceptance](development.md#grid-indicator-manual-gui-acceptance) |
| Finnish/English and fallback, Help/About with dock closed, offline links/legal texts and browser failure recovery | [Help and credits verification](development.md#help-and-credits-verification) |

### Release and distribution verification

- CI quality checks (27 October 2026): the workflow includes Pylint
  and offscreen QGIS 4.2.3 integration against source and the built ZIP, with
  release publication depending on both build and quality jobs. The
  [first hosted run](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/actions/runs/40484712894)
  passed the build job, official MSI installation, runtime verification,
  development dependency installation and Pylint. Source integration stopped
  with 36 failures and one downstream error because the shared fixture assumed
  its first unrestricted feature read was empty; hosted QGIS returned records.
  Fixture priming now opens and closes a zero-result iterator, with a regression
  reproducing the populated-read failure and checking successful output values.
  Local source verification passed Pylint, 36 pure tests and 81 integration
  tests; both suites also passed against the built and extracted 1.0.0 ZIP.
  Hosted artifact download and packaged integration were skipped, and
  release publication was correctly skipped after the source failure. A hosted
  rerun must verify the fix and complete those remaining steps; interactive
  acceptance remains separate.
  Optional merge blocking also requires administrator activation of the
  checked-in ruleset; it is independent of CI execution and release gating. See
  [required merge checks](development.md#required-merge-checks).
- Automatic GitHub releases (26 October 2026): the build/release workflow is implemented; its first hosted execution, token/tag policy and downloadable asset still require verification after pushing it to main. Local tooling/package checks, upload-recovery simulation and QGIS 4.2.3 suites against source and the extracted release ZIP passed; they do not establish hosted publication or interactive acceptance. See the [release contract](distribution.md#github-builds-and-releases).
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](distribution.md).
