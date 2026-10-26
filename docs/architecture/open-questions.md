# Remaining verification and deferred work

These are outstanding evidence gaps, acceptance checks and deferred choices.
Adopted technical decisions are indexed in the [ADRs](README.md#architecture-decision-records).

## Provider evidence

| Item | Current limit and next evidence needed |
| --- | --- |
| Representative classification values | Saved XSDs are not feature samples. Check sanitized habitat codes, active/inactive protected statuses/categories, programme identifiers/classes and null formats across all three protected sources. Current code rejects unrecognized values; a policy accepting inactive records would require an explicit change. |
| Groundwater | Capabilities and the exact VHS2022 XSD were downloaded on 26 October 2026; regenerate them with the reference downloader. Check representative identifiers/nulls and service-specific field meanings; the general groundwater PDF alone does not establish those semantics. |
| Wilderness evidence | Its dedicated XSD and protected-sites capabilities were downloaded on 26 October 2026. Representative statuses/categories and completeness remain unverified. |
| Inventory coverage and dates | Check stand/grid identifiers, measurement/update semantics, null prevalence and selected-product freshness. Successful empty retrieval permits a no-hit in the current application but does not establish authoritative geographic coverage or absence of unmapped habitats. |
| Raw XSD metadata parser | `describe_feature_type()` still walks global XML elements into saved properties. Provider-field readiness bypasses this defect; provenance metadata may still be misleading. Correcting that parser is separate work. |
| Growth meaning | Units support relative annual volume growth, but current/periodic, gross/net and denominator timing remain unspecified. Keep the transparent derived indicator until provider semantics support stricter wording. |

Evidence locations and primary sources are in [data sources](data-sources.md) and [indicators](indicators.md); saved XML/XSD/model artifacts remain under [references](../references/README.md).

## Scope and source alternatives

Local GeoPackage/raster adapters, open-mire/whole-AOI reporting, potential protection screening, urban-forest/MY interpretation, peat sensitivity and water buffers remain deferred. Candidate sources and unanswered thresholds/denominators are recorded in [deferred sources](deferred-sources.md).

No reviewed repository evidence establishes Savonia acceptance of the prototype's tier rules, interpretations or deliverables. Tender requirements and implementation choices have different authority. [Project context](../project-context.md).

## Acceptance and distribution

- Interactive desktop/browser/network-disconnected acceptance remains pending: bilingual wizard docked/floating behavior, language refresh/fallback, Help/About with the dock closed, local manual links, notices, cancellation, output inspection and reload/unload. Headless/offscreen checks do not close those items. The [development guide](development.md#help-and-credits-verification) provides the required checks.
- Arrange explicit map-visible OpenStreetMap attribution for the basemap and shared maps/screenshots; the reviewed setup and About credits do not establish that display. Separately review tile-client usage-policy behavior if preparing distribution.
- A full ownership and host/transitive licence-compatibility audit remains outstanding. Recheck inventory and dataset-specific terms when adding copied material, runtime bundles, custom data or a public distribution destination. [Distribution boundaries](distribution.md).
