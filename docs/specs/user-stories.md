# User stories

This catalogue records the prototype's current user goals.
Stable `US-` IDs identify stories; linked requirement IDs provide their acceptance
criteria.

Unless explicitly marked partial, deferred or retired, stories describe implemented prototype behavior with acceptance limits stated in the [index](README.md#implementation-and-acceptance-status). They do not establish Savonia acceptance.

## Starting and organizing work

| ID | User story | Acceptance |
| --- | --- | --- |
| US-001 | As a planner, I want to open or raise a persistent wizard beside the map and hide/reopen it with my choices retained, so I can move between map work and analysis setup. | [WF-05](workflow.md#wf-05-wizard-interaction) |
| US-002 | As a GIS analyst, I want a separate setup action available in the wizard and plugin menu, so I can prepare sources before analysis, including with the wizard closed. | [WF-02](workflow.md#wf-02-project-setup) |
| US-003 | As a planner, I want localized Results, References and Basemaps in a consistent draw order, with references grouped into property boundaries, forest inventory, protected areas and water, so results remain visible and the project tree is understandable. The Water group orders groundwater, line rivers, polygon rivers and lakes; Ranta10 rivers/lakes use blue symbols and the inclusive Stands display scale. | [WF-02](workflow.md#wf-02-project-setup) |
| US-004 | As a planner, I want each successful run added to Results with its exact clipped inputs, one combined Ranta10 buffer-evidence layer and earlier runs preserved, so I can inspect and compare analyses. | [IO-06](indicators-and-outputs.md#io-06-map-review-and-run-retention) |
| US-005 | As a planner, I want tier/class filtered map views with distinct sensitive, economic and unknown colors and tier switching through layer-tree group visibility, so I can inspect each classification independently. | [IO-06](indicators-and-outputs.md#io-06-map-review-and-run-retention) |
| US-006 | As a GIS analyst, I want the interface, project labels and new outputs to follow QGIS's Finnish/English language choice, so reports and interactions use a consistent language. | [HL-01](help-and-language.md#hl-01-language-selection-and-consistency) |
| US-007 | As a QGIS administrator, I want to use the plugin on QGIS 3.44 or 4.x with compatibility and experimental status visible before installation, so I can choose a suitable QGIS environment. | [WF-01](workflow.md#wf-01-installation-and-runtime) |

## Choosing the area and sources

| ID | User story | Acceptance |
| --- | --- | --- |
| US-008 | As a planner, I want to draw a polygon on the map, so I can analyze an area without an existing boundary layer. | [WF-04](workflow.md#wf-04-analysis-area-and-destination) |
| US-009 | As a planner, I want to use polygons from a project layer, so I can analyze prepared municipality, property or other boundaries. | [WF-04](workflow.md#wf-04-analysis-area-and-destination) |
| US-010 | As a planner, I want to use the current map extent, so I can quickly analyze the area in view. | [WF-04](workflow.md#wf-04-analysis-area-and-destination) |
| US-011 | As a planner, I want an explicit selected-features-only choice, so I can analyze a subset without changing the source layer. | [WF-04](workflow.md#wf-04-analysis-area-and-destination) |
| US-012 | As a planner, I want setup to prepare forest stands in References, so stand polygons supply the analysis units. | [WF-02](workflow.md#wf-02-project-setup) |
| US-013 | As a planner, I want setup to prepare mapped habitats, so Section 10 and other valuable habitats can supply distinct criteria. | [WF-02](workflow.md#wf-02-project-setup), [CL-02](classification.md#cl-02-six-cumulative-tiers) |
| US-014 | As a planner, I want all required protected-area products prepared and checked, so state-owned, private-land and wilderness evidence can inform classification. | [WF-02](workflow.md#wf-02-project-setup), [CL-03](classification.md#cl-03-classes-and-evidence-policy) |
| US-015 | As a planner, I want excluded criteria recorded as out of scope, so their intentional absence is distinguishable from unavailable required evidence. | [CL-04](classification.md#cl-04-exclusions-and-interpretation) |
| US-016 | **Retired on 30 October 2026.** This ID is reserved and will not be reused. | — |
| US-017 | As a planner, I want discovery and validation of required sources and fields, so changed or unusable services are reported before they are misinterpreted. | [WF-03](workflow.md#wf-03-source-readiness-and-retrieval) |
| US-018 | As a planner, I want online-source queries restricted to relevant analysis geometry with complete paging and exact local clipping, including an expanded candidate extent for Ranta10 features whose 30 m buffers can reach the AOI, so unnecessary features are reduced without truncating evidence. | [WF-03](workflow.md#wf-03-source-readiness-and-retrieval) |
| US-019 | As a planner, I want the grid prepared once with dark green borders and no fill, and stands, habitats and Ranta10 water references rendered only at their configured close scales, so detailed display stays practical while analysis works at any map scale. | [WF-02](workflow.md#wf-02-project-setup), [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation) |
| US-020 | As a planner, I want setup to initialize managed sources without sample-feature downloads and upgrade reused connections, so repeated setup and language changes avoid unnecessary data retrieval and duplicate layers. | [WF-02](workflow.md#wf-02-project-setup) |
| US-021 | As a planner, I want to supply a SYKE application identifier during setup and understand where it is retained, so I can configure services and review project URLs before sharing. | [WF-02](workflow.md#wf-02-project-setup) |
| US-022 | As a GIS analyst, I want each source interpreted using its actual provider fields, so casing, stale saved schemas or another source's aliases cannot silently change the evidence. | [WF-03](workflow.md#wf-03-source-readiness-and-retrieval) |
| US-068 | As a planner, I want red parcel boundaries and a separate red identifier-text layer grouped above other references, with boundaries visible at 1:25,000 or closer and identifiers at 1:10,000 or closer, so I can recognize properties without polygon labels or point symbols cluttering the map. | [WF-02](workflow.md#wf-02-project-setup) |
| US-069 | As a planner, I want setup to require and remember my MML API key, authenticate all layer requests without another credential prompt when the key is valid, and stop without changes when I omit it, so the parcel service is configured before project setup proceeds. | [WF-02](workflow.md#wf-02-project-setup) |

## Classifying forest evidence

| ID | User story | Acceptance |
| --- | --- | --- |
| US-023 | As a planner, I want mapped-area criteria to use an explicit hit threshold and only the adopted Ranta10 criterion to use its stated 30 m buffer, so undocumented distances or minor edge discrepancies do not change sensitivity. | [CL-01](classification.md#cl-01-reporting-domain-and-geometry) |
| US-024 | As a planner, I want consistent projected geometry and hectare measurements, so results from different source coordinate systems are comparable. | [CL-01](classification.md#cl-01-reporting-domain-and-geometry), [WF-04](workflow.md#wf-04-analysis-area-and-destination) |
| US-025 | As a planner, I want stands clipped and split at sensitivity boundaries, including the unioned Ranta10 buffer boundary, so sensitive and economic portions are visible without promoting an entire stand except under the explicit Section 10 rule. | [CL-01](classification.md#cl-01-reporting-domain-and-geometry) |
| US-076 | As a planner, I want negligible result fragments excluded with their count and area reported, so numerical remnants do not clutter result rows or summary counts. | [CL-01](classification.md#cl-01-reporting-domain-and-geometry) |
| US-026 | As a planner, I want recognized active protection to trigger sensitivity, so the analysis uses interpretable protection evidence. | [CL-02](classification.md#cl-02-six-cumulative-tiers), [CL-03](classification.md#cl-03-classes-and-evidence-policy) |
| US-027 | As a planner, I want uncertain evidence to remain explicit and failures of any required source, including the three Ranta10 products, to stop publication, so unavailable water is never interpreted as no water or economic forest. | [CL-03](classification.md#cl-03-classes-and-evidence-policy), [WF-07](workflow.md#wf-07-failure-cancellation-and-observability), [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values) |
| US-028 | As a planner, I want every result piece classified for six cumulative tiers, with the riparian criterion included from Balance upward, so I can compare sensitive/economic area over one consistent geometry partition. | [CL-02](classification.md#cl-02-six-cumulative-tiers) |
| US-029 | As a planner, I want a qualifying Section 10 hit to promote the entire clipped parent stand in applicable tiers, so this conservative planning assumption is applied consistently and traceably. | [CL-01](classification.md#cl-01-reporting-domain-and-geometry) |
| US-030 | As a planner, I want groundwater footprints and Ranta10 riparian buffers included from Balance upward, so those intersections inform the agreed sensitivity rules. | [CL-02](classification.md#cl-02-six-cumulative-tiers) |
| US-031 | As a planner, I want programme areas distinguished from established protection, so programme context is retained without asserting legal protection. | [CL-02](classification.md#cl-02-six-cumulative-tiers), [CL-04](classification.md#cl-04-exclusions-and-interpretation) |
| US-032 | As a planner, I want stand overlaps of any size retained with parent flags, technical identifiers and a completion warning, so I can obtain results while understanding duplicate area/timber contributions. | [CL-01](classification.md#cl-01-reporting-domain-and-geometry), [WF-07](workflow.md#wf-07-failure-cancellation-and-observability) |
| US-033 | As a downstream model user, I want spatial inputs kept separate from impact calculations, so the separate value-table model remains responsible for scenario effects. | [CL-04](classification.md#cl-04-exclusions-and-interpretation) |

## Calculating and interpreting indicators

| ID | User story | Acceptance |
| --- | --- | --- |
| US-034 | As a planner, I want the specified forest indicators summarized separately per tier and class, so I can transfer comparable inputs to the value-table model. | [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation) |
| US-035 | As a planner, I want source-classified peatland and natural-mire hectares within analyzed forest with coverage disclosed, so these indicators are available without adding peat/mire sensitivity rules. | [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values) |
| US-036 | As a planner, I want unavailable and partial metrics shown with coverage statuses and blanks, so downstream users can distinguish missing evidence from zero without a separate status or per-value diagnostic interface. | [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values) |
| US-037 | As a planner, I want stand and grid totals as independent estimates, so I can compare them without hidden blending or fallback. | [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation) |
| US-038 | As a planner, I want grid pine, spruce and deciduous volumes weighted by actual valid intersected area, so clipped cells and missing species values are represented correctly. | [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation) |
| US-039 | As a planner, I want age-band shares based on grid mean age with their valid-area denominator and unknown hectares visible, so I can interpret their coverage. | [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation), [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values) |
| US-040 | As a planner, I want partial peat/mire observations reported as lower bounds with unknown area, so incomplete evidence does not appear to be a complete total. | [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values) |
| US-041 | As a planner, I want source-first labels and consistent indicator grouping across maps, tables and notes, so I can find each value and understand its source. | [IO-04](indicators-and-outputs.md#io-04-labels-order-and-precision) |
| US-042 | As a planner, I want land area distinguished from tree basal area in both languages, so unlike measurements cannot be mistaken for one another. | [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-04](indicators-and-outputs.md#io-04-labels-order-and-precision) |
| US-043 | As a planner, I want readable rounded results with full-precision aggregation and coverage retained, so reporting choices do not distort summaries. | [IO-04](indicators-and-outputs.md#io-04-labels-order-and-precision) |
| US-044 | As a planner, I want explanations for differences between species means, grid total and stand total, so I can compare estimates without treating missing data as zero. | [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation), [IO-04](indicators-and-outputs.md#io-04-labels-order-and-precision) |
| US-045 | As a downstream model user, I want the deciduous-volume and sawlog-only pricing scope stated clearly, so I can distinguish the adopted behavior from the original bid/project requirements. | [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values) |

## Exporting, auditing and repeatable runs

| ID | User story | Acceptance |
| --- | --- | --- |
| US-046 | As a planner, I want one polygon result dataset carrying every tier class, criterion check, indicator and piece-local riparian reason, with one combined buffered-evidence layer, so I can inspect and compare all results together. | [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-047 | As a planner, I want an Excel workbook of tier/class indicators, coverage and calculation notes for the new buffer criterion in the existing four-sheet layout, so I can review and share the prepared inputs. | [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-048 | As a planner, I want source and metric coverage, including separate status and retrieval details for all three water products and their derived evidence, in both outputs, so I know which evidence needs investigation. | [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values), [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-049 | As an auditor, I want exact AOI-clipped source snapshots preserved with original attributes and the single derived combined water-buffer evidence, so I can inspect what a run used after online services change. | [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-050 | As an auditor, I want provider, endpoint, feature type, query time, schema/field, CRS and spatial-filter provenance, including the expanded Ranta10 candidate extent and buffer settings, so I can trace the evidence used in a result. | [WF-03](workflow.md#wf-03-source-readiness-and-retrieval), [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-051 | As an auditor, I want measurement and update dates kept distinct and source limitations retained for each Ranta10 product and the derived evidence, so a refreshed service is not mistaken for a newer observation. | [WF-03](workflow.md#wf-03-source-readiness-and-retrieval), [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-052 | As a GIS analyst, I want wizard and Processing runs to use the same eleven-source retrieval, buffer, classification and publication policy, so batch/model results match interactive analyses. | [WF-06](workflow.md#wf-06-processing-and-repeatability) |
| US-053 | As a GIS analyst, I want returned output paths and actionable errors, so automated workflows can detect failure and locate results. | [WF-06](workflow.md#wf-06-processing-and-repeatability), [WF-07](workflow.md#wf-07-failure-cancellation-and-observability) |
| US-054 | As a planner, I want meaningful progress and cancellation with partial-file cleanup, so I can stop work without a failed run being presented as successful. | [WF-07](workflow.md#wf-07-failure-cancellation-and-observability) |
| US-055 | As a planner, I want paired named outputs without overwriting existing files and a remembered output folder, so rerunning does not destroy previous work. | [WF-04](workflow.md#wf-04-analysis-area-and-destination), [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |

## Help, identity and maintenance

| ID | User story | Acceptance |
| --- | --- | --- |
| US-056 | As a user, I want complete local help in my QGIS language, accessible with the wizard closed or floating, so I can recover instructions without internet access. | [HL-01](help-and-language.md#hl-01-language-selection-and-consistency), [HL-02](help-and-language.md#hl-02-offline-help-and-recovery) |
| US-057 | As a GIS analyst, I want Processing help to explain the actual inputs/outputs and open the relevant local manual section, so I can configure standalone runs. | [HL-03](help-and-language.md#hl-03-processing-help) |
| US-058 | As a user reporting a problem, I want installed version, author, source and issue links in About, so I can identify the build and report useful information. | [HL-04](help-and-language.md#hl-04-identity-credits-and-attribution) |
| US-059 | As a user or report recipient, I want clear personal-prototype identity and limitations, so I do not mistake this work for a finalized Savonia-approved tool or result. | [HL-04](help-and-language.md#hl-04-identity-credits-and-attribution) |
| US-060 | As a user, I want complete original licences/notices offline and software credits separate from data credits, so I can inspect the applicable terms. | [HL-04](help-and-language.md#hl-04-identity-credits-and-attribution) |
| US-061 | As a recipient of exported results, I want portable source attribution and provenance, so dataset context travels with the files. | [HL-04](help-and-language.md#hl-04-identity-credits-and-attribution), [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-062 | As a user, I want recognizable icons, translated tooltips and accessible control names with theme fallbacks, so I can identify drawing, browsing, running and docking actions. | [HL-05](help-and-language.md#hl-05-accessible-controls) |
| US-063 | As a QGIS administrator, I want clean plugin reload/unload and a complete installation package, so repeated use does not accumulate duplicate actions or omit local help. | [WF-01](workflow.md#wf-01-installation-and-runtime) |
| US-064 | As a maintainer, I want building the current-version installation ZIP to preserve its version by default, so packaging for review is separate from an explicit version increment. | [WF-01](workflow.md#wf-01-installation-and-runtime) |
| US-065 | As a maintainer or agent, I want one command to cache official source descriptions and provider documents locally, so I can inspect them offline without committing downloaded artifacts. | [WF-08](workflow.md#wf-08-local-development-reference-material) |
| US-066 | As a QGIS user, I want an installable ZIP downloadable from GitHub Releases, so I can install the plugin without building it. | [WF-01](workflow.md#wf-01-installation-and-runtime) |
| US-067 | As a maintainer, I want each push to main to test, build and publish the next minor release, so distribution is automatic and retains the major version. | [WF-01](workflow.md#wf-01-installation-and-runtime) |
| US-070 | As a maintainer, I want reusable pinned runtimes, an isolated dependency bootstrap and one check command with validated imports, isolated QGIS state, timeouts and complete logs, so I can reproduce the development environment and diagnose failures. | [WF-09](workflow.md#wf-09-isolated-developer-checks) |
| US-081 | As a reviewer, I want executed, omitted and blocked verification stages with counts, revision and dirty state in a machine-readable summary, so a passing subset is reported accurately. | [WF-09](workflow.md#wf-09-isolated-developer-checks) |
| US-082 | As an implementation agent, I want a short prepared worktree with exact base/spec/runtime paths and an early Git write check, so I can start isolated work and identify which operations need an authorized owner. | [WF-09](workflow.md#wf-09-isolated-developer-checks) |

## Completing inputs and inspecting results

| ID | User story | Acceptance |
| --- | --- | --- |
| US-071 | As a planner, I want a required remembered sawlog unit price and an explicit Processing price, so my own repeatable assumption appears only where positive sawlog stock is represented. | [WF-04](workflow.md#wf-04-analysis-area-and-destination), [WF-06](workflow.md#wf-06-processing-and-repeatability), [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation) |
| US-072 | As a planner, I want Run enabled only when my current area, selection, sources, price and destination are ready, so incomplete choices cannot start an analysis. | [WF-05](workflow.md#wf-05-wizard-interaction) |
| US-073 | As a planner, I want ordinary source-criterion checks alongside retained detailed reasons, including a piece-local riparian buffer check, so I can inspect sensitivity decisions and distinguish Section 10 parent promotion from direct or buffered footprints. | [CL-03](classification.md#cl-03-classes-and-evidence-policy), [IO-05](indicators-and-outputs.md#io-05-files-and-publication) |
| US-074 | As a planner, I want checked class and snapshot children within initially hidden groups, including the combined buffered water evidence, so one group toggle reveals the views while only All out starts visible. | [IO-06](indicators-and-outputs.md#io-06-map-review-and-run-retention) |
| US-075 | As a planner, I want represented sawlog volume multiplied by my supplied unit price into a separate euro amount, with complete totals and unknown coverage distinguished, so I can inspect calculated sawlog value alongside the €/m³ assumption. | [IO-01](indicators-and-outputs.md#io-01-indicator-catalogue), [IO-02](indicators-and-outputs.md#io-02-weighting-and-aggregation), [IO-03](indicators-and-outputs.md#io-03-unavailable-and-partial-values), [IO-04](indicators-and-outputs.md#io-04-labels-order-and-precision) |
| US-077 | As a planner, I want stands with mean age over 80 years flagged as potential protected areas in Protection and Superprotection, with unknown ages explicit and the parent stand traceable, so I can screen older forest separately from established protection. | [CL-02](classification.md#cl-02-six-cumulative-tiers), [CL-03](classification.md#cl-03-classes-and-evidence-policy) |

## Riparian water evidence

| ID | User story | Acceptance |
| --- | --- | --- |
| US-078 | As a planner, I want the three Ranta10 line-river, polygon-river and lake references set up beneath groundwater in the Water group, so I can inspect the exact water products used by the analysis. | [WF-02](workflow.md#wf-02-project-setup) |
| US-079 | As a planner, I want a fixed 30 m buffer derived before AOI clipping, with outside-AOI candidates retrieved and overlapping buffer ground counted once, so nearby water evidence is applied reproducibly to only affected result pieces. | [WF-03](workflow.md#wf-03-source-readiness-and-retrieval), [CL-01](classification.md#cl-01-reporting-domain-and-geometry), [CL-02](classification.md#cl-02-six-cumulative-tiers) |
| US-080 | As an auditor, I want source-qualified contributing feature references, separate retrieval coverage and buffer assumptions retained with the combined evidence, so the result remains interpretable and traceable. | [IO-05](indicators-and-outputs.md#io-05-files-and-publication), [architecture output schema](../architecture/output-schema.md#supporting-metadata) |
Technical design, module boundaries and verification belong in
[architecture](../architecture/README.md).
