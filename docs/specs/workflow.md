# Workflow specification

Scope and status follow the [specification index](README.md). These requirements describe user-observable behavior; [architecture](../architecture/overview.md), [source contracts](../architecture/source-layer-requirements.md) and [development](../architecture/development.md) own implementation details.

## WF-01 Installation and runtime

- Distribute an experimental QGIS plugin with its declared compatibility visible before installation. The current target is QGIS 3.44 and newer 3.x/4.x releases; 3.44.0 and 4.2.3 are the verification baselines. Intervening and newer releases require their own runtime checks. Packaged metadata owns the precise installation range.
- During development, only the current plugin's project setup, configuration and output formats are supported. Earlier plugin releases have no backward compatibility or migration guarantee; create a fresh setup and rerun the analysis when needed.
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
- Setup creates or reuses localized Results, References and Basemaps groups. Results draw above References, which draw above Basemaps; custom drawing order must not defeat this arrangement.
- Basemaps contains Orthophoto, Topographic map and OpenStreetMap, in that order (Finnish: Ortokuva, Maastokartta, OpenStreetMap). MML layers use the ETRS-TM35FIN versions and the saved MML API key. When Topographic map is first added, it is the only visible managed basemap, including in existing OSM-only projects. Later setup preserves user visibility choices, restores managed order and reuses layer identities. Unavailable basemaps are reported without preventing analysis with valid required sources. Basemaps are display context only and never enter analysis snapshots or calculations.
- Repeated setup reuses managed groups/layers without duplicates and relabels them when the QGIS language changes. Stable source identity survives display-name changes.
- Grouping and sorting retain every layer in both the project and layer list after GUI events are processed. Repeating setup recreates missing managed source layers when their services are available.
- Setup requires an MML API key, saved separately from the SYKE identifier. Cancelling or submitting a blank key stops setup before project changes or source requests. A saved key is reused; an invalid key or unavailable parcel service is reported as incomplete setup.
- The saved MML key authenticates all requests made by both context layers, including discovery and conformance, without a second credential prompt for a valid key. Connections use the key as username and an empty password; saved projects retain that username. Repeating setup refreshes existing managed connections to the current key and authentication method.
- References are organized into localized Property boundaries, Forest inventory, Protected areas and Water groups, in that order (Finnish: Kiinteistörajat, Metsävara, Suojelualueet, Vesistö). Setup restores the managed order while preserving user layers and visibility choices.
- Property boundaries contains unfilled red parcel polygons with 1 mm borders (`PalstanSijaintitiedot`), followed by a separate identifier-point layer (`KiinteistotunnuksenSijaintitiedot`). Finnish layer names are Kiinteistörajat and Kiinteistötunnukset. Polygons have no labels; identifier points show only red 20-point `kiinteistotunnuksenEsitysmuoto` text with a white 2 mm buffer and no point symbols. Boundaries are visible at 1:25,000 or closer; identifiers at 1:10,000 or closer. Repeated setup restores presentation and reuses the layers. A failure of either MML layer leaves setup incomplete; the eleven WFS analysis inputs remain usable independently of this map context.
- References contain the eleven required layers: three Metsäkeskus products; three SYKE protected-area and wilderness products; one conservation-programme layer; one groundwater layer; and three Ranta10 water products.
- Forest inventory contains habitats, stands and grid, in that order. The grid uses dark green borders with no fill and renders at 1:300 or closer; stands and habitats render at 1:7,763 or closer. Repeated setup restores these scale limits on existing managed layers. Protected areas contains programmes, wilderness, state-owned and private-land areas in that order, all in one consistent rose color with the translucent fill and outline treatment used by groundwater. Water contains groundwater, line rivers, polygon rivers and lakes, in that order. The Ranta10 layers use blue line or polygon symbols and render at 1:7,763 or closer. These display choices never affect analysis availability or calculations.
- Setup permits a blank SYKE application identifier and allows it to be supplied later. When supplied, it is retained in settings and service URLs, including URLs saved with a QGIS project. The user instructions explain the provider's identifier requirements and the consequences for sharing project URLs. Provider terms and technical configuration remain in [data sources](../architecture/data-sources.md).

