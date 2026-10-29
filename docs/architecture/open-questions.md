# Remaining verification and deferred work

These are outstanding evidence gaps, acceptance checks and deferred choices.
This register owns current outstanding status and dated evidence; procedures
belong to [development](development.md), and current behavior belongs to
[specs](../specs/README.md). Adopted choices are indexed in the
[ADRs](README.md#architecture-decision-records).

## Automated regression verification

On 29 October 2026, shorter loopback fixture shutdown polling passed all 25
tooling tests, full Pylint, and 37 unit/resource plus 102 QGIS 4.2.3 tests against
both source and the extracted current-version ZIP. On the same Windows/Python
3.12 runtime, source integration including startup fell from 80.4s to 62.7s;
packaged integration fell from 81.7s to 63.4s. Ten real WFS request/shutdown
cycles fell from 5.150s to 0.357s. These are local comparisons, not hosted timing
guarantees. Slowest-test reporting is enabled on Python 3.12+.
The new CI MSI cache passed local cache-hit, cache-miss and corrupt-file checks;
hosted cache restoration and net performance savings still require a run of the
updated workflow. Planner behavior and interactive acceptance are unchanged.

On 29 October 2026, removal of backward-compatibility paths passed 25 tooling
tests, full Pylint, and 37 unit/resource plus 102 QGIS 4.2.3 integration/offscreen
tests against both source and the extracted current-version ZIP. Checks include
Finnish/English workflows, Processing, help, project setup and plugin lifecycle.
Summaries now require current coverage records; retired-layer migration,
old test-root aliases and obsolete language-setting test fixtures are removed.
The current development formats are the supported contract under
[WF-01](../specs/workflow.md#wf-01-installation-and-runtime). Interactive desktop
and live-provider acceptance remain pending below.

On 28 October 2026, the shared isolated QGIS bootstrap and local check runner
passed 103 integration/offscreen tests and 36 unit/resource tests against both
source and the extracted current-version ZIP. All 25 tooling tests passed;
full Pylint and the final changed-runner lint checks passed. Direct unittest
environment checks also passed. Checks cover settings/profile/cache isolation,
SQLite access, failed prerequisites, runtime routing, relative launcher paths,
complete logs and child-environment cleanup. Planner behavior is unchanged;
existing provider and interactive acceptance checks remain open below.

On 28 October 2026, property identifiers were restricted to 1:10,000 or closer,
with boundaries retaining their inclusive 1:25,000 limit. Six source parcel
checks passed on QGIS 4.2.3, covering both limits, repeated Finnish/English setup
and saved-project persistence. The rebuilt/extracted 1.0.0 ZIP passed 19 targeted
parcel, bilingual lifecycle and Processing checks and 36 unit/resource/package
checks. Pylint passed for the changed implementation/test files. Both manuals
reflect the separate limits; desktop visual acceptance remains pending.

On 28 October 2026, property identifier labels changed to 20-point red text
with a white 2 mm buffer (rounded joins, full opacity, no interior fill).
Six source parcel checks passed on QGIS 4.2.3. The rebuilt/extracted 1.0.0 ZIP
passed 21 targeted parcel, bilingual lifecycle and Processing help checks,
plus 36 unit/resource/package checks. Parcel checks verify both languages,
repeated setup and saved-project persistence of label size and buffer settings.
Packaged styling matches source and both manuals describe it. Desktop visual
acceptance remains pending below.

On 28 October 2026, MML Ortokuva and Maastokartta basemaps were added using
ETRS-TM35FIN and the saved MML key. QGIS 4.2.3 source verification passed the
98-test integration suite, followed by all four basemap checks after adding
key-change/recreation coverage. The final rebuilt/extracted 1.0.0 ZIP passed
all 99 integration/offscreen checks and 36 unit/resource checks; the source
36-test unit/resource suite also passed. All 17 tooling checks and full
`qgis_plugin scripts` Pylint passed. Checks confirmed 255 maintained local
Markdown targets (manifest-listed downloads may be uncached) and parity for
all 35 packaged Python files, both manuals and notices. Tests cover national-grid
rendering, credentials on capabilities/tiles, initial stack/visibility, both
languages, retained identities/check states, key replacement, missing-layer
recreation, saved-project connections and service failure/retry. Authenticated
live MML access and desktop visual acceptance remain pending below.

On 28 October 2026, Kiinteistörajat and Kiinteistötunnukset visibility changed
to 1:25,000 or closer. Six source parcel checks passed on QGIS 4.2.3, covering
the inclusive boundary, hidden farther-out scales, restoration during repeated
Finnish/English setup and saved-project persistence for both layers. The
rebuilt/extracted 1.0.0 ZIP passed 19 targeted checks covering parcels, bilingual
plugin lifecycle and Processing, plus all 36 unit/resource/package checks.
Both manuals reflect the new limit. Desktop visual acceptance remains pending.

On 28 October 2026, the managed parcel polygon border changed from 0.3 mm to
1 mm. Six source parcel checks passed on QGIS 4.2.3, covering Finnish/English
setup, restoration after user style changes and saved-project persistence.
The rebuilt/extracted 1.0.0 ZIP passed all 98 integration/offscreen checks,
including bilingual lifecycle and Processing, and 36 unit/resource checks;
the same 36 unit/resource checks passed against source. Pylint passed for the
changed implementation/test files, and packaged styling matches source.
Both manuals describe the width. Desktop visual acceptance remains pending.

On 28 October 2026, managed WFS initialization was changed to skip startup
sample-feature requests, explicitly request WFS 2.0 metadata and use bounded
1,000-feature pages without a total cap. Existing connections are upgraded on
repeated setup. QGIS 4.2.3 checks cover zero feature/count requests during
creation, reconnect, reopen and worker reconstruction; preserved layer IDs,
filters and visibility; first/cached map rendering with view bounds; and complete
1,001-record retrieval with AOI bounds. All 95 integration/offscreen and 36
unit/resource tests passed against source and the extracted 1.0.0 ZIP; full
Pylint passed. All 35 packaged Python files match source, both manuals include
the updated guidance, 190 local links in affected Markdown documents exist and
whitespace checks passed.

A separate live eight-WFS-source check took 9.4 seconds, compared with 37.5
seconds in the earlier check. These runs exclude MML, OSM and desktop rendering
and do not control for changing network conditions. They do not establish a
guaranteed speedup or reproduce the original full minute-long desktop stall.
Metadata waits and interactive acceptance remain open below.

On 28 October 2026, Hila/grid setup styling changed to a solid dark green
(`#006400`) 0.25 mm outline with no fill. QGIS 4.2.3 checks cover initial setup,
restoration after style changes during repeated Finnish/English setup, and
saved-project persistence. All 91 integration/offscreen and 36 unit/resource
tests passed against source and the extracted 1.0.0 ZIP; full Pylint passed.
Both manuals describe the symbol. Desktop visual acceptance remains pending.

On 28 October 2026, stand and habitat rendering was restricted to 1:7,763 or
closer. QGIS 4.2.3 local fixture checks cover the inclusive boundary, hidden
farther-out scales, restoration of changed limits during repeated Finnish/English
setup, recreation of missing layers and saved-project persistence. Source
verification passed 91 integration/offscreen tests, 36 unit/resource tests and
full Pylint. Both test suites also passed against the rebuilt/extracted 1.0.0
ZIP, which contains the changed settings and both updated manuals. Interactive
map acceptance remains pending below.

On 28 October 2026, an MML credential-dialog report exposed another fixture gap:
QGIS's conformance request omitted the URL API key, while the fixture's 401 lacked
the Basic challenge that opens QGIS's credential dialog. MML connections now use
the saved key as username with an empty password. The regression uses a real
OAPIF provider and a Basic-challenging fixture and requires zero rejected
discovery requests for both collections/languages. Connection persistence,
feature reads and raw/escaped/Basic credential redaction are also checked.

The authentication correction passed 91 integration/offscreen tests and 36
unit/resource tests against source and the rebuilt extracted 1.0.0 ZIP on
Windows/QGIS 4.2.3. Full Pylint passed; all 35 packaged Python files match source,
all 280 checked local Markdown targets exist, and whitespace checks pass. The
local Basic-challenge test establishes credential propagation; a real MML key
and desktop verification remain pending in the provider/interactive sections.

On 28 October 2026, a desktop report exposed a gap in the reference-presentation
checks below: they inspected reordered layers before queued Qt events ran. The
minimal regression reproduced habitat-layer deletion after event processing.
Tree moves now insert the replacement node before removing the original;
disabling the registry bridge alone does not prevent queued deletion. New
regressions cover sorting, moves between groups, populated-group moves and
recreating missing habitat/programme/wilderness sources after setup. Both
languages are covered by full local WFS/OAPIF setup checks. Desktop/live-provider
acceptance remains separate from these deterministic checks.

The correction passed 90 integration/offscreen tests and 36 unit/resource tests
against source and the rebuilt, extracted 1.0.0 ZIP on Windows/QGIS 4.2.3. Full
`qgis_plugin scripts` Pylint passed; all 35 packaged Python files match source.
All 280 checked local Markdown link targets exist and whitespace checks pass.

The reference presentation update on 28 October 2026 passed the same QGIS 4.2.3
Windows checks: 87 integration/offscreen and 36 unit/resource tests against
source and the rebuilt, extracted 1.0.0 ZIP, plus 15 tooling tests and full
Pylint. Tests cover both authenticated MML collections, labels without point
symbols, polygon labeling disabled, inclusive 1:500,000 visibility, localized
subgroups/child order, retained layer identities/check states and consistent
protected-area styling. All 35 packaged Python files match source; 248 local
Markdown link targets exist and whitespace checks pass. Live MML and interactive
desktop acceptance remain pending below.

On 28 October 2026, the MML parcel addition passed on Windows with QGIS 4.2.3:
87 integration/offscreen tests and 36 unit/resource/package tests against both
the source checkout and the rebuilt, extracted 1.0.0 ZIP; 15 development-tooling
tests and full `qgis_plugin scripts` Pylint also passed. The five new parcel
tests cover mandatory-key setup, authenticated OAPIF access, first/cached red
labels, view bounds, failed-key recovery and project persistence. All 35
packaged Python files match source. Checks found no missing targets among 246
local Markdown links; bilingual packaged manuals and whitespace checks passed.
Live MML and interactive desktop acceptance remain open below.

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
| MML property context | Added 28 October 2026 using the provider's API-key technical description and cached 2020 parcel and identifier-point models. Local authenticated OAPIF fixtures verify both collection connections, view bounds, schema/geometry failures and red identifier rendering. A real MML key was not supplied: verify both current live collections/schemas, paging, representative formatted identifiers and network errors with an authorized key. |
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

For the MML basemap addition (28 October 2026), use a valid saved MML API key
and repeat setup in Finnish and English. Check Ortokuva, Maastokartta and
OpenStreetMap order, only Maastokartta initially visible (also in OSM-only
projects), switching maps, retained choices after repeated setup and saving/
reopening, and no additional credential dialog while panning/zooming. A live
authenticated capabilities/tile check remains pending: the unauthenticated
capabilities endpoint returned HTTP 401. Local authenticated WMTS rendering and
persistence tests establish adapter behavior, not live-provider availability.

For the parcel border change (28 October 2026), inspect the red 1 mm outlines
in Finnish and English after repeated setup and saved-project reopen, using
the rebuilt ZIP. Offscreen symbol checks do not establish desktop visual clarity.

For the property identifier label change (28 October 2026), inspect the red
20-point text and white 2 mm buffer in Finnish and English after repeated setup
and saved-project reopen, using the rebuilt ZIP. Desktop visual acceptance
remains pending.

For the WFS startup optimization (28 October 2026), repeat setup in Finnish and
English on an existing project and a fresh ZIP installation. Capture requests
with analysis layers outside their display scales: managed WFS construction
must not issue GetFeature/count requests. Zoom into stands/habitats/grid and
confirm bounded drawing, then run analysis and confirm complete paged outputs.
Check layer identities, filters and visibility choices after reconnect/reopen.
Setup remains synchronous; slow metadata can still delay it. The original
minute-long desktop stall has not been reproduced end to end.

For the Hila style change (28 October 2026), inspect dark green borders with no
fill in Finnish and English at 1:200 and 1:300, after repeated setup and project
reopen. Confirm the existing hidden state at 1:500. Automated symbol and
persistence checks do not establish desktop visual acceptance.

For the stand/habitat scale change on 28 October 2026, reload the plugin and
repeat setup in Finnish and English. Check both layers render at 1:7,763 and
closer, disappear farther out, and retain that behavior after saving/reopening
the project. Automated scale-range checks do not establish desktop map acceptance.

For the MML property layers updated on 28 October 2026, repeat setup in Finnish and
English, cancel/omit the key and verify no project changes, then supply a valid
key. Confirm there is no additional credential dialog for a valid key, including
during discovery/conformance and after reopening a saved project. Existing
connections are refreshed by repeating setup after installing the correction.
Inspect the Property boundaries group's red polygon outlines without labels
at 1:25,000 and separate formatted red identifier labels without point symbols at 1:10,000
and closer, hidden farther out, while panning/zooming and after saving/reopening
the project. Check the four reference subgroups/child order and consistent rose
protected-area styling with groundwater's translucent treatment. Check rejected-key
replacement and that existing analysis inputs remain usable separately from
this map context. Deterministic offscreen checks do not close this desktop or
live-provider acceptance.

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
  release publication was correctly skipped after the source failure. A
  [successful hosted run on 29 October 2026](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/actions/runs/40818055010)
  subsequently passed source and packaged integration, artifact transfer and
  release publication. The installer-cache changes above still need their own
  hosted verification; interactive acceptance remains separate.
  Optional merge blocking also requires administrator activation of the
  checked-in ruleset; it is independent of CI execution and release gating. See
  [required merge checks](development.md#required-merge-checks).
- Automatic GitHub releases (implemented 26 October 2026; hosted evidence checked
  29 October 2026): the successful run above completed version preparation,
  release ZIP checks, tagging and publication. Earlier local tooling/package
  checks, upload-recovery simulation and QGIS 4.2.3 source/extracted-ZIP checks
  passed. Installing a downloaded release and interactive desktop acceptance
  remain separate checks. See the
  [release contract](distribution.md#github-builds-and-releases).
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](distribution.md).
