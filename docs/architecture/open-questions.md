# Remaining verification and deferred work

These are outstanding evidence gaps, acceptance checks and deferred choices.
This register owns current outstanding status and dated evidence; procedures
belong to [development](development.md), and current behavior belongs to
[specs](../specs/README.md). Adopted choices are indexed in the
[ADRs](README.md#architecture-decision-records).

## Provider evidence

| Item | Current limit and next evidence needed |
| --- | --- |
| Representative classification values | Saved XSDs are not feature samples. Check sanitized habitat codes, active/inactive protected statuses/categories, programme identifiers/classes and null formats across all three protected sources. Current code rejects unrecognized values; a policy accepting inactive records would require an explicit change. |
| Groundwater | Capabilities and the exact VHS2022 XSD were downloaded on 26 October 2026; regenerate them with the reference downloader. Check representative identifiers/nulls and service-specific field meanings; the general groundwater PDF alone does not establish those semantics. |
| Wilderness evidence | Its dedicated XSD and protected-sites capabilities were downloaded on 26 October 2026. Representative statuses/categories and completeness remain unverified. |
| Inventory coverage and dates | Check stand/grid identifiers, measurement/update semantics, null prevalence and selected-product freshness. Successful empty retrieval permits a no-hit in the current application but does not establish authoritative geographic coverage or absence of unmapped habitats. |
| Growth meaning | Units support relative annual volume growth, but current/periodic, gross/net and denominator timing remain unspecified. Keep the transparent derived indicator until provider semantics support stricter wording. |

Evidence locations and primary sources are in [data sources](data-sources.md) and [indicators](indicators.md); saved XML/XSD/model artifacts remain under [references](../references/README.md).

## Scope and source alternatives

Local GeoPackage/raster adapters, open-mire/whole-AOI reporting, potential protection screening, urban-forest/MY interpretation, peat sensitivity and water buffers remain deferred. Candidate sources and unanswered thresholds/denominators are recorded in [deferred sources](deferred-sources.md).

No reviewed repository evidence establishes Savonia acceptance of the prototype's tier rules, interpretations or deliverables. Tender requirements and implementation choices have different authority. [Project context](../project-context.md).

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

| Pending check | Procedure |
| --- | --- |
| Wizard docked/floating layout, resize spacing, toolbar icon sizing, setup and reload/unload | [Package and wizard checks](development.md#check-packaging-separately) |
| Grid placement/scales, repeated setup/language refresh, cancellation and localized failures | [Grid GUI acceptance](development.md#grid-indicator-manual-gui-acceptance) |
| Field order/labels/forms, partial coverage, source dates and output inspection in QGIS and Microsoft Excel | [Result fields](development.md#result-field-organization-checks) and [grid GUI acceptance](development.md#grid-indicator-manual-gui-acceptance) |
| Finnish/English and fallback, Help/About with dock closed, offline links/legal texts and browser failure recovery | [Help and credits verification](development.md#help-and-credits-verification) |

### Release and distribution verification

- Automatic GitHub releases (26 October 2026): the build/release workflow is implemented; its first hosted execution, token/tag policy and downloadable asset still require verification after pushing it to main. Local tooling/package checks, upload-recovery simulation and QGIS 4.2.3 suites against source and the extracted release ZIP passed; they do not establish hosted publication or interactive acceptance. See the [release contract](distribution.md#github-builds-and-releases).
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](distribution.md).
