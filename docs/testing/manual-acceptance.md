# Manual testing checklist

Use this guide to test the installed plugin in QGIS and review its outputs in a
browser and Microsoft Excel. It owns repeatable manual procedures. The
[specifications](../specs/README.md) own expected product behavior;
[development](../architecture/development.md) owns build and automated-test
commands; [open questions](../open-questions.md) tracks unresolved
defects, provider questions and planning assumptions.

This is a personal checklist for the repository's sole maintainer. Use the steps
and expected results directly; no manual test reports, status tables, screenshots
or sign-off records are required. Checking the interface is separate from
accepting planning assumptions or establishing provider completeness.

## Choose the scope

- For an installation smoke check, run MT-01–03, MT-06, MT-13, MT-16–17,
  MT-19 and MT-26 in Finnish and English. This covers installation, a successful
  run, result views, saved outputs and local help; it is not full acceptance.
- For full manual acceptance, run every applicable case below. Repeat the
  language-dependent cases in Finnish and English; MT-04 also covers English
  fallback.
- For a focused change, select affected cases and their prerequisites. A focused
  check covers only those interactions and the QGIS version being used.

## Prepare the session

1. Build the current-version ZIP or download the release being reviewed, using
   [packaging instructions](../architecture/development.md#check-packaging-separately).
   Check that the installed version matches the intended ZIP. Use a separate
   QGIS profile so the development checkout cannot supply imports.
2. Check both QGIS 3.44.0 and 4.2.3 baselines. Repeat applicable checks when
   targeting another QGIS release or a different browser/Excel environment.
3. Start with an empty project and disposable output folder. Keep test projects,
   output copies and any debugging artifacts under ignored `.local/<effort>/`
   when working in the repository. Use copies for failure/recovery checks.
4. Prepare a small saved polygon AOI, a polygon layer with at least two selectable
   features, and a positive sawlog price such as 10 €/m³. Reuse the same AOI,
   CRS, selection and price when comparing runs.
5. For online setup/run checks, use authorized provider access and the documented
   MML/SYKE setup. Review saved projects before sharing them because saved
   connections can contain credentials.
6. For controlled numerical and failure cases, arrange known WFS 2.0 fixture
   services/inputs and expected values before testing. Existing
   [workflow fixtures](../../qgis_plugin/tests/qgis/workflow_fixture.py) and
   [regression entry points](../architecture/development.md#regression-seams)
   describe reproducible scenarios, but their automated runner is not a
   persistent service for interactive QGIS. No standalone manual fixture launcher
   is supplied. Checks needing unavailable inputs or credentials can wait until
   those prerequisites are available. Ordinary local GeoPackages do not replace
   the required WFS analysis sources.

Switch QGIS's application language and restart when prompted. Keep the chosen
language unchanged during a run. Reuse the same controlled evidence when
comparing languages, entry points or map scales; live sources may change between
requests. Compare snapshots before attributing a live-result difference to the
plugin.

## Installation, lifecycle and language

Expected behavior: [WF-01/05](../specs/workflow.md#wf-01-installation-and-runtime)
and [HL-01/04/05](../specs/help-and-language.md#hl-01-language-selection-and-consistency).

| ID | Actions | Expected result |
| --- | --- | --- |
| MT-01 | Install the ZIP in the test profile; enable the plugin and inspect Plugin Manager/About. | Installed version matches the intended ZIP; compatibility and experimental status are visible; menus, toolbar and Processing register without errors. |
| MT-02 | Open, hide and reopen the wizard; reload/disable/enable the plugin while idle. | Choices survive hiding/reopening. Reload adds no duplicate actions or Processing providers; disabling removes plugin-owned UI/provider entries. |
| MT-03 | Dock left/right, float, resize and redock; use drawing, folder browsing, setup, Help and About. | Controls stay readable and usable; redock returns right; icons, translated tooltips and accessible names identify actions. Setup is first, separated from redock/Help/About. |
| MT-04 | Test Finnish, English and a non-Finnish/non-English QGIS language, restarting as prompted. Inspect wizard, menus, About and Processing help. | Finnish uses Finnish; other languages use English. QGIS is the sole language setting. Working tool labels have no prototype suffix/banner; identity notices remain in About/metadata/help. |

## Source setup and map context

Expected behavior: [WF-02/03](../specs/workflow.md#wf-02-project-setup).
Use the exact presentation/scales there instead of inventing visual tolerances.
MT-07–08 require live access or an appropriate controlled service.

| ID | Actions | Expected result |
| --- | --- | --- |
| MT-05 | With no saved MML key in the disposable profile, cancel setup or submit a blank key. | Setup stops before project changes or source requests. A failed prerequisite is reported clearly. |
| MT-06 | Run setup from the wizard and from the plugin menu with the wizard closed. Repeat, change visibility, save/reopen the project and repeat after switching language. | Results/References/Basemaps and reference subgroups have the specified order. Eight analysis layers and available context layers are reused without duplicates/lost user layers; language and managed styling/scales update; later visibility choices and identities survive reuse. |
| MT-07 | With an authorized MML key, inspect parcels, identifier text, Orthophoto and Topographic map at their applicable scales. In the test profile also try rejected/replaced keys and retry setup. | Valid keys authenticate discovery and map reads without another credential prompt. Rejected/unavailable services report incomplete context; replacement updates connections. Names, labels, scale visibility and basemap defaults match WF-02. Fixture behavior alone does not establish live access. |
| MT-08 | On fresh/reused projects, observe setup separately from map rendering, then pan/zoom and run a small AOI. Inspect requests/timing if diagnosing a retrieval or responsiveness problem. | Setup avoids sample/count downloads; map reads are view-bounded; analysis retains all pages and exact clipping. Watch for unexpected waits/stalls. Transport/paging behavior needs a request trace or known paged fixture to inspect directly. |

## Inputs and execution

Expected behavior: [WF-04–07](../specs/workflow.md#wf-04-analysis-area-and-destination).

| ID | Actions | Expected result |
| --- | --- | --- |
| MT-09 | Run each AOI mode: drawn polygon, polygon layer and captured map extent. Use selected-only with a nonempty selection, including two separate polygons from the same parcel and an AOI with a hole. | The intended AOI/CRS is captured, both selected parts are retrieved without a multipart WFS filter error, holes remain excluded, inputs remain intact, overlapping AOI polygons are dissolved, and outputs use EPSG:3067. |
| MT-10 | Change selection, manually toggle selected-only, clear/restore selection and change/remove a required source or output destination. | Run readiness updates without feature downloads. A manually selected empty selection disables Run until restored or unchecked; automatic selection handling follows WF-05. |
| MT-11 | Try blank, positive, zero and invalid prices; clear a remembered entry. Test decimal-comma input in Finnish, hide/reopen and restart. Omit the Processing price once. | Only a finite positive current price permits execution. Valid wizard values are remembered; clearing blocks the run. Processing requires its own explicit price. |
| MT-12 | Use writable/unwritable destinations and a conflicting existing output basename through Processing. | Invalid destinations/names fail clearly; existing files are not overwritten and remain unchanged. The wizard remembers its output folder. |
| MT-13 | Complete a wizard run; hide/reopen the dock while it runs and inspect completion. | Progress remains meaningful, the task survives hiding, both output paths are reported, and results are readable. Warnings identify their limitation and diagnostic destination. |
| MT-14 | Run equivalent controlled AOI/source/price inputs through wizard and Processing, then at a different canvas scale. | Classes, values, coverage and snapshots agree semantically. Processing returns usable paths; only the wizard adds grouped project views. Canvas rendering scale does not change calculations. |
| MT-15 | Cancel during a sufficiently long controlled run, both before and after output creation where possible. Separately disable/unload during a run and wait for completion/cancellation. | Cancellation reports no success; partial outputs are cleaned where possible. A late task completion after unload updates no deleted UI and adds no results. |

## Map review and saved results

Expected behavior: [IO-04–06](../specs/indicators-and-outputs.md#io-04-labels-order-and-precision).
Field and metadata definitions: [output schema](../architecture/output-schema.md).
US-005's accepted interaction is switching tier groups in QGIS's layer tree.

| ID | Actions | Expected result |
| --- | --- | --- |
| MT-16 | Expand a completed run. Turn All out off and each other tier on; enable the snapshots group. | Six tier groups contain eighteen checked class views; initially only All out is enabled. Sensitive is red/orange, economic green and unknown grey. Hidden groups reveal checked children when enabled; empty class views are valid. Snapshots remain initially hidden. |
| MT-17 | Open tables/forms/Identify, add the complete classified dataset manually from the GeoPackage, close/reopen the files and save/reopen the project. Compare criterion labels with the output schema in both languages. | Field aliases, order, groups, units, nulls and all six class fields remain readable. Criterion labels follow the shared naming convention without formulas or thresholds. Filtered views share one stored result dataset; every snapshot/view can still be read. |
| MT-18 | Add a second run, inspect both runs and change reference visibility/scale. | Earlier runs and configured sources remain intact; readers and filters stay usable. Results remain above References above Basemaps; presentation changes do not alter saved analysis. |
| MT-19 | Open the workbook in Microsoft Excel, inspect all four localized sheets, save a disposable copy and reopen it. Compare saved calculation definitions with GeoPackage run metadata. | Excel raises no repair warning. Summaries, source coverage, metric coverage and notes are readable with correct units, dates, nulls, attribution and prototype notice. Calculation definitions agree across both formats and with the output schema. Another XLSX reader is useful evidence but does not close Microsoft Excel acceptance. |

## Numerical interpretation and exceptional evidence

Expected behavior: [CL-01–03](../specs/classification.md#cl-01-reporting-domain-and-geometry)
and [IO-01–04](../specs/indicators-and-outputs.md#io-01-indicator-catalogue).
Use controlled inputs with independently calculated expected results for MT-20–25 and MT-30.
The [worked examples](../examples/classified-forest-polygons.md) help interpret
fields; they are not a runnable service or proof that a chosen live AOI has the
required values.

| ID | Actions | Expected result |
| --- | --- | --- |
| MT-20 | Compare known sawlog stock/area with the entered unit price, including zero stock and missing stock. Check piece values and group totals in QGIS/Excel. | €/m³ stays distinct from €. Exact represented m³ × price gives the euro amount, rounded after calculation/summation; zero stock gives zero euros, unknown stock stays blank, incomplete group totals retain known subtotals only in coverage. |
| MT-21 | Inspect independent missing species/age/soil/drainage values and true zeros. Compare results with independently calculated valid-area weights and full-precision summary inputs. | Stand/grid estimates stay separate; species need not sum to grid total. Partial means/shares disclose their own denominators; incomplete peat/mire totals stay blank with observed lower bounds. Rounding and date meanings follow the maintained contracts. |
| MT-22 | Run overlapping stands and inspect flags, warning and log. | Geometry is retained; every affected parent's piece is flagged. Completion explains duplicate area/timber/value contributions. Pairwise overlap totals are not presented as unique ground coverage. |
| MT-23 | Use tiny standalone, multipart and split result polygons below/at/above 0.01 m², a larger polygon whose hectares round to zero, and an all-excluded case. | Final connected polygons of <= 0.01 m² are excluded before summaries; count/area are reported and retained in metadata; source snapshots remain intact. Larger polygons remain. All-excluded runs fail before publication. |
| MT-24 | Trigger a required-source/field failure, uninterpretable classification record, unrepairable geometry or controlled output-write failure. | The failed source/stage and corrective action are understandable and localized. No assumed economic class/valid zero replaces failure, and paired publication leaves no apparently successful partial output. Check original inputs remain unchanged. |
| MT-25 | Compare a successful empty grid response, missing numeric values and an actual provider request/paging failure. Also exercise a repairable returned polygon. | Empty/missing numeric evidence can leave grid metrics unavailable while usable classification completes; a request/iteration failure stops publication. Repair is reported on the analysis copy without modifying source data. |
| MT-30 | Compare stand MEANAGE below, exactly at and above 80 years and SOILTYPE 59, 60, 69 and 70 as returned by the provider, including split stands, missing/invalid values and another positive criterion. Inspect check codes, tier reasons and summaries in both languages. | Numeric strings from the provider's SOILTYPE field are interpreted as codes. Age matches apply to every parent piece in Protection and Superprotection; SOILTYPE 60–69 matches apply to every piece from Balance through Superprotection. Unknown values, positive-trigger precedence and parent IDs follow [CL-02/03](../specs/classification.md#cl-02-six-cumulative-tiers). Active-protection checks stay independent. Use MT-17/19 for shared label and metadata checks. |

## Help, offline use and notices

Expected behavior: [HL-01–05](../specs/help-and-language.md#hl-01-language-selection-and-consistency).

| ID | Actions | Expected result |
| --- | --- | --- |
| MT-26 | Open Help/About with the wizard closed, docked and floating; open Processing Help. Disconnect networking and follow local manual/legal links. | The selected-language manual opens in the system browser, Processing reaches its section, and essential instructions/full legal texts work offline. Online analysis still requires connectivity. |
| MT-27 | In the disposable installation, temporarily make a manual unavailable; separately arrange a controlled browser-launch failure when practical and restore the environment afterward. | A localized actionable error appears and diagnostics identify the failure. No silent language substitution or false success occurs. |
| MT-28 | Inspect About, Plugin Manager, Processing help, exported provenance/workbook notes and an OSM map. | Author/version, personal-prototype identity, software/data credits and portable attribution are present. Inspect map-visible OSM attribution separately; About credits alone do not establish it. |

## Use the checklist with open questions

Use these checks to investigate the corresponding open questions:

| Open item | Relevant checks | What to examine |
| --- | --- | --- |
| Installed desktop, language and resources | MT-01–06, MT-09–19, MT-26–27 | Check the installed plugin in each applicable language; offscreen tests do not show desktop layout or browser behavior. |
| Result interpretation and edge behavior | MT-16–25, MT-30 | Compare known inputs and independently expected results in QGIS and Excel. |
| MML live context and WFS initialization/query behavior | MT-07–08, MT-14, MT-25 | Try authorized live access and inspect requests when needed. Fixture behavior is separate from live-provider behavior. |
| OSM display/distribution attribution | MT-28 | Look for attribution on the map; tile-policy and licence review remain separate. |
| Section 10 stand-wide planning assumption | Separate planner review | Discuss the register's 10 ha stand/0.2 ha habitat example and intended spatial extent with the planner. Correct rendering alone does not establish that the rule is appropriate. |

The [provider evidence](../open-questions.md#provider-evidence)
questions about representative values, dates, inventory completeness and growth
meaning require provider samples/documentation or expert clarification. The XSD
parser gap requires implementation work. Keep substantive unresolved issues in
the register. When a check reveals a defect, fix it or retain a concise problem
description and useful reproduction steps; individual manual-check results need
no separate tracking.
