# Workflow specification

Scope and status follow the [specification index](README.md). These requirements describe user-observable behavior; [architecture](../architecture/overview.md), [source contracts](../architecture/source-layer-requirements.md) and [development](../architecture/development.md) own implementation details.

## WF-01 Installation and runtime

- Distribute an experimental QGIS plugin with its declared compatibility visible before installation. The current target is QGIS 4.2.3 and newer 4.x releases; 4.2.3 is the verification baseline. Later releases require their own runtime checks. Packaged metadata owns the precise installation range.
- The installable ZIP includes both manuals, licence texts, notices and inventory, and supports plugin load, Processing registration and unload without duplicate actions or providers on reload.
- Analysis uses online configured WFS services and writes results locally. Reading packaged help and notices works offline.
- Building an installation ZIP preserves the current version by default;
  pushing to `main` triggers a tested GitHub Release with a downloadable plugin
  ZIP. Each new release increments the minor version, preserves the major and
  resets the patch to zero. Retries reuse the release for that source commit.
  Pull requests build/test without publishing. Failed builds or tests prevent
  publication; a release becomes public only after its ZIP is attached.
  Packaging commands and
  verification are documented in the [development guide](../architecture/development.md#check-packaging-separately).

## WF-02 Project setup

- The main plugin toolbar opens or raises the wizard. Opening it does not automatically run source setup.
- **Set up forest planning layers** is first in the wizard toolbar, followed by a separator and redock, Help and About. Setup remains available when the wizard floats and through the plugin menu with the wizard closed. Both entry points perform the same setup.
- Setup creates or reuses localized Results, References and Basemaps groups and OpenStreetMap context. Results draw above References, which draw above Basemaps; custom drawing order must not defeat this arrangement.
- Repeated setup reuses managed groups/layers without duplicates and relabels them when the QGIS language changes. Stable source identity survives display-name changes.
- References contain all eight required layers: Metsäkeskus stands, habitats and grid cells; SYKE state-owned protected areas, private-land protected areas, wilderness areas, nature conservation programme areas and groundwater areas.
- The grid stays at the bottom of References without changing other references' relative order. It renders at 1:300 or closer. Stands and habitats are hidden farther out than 1:500,000. These visibility settings affect map display, never analysis availability or calculations.
- Setup permits a blank SYKE application identifier and allows it to be supplied later. When supplied, it is retained in settings and service URLs, including URLs saved with a QGIS project. The user instructions explain the provider's identifier requirements and the consequences for sharing project URLs. Provider terms and technical configuration remain in [data sources](../architecture/data-sources.md).

## WF-03 Source readiness and retrieval

- Only WFS 2.0 sources are supported through the wizard and Processing. Legacy WFS 1.x endpoints are outside the planned scope; there is no protocol downgrade fallback. [ADR-0010](../architecture/adr/0010-wfs-2-only.md) records the decision and rationale.
- The wizard reads configured sources from References by managed identity; it does not ask users to discover or select source layers. Processing accepts explicit source inputs for repeatable and batch use under the same source policy.
- Setup discovers/verifies configured feature types and schema information. Before analysis, all eight sources must be valid polygon layers with usable coordinate systems, the expected provider/source identity and required provider fields. Report all source-readiness failures together where preflight can collect them.
- Current provider fields determine readiness and interpretation. Match accepted names case-insensitively, ignore extra fields/order and apply the documented alias priority independently for each source. Saved discovery schemas are provenance and cannot override usable provider fields. Exact aliases, fields and value sets belong to [source-layer requirements](../architecture/source-layer-requirements.md).
- Retrieve AOI-bounded evidence and clip it exactly. Reuse the retrieved grid for all result pieces rather than requesting each piece separately or downloading the national grid.
- Retain original source attributes, identifiers, dates, source identity and clipped snapshots. Distinguish measurement dates from database update dates.
- A successful empty response is different from a request failure. Counts and observed mapped overlaps do not prove complete inventory coverage or absence of an unmapped habitat.

## WF-04 Analysis area and destination

- Support drawing one polygon, choosing polygon features from a project layer, and using the current map extent. Capture the extent and its coordinate system when the run starts.
- Layer selection has an explicit selected-features-only choice. Preserve input features and layers. When the AOI layer is also a configured source and selected-only mode applies, use the captured selected features for that source while retaining the same clipping and provenance behavior.
- Dissolve overlapping AOI features so overlapping boundary inputs are counted once. Validate the area, coordinate transformations, output basename and writable destination before expensive work or publication.
- Use EPSG:3067 spatial outputs and planar hectares. The reporting domain is the analyzed forest within the AOI, as defined in [CL-01](classification.md#cl-01-reporting-domain-and-geometry).
- The wizard remembers the output folder and generates a basename beginning `savonia_responsible_forest_inputs_`. Processing permits an explicit basename. Reject existing paired output names instead of overwriting user files.

## WF-05 Wizard interaction

- Open a persistent nonmodal dock beside the map; it opens on the right, allows left/right docking and floating, and redocks to the right.
- The current wizard has one analysis page: area mode and status, output folder and Run. Hiding/closing and reopening the dock preserves its current choices.
- Keep map interaction available for drawing and selection. Setup, redock, Help and About work in docked and floating modes.
- Run the same analysis behavior as Processing, report meaningful progress, provide cancellation and show both output paths on success. On success, add the run's results and snapshots to Results as specified in [IO-06](indicators-and-outputs.md#io-06-map-review-and-run-retention).
- Show a concise localized error identifying the failed phase/source and a corrective next step where possible. Detailed diagnostics retain the run context.

## WF-06 Processing and repeatability

- Expose the same AOI, required source, classification, indicator and publication behavior through the Processing Toolbox, batch and model workflows.
- Explicit inputs include the polygon AOI, selected-only option, all eight source layers including grid cells, output folder and basename. The technical parameter IDs and execution interface belong to architecture and the installed Processing help.
- Equivalent inputs produce equivalent classes, indicators, coverage and artifacts through both entry points. Return usable output paths and actionable failures to callers.
- Keep input data intact. One entry point must not silently apply a different tier rule, missing-value policy or indicator fallback.

## WF-07 Failure, cancellation and observability

| Condition | Required result |
| --- | --- |
| Invalid AOI, unusable transform, missing/invalid required source or required field, failed source request/iteration | Stop before publishing results and identify the problem. |
| Returned classification values cannot be interpreted | Stop publication; do not turn the source into a no-hit or publish an assumed economic class. |
| Repairable invalid nonempty source polygon | Repair the analysis copy, retain polygonal components and report repaired IDs/counts; preserve original input data. |
| Null/empty or unrepairable returned geometry, failed overlay, ambiguous overlap beyond the specified tolerance or internal invariant failure | Stop publication with source identifiers and diagnostics. |
| Successful empty retrieval or missing/invalid numeric metric values | Continue where classification remains usable; publish unavailable/partial indicators and coverage as specified in [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values). |
| Intentionally excluded source/criterion | Record out of scope; its absence is not a required-source error. |
| Cancellation | Stop at safe checkpoints; do not report success. Attempt cleanup of partial outputs. |
| File writing or persistence of required result presentation fails | Fail the paired publication and attempt removal of both partial files. Cleanup is not guaranteed after a process crash or an operating-system deletion failure. |

Progress and diagnostic records identify the run and failed stage. Local technical diagnostics and aggregate business-action records serve separate purposes, as documented in [operations](../architecture/operations.md#logging). Failure to write an operational log must not mask the analysis error or unnecessarily prevent using the application. Logs are separate from the durable provenance in successful outputs.

Acceptance includes representative successful and failing runs through both entry points, cancellation, source preservation, reload/unload and Finnish/English presentation. Pending interactive and provider checks remain in the [verification register](../architecture/open-questions.md).

## WF-08 Local development reference material

- A maintainer or agent can explicitly populate a local reference folder with
  service capabilities, schemas for every required source layer and useful
  provider documents, then read those files offline.
- Keep the downloader, source inventory and instructions in version control;
  downloaded artifacts and retrieval metadata remain ignored local files.
- Repeated runs reuse valid cached files. Refresh is explicit; selection and
  listing let maintainers inspect or retry only part of the inventory.
- Validate downloads before replacement, preserve existing files on failure,
  report failed entries and exit nonzero if any fail while retaining successes.
- Record actual retrieval dates and source/checksum information for completed
  downloads; reused files without retrieval metadata keep capture dates unspecified.
- Support an optional local SYKE identifier without adding it to the committed
  inventory or recorded request URLs. Downloaded provider content remains local.
- This caches reference descriptions rather than analysis feature data. Schema
  availability does not certify values, interpretation or geographic coverage.
- Commands, formats, exact inventory and verification belong in
  [development](../architecture/development.md#local-provider-references) and
  [reference instructions](../references/README.md).