## WF-03 Source readiness and retrieval

- Only WFS 2.0 analysis sources are supported through the wizard and Processing. Legacy WFS 1.x endpoints are outside the planned scope; there is no protocol downgrade fallback. The MML OGC API Features layer is display context only. [ADR-0010](../architecture/adr/0010-wfs-2-only.md) records the analysis protocol decision and rationale.
- The wizard reads configured sources from References by managed identity; it does not ask users to discover or select source layers. Processing accepts explicit source inputs for repeatable and batch use under the same source policy.
- Managed WFS initialization checks service metadata and provider fields without sample-feature or feature-count downloads. Map reads use the view bounds; analysis reads use the AOI bounds and retrieve all pages. Repeated setup upgrades older managed connection options while retaining layer identity, filters, authentication and visibility choices. A per-response page size must not become a total feature limit.
- Setup discovers/verifies configured feature types and schema information. Before analysis, all eleven sources must have the configured provider/source identity, usable coordinate systems and required provider fields. Existing analysis sources and the two Ranta10 polygon products require polygon geometry; `syke_rantaviiva_line_river` requires line geometry. Report all source-readiness failures together where preflight can collect them.
- Current provider fields determine readiness and interpretation. Match accepted names case-insensitively, ignore extra fields/order and apply the documented alias priority independently for each source. Saved discovery schemas are provenance and cannot override usable provider fields. Exact aliases, fields and value sets belong to [source-layer requirements](../architecture/source-layer-requirements.md).
- Saved discovery properties have a [known XSD parser limitation](../open-questions.md#raw-xsd-metadata-parser). They must not be interpreted as a verified list of fields belonging only to the selected feature type; provider-field readiness remains the current validation authority.
- Retrieve AOI-bounded evidence and clip it exactly. Ordinary WFS reads additionally filter by the actual AOI polygon, including its holes and separate parts, to reduce transferred candidates. The three Ranta10 water reads instead query an AOI footprint expanded by 31 m in EPSG:3067 before transforming it to source CRS; both the bbox and any polygon predicate use that expanded footprint. The extra metre is a conservative candidate margin for the eight-segment 30 m buffer approximation; derived evidence uses exactly 30 m. Buffer source geometry before clipping final water evidence to the AOI, so nearby outside-AOI water is retained and clipping raw water cannot create artificial buffer edges. Multiple selected polygons must remain usable when a service rejects multipart filter geometry; the [retrieval contract](../architecture/data-sources.md#wfs-retrieval-success) defines compatible polygon predicates. Oversized polygon filters retain the bounding-box read and exact local clipping. Keep every response page and record the chosen spatial filter in source coverage. Reuse the retrieved grid for all result pieces rather than requesting each piece separately or downloading the national grid; its snapshot still covers the AOI rather than only the forest stands.
- Cache initialization must not duplicate source evidence in observed counts or retained snapshots.
- Retain original source attributes, identifiers, dates, source identity and clipped snapshots. Distinguish measurement dates from database update dates.
- A successful empty response is different from a request failure. Counts and observed mapped overlaps do not prove complete inventory coverage or absence of an unmapped habitat.

## WF-04 Analysis area and destination

- Support drawing one polygon, choosing polygon features from a project layer, and using the current map extent. Capture the extent and its coordinate system when the run starts.
- Layer selection has an explicit selected-features-only choice. Preserve input features and layers. When the AOI layer is also a configured source and selected-only mode applies, both entry points use one captured set of selected geometries and attributes for that source, retaining clipping and provenance. Later selection or remote-data changes do not alter the wizard's captured run; run metadata retains the selected-only choice.
- Dissolve overlapping AOI features so overlapping boundary inputs are counted once. Validate the area, coordinate transformations, output basename and writable destination before expensive work or publication.
- Use EPSG:3067 spatial outputs and planar hectares. The reporting domain is the analyzed forest within the AOI, as defined in [CL-01](classification.md#cl-01-reporting-domain-and-geometry).
- The wizard remembers the output folder and generates a basename beginning `savonia_responsible_forest_inputs_`. Processing permits an explicit basename. Reject existing paired output names instead of overwriting user files.
- Require an explicit finite positive sawlog stumpage price (€/m³). The wizard accepts two decimal places using the selected locale, starts blank without a saved value, and remembers the last valid entry across projects and restarts. Clearing the current entry prevents a run even when settings contain a previous price. The price control follows the area controls and precedes the output folder.

## WF-05 Wizard interaction

- Open a persistent nonmodal dock beside the map; it opens on the right, allows left/right docking and floating, and redocks to the right.
- The wizard has one analysis page: area mode and status, sawlog stumpage price, output folder and Run. Hiding/closing and reopening the dock preserves its current choices, including the current price text.
- Enable Run only while idle and when the current area mode has a usable AOI, selected-only mode has a usable selection, required sources are configured and locally ready, the current price is valid and the output destination is valid. Refresh readiness after relevant area, selection, extent, source, price and destination changes without feature downloads. Execution still performs complete shared validation.
- Preserve the automatic selected-only choice while a selection exists. If a manually checked selected-only choice loses its selection, keep that choice and disable Run until a selection is restored or the user unchecks it. An automatic choice may clear with an empty selection as before; the displayed area status reflects the resulting mode.
- Hiding the dock leaves a run active. Unloading the plugin requests cancellation and detaches its completion callback before deleting the wizard; a late completion must not update deleted controls or add results to the project.
- Keep map interaction available for drawing and selection. Setup, redock, Help and About work in docked and floating modes.
- Run the same analysis behavior as Processing, report meaningful progress, provide cancellation and show both output paths on success. On success, add the run's results and snapshots to Results as specified in [IO-06](indicators-and-outputs.md#io-06-map-review-and-run-retention).
- Show a concise localized error identifying the failed phase/source and a corrective next step where possible. Detailed diagnostics retain the run context.

## WF-06 Processing and repeatability

- Expose the same AOI, required source, classification, indicator and publication behavior through the Processing Toolbox, batch and model workflows.
- Explicit inputs include the polygon AOI, selected-only option, all eleven source layers including grid cells and three Ranta10 water products, required sawlog stumpage price, output folder and basename. Processing has no silent price default from wizard settings. The technical parameter IDs and execution interface belong to architecture and the installed Processing help.
- Equivalent inputs produce equivalent classes, indicators, coverage and artifacts through both entry points. Return usable output paths and actionable failures to callers.
- Keep input data intact. One entry point must not silently apply a different tier rule, missing-value policy or indicator fallback.

## WF-07 Failure, cancellation and observability

| Condition | Required result |
| --- | --- |
| Invalid AOI, unusable transform, missing/invalid required source or required field, failed source request/iteration, or failed Ranta10 buffer/union/overlay | Stop before publishing results and identify the problem. Water line geometry must be validated and processed as line input, not silently dropped by polygon processing. |
| Missing, nonpositive or non-finite sawlog price | Reject before source retrieval or output mutation in both entry points. |
| Returned protected, habitat or programme classification values cannot be interpreted | Stop publication; do not turn the source into a no-hit or publish an assumed economic class. |
| Individual stand mean age is missing/invalid | Publish an unknown age check; without another positive trigger, Protection and Superprotection remain unknown under [CL-03](classification.md#cl-03-classes-and-evidence-policy). Missing required field names still stop validation. |
| Repairable invalid nonempty source polygon | Repair the analysis copy, retain polygonal components and report repaired IDs/counts; preserve original input data. |
| Null/empty or unrepairable returned geometry, failed overlay, grid-cell conflict/overlap beyond numerical tolerance or internal invariant failure | Stop publication with source identifiers and diagnostics. |
| AOI-clipped forest stands overlap beyond numerical tolerance | Continue with original clipped geometry and duplicate contributions. After successful publication, report a localized completion warning explaining this limit and giving the technical log destination in both entry points. |
| Successful empty retrieval or missing/invalid numeric metric values | Continue where classification remains usable; publish unavailable/partial indicators and coverage as specified in [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values). |
| Intentionally excluded source/criterion | Record out of scope; its absence is not a required-source error. |
| Cancellation | Stop at safe checkpoints; do not report success. Attempt cleanup of partial outputs. |
| File writing or persistence of required result presentation fails | Fail the paired publication and attempt removal of both partial files. Cleanup is not guaranteed after a process crash or an operating-system deletion failure. |

Progress and diagnostic records identify the run and failed stage. Local technical diagnostics and aggregate business-action records serve separate purposes, as documented in [operations](../architecture/operations.md#logging). Failure to write an operational log must not mask the analysis error or unnecessarily prevent using the application. Logs are separate from the durable provenance in successful outputs.

Acceptance includes representative successful and failing runs through both entry points, cancellation, source preservation, reload/unload and Finnish/English presentation. Pending interactive and provider checks remain in the [verification register](../open-questions.md).

## WF-08 Local development reference material

This requirement is maintainer/agent tooling, separate from the planner analysis workflow.

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
  [reference instructions](../references/service-metadata/README.md).
- The inventory can be only partly populated when an entry requires credentials. In particular, MML WMTS capabilities require a separately supplied downloader key; a missing cached entry does not disable the other references. The versioned inventory includes Ranta10 capabilities and schemas for all three configured water feature types. Record [material availability and integrity](../open-questions.md#reference-material-integrity) separately from tooling implementation and live-service verification.


## WF-09 Isolated developer checks

This requirement covers maintainer tooling; planner behavior is unchanged.

- A maintainer can run selected tooling, unit, lint and QGIS checks from one
  local command, with an optional current-version package validation pass.
- A maintainer can prepare either pinned Windows QGIS baseline inside the
  checkout using one setup command. CI and local setup share installer versions,
  launcher names and checksums. Downloads and extracted runtimes stay in ignored
  workspace storage; setup does not run installer actions or change system QGIS
  installations or user profiles.
- Runtime setup verifies cached or new installers against the shared checksum,
  validates the shipped launcher against the pinned QGIS version, and reports
  its absolute path and a usable check command. Repeated setup reuses verified
  downloads and completed extractions. Interrupted or invalid downloads and
  failed extraction/version checks never establish a completed runtime; failures
  return nonzero with corrective guidance and retain extraction diagnostics.
- Tooling/unit checks use plain Python; lint/integration use QGIS Python.
  Required executables and writable test storage are checked before suites run.
- Selecting tooling first verifies actual Markdown and YAML parser imports and
  basic parsing using the selected plain interpreter. Console output and a
  dedicated log identify the interpreter and imported module paths. Missing,
  broken or incomplete packages stop all selected suites before test discovery;
  diagnostics include source-file access errors when available, a dependency
  installation command for that interpreter, and file-permission guidance.
  Other selections do not require these parser dependencies. The hosted tooling
  job uses the same preflight; checks never install packages or repair permissions.
- Selecting lint also checks the Pylint and Astroid modules actually imported
  through that QGIS launcher, reporting their versions and paths on the console
  and in logs. Missing, broken or unsupported stable versions stop preflight
  before suites run, with a dependency-upgrade command for the selected launcher.
  Other selections do not require lint tools.
- QGIS tests use a shared offscreen application with temporary settings,
  profile, authentication and cache storage. Tests do not use or change the
  planner's QGIS settings or credentials. Direct unittest and CI runs share this
  isolation.
- A failed prerequisite or selected check returns nonzero with an actionable
  stage summary. Full stdout/stderr remains in unique ignored local logs.
  Failure summaries include failing unittest names from the complete log; when
  no failure report is available, they identify the last reported test if known.
  Keep generated logs and extracted packages separate from working tickets and specs.
  Focused QGIS runs fail if no tests match their pattern.
- Integration entry-point runs enable Python fault handling before native QGIS
  initialization. Local checks enable it in subprocesses and bound each stage
  with a configurable positive timeout (600 seconds by default). Timeouts stop
  the process tree, return nonzero and retain diagnostics before cleanup.
- Integration logs report the slowest test cases on Python 3.12+ so maintainers
  can identify performance bottlenecks without changing the selected coverage.
- Package validation preserves the plugin version and repeats selected unit
  and QGIS suites against the extracted ZIP. Source checks always use the
  checkout even if installed-plugin overrides were inherited.
- Commands, environment ownership and test boundaries belong to the
  [development guide](../architecture/development.md#local-check-runner).
